"""Selection/metadata checks, never runtime or cryptographic conformance."""

import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profiles_validator", ROOT / "scripts/validate-repo.py")
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ProfileSelectionTests(unittest.TestCase):
    def setUp(self):
        VALIDATOR.ERRORS.clear()
        self.registry = yaml.safe_load((ROOT / "conformance/profiles.yaml").read_text())
        self.profiles = {p["id"]: p for p in self.registry["profiles"]}

    def test_registry_has_only_defined_carrier_bindings(self):
        VALIDATOR.check_profiles()
        self.assertEqual(VALIDATOR.ERRORS, [])
        actual = {p["id"]: (p["carrier"], p["production_allowed"])
                  for p in self.profiles.values() if p["kind"] == "TRANSPORT_PROFILE"}
        self.assertEqual(actual, {"SYNTRA-1.0-TCP": (1, True),
                                  "SYNTRA-1.0-WS": (2, False),
                                  "SYNTRA-1.0-WSS": (3, True)})

    def test_selected_cases_have_exact_carrier_membership(self):
        for pid in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
            with self.subTest(profile=pid):
                cases = VALIDATOR.selected_cases(self.profiles[pid])
                self.assertTrue(cases)
                for case in cases.values():
                    declared = case["profile"]
                    declared = declared if isinstance(declared, list) else [declared]
                    self.assertIn(pid, declared)
                if pid == "SYNTRA-1.0-TCP":
                    self.assertIn("CONF-SCT-001", cases)
                    for cid in ("CONF-SCW-001", "CONF-SCW-004", "CONF-SCW-005",
                                "CONF-SCW-007", "CONF-SCW-017"):
                        self.assertNotIn(cid, cases)
                else:
                    self.assertIn("CONF-SCW-005", cases)
        # No capability-free event selection may enable the recovery gate.
        core = VALIDATOR.selected_cases(self.profiles["SNTR-CORE-V1"])
        self.assertNotIn("CONF-URP-001", core)
        self.assertFalse(any(c["capabilities"] for c in core.values()))

    def test_selection_cannot_load_noncurrent_manifests(self):
        profile = copy.deepcopy(self.profiles["SYNTRA-1.0-TCP"])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "noncurrent.yaml").write_text("selection_status: unselected_archive\ncases: []\n")
            profile["manifests"] = ["noncurrent.yaml"]
            with self.assertRaisesRegex(ValueError, "non-current manifest"):
                VALIDATOR.selected_cases(profile, base=base)

    def test_selector_empty_capabilities_is_an_exact_filter(self):
        profile = {"id": "SNTR-CORE-V1", "manifests": [{"path": "cases.yaml", "select": {
            "mandatory": True, "capabilities": [], "profile": "SNTR-CORE-V1"}}]}
        cases = [
            {"id": "CONF-TEST-001", "profile": ["SNTR-CORE-V1", "SNTR-RPC-V1"], "mandatory": True, "capabilities": []},
            {"id": "CONF-TEST-002", "profile": "SNTR-CORE-V1", "mandatory": True, "capabilities": ["syntra.update-recovery/1"]},
            {"id": "CONF-TEST-003", "profile": "SNTR-CORE-V1", "mandatory": False, "capabilities": []},
            {"id": "CONF-TEST-004", "profile": "SNTR-RPC-V1", "mandatory": True, "capabilities": []},
        ]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "cases.yaml").write_text(yaml.safe_dump({"cases": cases}))
            selected = VALIDATOR.selected_cases(profile, base=base, capabilities=["syntra.update-recovery/1"])
        self.assertEqual(set(selected), {"CONF-TEST-001"})

    def test_string_mandatory_filter_cannot_silently_drop_core_event_probes(self):
        selected = VALIDATOR.selected_cases(self.profiles["SNTR-CORE-V1"])
        self.assertLessEqual({"CONF-EVT-002", "CONF-EVT-014"}, selected.keys())
        profile = copy.deepcopy(self.profiles["SNTR-CORE-V1"])
        event_ref = next(ref for ref in profile["manifests"] if isinstance(ref, dict))
        event_ref["select"]["mandatory"] = "true"
        with self.assertRaisesRegex(ValueError, "mandatory.*boolean"):
            VALIDATOR.selected_cases(profile)
        registry = copy.deepcopy(self.registry)
        registry["profiles"][0] = profile
        self.assertIn("mandatory must be boolean", self.check_registry_fixture(registry))

    def test_malformed_selectors_are_rejected_before_case_matching(self):
        invalid = [
            None, [], "mandatory", {"unknown": True},
            {"mandatory": 1}, {"mandatory": 0}, {"mandatory": None}, {"mandatory": []},
            {"capabilities": "syntra.update-recovery/1"},
            {"capabilities": None}, {"capabilities": [["syntra.update-recovery/1"]]},
            {"capabilities": ["undefined-capability"]},
            {"profile": ["SNTR-CORE-V1"]}, {"profile": None},
            {"profile": "SNTR-UNDEFINED-V1"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "empty.yaml").write_text("cases: []\n")
            for selector in invalid:
                with self.subTest(selector=selector), self.assertRaises(ValueError):
                    VALIDATOR.selected_cases({"id": "SNTR-CORE-V1", "manifests": [
                        {"path": "empty.yaml", "select": selector}]}, base=base)

    def test_profile_filter_must_resolve_in_the_supplied_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "empty.yaml").write_text("cases: []\n")
            profile = {"id": "SNTR-CORE-V1", "manifests": [{"path": "empty.yaml", "select": {
                "profile": "SNTR-RPC-V1"}}]}
            with self.assertRaisesRegex(ValueError, "known registered profile"):
                VALIDATOR.selected_cases(profile, base=base, registered_profiles={"SNTR-CORE-V1"})
            self.assertEqual(VALIDATOR.selected_cases(profile, base=base,
                             registered_profiles={"SNTR-CORE-V1", "SNTR-RPC-V1"}), {})

    def test_manifest_reference_shape_and_containment_are_validated(self):
        invalid = [None, 1, [], {}, {"path": "cases.yaml"}, {"select": {}},
                   {"path": "cases.yaml", "select": {}, "extra": True},
                   {"path": None, "select": {}}, {"path": [], "select": {}}, "", " ", "/absolute.yaml",
                   "../outside.yaml", "nested/../../outside.yaml", "C:\\outside.yaml",
                   {"path": "../outside.yaml", "select": {}}]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for ref in invalid:
                with self.subTest(ref=ref), self.assertRaises(ValueError):
                    VALIDATOR.selected_cases({"id": "SNTR-CORE-V1", "manifests": [ref]}, base=base)
            for refs in (None, [], "cases.yaml", {"path": "cases.yaml"}):
                with self.subTest(manifests=refs), self.assertRaises(ValueError):
                    VALIDATOR.selected_cases({"id": "SNTR-CORE-V1", "manifests": refs}, base=base)

    def test_manifest_reference_cannot_follow_a_symlink_outside_its_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "conformance"
            base.mkdir()
            outside = root / "outside.yaml"
            outside.write_text("cases: []\n")
            (base / "escape.yaml").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "within the conformance directory"):
                VALIDATOR.selected_cases({"id": "SNTR-CORE-V1", "manifests": ["escape.yaml"]}, base=base)

    def check_registry_fixture(self, registry):
        VALIDATOR.ERRORS.clear()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "conformance").mkdir()
            (root / "conformance/profiles.yaml").write_text(yaml.safe_dump(registry))
            # Keep real fixture paths, but point registry discovery at this
            # disposable root. No working-tree file is changed by these tests.
            select = VALIDATOR.selected_cases
            def select_real(profile, **kwargs):
                return select(profile, base=ROOT / "conformance", **kwargs)
            with (mock.patch.object(VALIDATOR, "ROOT", root),
                  mock.patch.object(VALIDATOR, "selected_cases", side_effect=select_real)):
                VALIDATOR.check_profiles()
        return "\n".join(VALIDATOR.ERRORS)

    def test_every_current_selector_registration_is_required(self):
        for pid in self.profiles:
            registry = copy.deepcopy(self.registry)
            registry["profiles"] = [p for p in registry["profiles"] if p["id"] != pid]
            with self.subTest(missing=pid):
                self.assertIn(pid, self.check_registry_fixture(registry))

    def test_selector_kind_and_duplicate_registrations_are_rejected(self):
        for pid in self.profiles:
            registry = copy.deepcopy(self.registry)
            profile = next(p for p in registry["profiles"] if p["id"] == pid)
            profile["kind"] = "OPTIONAL_CAPABILITY" if profile["kind"] != "OPTIONAL_CAPABILITY" else "MANDATORY_CORE"
            with self.subTest(wrong_kind=pid):
                self.assertIn("kind", self.check_registry_fixture(registry))
        registry = copy.deepcopy(self.registry)
        registry["profiles"].append(copy.deepcopy(registry["profiles"][0]))
        self.assertIn("duplicate", self.check_registry_fixture(registry))

    def test_registry_reports_malformed_yaml_and_shapes(self):
        for text in ("profiles: [", "null\n", "profiles: null\n", "profiles: {}\n",
                     "profiles: [null, 7, {id: []}]\n"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "conformance").mkdir()
                (root / "conformance/profiles.yaml").write_text(text)
                VALIDATOR.ERRORS.clear()
                with mock.patch.object(VALIDATOR, "ROOT", root):
                    VALIDATOR.check_profiles()
                self.assertTrue(VALIDATOR.ERRORS)

    def test_registry_reports_malformed_selected_manifest_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "conformance"
            base.mkdir()
            registry = copy.deepcopy(self.registry)
            for profile in registry["profiles"]:
                profile["manifests"] = ["bad.yaml"]
            (base / "profiles.yaml").write_text(yaml.safe_dump(registry))
            (base / "bad.yaml").write_text("cases: [")
            VALIDATOR.ERRORS.clear()
            with mock.patch.object(VALIDATOR, "ROOT", root):
                VALIDATOR.check_profiles()
            self.assertTrue(VALIDATOR.ERRORS)

    def test_noise_pin_rotation_is_selected_for_all_carriers(self):
        for pid in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
            with self.subTest(profile=pid):
                cases = VALIDATOR.selected_cases(self.profiles[pid])
                self.assertIn("CONF-SCW-038", cases.keys())
                self.assertNotIn("valid_chain", cases["CONF-SCW-038"]["preconditions"])

    def test_fragmented_handshake_has_no_unconditional_tls_precondition(self):
        for pid in ("SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
            with self.subTest(profile=pid):
                cases = VALIDATOR.selected_cases(self.profiles[pid])
                self.assertNotIn("valid_chain", cases["CONF-SCW-021"]["preconditions"])

    def test_upgrade_cases_are_profile_specific_with_numeric_carriers(self):
        upgrades = {}
        for pid, cid in (("SYNTRA-1.0-WS", "CONF-SCW-001"),
                         ("SYNTRA-1.0-WSS", "CONF-SCW-043")):
            with self.subTest(profile=pid):
                cases = VALIDATOR.selected_cases(self.profiles[pid])
                upgrades[pid] = {key for key in ("CONF-SCW-001", "CONF-SCW-043") if key in cases}
                self.assertEqual(upgrades[pid], {cid})
                case = cases[cid]
                self.assertEqual(case["profile"], pid)
                self.assertEqual(case["input"]["transport"]["carrier"], self.profiles[pid]["carrier"])
        manifest = yaml.safe_load((ROOT / "conformance/manifest/connection.yaml").read_text())
        self.assertEqual(manifest["profile"], ["SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"])
        matrix = yaml.safe_load((ROOT / "conformance/interoperability/matrix.yaml").read_text())
        for pair in matrix["pairs"]:
            for leg in pair["legs"]:
                for cid in ("CONF-SCW-001", "CONF-SCW-043"):
                    if cid in leg.get("cases", []):
                        self.assertIn(cid, upgrades[leg["transport"]])

    def test_recovery_selection_requires_its_allocated_gate(self):
        profile = self.profiles["SNTR-EVENTS-V1"]
        without = VALIDATOR.selected_cases(profile)
        with_recovery = VALIDATOR.selected_cases(profile, capabilities=["syntra.update-recovery/1"])
        self.assertIn("CONF-EVT-014", without)
        self.assertNotIn("CONF-URP-001", without)
        self.assertIn("CONF-URP-001", with_recovery)
        self.assertIn("CONF-URP-011", with_recovery)
        self.assertEqual(profile["capabilities"], ["syntra.update-recovery/1"])
        schema = yaml.safe_load((ROOT / "conformance/manifest/schema.yaml").read_text())["schema"]
        self.assertEqual(set(schema["capability_id"]["enum"]), VALIDATOR.KNOWN_CAPABILITIES)
        self.assertEqual(schema["test_case"]["fields"]["capabilities"]["item"],
                         {"$ref": "#/schema/capability_id"})
        self.assertEqual(schema["declaration_file"]["fields"]["capabilities"]["item"],
                         {"$ref": "#/schema/capability_id"})
        for selected in (without, with_recovery):
            self.assertNotIn("CONF-SESS-R01", selected)
            self.assertFalse(any(cid.startswith(("CONF-HTTP-", "CONF-HTTPS-")) for cid in selected))

    def test_terminal_receipt_selection_preserves_refusal_on_every_carrier_and_role(self):
        """Check definition selection, not host enablement or runtime verdicts."""
        shared = {f"CONF-TRC-{n:03d}" for n in range(1, 14)}
        for suite in ("SNTR-CORE-V1", "SNTR-RPC-V1"):
            # Without a carrier, the selector inventories all definitions.
            inventory = VALIDATOR.selected_cases(self.profiles[suite])
            self.assertEqual({cid for cid in inventory if cid.startswith("CONF-TRC-")},
                             shared | {"CONF-TRC-014"})
            # Preserve broad default applicability, especially mandatory refusal;
            # the selector does not itself apply the runner's coarse-family gate.
            for cid in shared | {"CONF-TRC-014"}:
                self.assertNotIn("applicable_transports", inventory[cid])
                if cid in shared:
                    self.assertNotIn("applicable_profiles", inventory[cid])
            self.assertEqual(inventory["CONF-TRC-014"]["applicable_profiles"], ["SYNTRA-1.0-TCP"])
            for carrier in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
                selected = VALIDATOR.selected_cases(self.profiles[suite], carrier_profile=carrier)
                expected = shared | ({"CONF-TRC-014"} if carrier == "SYNTRA-1.0-TCP" else set())
                # Roles are gated after profile selection, as the runner contract requires.
                for role in ("client", "server"):
                    with self.subTest(suite=suite, carrier=carrier, role=role):
                        cases = {cid: case for cid, case in selected.items()
                                 if cid.startswith("CONF-TRC-") and role in case["roles"]}
                        self.assertEqual(set(cases), expected)
                        self.assertEqual({cid for cid, case in cases.items() if case["mandatory"]},
                                         {"CONF-TRC-001"})
                        for case in cases.values():
                            self.assertEqual(case["capabilities"], [])
                            self.assertIn("NOT_EXECUTED", case["notes"])
                            self.assertNotIn("verdict", case)
                            self.assertNotIn("results", case)

    def test_schema_uses_numeric_case_ids_in_all_reference_positions(self):
        schema = yaml.safe_load((ROOT / "conformance/manifest/schema.yaml").read_text())["schema"]
        pattern = re.compile(schema["case_id"]["pattern"])
        for value in ("CONF-SESS-001", "CONF-CORE-001", "CONF-SCT-006"):
            self.assertIsNotNone(pattern.fullmatch(value))
            self.assertIsNotNone(VALIDATOR.CASE_ID.fullmatch(value))
        for value in ("CONF-SESS-R01", "CONF-SESS-R02", "CONF-SESS-R01x", "CONF-SESS-X01"):
            self.assertIsNone(pattern.fullmatch(value))
            self.assertIsNone(VALIDATOR.CASE_ID.fullmatch(value))
        self.assertEqual(schema["test_case"]["fields"]["id"], {"$ref": "#/schema/case_id"})
        self.assertEqual(schema["requirement_entry"]["fields"]["test_ids"]["item"],
                         {"$ref": "#/schema/case_id"})
        self.assertEqual(schema["declaration_file"]["fields"]["results"]["item"]["fields"]["test_id"],
                         {"$ref": "#/schema/case_id"})

    def test_context_positive_probes_cover_both_modes_for_actual_carrier(self):
        vectors = json.loads((ROOT / "conformance/test-vectors/connection/context-vectors.json").read_text())
        vectors = {v["id"]: v for v in vectors["contexts"]}
        for pid, cid in (("SYNTRA-1.0-TCP", "CONF-SCT-001"),
                         ("SYNTRA-1.0-WS", "CONF-SCS-001"),
                         ("SYNTRA-1.0-WSS", "CONF-SCW-002")):
            profile = self.profiles[pid]
            case = VALIDATOR.selected_cases(profile)[cid]
            self.assertEqual(case["input"]["transport"]["action"], "channel_handshake")
            probes = [vectors[v] for v in case["input"]["transport"]["contexts"]]
            self.assertEqual({v["carrier"] for v in probes}, {profile["carrier"]})
            self.assertEqual({v["mode"] for v in probes}, {1, 2})

    def test_context_negative_probes_use_carrier_matched_bases(self):
        data = json.loads((ROOT / "conformance/test-vectors/connection/context-vectors.json").read_text())
        vectors = {v["id"]: v for v in data["contexts"]}
        recipes = {r["id"]: r for r in data["negative_recipes"]}
        original = {recipes[f"SYNTRA-N{n:02d}"]["mutation"]:
                    recipes[f"SYNTRA-N{n:02d}"]["detail"] for n in range(1, 13)}
        for pid in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
            cases = VALIDATOR.selected_cases(self.profiles[pid])
            probes = [c["input"]["transport"] for c in cases.values()
                      if c["input"].get("transport", {}).get("action") == "channel_context_negatives"]
            self.assertEqual(len(probes), 1)
            selected = [recipes[r] for r in probes[0]["recipes"]]
            self.assertCountEqual([r["mutation"] for r in selected], original)
            for recipe in selected:
                with self.subTest(profile=pid, recipe=recipe["id"]):
                    base = vectors[recipe["base"]]
                    self.assertEqual(base["carrier"], self.profiles[pid]["carrier"])
                    self.assertEqual(recipe["detail"], original[recipe["mutation"]])
                    if recipe["mutation"] == "bootstrap-epoch":
                        self.assertEqual((base["mode"], base["epoch"]), (1, 0))
                    elif recipe["mutation"] == "returning-handle":
                        self.assertEqual(base["mode"], 2)
                        self.assertNotEqual(bytes.fromhex(base["handle_hex"]), bytes(8))
                    elif recipe["mutation"] == "invalid-utf8":
                        self.assertEqual(len(base["scope"].encode("utf-8")), 1)
                    elif recipe["mutation"] == "scope-byte-length":
                        self.assertEqual(base["scope"].encode("utf-8"), bytes.fromhex("c3a9"))

    def test_preready_principal_mismatch_probes_cover_both_directions(self):
        for pid in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
            cases = VALIDATOR.selected_cases(self.profiles[pid])
            forward = cases["CONF-SCW-030"]["input"]["transport"]
            self.assertEqual(forward["enrollment_principal"], "principal-a")
            self.assertEqual(forward["application_principal"], "principal-b")
            probes = [c for c in cases.values()
                      if c["input"].get("transport", {}).get("action") == "channel_binding_mismatch"]
            directions = set()
            for case in probes:
                transport = case["input"]["transport"]
                directions.add((transport["enrollment_principal"], transport["application_principal"]))
                self.assertEqual(case["requirement"], ["SNTR-DAUTH-016"])
                self.assertEqual(case["expected"], cases["CONF-SCW-030"]["expected"])
                self.assertEqual(case["preconditions"], cases["CONF-SCW-030"]["preconditions"])
            self.assertEqual(directions, {("principal-a", "principal-b"),
                                          ("principal-b", "principal-a")})

    def test_tls_cases_are_wss_only_and_template_has_no_pass_claim(self):
        security = yaml.safe_load((ROOT / "conformance/manifest/security.yaml").read_text())
        tls = [c for c in security["cases"]
               if c["input"].get("transport", {}).get("action") == "tls_handshake"]
        self.assertTrue(tls)
        self.assertIn("test-pki-untrusted", {c["input"]["transport"].get("pki") for c in tls})
        self.assertIn("test-pki-wrong-san", {c["input"]["transport"].get("pki") for c in tls})
        self.assertIn("TLS1_2_only", {c["input"]["transport"].get("version") for c in tls})
        for case in tls:
            self.assertEqual(case["applicable_profiles"], ["SYNTRA-1.0-WSS"])
        for pid in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"):
            cases = VALIDATOR.selected_cases(self.profiles["SNTR-CORE-V1"], carrier_profile=pid)
            for case in tls:
                self.assertEqual(case["id"] in cases, pid == "SYNTRA-1.0-WSS")
        declaration = yaml.safe_load((ROOT / "conformance/declaration.example.yaml").read_text())
        self.assertEqual(declaration["verdict_summary"]["PASS"], 0)
        self.assertTrue(all(r["verdict"] == "NOT_EXECUTED" for r in declaration["results"]))


if __name__ == "__main__":
    unittest.main()
