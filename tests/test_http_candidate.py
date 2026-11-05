"""Static proposal regression tests, not HTTP/TLS/Noise runtime conformance."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("http_candidate", ROOT / "scripts/check-http-candidate.py")
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class HttpCandidateTests(unittest.TestCase):
    def setUp(self):
        self.contract = C.load(ROOT, f"{C.BUNDLE}/contract.json")
        self.contexts = C.load(ROOT, f"{C.BUNDLE}/context-vectors.json")
        self.base = C.load(ROOT, "conformance/test-vectors/connection/context-vectors.json")
        self.encode = C.context_encoder(ROOT)

    def test_isolated_bundle_and_active_base_are_consistent(self):
        report = C.validate(ROOT)
        self.assertEqual(report["kind"], "worktree-not-release")
        self.assertIsNone(report["source"]["candidate_revision"])
        self.assertEqual(report["runtime_conformance"], "NOT_EXECUTED")
        self.assertFalse(report["authority"]["accepted"])
        self.assertEqual(len(report["base_git_blobs_sha256"]), len(C.BASE_FILES) + 8)
        self.assertEqual(set(report["files_sha256"]), set(C.SOURCE_FILES))

    def test_candidate_validation_jobs_fetch_pinned_base_history(self):
        for workflow, job in (("repo-validation.yml", "docs"),
                              ("repo-validation.yml", "conformance"),
                              ("release-please.yml", "validate")):
            config = yaml.safe_load(C.read_bounded(ROOT, f".github/workflows/{workflow}"))
            checkout = next(step for step in config["jobs"][job]["steps"]
                            if step.get("uses", "").startswith("actions/checkout@"))
            with self.subTest(workflow=workflow, job=job):
                self.assertEqual(checkout.get("with", {}).get("fetch-depth", 1), 0,
                                 "candidate validation needs the pinned base Git objects")

    def test_base_guard_rejects_active_owner_edits_without_writing_files(self):
        read = C.read_bounded
        target = C.BASE_FILES[0]
        with mock.patch.object(C, "read_bounded", side_effect=lambda root, path:
                               b"unauthorized active edit" if path == target else read(root, path)):
            with self.assertRaisesRegex(ValueError, "active input changed before adoption"):
                C.verify_base(ROOT)

    def test_worktree_report_rejects_source_changes_during_validation(self):
        original = C.read_bounded
        reads = 0

        def changing(root, path):
            nonlocal reads
            raw = original(root, path)
            if path == C.SOURCE_FILES[0]:
                reads += 1
                if reads > 1:
                    return raw + b"changed during validation"
            return raw

        with mock.patch.object(C, "read_bounded", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "candidate source changed during validation"):
                C.validate(ROOT)

    def test_consent_does_not_satisfy_public_or_human_review(self):
        for gate in ("public_approval", "human_security_review", "accepted", "active", "freeze", "release_authorized"):
            changed = copy.deepcopy(self.contract)
            changed["authority"][gate] = True
            with self.subTest(gate=gate), self.assertRaises(ValueError):
                C.validate_contract(changed)
        for changes in ({"accepted": 0}, {"formal_conformance": "PASS"}, {"unrecorded_gate": True}):
            changed = copy.deepcopy(self.contract)
            changed["authority"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                C.validate_contract(changed)

    def test_contract_rejects_bad_mapping_or_security_constants(self):
        for field, value in (("send_ack_requires_decryption", True),
                             ("send_ack_requires_runtime_consumption", True),
                             ("automatic_rpc_replay", True), ("streams", 3),
                             ("status_204_content_length", "required")):
            changed = copy.deepcopy(self.contract)
            changed["http"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.validate_contract(changed)
        for path in ("/syntra/http/send", "/syntra/1.0/http/send?route=x"):
            changed = copy.deepcopy(self.contract)
            changed["http"]["operations"]["send"]["path"] = path
            with self.assertRaises(ValueError):
                C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed["limits"]["poll_hold_ms_max"] = 30001
        with self.assertRaises(ValueError):
            C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed["tls_provider"]["forwarded_claims"] = True
        with self.assertRaises(ValueError):
            C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed["http"]["extra_authentication"] = True
        with self.assertRaises(ValueError):
            C.validate_contract(changed)

    def test_current_encoder_still_rejects_unadopted_carriers_by_default(self):
        for code in (4, 5):
            case = dict(self.base["contexts"][0], carrier=code)
            with self.assertRaises(ValueError):
                self.encode(case)
            self.assertEqual(len(self.encode(case, permitted_carriers=(4, 5))), 35)
    def test_public_context_bytes_and_negative_recipes(self):
        C.validate_contexts(self.contexts, self.base, self.encode)
        changed = copy.deepcopy(self.contexts)
        changed["contexts"][0]["context_hex"] += "00"
        with self.assertRaises(ValueError):
            C.validate_contexts(changed, self.base, self.encode)
        changed = copy.deepcopy(self.contexts)
        changed["negative_recipes"][0]["changes"]["carrier"] = 4
        with self.assertRaises(ValueError):
            C.validate_contexts(changed, self.base, self.encode)
        # Scope byte bounds, UTF-8 and upper numeric fields reuse the source encoder.
        for code in (4, 5):
            for scope in ("a", "é", "a" * 255):
                case = dict(self.base["contexts"][0], carrier=code, scope=scope)
                self.assertEqual(len(self.encode(case, permitted_carriers=(4, 5))), 34 + len(scope.encode()))
            with self.assertRaises(ValueError):
                self.encode(dict(case, scope="é" * 128), permitted_carriers=(4, 5))

    def test_http_shapes_and_ack_are_structural_not_authentication(self):
        data = C.load(ROOT, f"{C.BUNDLE}/http-vectors.json")
        C.validate_http(data)
        rows = C.materialize_http(data["vectors"])
        self.assertEqual(C.lint_http_shape(rows["R13-H02"]), "accept")
        self.assertFalse(rows["R13-H02"]["attests"]["noise_authenticated"])
        self.assertFalse(rows["R13-H02"]["attests"]["runtime_consumed"])
        for name in ("R13-H05", "R13-H06", "R13-H07", "R13-H09", "R13-H10", "R13-H12", "R13-H14", "R13-H25"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                C.lint_http_shape(rows[name])
        self.assertEqual(C.lint_http_shape(rows["R13-H15"]), "tunnel")
        self.assertEqual(bytes.fromhex(rows["R13-H15"]["read_ahead_hex"]), b"\x16\x03\x03")
        self.assertEqual({(row["operation"], row["direction"]) for row in rows.values()
                          if row["expected"] == "accept"},
                         {(op, side) for op in ("open", "send", "poll", "close")
                          for side in ("request", "response")})
        self.assertEqual(len(bytes.fromhex(rows["R13-H23"]["body_hex"])), 65535)
        with self.assertRaises(ValueError):
            C.lint_http_shape(rows["R13-H24"])

    def test_http_fixture_mutations_and_bounds_fail_closed(self):
        row = C.materialize_http(C.load(ROOT, f"{C.BUNDLE}/http-vectors.json")["vectors"])["R13-H01"]
        for header in (["Injected\r\nName", "1"], ["X-Test", "bad\r\nvalue"],
                       ["X-Test", "x" * 4096], ["Syntra-Poll", "0"],
                       ["Content-Encoding", "identity"],
                       ["Connection", "keep-alive, close"],
                       ["Connection", "Close"],
                       ["Connection", " keep-alive , CLOSE "]):
            changed = copy.deepcopy(row)
            changed["headers"].append(header)
            with self.subTest(header=header[0]), self.assertRaises(ValueError):
                C.lint_http_shape(changed)
        with self.assertRaises(ValueError):
            C.materialize_http([{"id": "x", "base": "missing"}])
        with self.assertRaises(ValueError):
            C.materialize_http([dict(row, append_zero_bytes=65537)])

    def test_registry_does_not_enable_claims_or_conflict_with_active_codes(self):
        profiles = C.load(ROOT, f"{C.BUNDLE}/profiles.yaml")
        current = C.load(ROOT, "conformance/profiles.yaml")
        C.validate_profiles(profiles, self.contract, current)
        for field, value in (("claimable", True), ("carrier", 3), ("integral_noise", False)):
            changed = copy.deepcopy(profiles)
            changed["profiles"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.validate_profiles(changed, self.contract, current)

    def test_cases_have_reciprocal_trace_without_execution_claim(self):
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        rfc = C.read_bounded(ROOT, "rfcs/0013-http-tls-carriers.md").decode()
        C.validate_cases(cases, rfc)
        for change in ("missing-case", "unknown-requirement", "pass-verdict", "remove-role",
                       "inverted-positive", "inverted-negative", "bad-case-id"):
            changed = copy.deepcopy(cases)
            if change == "missing-case":
                changed["cases"].pop()
            elif change == "unknown-requirement":
                changed["cases"][0]["requirements"].append("R13-99")
            elif change == "pass-verdict":
                changed["runtime_verdict"] = "PASS"
            elif change == "inverted-positive":
                key = next(iter(changed["cases"][0]["positive_expected"]))
                changed["cases"][0]["positive_expected"][key] = False
            elif change == "inverted-negative":
                key = next(iter(changed["cases"][0]["negative_expected"]))
                changed["cases"][0]["negative_expected"][key] = True
            elif change == "bad-case-id":
                changed["cases"][0]["id"] = "R13-T01|.*"
            else:
                changed["cases"][0]["roles"] = ["client"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                C.validate_cases(changed, rfc)

    def test_canonical_snapshot_adoption_retains_consent_gates(self):
        readme = " ".join(C.read_bounded(ROOT, f"{C.BUNDLE}/README.md").decode().split())
        for wording in (
                "public acceptance",
                "human security-review disposition, compatibility decision and any objection resolutions",
                "formal acceptance and activation",
                "synchronized canonical specification, registry and fixture changes",
                "real reviewed commit and verified blobs"):
            with self.subTest(wording=wording):
                self.assertIn(wording, readme)

    def test_tls_variants_have_separate_wss_and_https_groups(self):
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        tls = next(case for case in cases["cases"] if case["id"] == "R13-T10")
        variants = tls["input"]["variants"]
        self.assertTrue(all(isinstance(group, dict) for group in variants),
                        "TLS variants must have explicit carrier-scoped groups")
        self.assertEqual([group["carriers"] for group in variants], [[3], [5]])
        wss, https = variants
        paired = {"wrong_d_identity", "wrong_d_policy_generation",
                  "equal_authority_deadline_different_generation",
                  "policy_replacement_between_handshakes"}
        self.assertTrue(paired.isdisjoint(wss["scenarios"]))
        self.assertTrue(paired <= set(https["scenarios"]))
        self.assertTrue(set(wss["scenarios"]) <= set(https["scenarios"]))
        self.assertIn("selected_policy_withdrawal", wss["scenarios"])
        self.assertNotIn("mixed_generation_pair_accepted", tls["negative_expected"])
        self.assertFalse(https["negative_expected"]["mixed_generation_pair_accepted"])
        self.assertEqual(cases["runtime_verdict"], "NOT_EXECUTED")

    def test_tls_variant_scope_mutations_are_rejected(self):
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        rfc = C.read_bounded(ROOT, "rfcs/0013-http-tls-carriers.md").decode()
        C.validate_cases(cases, rfc)
        for change in ("missing-wss", "missing-https", "unscoped", "mixed-carriers",
                       "pair-on-wss", "missing-pair", "unscoped-pair-expectation",
                       "nonboolean-assertion", "duplicate-scenario", "missing-common"):
            changed = copy.deepcopy(cases)
            tls = next(case for case in changed["cases"] if case["id"] == "R13-T10")
            groups = tls["input"]["variants"]
            if change == "missing-wss":
                groups.pop(0)
            elif change == "missing-https":
                groups.pop()
            elif change == "unscoped":
                del groups[0]["carriers"]
            elif change == "mixed-carriers":
                groups[0]["carriers"] = [3, 5]
            elif change == "pair-on-wss":
                groups[0]["scenarios"].append("wrong_d_policy_generation")
            elif change == "missing-pair":
                groups[1]["scenarios"].remove("wrong_d_policy_generation")
            elif change == "unscoped-pair-expectation":
                tls["negative_expected"]["mixed_generation_pair_accepted"] = False
            elif change == "nonboolean-assertion":
                groups[1]["negative_expected"]["mixed_generation_pair_accepted"] = "false"
            elif change == "duplicate-scenario":
                groups[0]["scenarios"].append(groups[0]["scenarios"][0])
            else:
                groups[0]["scenarios"].remove("selected_policy_withdrawal")
            with self.subTest(change=change), self.assertRaises(ValueError):
                C.validate_cases(changed, rfc)

    def test_requirement_owner_mapping_is_local_collision_free_and_reciprocal(self):
        requirements = C.load(ROOT, f"{C.BUNDLE}/requirements.yaml")
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        active = C.load(ROOT, "conformance/manifest/requirements.yaml")
        C.validate_requirements(requirements, cases, active)
        for field, value in (("test_ids", []), ("proposed_requirement_id", "SNTR-HPC-029"),
                             ("owner", "specifications/security.md")):
            changed = copy.deepcopy(requirements)
            changed["requirements"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.validate_requirements(changed, cases, active)

    def test_duplicate_keys_path_escape_symlinks_and_file_caps_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=C.unique_pairs)
        with self.assertRaises(ValueError):
            yaml.load("a: 1\na: 2\n", Loader=C.UniqueYaml)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large").write_bytes(b"x" * (C.MAX_FILE + 1))
            (root / "link").symlink_to(root / "large")
            for name in ("../outside", "/absolute", "link", "large"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    C.read_bounded(root, name)

    def test_adoption_command_is_explicitly_blocked(self):
        result = subprocess.run([sys.executable, "scripts/check-http-candidate.py", "--require-adoption"],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("public approval, human security review", result.stderr)


if __name__ == "__main__":
    unittest.main()
