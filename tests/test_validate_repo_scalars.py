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

    def test_bad_connection_state_is_recorded(self):
        case = make_case()
        case["expected"]["connection_state"] = ["ACTIVE"]
        self.assertIn("invalid connection_state", self.check_case(case))


if __name__ == "__main__":
    unittest.main()
