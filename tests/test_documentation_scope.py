"""The public reference describes one protocol, independently of a runtime."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("connection", "wire-format", "rpc", "security", "transports", "recovery")


class DocumentationScopeTests(unittest.TestCase):
    def test_overview_has_six_protocol_pages_and_separate_supporting_guides(self):
        overview = (ROOT / "README.md").read_text()
        for page in PAGES:
            self.assertIn(f"specifications/{page}.md", overview)
        self.assertIn("pre-release", overview)
        self.assertIn("Syntra 1.0 defines one protocol", overview)
        self.assertIn("conformance/README.md", overview)
        self.assertIn("docs/schema-tooling.md", overview)
        self.assertNotIn("SNTR-RPC-V1", overview)
        self.assertNotIn("SYNTRA-1.0-WSS", overview)
        self.assertFalse((ROOT / "specifications/conformance.md").exists())

    def test_protocol_pages_do_not_prescribe_runtime_architecture(self):
        patterns = (r"\bC ABI\b", r"\bTokio\b", r"\bcallbacks?\b",
                    r"\bone writer\b", r"\bexecution permits?\b", r"\bjoin(?:ing)? tasks\b",
                    r"\bbuf (?:generate|lint|build)\b", r"\bcargo (?:test|build)\b",
                    r"SNTR-(?:CORE|SESS|RPC|EVENTS)-V1", r"SYNTRA-1\.0-(?:TCP|WS|WSS)")
        for page in PAGES:
            text = (ROOT / "specifications" / f"{page}.md").read_text()
            for pattern in patterns:
                with self.subTest(page=page, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text, re.I))

    def test_current_docs_do_not_link_to_implementation_development_records(self):
        paths = [ROOT / "README.md", *(ROOT / "specifications" / f"{p}.md" for p in PAGES),
                 *[p for p in (ROOT / "docs").glob("*.md")
                   if p.name != "decision-record-template.md"]]
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("development-record.md", path.read_text())
        for name in ("sc1-implementation.md", "perf-tradeoffs.md", "schema-validation-record.md"):
            self.assertFalse((ROOT / "docs" / name).exists())

    def test_obsolete_audit_reports_are_not_repository_documents(self):
        self.assertFalse((ROOT / "audits").exists())
        roots = (ROOT / "README.md", ROOT / "compatibility", ROOT / "rfcs",
                 ROOT / "specifications", ROOT / "conformance", ROOT / "docs")
        for root in roots:
            paths = [root] if root.is_file() else root.rglob("*.md")
            for path in paths:
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertNotIn("audits/", path.read_text())

    def test_schema_comments_link_current_owners_without_speculative_apis(self):
        for path in (ROOT / "proto/syntra/v1").glob("*.proto"):
            text = path.read_text()
            with self.subTest(path=path.name):
                self.assertNotIn("specifications/schema/", text)
                self.assertNotIn("unresolved behavioral", text)
                self.assertNotIn("await a capability RFC", text)
                self.assertNotIn("RpcResponse", text)

    def test_current_reference_and_test_inputs_have_no_standalone_channel_name(self):
        paths = [ROOT / "README.md", ROOT / "docs/decision-record-template.md",
                 *(ROOT / "specifications" / f"{p}.md" for p in PAGES)]
        paths.extend((ROOT / "docs").glob("*.md"))
        for directory in ("conformance", "proto", "scripts"):
            paths.extend(p for p in (ROOT / directory).rglob("*")
                         if p.suffix in (".md", ".yaml", ".json", ".proto", ".py"))
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIsNone(re.search("sc1", path.read_text(), re.I))

    def test_optional_behavior_is_described_as_capabilities(self):
        for page in PAGES:
            text = (ROOT / "specifications" / f"{page}.md").read_text()
            # These are existing schema names, not selectable protocol variants.
            text = text.replace("profile_version", "").replace("recovery_profile.proto", "")
            with self.subTest(page=page):
                self.assertIsNone(re.search(r"\bprofiles?\b", text, re.I))

    def test_decision_records_do_not_present_historical_names_as_current_options(self):
        for name in ("rfcs/0007-secure-channel-device-authorization.md",
                     "rfcs/0010-sc1-host-authorization-lifecycle.md",
                     "specifications/decisions/ADR-008-transport-security.md",
                     "specifications/decisions/ADR-011-noise-device-authorization.md"):
            with self.subTest(record=name):
                text = (ROOT / name).read_text()
                self.assertIn("> Historical", text)
                self.assertIn("README.md#detailed-description", text)


if __name__ == "__main__":
    unittest.main()
