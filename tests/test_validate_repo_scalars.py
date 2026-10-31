"""Regression tests: malformed YAML scalars must report errors, not crash."""

import importlib.util
from pathlib import Path
import unittest

import yaml
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate-repo.py"
SPEC = importlib.util.spec_from_file_location("syntra_validate_repo", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def make_case():
    return {
        "id": "CONF-TEST-999",
        "requirement": ["SNTR-RPC-002"],
        "profile": "SNTR-RPC-V1",
        "roles": ["server"],
        "capabilities": [],
        "mandatory": True,
        "preconditions": ["active_session"],
        "input": {"frames": []},
        "expected": {"connection_state": "ACTIVE", "session_state": "unchanged"},
    }


class ValidateManifestScalarsTests(unittest.TestCase):
    def setUp(self):
        VALIDATOR.ERRORS.clear()

    def check_case(self, case):
        with (mock.patch.object(VALIDATOR, "parse_proto_model", return_value=(
                  {}, {"ErrorCode": {"ERROR_CODE_FAILED_PRECONDITION": 1}})),
              mock.patch.object(VALIDATOR, "load_manifest_cases", return_value=(
                  {case["id"]: ("fixture.yaml", case)}, [])),
              mock.patch.object(VALIDATOR, "load_requirements", return_value=[
                  {"requirement_id": "SNTR-RPC-002"}])):
            VALIDATOR.check_manifests()
        return "\n".join(VALIDATOR.ERRORS)

    def test_schema_and_duplicate_fixture(self):
        root = SCRIPT.parents[1]
        schema = yaml.safe_load((root / "conformance/manifest/schema.yaml").read_text())
        control = schema["schema"]["test_case"]["fields"]["control_connection"]
        self.assertEqual(control["type"], "map")
        self.assertEqual(control["required"], ["preconditions", "expected"])
        manifest = yaml.safe_load((root / "conformance/manifest/rpc.yaml").read_text())
        case = next(c for c in manifest["cases"] if c["id"] == "CONF-RPC-004")
        self.assertEqual(case["expected"]["frames"], [])
        self.assertEqual(case["expected"]["error"], {
            "code": "FAILED_PRECONDITION", "observer": "detecting_host",
            "carriage": "local_only",
        })

    def test_known_string_values_are_accepted(self):
        case = make_case()
        case["expected"]["error"] = {
            "code": "FAILED_PRECONDITION", "observer": "detecting_host",
            "carriage": "local_only",
        }
        case["expected"]["transport"] = {
            "peer_observation": {"tcp_tls": {
                "signal": "transport_close", "local_report": "UNAVAILABLE"
            }},
            "result_envelope": "absent",
        }
        # Also register UNAVAILABLE in the fake ErrorCode table.
        with mock.patch.object(VALIDATOR, "parse_proto_model", return_value=(
                {}, {"ErrorCode": {"ERROR_CODE_FAILED_PRECONDITION": 1,
                                    "ERROR_CODE_UNAVAILABLE": 2}})):
            # Direct check still guards the helper while check_case exercises
            # the parent validation path for ordinary known strings.
            self.assertTrue(VALIDATOR._is_local_report("UNAVAILABLE", {"UNAVAILABLE"}))
            self.assertTrue(VALIDATOR._is_local_report("generic_protocol_rejection", set()))
        case["expected"]["transport"]["peer_observation"]["tcp_tls"]["local_report"] = "generic_protocol_rejection"
        self.assertEqual(self.check_case(case), "")

    def test_bad_top_level_error_code_is_recorded(self):
        for bad in (["FAILED_PRECONDITION"], {"value": "FAILED_PRECONDITION"}, 123, None):
            with self.subTest(bad=bad):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["expected"]["error"] = {"code": bad}
                self.assertIn("unknown error code", self.check_case(case))

    def test_bad_observer_and_carriage_are_recorded(self):
        for key in ("observer", "carriage"):
            for bad in (["detecting_host"], {"value": "local_only"}, None):
                with self.subTest(key=key, bad=bad):
                    VALIDATOR.ERRORS.clear()
                    case = make_case()
                    case["expected"]["error"] = {"code": "FAILED_PRECONDITION", key: bad}
                    self.assertIn("unknown error " + key, self.check_case(case))

    def test_bad_transport_values_are_recorded(self):
        for target, bad in (("signal", ["transport_close"]),
                            ("local_report", ["UNAVAILABLE"]),
                            ("result_envelope", ["absent"])):
            with self.subTest(target=target):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                if target == "result_envelope":
                    case["expected"]["transport"] = {target: bad}
                else:
                    case["expected"]["transport"] = {"peer_observation": {
                        "tcp_tls": {target: bad}
                    }}
                result = self.check_case(case)
                self.assertIn(target, result)

    def test_bad_control_connection_values_are_recorded(self):
        for key in ("code", "observer", "carriage"):
            with self.subTest(key=key):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["control_connection"] = {
                    "preconditions": ["active_session"],
                    "expected": {"connection_state": "ACTIVE", "error": {key: ["bad"]}},
                }
                self.assertIn("control_connection", self.check_case(case))

    def test_null_expectation_maps_are_recorded(self):
        # A present `error`/`transport` key with a null value must be
        # rejected, at both call sites (case-level and control_connection).
        for owner in ("case", "control_connection"):
            for key in ("error", "transport"):
                with self.subTest(owner=owner, key=key):
                    VALIDATOR.ERRORS.clear()
                    case = make_case()
                    if owner == "case":
                        case["expected"][key] = None
                    else:
                        case["control_connection"] = {
                            "preconditions": ["active_session"],
                            "expected": {"connection_state": "ACTIVE", key: None},
                        }
                    self.assertIn("must be a map", self.check_case(case))

    def test_absent_expectation_keys_still_pass(self):
        # Absent `error`/`transport` keys must stay silently allowed.
        case = make_case()
        self.assertEqual(self.check_case(case), "")

    def test_non_map_expectation_values_are_recorded(self):
        for key in ("error", "transport"):
            with self.subTest(key=key):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["expected"][key] = "not-a-map"
                self.assertIn("must be a map", self.check_case(case))

    def test_applicable_transports_are_validated(self):
        # Valid known families; absent key on make_case stays accepted.
        case = make_case()
        case["applicable_transports"] = ["tcp_tls", "ws_wss"]
        self.assertEqual(self.check_case(case), "")
        for bad in (None, [], "tcp_tls", [""], "http_1_1"):
            with self.subTest(bad=bad):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["applicable_transports"] = bad
                self.assertIn("applicable_transports", self.check_case(case))

    def test_bad_roles_are_recorded(self):
        # Nested sequences, non-list scalars and non-string members must be
        # reported, not crash the validator (no set()/membership TypeErrors).
        for bad in ([["server"]], 5, "server", [5], None):
            with self.subTest(bad=bad):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["roles"] = bad
                self.assertIn("invalid roles", self.check_case(case))

    def test_bad_capability_values_are_recorded(self):
        # Unhashable members (nested maps/sequences) and non-list values must
        # produce recorded errors instead of TypeError at membership/iteration.
        for bad in ([{"id": 1}], 7, "resumable", [["x"]]):
            with self.subTest(bad=bad):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["capabilities"] = bad
                self.assertIn("capabilit", self.check_case(case))

    def test_bad_requirement_values_are_recorded(self):
        # Non-list `requirement` (scalar) and nested sequences inside it.
        for bad in (5, "SNTR-RPC-002", [["SNTR-RPC-002"]]):
            with self.subTest(bad=bad):
                VALIDATOR.ERRORS.clear()
                case = make_case()
                case["requirement"] = bad
                result = self.check_case(case)
                self.assertTrue(
                    "must be a list" in result or "malformed requirement ref" in result,
                    result)

    def test_malformed_collected_requirement_ref_is_recorded(self):
        # The req_refs consumer (parsed once by load_manifest_cases, consumed
        # at the end of check_manifests) must tolerate non-string entries.
        with (mock.patch.object(VALIDATOR, "parse_proto_model", return_value=({}, {})),
              mock.patch.object(VALIDATOR, "load_manifest_cases", return_value=(
                  {}, [(["SNTR-RPC-002"], "fixture.yaml", "CONF-TEST-999")])),
              mock.patch.object(VALIDATOR, "load_requirements", return_value=[])):
            VALIDATOR.ERRORS.clear()
            VALIDATOR.check_manifests()
        self.assertIn("malformed requirement ref", "\n".join(VALIDATOR.ERRORS))

    def test_load_manifest_cases_survives_malformed_yaml(self):
        # The loader must report structurally invalid manifest files (non-map
        # documents, non-list `cases`, non-map entries, non-string ids, and
        # malformed nested `requirement` values) instead of crashing; valid
        # siblings keep loading side effects free of the malformed ones.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(VALIDATOR, "ROOT", root):
                mdir = root / "conformance" / "manifest"
                mdir.mkdir(parents=True)
                (mdir / "bad-nonmap.yaml").write_text("hello\n")
                (mdir / "bad-cases.yaml").write_text("cases: 5\n")
                (mdir / "bad-entry.yaml").write_text("cases: [5]\n")
                (mdir / "bad-id.yaml").write_text(
                    "cases:\n"
                    "  - requirement: [SNTR-RPC-002]\n"
                    "    profile: SNTR-RPC-V1\n"
                    "    roles: [client]\n"
                    "    capabilities: []\n"
                    "    mandatory: true\n"
                    "    preconditions: [active_session]\n"
                    "    input: {frames: []}\n"
                    "    expected: {connection_state: CLOSED, session_state: none}\n")
                (mdir / "bad-req.yaml").write_text(
                    "cases:\n"
                    "  - id: CONF-REQT-001\n"
                    "    requirement: [[SNTR-RPC-002]]\n"
                    "    profile: SNTR-RPC-V1\n"
                    "    roles: [client]\n"
                    "    capabilities: []\n"
                    "    mandatory: true\n"
                    "    preconditions: [active_session]\n"
                    "    input: {frames: []}\n"
                    "    expected: {connection_state: CLOSED, session_state: none}\n")
                VALIDATOR.ERRORS.clear()
                cases, req_refs = VALIDATOR.load_manifest_cases()
        result = "\n".join(VALIDATOR.ERRORS)
        self.assertIn("manifest file must be a map", result)
        self.assertIn("cases must be a list of case maps", result)
        self.assertIn("case entry must be a map", result)
        self.assertIn("case entry must have a string id", result)
        # The malformed-but-parseable case keeps its collected refs; nested
        # sequences land in req_refs and are rejected by the consumer later.
        self.assertEqual(len(req_refs), 1)
        self.assertIn("CONF-REQT-001", cases)

    def test_bad_connection_state_is_recorded(self):
        case = make_case()
        case["expected"]["connection_state"] = ["ACTIVE"]
        self.assertIn("invalid connection_state", self.check_case(case))


if __name__ == "__main__":
    unittest.main()
