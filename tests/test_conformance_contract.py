"""Candidate contract metadata/fixture checks; no runtime execution verdicts."""

import base64
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("contract_validator", ROOT / "scripts/validate-repo.py")
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
SYNC_SPEC = importlib.util.spec_from_file_location("contract_owner_sync", ROOT / "scripts/sync-conformance-owners.py")
assert SYNC_SPEC is not None and SYNC_SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SYNC_SPEC)
SYNC_SPEC.loader.exec_module(SYNC)


class ConsolidatedContractTests(unittest.TestCase):
    def test_current_registry_and_case_references_validate(self):
        V.ERRORS.clear()
        V.check_requirements()
        V.check_manifests()
        self.assertEqual(V.ERRORS, [])

    def test_only_current_conformance_assets_are_present(self):
        for name in ("archived-profiles.yaml", "archived-requirements.yaml"):
            self.assertFalse((ROOT / "conformance" / name).exists())
        self.assertFalse(list((ROOT / "conformance/manifest").glob("transport-*.yaml")))
        for family in ("http", "websocket"):
            self.assertFalse(list((ROOT / "conformance/test-vectors" / family).glob("*")))
        self.assertFalse((ROOT / "compatibility/syntra-1.0-requirement-inventory.json").exists())
        cases, _ = V.load_manifest_cases()
        self.assertNotIn("CONF-SESS-R01", cases)
        for case in cases.values():
            self.assertLessEqual(set(case[1]["capabilities"]), {"syntra.update-recovery/1"})

    def test_suffix_is_preserved_in_every_requirement_parser(self):
        text = "**SNTR-SER-008**, **SNTR-SER-008A** and **SNTR-TEST-123AB — historical heading**"
        expected = ["SNTR-SER-008", "SNTR-SER-008A", "SNTR-TEST-123AB"]
        self.assertEqual(V.REQ_PATTERN.findall(text), expected)
        self.assertEqual(V.BOLD_DEF.findall(text), expected)
        self.assertEqual(SYNC.DEFINITION.findall(text), expected)
        schema = yaml.safe_load((ROOT / "conformance/manifest/schema.yaml").read_text())["schema"]
        patterns = [V.REQ_NAMING,
                    re.compile(schema["requirement_entry"]["fields"]["requirement_id"]["pattern"]),
                    re.compile(schema["test_case"]["fields"]["requirement"]["item"]["pattern"])]
        for pattern in patterns:
            for rid in expected:
                self.assertIsNotNone(pattern.fullmatch(rid))
            self.assertIsNone(pattern.fullmatch("SNTR-SER-008a"))
        rows = {r["requirement_id"]: r for r in V.load_requirements()}
        self.assertNotEqual(rows["SNTR-SER-008"], rows["SNTR-SER-008A"])
        self.assertIn("CONF-CORE-011", rows["SNTR-SER-008A"]["test_ids"])

    def test_current_profile_vocabulary_has_no_path_whitelist(self):
        meta = json.loads((ROOT / "compatibility/syntra-1.0.json").read_text())
        self.assertNotIn("historical_profile_references", meta)
        self.assertNotIn("owner_mapping", meta)
        for path in ("specifications/transports.md", "conformance/profiles.yaml",
                     "specifications/decisions/ADR-001.md"):
            self.assertFalse(V.profile_reference_known("SNTR-UNDEFINED-V1", path))
        for path in ("rfcs/0001-history.md", "specifications/decisions/ADR-001.md",
                     "docs/decisions/0001-history.md", "audits/review.md", "GOVERNANCE.md"):
            self.assertFalse(V.is_current_reference_path(path))
        for path in ("conformance/README.md", "specifications/security.md",
                     "docs/schema-tooling.md", "proto/syntra/v1/envelope.proto"):
            self.assertTrue(V.is_current_reference_path(path))

    def test_binding_policy_selects_current_cases(self):
        registry = yaml.safe_load((ROOT / "conformance/profiles.yaml").read_text())
        bindings = [p for p in registry["profiles"] if p["kind"] == "TRANSPORT_PROFILE"]
        selected = {p["id"]: V.selected_cases(p) for p in bindings}
        self.assertIn("CONF-SCT-006", selected["SYNTRA-1.0-TCP"])
        self.assertIn("CONF-SCS-002", selected["SYNTRA-1.0-WS"])
        self.assertIn("CONF-SCW-038", selected["SYNTRA-1.0-WSS"])
        policy = yaml.safe_load((ROOT / "conformance/manifest/binding-policy.yaml").read_text())
        cases = {c["id"]: c for c in policy["cases"]}
        self.assertLessEqual({"CONF-BIND-001", "CONF-BIND-002", "CONF-BIND-003",
                              "CONF-BUDGET-001", "CONF-BUDGET-002"}, cases.keys())
        for pid in ("SYNTRA-1.0-TCP", "SYNTRA-1.0-WSS"):
            for cid in ("CONF-BIND-001", "CONF-BIND-002", "CONF-BIND-003"):
                self.assertIn(pid, cases[cid]["profile"])
                self.assertNotIn("SYNTRA-1.0-WS", cases[cid]["profile"])
        self.assertIn([], cases["CONF-BIND-001"]["input"]["transport"]["invalid_sets"])
        self.assertIn(["undefined-binding"], cases["CONF-BIND-001"]["input"]["transport"]["invalid_sets"])
        self.assertEqual(cases["CONF-BUDGET-001"]["input"]["transport"]["hard_maximum_ms"], 15000)
        self.assertEqual(cases["CONF-BUDGET-002"]["input"]["transport"]["hard_maximum_ms"], 5000)
        self.assertTrue(all("verdict" not in c and "results" not in c for c in cases.values()))

    def test_recovery_completion_has_wrapper_and_bare_control_is_rejected(self):
        cases = yaml.safe_load((ROOT / "conformance/manifest/recovery.yaml").read_text())["cases"]
        bare = bytes.fromhex("0801120868616e646c652d411807220142")
        for cid in ("CONF-URP-011", "CONF-URP-012"):
            case = next(c for c in cases if c["id"] == cid)
            payload = next(f["payload_b64"] for f in case["expected"]["frames"] if f["body"] == "notification")
            raw = base64.b64decode(payload, validate=True)
            self.assertEqual(V.check_replay_complete_fixture(raw), bare)
            self.assertNotEqual(raw, bare)
        for raw in (bare, b"\x08\x01", b"\x08\x01\x12\x00"):
            with self.assertRaises(ValueError):
                V.check_replay_complete_fixture(raw)

    def test_first_hello_expects_only_host_ready_response(self):
        manifest = yaml.safe_load((ROOT / "conformance/manifest/connection.yaml").read_text())
        case = next(c for c in manifest["cases"] if c["id"] == "CONF-SCW-011")
        self.assertEqual(case["expected"]["frames"], [{"request_id": 0, "body": "ready"}])

    def test_version_rejection_does_not_require_a_ws_close_code(self):
        manifest = yaml.safe_load((ROOT / "conformance/manifest/core.yaml").read_text())
        case = next(c for c in manifest["cases"] if c["id"] == "CONF-CORE-005")
        self.assertEqual(case["expected"]["connection_state"], "CLOSED")
        self.assertEqual(case["expected"]["frames"], [])
        ws = case["expected"]["transport"]["peer_observation"]["ws_wss"]
        self.assertEqual(ws["signal"], "ws_close")
        self.assertNotIn("close_code", ws)

    def test_successful_inner_stream_probes_use_valid_envelope_sizes(self):
        cases, _ = V.load_manifest_cases()
        for cid in ("CONF-SCW-010", "CONF-SCT-005"):
            with self.subTest(case=cid):
                transport = cases[cid][1]["input"]["transport"]
                self.assertEqual(transport["frame_bytes"], [32, 1048576])
                self.assertNotIn(1, transport["frame_bytes"])

    def check_requirement_rows(self, rows):
        V.ERRORS.clear()
        definitions = {"SNTR-RPC-002": [(Path("specifications/rpc.md"), 1, "RPC")]}
        cases = {"CONF-RPC-001": ("fixture.yaml", {"requirement": ["SNTR-RPC-002"]}),
                 "CONF-RPC-002": ("fixture.yaml", {"requirement": ["SNTR-RPC-008"]})}
        with (mock.patch.object(V.OWNERS, "owner_definitions", return_value=definitions),
              mock.patch.object(V, "load_requirements", return_value=rows),
              mock.patch.object(V, "load_manifest_cases", return_value=(cases, []))):
            V.check_requirements()
        return "\n".join(V.ERRORS)

    def test_traceability_rejects_nonreciprocal_edges_without_inventing_coverage(self):
        row = {"requirement_id": "SNTR-RPC-002", "specification": "specifications/rpc.md",
               "section": "RPC", "test_ids": ["CONF-RPC-001"], "automation_status": "automated"}
        self.assertEqual(self.check_requirement_rows([row]), "")
        row["test_ids"] = ["CONF-RPC-002"]
        self.assertIn("without a reciprocal", self.check_requirement_rows([row]))
        row.update(test_ids=[], automation_status="manual", notes="Review needed; no executable case covers this rule.")
        self.assertEqual(self.check_requirement_rows([row]), "")
        row.pop("notes")
        self.assertIn("explanatory notes", self.check_requirement_rows([row]))

    def test_stale_row_is_not_accepted_as_a_definition(self):
        row = {"requirement_id": "SNTR-REMOVED-001", "specification": "specifications/rpc.md",
               "section": "RPC", "test_ids": [], "automation_status": "manual", "notes": "Review."}
        result = self.check_requirement_rows([row])
        self.assertIn("no bold definition in a current owner", result)
        self.assertIn("SNTR-RPC-002 has no traceability row", result)

    def test_history_keeps_link_checks_without_current_vocabulary_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            records = ("rfcs/0001-history.md", "specifications/decisions/ADR-001.md",
                       "docs/decisions/0001-history.md", "GOVERNANCE.md")
            for name in records + ("specifications/rpc.md",):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SNTR-REMOVED-999 SNTR-UNDEFINED-V1\n[broken](missing.md)\n")
            V.ERRORS.clear()
            with (mock.patch.object(V, "ROOT", root),
                  mock.patch.object(V.OWNERS, "owner_definitions", return_value={})):
                V.check_links()
            for name in records:
                self.assertTrue(any(e.startswith(name + ":2:") and "broken link" in e for e in V.ERRORS))
                self.assertFalse(any(e.startswith(name + ": references") for e in V.ERRORS))
            self.assertIn("specifications/rpc.md: references undefined requirement SNTR-REMOVED-999", V.ERRORS)
            self.assertIn("specifications/rpc.md: references unknown transport profile SNTR-UNDEFINED-V1", V.ERRORS)

    def test_requirement_owner_metadata_cannot_be_missing_or_malformed(self):
        valid = {"requirement_id": "SNTR-RPC-002", "specification": "specifications/rpc.md",
                 "section": "RPC", "test_ids": [], "automation_status": "manual", "notes": "Review."}
        for key, value, message in (("specification", None, "needs a current owner path"),
                                    ("specification", ["specifications/rpc.md"], "needs a current owner path"),
                                    ("specification", "conformance/README.md", "not defined by its declared owner"),
                                    ("section", ["RPC"], "stale section"),
                                    ("automation_status", ["manual"], "invalid automation_status"),
                                    ("test_ids", [["CONF-RPC-001"]], "invalid test ID")):
            with self.subTest(key=key, value=value):
                self.assertIn(message, self.check_requirement_rows([dict(valid, **{key: value})]))


if __name__ == "__main__":
    unittest.main()
