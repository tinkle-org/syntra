"""Runner verdict regressions; no third-party Python packages required."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runner", ROOT / "conformance/runner/runner.py")
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def matrix(self):
        return {
            "format_version": "1.0", "runner": "syntra-conformance-runner v1",
            "pairings": [{"id": p} for p in runner.PAIRINGS],
            "scenarios": [{"id": "SC-ECHO", "name": "echo", "steps": ["echo"]}],
            "fault_injection": {"seed": "0x5EED1234", "faults": [
                {"kind": "drop", "rate": "1/64", "scope": "notifications"},
                {"kind": "delay", "max_ms": 5, "scope": "send"},
            ]},
        }

    def load(self, value):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "conformance/runner"
            directory.mkdir(parents=True)
            (directory / "scenarios.yaml").write_text(json.dumps(value))
            with patch.object(runner, "ROOT", root):
                return runner.load_scenarios()

    def test_complete_fault_entries_survive_loading(self):
        matrix = self.matrix()
        result = self.load(matrix)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["faults"], matrix["fault_injection"]["faults"])

    def test_bad_matrix_fails_closed(self):
        for field, value in (("seed", None), ("seed", "oops"), ("faults", [])):
            with self.subTest(field=field, value=value):
                matrix = self.matrix()
                matrix["fault_injection"][field] = value
                self.assertFalse(self.load(matrix)["ok"])
        for change in ({"rate": "1/0"}, {"scope": ""}, {"max_ms": -1}, {"kind": "invented"}):
            with self.subTest(change=change):
                matrix = self.matrix()
                matrix["fault_injection"]["faults"][1 if "max_ms" in change else 0].update(change)
                self.assertFalse(self.load(matrix)["ok"])

    def test_prints_and_records_full_matrix(self):
        matrix = self.matrix()
        loaded = self.load(matrix)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "results.json"
            with patch.object(runner, "load_scenarios", return_value=loaded), patch.dict(
                runner.LEGS, {"go-pure": lambda: ("PASS", "stub", "")}
            ), patch("sys.argv", ["runner", "--pair", "go-pure", "--json", str(output)]):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(runner.main(), 0)
            self.assertIn('"rate": "1/64"', stream.getvalue())
            self.assertIn('"scope": "notifications"', stream.getvalue())
            self.assertIn('"max_ms": 5', stream.getvalue())
            self.assertEqual(json.loads(output.read_text())["matrix"]["faults"], loaded["faults"])

    def test_go_filter_includes_actual_recovery_tests(self):
        names = re.findall(r"^func (Test\w+)\(", (ROOT / "bindings/go/recovery_test.go").read_text(), re.M)
        self.assertGreater(len(names), 10)
        self.assertEqual([name for name in names if not re.search(runner.GO_COVERAGE_RUN, name)], [])

    def test_go_verdict_rejects_runner_only_output(self):
        self.assertFalse(runner._go_ok(0, "--- PASS: TestRunnerEcho (0.00s)\nPASS\n"))

    def test_interop_rejects_success_without_runtime_corpus_evidence(self):
        go = "--- PASS: TestGoldenVectors\n--- PASS: TestRunnerWireInteropGolden\nPASS\n"
        rust = "test sc_wire_vectors_decode ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored;"
        with patch.object(runner, "run", side_effect=[(0, go, "", 0), (0, rust, "", 0)]):
            self.assertEqual(runner.leg_interop()[0], "FAIL")

    def corpus_output(self, records):
        return "\n".join("CORPUS " + json.dumps(record) for record in records)

    def test_interop_checks_executed_bytes_and_every_decoded_field(self):
        records = list(runner._corpus_expected().values())
        good = self.corpus_output(records)
        self.assertTrue(runner._shared_corpus_check(good, good)[0])
        for index, record in enumerate(records):
            for field, value in record["semantic_fields"].items():
                with self.subTest(id=record["id"], field=field):
                    changed = copy.deepcopy(records)
                    changed[index]["semantic_fields"][field] = 999 if isinstance(value, int) else "wrong"
                    bad = self.corpus_output(changed)
                    self.assertFalse(runner._shared_corpus_check(good, bad)[0])
                    self.assertFalse(runner._shared_corpus_check(bad, good)[0])
            changed = copy.deepcopy(records)
            changed[index]["frame_hex"] = "0801"
            self.assertFalse(runner._shared_corpus_check(good, self.corpus_output(changed))[0])
        for incomplete in (records[:1], records + records[:1], [records[0], records[0]]):
            self.assertFalse(runner._shared_corpus_check(good, self.corpus_output(incomplete))[0])

    def test_corpus_changes_invalidate_stale_execution_records(self):
        good = self.corpus_output(list(runner._corpus_expected().values()))
        corpus = ROOT / "conformance/test-vectors/protobuf/vectors.yaml"
        for old, new in (('version: 1, request_id: 0, body: hello', 'version: 2, request_id: 0, body: hello'),
                         ('0801521e08011001', '0802521e08011001')):
            with self.subTest(change=new), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / "conformance/test-vectors/protobuf"
                directory.mkdir(parents=True)
                (directory / "vectors.yaml").write_text(corpus.read_text().replace(old, new))
                with patch.object(runner, "ROOT", root):
                    self.assertFalse(runner._shared_corpus_check(good, good)[0])

    def test_rejects_string_steps(self):
        matrix = self.matrix()
        matrix["scenarios"][0]["steps"] = "echo"
        self.assertFalse(self.load(matrix)["ok"])

    def test_rejects_nonstring_name(self):
        matrix = self.matrix()
        matrix["scenarios"][0]["name"] = 123
        self.assertFalse(self.load(matrix)["ok"])

    def test_uppercase_hex_corpus_still_passes(self):
        corpus = ROOT / "conformance/test-vectors/protobuf/vectors.yaml"
        text = corpus.read_text()
        upper_text = re.sub(
            r'frame_hex: "([0-9a-fA-F]+)"',
            lambda m: 'frame_hex: "%s"' % m.group(1).upper(),
            text)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "conformance/test-vectors/protobuf"
            directory.mkdir(parents=True)
            (directory / "vectors.yaml").write_text(upper_text)
            with patch.object(runner, "ROOT", root):
                expected = runner._corpus_expected()
                for vid in ("GOLD-PROT-HELLO-01", "GOLD-PROT-REQ-01"):
                    hexval = expected[vid]["frame_hex"]
                    assert isinstance(hexval, str)
                    self.assertEqual(hexval, hexval.upper())
                    self.assertTrue(any(c.isupper() for c in hexval if c.isalpha()))
                upper_records = list(expected.values())
                upper_output = self.corpus_output(upper_records)
                self.assertTrue(runner._shared_corpus_check(upper_output, upper_output)[0])
        # Mixed case must also pass: lowercase fixture vs uppercase
        # execution records (case-insensitive comparison).
        real_records = list(runner._corpus_expected().values())
        mixed = copy.deepcopy(real_records)
        for record in mixed:
            record["frame_hex"] = record["frame_hex"].upper()
        self.assertTrue(
            runner._shared_corpus_check(
                self.corpus_output(mixed), self.corpus_output(mixed))[0])
        self.assertTrue(
            runner._shared_corpus_check(
                self.corpus_output(real_records), self.corpus_output(mixed))[0])

    def test_verdicts_require_execution_and_reject_skips_failures(self):
        go = "\n".join(f"--- PASS: {name} (0.00s)" for name in runner.GO_REQUIRED_TESTS)
        self.assertTrue(runner._go_ok(0, go))
        for rc, log in ((1, go), (0, go + "\n--- SKIP: TestRunnerSkipped"), (0, go + "\nFAIL"), (0, "ok [no tests to run]")):
            self.assertFalse(runner._go_ok(rc, log))
        cargo = "test result: ok. 1 passed; 0 failed; 0 ignored;"
        self.assertTrue(runner._cargo_ok(0, cargo))
        for rc, log in ((1, cargo), (0, cargo.replace("1 passed", "0 passed")),
                        (0, cargo.replace("0 ignored", "1 ignored"))):
            self.assertFalse(runner._cargo_ok(rc, log))


if __name__ == "__main__":
    unittest.main()
