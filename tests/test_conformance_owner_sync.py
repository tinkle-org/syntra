"""The location generator must not alter requirements or claim test execution."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("owner_sync", ROOT / "scripts/sync-conformance-owners.py")
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class OwnerSynchronizationTests(unittest.TestCase):
    def test_flow_and_block_locations_only(self):
        original = '''format_version: "1.0"
requirements:
  - { requirement_id: SNTR-SC-003, specification: old/security.md, section: "§1", test_ids: [CONF-SCW-002], automation_status: automated }
  - requirement_id: SNTR-SESS-006
    specification: old/session.md
    section: "§2"
    test_ids: []
    automation_status: manual
    notes: "Registration is not execution."
'''
        locations = {"SNTR-SC-003": ("specifications/security.md", "2. Context"),
                     "SNTR-SESS-006": ("specifications/connection.md", "4. Sessions")}
        updated = SYNC.synchronized(original, locations)
        self.assertEqual(SYNC.synchronized(updated, locations), updated)
        before = yaml.safe_load(original)["requirements"]
        after = yaml.safe_load(updated)["requirements"]
        for old, new in zip(before, after):
            self.assertEqual((new["specification"], new["section"]), locations[old["requirement_id"]])
            for field in ("requirement_id", "test_ids", "automation_status", "notes"):
                self.assertEqual(old.get(field), new.get(field))

    def test_missing_definition_is_not_invented(self):
        with self.assertRaisesRegex(ValueError, "no definition"):
            SYNC.synchronized("requirements:\n  - { requirement_id: SNTR-SC-003 }\n", {})

    def test_unregistered_definition_does_not_create_a_row_or_coverage(self):
        original = "format_version: '1.0'\nrequirements: []\n"
        self.assertEqual(SYNC.synchronized(original, {
            "SNTR-SC-003": ("specifications/security.md", "Context")}), original)

    def test_duplicate_registry_ids_fail_closed(self):
        original = "requirements:\n" + "  - { requirement_id: SNTR-SC-003 }\n" * 2
        with self.assertRaisesRegex(ValueError, "duplicate registry"):
            SYNC.synchronized(original, {"SNTR-SC-003": ("specifications/security.md", "Context")})

    def test_plain_block_section_and_quoted_flow_section(self):
        original = '''# retained comment
requirements:
  - { requirement_id: SNTR-SC-003, specification: old.md, section: 'Old, section', test_ids: [], automation_status: manual, notes: "No executed coverage." }
  - requirement_id: SNTR-SESS-006
    specification: old.md
    section: Old plain heading
    test_ids: []
    automation_status: manual
    notes: "Needs review."
'''
        locations = {rid: ("conformance/README.md", 'Test "quotes": café')
                     for rid in ("SNTR-SC-003", "SNTR-SESS-006")}
        updated = SYNC.synchronized(original, locations)
        self.assertTrue(updated.startswith("# retained comment\n"))
        self.assertEqual(SYNC.synchronized(updated, locations), updated)
        self.assertTrue(all(r["section"] == 'Test "quotes": café'
                            for r in yaml.safe_load(updated)["requirements"]))

    def test_discovery_scopes_current_owners_and_optional_tooling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in SYNC.OWNERS:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Current\n")
            (root / "conformance/README.md").write_text("# Evidence\n**SNTR-STEST-001** — test\n")
            for name in ("rfcs/0001-history.md", "specifications/decisions/ADR-001.md",
                         "specifications/conformance.md", "docs/schema-validation-record.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("**SNTR-STEST-001** — excluded\n**SNTR-OLD-999**\n")
            self.assertEqual(SYNC.owner_locations(root), {
                "SNTR-STEST-001": ("conformance/README.md", "Evidence")})
            tooling = root / SYNC.OPTIONAL_OWNERS[0]
            tooling.parent.mkdir(parents=True, exist_ok=True)
            tooling.write_text("# Tools\n**SNTR-TOOL-001** — test\n")
            self.assertIn("SNTR-TOOL-001", SYNC.owner_locations(root))
            (root / "specifications/security.md").write_text("**SNTR-STEST-001** — duplicate\n")
            with self.assertRaisesRegex(ValueError, "duplicate owner"):
                SYNC.owner_locations(root)

    def test_required_owner_cannot_disappear_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                SYNC.owner_locations(Path(directory))


if __name__ == "__main__":
    unittest.main()
