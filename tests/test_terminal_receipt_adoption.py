"""Static RFC0014 adoption regressions; no protocol execution is asserted."""

import copy
import importlib.util
from pathlib import Path
import re
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("terminal_adoption", ROOT / "scripts/check-http-candidate.py")
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)
OWNERS = {
    "connection": (1, 2, 12), "rpc": (8, 10, 13),
    "security": (3, 4, 5), "transports": (6, 7, 9, 11),
}
TRACES = ((1, 2), (2, 3), (3, 8, 11), (3, 4), (4, 5, 11), (4, 5),
          (5, 6), (6, 7), (7, 11), (8, 9), (10, 12), (9, 12), (11, 13),
          tuple(range(1, 14)))


class TerminalReceiptAdoptionTests(unittest.TestCase):
    """Protect the accepted scope, old defaults, and the unrelated HTTP guard."""

    def test_thirteen_requirements_have_unique_current_owners_and_exact_case_edges(self):
        rows = C.load(ROOT, "conformance/manifest/requirements.yaml")["requirements"]
        rows = {r["requirement_id"]: r for r in rows if r["requirement_id"].startswith("SNTR-TRC-")}
        cases = C.load(ROOT, "conformance/manifest/rpc.yaml")["cases"]
        cases = {c["id"]: c for c in cases if c["id"].startswith("CONF-TRC-")}
        self.assertEqual(set(rows), {f"SNTR-TRC-{n:03d}" for n in range(1, 14)})
        self.assertEqual(set(cases), {f"CONF-TRC-{n:03d}" for n in range(1, 15)})
        for owner, numbers in OWNERS.items():
            text = (ROOT / f"specifications/{owner}.md").read_text()
            self.assertEqual(set(re.findall(r"\*\*(SNTR-TRC-\d+)\*\*", text)),
                             {f"SNTR-TRC-{n:03d}" for n in numbers})
            for n in numbers:
                row = rows[f"SNTR-TRC-{n:03d}"]
                self.assertEqual(row["specification"], f"specifications/{owner}.md")
                self.assertEqual(row["test_ids"], [f"CONF-TRC-{i:03d}" for i, refs in
                                                  enumerate(TRACES, 1) if n in refs])
        for n, refs in enumerate(TRACES, 1):
            case = cases[f"CONF-TRC-{n:03d}"]
            self.assertEqual(case["requirement"], [f"SNTR-TRC-{r:03d}" for r in refs])
            self.assertEqual(case["capabilities"], [])
            self.assertEqual(case["roles"], ["client", "server"])
            self.assertIn("NOT_EXECUTED", case["notes"])
            self.assertNotIn("verdict", case)
            scenario = case["input"]["faults"]["terminal_receipt"]
            self.assertEqual(scenario["rfc_case"], f"R14-T{n:02d}")
            self.assertTrue(scenario["variants"])
            self.assertTrue(case["expected"]["transport"]["positive_assertions"])
            self.assertTrue(case["expected"]["transport"]["negative_assertions"])

    def test_exact_adoption_passes_without_changing_http_activation(self):
        hashes = C.verify_base(ROOT)
        self.assertIn("conformance/manifest/requirements.yaml", hashes)
        C.validate_terminal_adoption(ROOT)
        report = C.validate(ROOT)
        self.assertEqual(report["status"], "accepted-unadopted")
        self.assertFalse(report["authority"]["active"])
        self.assertEqual(report["runtime_conformance"], "NOT_EXECUTED")

    def test_interoperability_variants_are_implementation_neutral(self):
        """Require independent A/B pairings in both directions without language pins."""
        cases = C.load(ROOT, "conformance/manifest/rpc.yaml")["cases"]
        case = next(c for c in cases if c["id"] == "CONF-TRC-014")
        self.assertIn("two_independent_implementations", case["preconditions"])
        self.assertEqual(case["input"]["faults"]["terminal_receipt"]["variants"], [
            {"setup": "implementation_A_host_B_client", "expect": "full_positive_and_negative_suite"},
            {"setup": "implementation_B_host_A_client", "expect": "full_positive_and_negative_suite"},
        ])

    def test_original_owner_and_registry_bytes_are_immutable(self):
        read = C.read_bounded
        for path in (*[f"specifications/{o}.md" for o in OWNERS],
                     "conformance/manifest/requirements.yaml", "conformance/manifest/rpc.yaml"):
            raw = read(ROOT, path)
            original = C.git(ROOT, "show", f"{C.BASE}:{path}")
            self.assertTrue(raw.startswith(original), path)
            # Mutate an old byte while retaining the complete valid adoption appendix.
            changed = b"!" + raw[1:]
            with self.subTest(path=path), mock.patch.object(C, "read_bounded", side_effect=
                    lambda root, name: changed if name == path else read(root, name)):
                with self.assertRaisesRegex(ValueError, "active input changed before adoption"):
                    C.verify_base(ROOT)

    def test_appendix_is_exact_not_a_blanket_marker_exception(self):
        read = C.read_bounded
        for path in (*[f"specifications/{o}.md" for o in OWNERS],
                     "conformance/manifest/requirements.yaml", "conformance/manifest/rpc.yaml"):
            raw = read(ROOT, path)
            original = C.git(ROOT, "show", f"{C.BASE}:{path}")
            for changed in (raw + b"\nHTTP mapping permitted.\n", original,
                            raw.replace(b"SNTR-TRC-", b"SNTR-HPC-", 1),
                            raw + raw[len(original):]):
                with self.subTest(path=path), mock.patch.object(C, "read_bounded", side_effect=
                        lambda root, name: changed if name == path else read(root, name)):
                    with self.assertRaises(ValueError):
                        C.verify_base(ROOT)

    def test_semantic_trace_mutations_fail_even_without_digest_check(self):
        load = C.load
        for target in ("conformance/manifest/rpc.yaml", "conformance/manifest/requirements.yaml"):
            data = load(ROOT, target)
            key = "cases" if target.endswith("rpc.yaml") else "requirements"
            rows = [r for r in data[key] if str(r.get("id", r.get("requirement_id", ""))).startswith(
                "CONF-TRC-" if key == "cases" else "SNTR-TRC-")]
            self.assertTrue(rows)
            for mutation in ("edge", "duplicate", "missing", "elevated"):
                changed = copy.deepcopy(data)
                row = next(r for r in changed[key] if r == rows[0])
                if mutation == "edge":
                    row["requirement" if key == "cases" else "test_ids"] = []
                elif mutation == "duplicate":
                    changed[key].append(copy.deepcopy(row))
                elif mutation == "missing":
                    changed[key].remove(row)
                elif key == "cases":
                    row["capabilities"] = ["syntra.terminal-receipt/1"]
                else:
                    row["notes"] = "PASS"
                with self.subTest(target=target, mutation=mutation), mock.patch.object(
                        C, "load", side_effect=lambda root, path:
                        changed if path == target else load(root, path)):
                    with self.assertRaises(ValueError):
                        C.validate_terminal_adoption(ROOT)

    def test_no_automatic_enablement_or_wire_allocation(self):
        text = (ROOT / "specifications/connection.md").read_text()
        self.assertIn("disabled by default", text)
        self.assertIn("SNTR-AUTH-008", text)
        cases = C.load(ROOT, "conformance/manifest/rpc.yaml")["cases"]
        cases = {c["id"]: c for c in cases if c["id"].startswith("CONF-TRC-")}
        self.assertIn("CONF-TRC-001", cases)
        self.assertTrue(cases["CONF-TRC-001"]["mandatory"])
        self.assertTrue(all(not c["mandatory"] for cid, c in cases.items() if cid != "CONF-TRC-001"))
        # The pre-existing default/withdrawal suites are byte-preserved too.
        for path in ("conformance/manifest/session.yaml", "conformance/manifest/security.yaml",
                     "conformance/manifest/connection.yaml", "conformance/profiles.yaml",
                     "conformance/test-vectors/connection/context-vectors.json"):
            self.assertEqual(C.read_bounded(ROOT, path), C.git(ROOT, "show", f"{C.BASE}:{path}"))

    def test_accepted_rfc_trace_is_a_bijection_not_a_first_match(self):
        """Reject duplicate local labels/rows and an altered all-requirements range."""
        read = C.read_bounded
        path = "rfcs/0014-scoped-terminal-receipt.md"
        rfc = read(ROOT, path)
        row = re.search(rb"^\| R14-T01 \|.*$", rfc, re.MULTILINE)
        self.assertIsNotNone(row)
        for changed in (rfc + b"\n**R14-01 (duplicate; host).**\n",
                        rfc + b"\n" + row[0] + b"\n",
                        rfc.replace(b"R14-01 through R14-13", b"R14-01 through R14-99")):
            self.assertNotEqual(changed, rfc)
            with mock.patch.object(C, "read_bounded", side_effect=lambda root, name:
                                   changed if name == path else read(root, name)):
                with self.assertRaises(ValueError):
                    C.validate_terminal_adoption(ROOT)


if __name__ == "__main__":
    unittest.main()
