"""Offline tests for specification-release authorization and publication."""

import hashlib
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "spec-release.py"
SPEC = importlib.util.spec_from_file_location("spec_release", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)

SHA = "a" * 40
BODY = "\n".join((
    "Release-Tag: v1.0",
    f"Release-Commit: {SHA}",
    "Release-Scope: SC1/WSS and recovery",
    "Release-Freeze: https://example.invalid/freeze",
    "Release-Evidence: https://example.invalid/evidence",
    "Release-Security: https://example.invalid/review",
    "Release-Objections: none",
    "Release-Self-Review: yes",
))
ISSUE = {"state": "open", "body": BODY, "user": {"login": "alice", "type": "User"}}
ROSTER = "| [alice](https://github.com/alice) | Active maintainer; owner | all |\n"


def approval(user="alice", body=BODY, tag="v1.0", sha=SHA, ident=1):
    digest = hashlib.sha256(body.encode()).hexdigest()
    return {"id": ident, "updated_at": f"2026-10-31T12:00:{ident:02d}Z",
            "user": {"login": user, "type": "User"},
            "body": f"SYNTRA-APPROVE {tag} {sha} {digest}"}


class AuthorizationTests(unittest.TestCase):
    def test_sole_maintainer_may_approve_their_own_decision(self):
        roster = RELEASE.parse_roster(ROSTER)
        self.assertEqual(RELEASE.verify_authorization(ISSUE, [approval()], roster,
                                                      "v1.0", SHA), {"alice"})

    def test_missing_stale_or_untrusted_approval_fails(self):
        roster = RELEASE.parse_roster(ROSTER)
        for comments in ([], [approval(user="mallory")],
                         [approval(body=BODY + " changed")],
                         [approval(tag="v1.1")], [approval(sha="b" * 40)]):
            with self.subTest(comments=comments):
                with self.assertRaises(RELEASE.ReleaseError):
                    RELEASE.verify_authorization(ISSUE, comments, roster, "v1.0", SHA)

    def test_edited_issue_invalidates_prior_approval(self):
        issue = dict(ISSUE, body=BODY + "\nAdditional evidence: changed")
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_authorization(issue, [approval()], {"alice"}, "v1.0", SHA)

    def test_objection_or_revocation_blocks_release(self):
        objection = approval(ident=2)
        objection["body"] = f"SYNTRA-OBJECT v1.0 {SHA}"
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_authorization(ISSUE, [approval(), objection], {"alice"}, "v1.0", SHA)
        stale = approval(body=BODY + " stale", ident=3)
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_authorization(ISSUE, [approval(), objection, stale,
                approval(user="bob", ident=4), approval(user="carol", ident=5)],
                {"alice", "bob", "carol"}, "v1.0", SHA)

    def test_distinct_maintainers_required_if_roster_grows(self):
        roster = {"alice", "bob"}
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_authorization(ISSUE, [approval(), approval(ident=2)], roster,
                                         "v1.0", SHA)
        self.assertEqual(RELEASE.verify_authorization(ISSUE, [approval(),
                            approval(user="bob", ident=2)], roster, "v1.0", SHA), roster)

    def test_missing_disclosure_or_stable_evidence_fails(self):
        for text in (BODY.replace("Release-Self-Review: yes", "Release-Self-Review: no"),
                     BODY.replace("Release-Evidence: https://example.invalid/evidence",
                                  "Release-Evidence: pending")):
            with self.subTest(text=text):
                with self.assertRaises(RELEASE.ReleaseError):
                    RELEASE.verify_authorization(dict(ISSUE, body=text), [approval(body=text)],
                                                 {"alice"}, "v1.0", SHA)

    def test_roster_refuses_unparseable_active_rows(self):
        for text in ("", ROSTER + "| bob | Active maintainer | all |\n", ROSTER + ROSTER):
            with self.subTest(text=text):
                with self.assertRaises(RELEASE.ReleaseError):
                    RELEASE.parse_roster(text)


class EnvironmentAndNotesTests(unittest.TestCase):
    def environment(self):
        return {"name": "spec-release", "deployment_branch_policy": {
            "protected_branches": False, "custom_branch_policies": True},
            "protection_rules": [{"type": "required_reviewers", "prevent_self_review": False,
                                  "reviewers": [{"type": "User", "reviewer": {"login": "alice"}}]}]}

    def test_explicit_main_environment_accepts_sole_self_review(self):
        RELEASE.verify_environment(self.environment(), [{"type": "branch", "name": "main"}], {"alice"})

    def test_missing_or_permissive_environment_fails(self):
        cases = [(dict(self.environment(), protection_rules=[]), [{"type": "branch", "name": "main"}]),
                 (dict(self.environment(), deployment_branch_policy=None), [{"type": "branch", "name": "main"}]),
                 (self.environment(), [{"type": "branch", "name": "*"}]),
                 (self.environment(), [{"type": "branch", "name": "main"}, {"type": "tag", "name": "*"}])]
        for env, branches in cases:
            with self.subTest(env=env, branches=branches):
                with self.assertRaises(RELEASE.ReleaseError):
                    RELEASE.verify_environment(env, branches, {"alice"})

    def test_prevent_self_review_would_block_the_only_maintainer(self):
        env = self.environment()
        env["protection_rules"][0]["prevent_self_review"] = True
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_environment(env, [{"type": "branch", "name": "main"}], {"alice"})

    def test_release_notes_are_from_exact_changelog_section(self):
        text = "# Changelog\n\n## [Unreleased]\n\n## [v1.0] - 2026-10-31\n\nChanges.\n\n## [v0.9]\n\nOld.\n"
        self.assertIn("Changes.", RELEASE.extract_notes(text, "v1.0"))
        self.assertNotIn("Old.", RELEASE.extract_notes(text, "v1.0"))
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.extract_notes(text, "v1.1")

class FakeGitHub:
    def __init__(self):
        self.ref: dict | None = None
        self.comments = [approval()]
        self.issue = ISSUE
        self.environment = EnvironmentAndNotesTests().environment()
        self.writes = []

    def call(self, method, path, data=None, missing=False):
        if method != "GET":
            assert data is not None
            self.writes.append((method, path, data))
            if path.endswith("/git/refs"):
                self.ref = {"object": {"sha": data["sha"], "type": "commit"}}
                return self.ref
            raise AssertionError(path)
        if path.endswith("/commits/main"):
            return {"sha": "b" * 40}
        if path.endswith("/environments/spec-release"):
            return self.environment
        if path.endswith("/issues/42"):
            return self.issue
        if "/git/ref/tags/" in path:
            if self.ref is None and not missing:
                raise RELEASE.ReleaseError("missing tag")
            return self.ref
        raise AssertionError(path)

    def pages(self, path, key=None):
        if path.endswith("/deployment-branch-policies"):
            return [{"type": "branch", "name": "main"}]
        if path.endswith("/issues/42/comments"):
            return list(self.comments)
        raise AssertionError(path)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "rfcs").mkdir()
        (root / "rfcs/0011-specification-release-versioning.md").write_text("- Status: Accepted\n")
        (root / "MAINTAINERS.md").write_text(ROSTER)
        self.root = mock.patch.object(RELEASE, "ROOT", root)
        self.root.start()
        self.addCleanup(self.root.stop)
        self.git = mock.patch.object(RELEASE.PREFLIGHT, "git", return_value=SimpleNamespace(
            stdout="## [v1.0]\n\nReviewed changes.\n"))
        self.git.start()
        self.addCleanup(self.git.stop)
        self.api = FakeGitHub()

    def publish(self, recovery=False):
        RELEASE.publish(self.api, self.api, "v1.0", SHA, "b" * 40, 42, recovery)

    def test_valid_decision_creates_tag(self):
        self.publish()
        self.assertEqual([x[0] for x in self.api.writes], ["POST"])
        assert self.api.ref is not None
        self.assertEqual(self.api.ref["object"]["sha"], SHA)

    def test_missing_approval_or_environment_never_writes(self):
        for kind in ("approval", "environment"):
            self.api = FakeGitHub()
            if kind == "approval":
                self.api.comments = []
            else:
                self.api.environment["protection_rules"] = []
            with self.subTest(kind=kind):
                with self.assertRaises(RELEASE.ReleaseError):
                    self.publish()
                self.assertEqual(self.api.writes, [])

    def test_unaccepted_rfc_never_writes(self):
        (RELEASE.ROOT / "rfcs/0011-specification-release-versioning.md").write_text("- Status: Draft\n")
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish()
        self.assertEqual(self.api.writes, [])

    def test_existing_tag_requires_explicit_recovery_at_the_same_sha(self):
        self.api.ref = {"object": {"sha": SHA, "type": "commit"}}
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish()
        self.assertEqual(self.api.writes, [])
        self.publish(recovery=True)
        self.assertEqual(self.api.writes, [])

    def test_recovery_never_repoints_a_different_tag(self):
        self.api.ref = {"object": {"sha": "c" * 40, "type": "commit"}}
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish(recovery=True)
        self.assertEqual(self.api.writes, [])

    def test_recovery_rejects_non_commit_tag_object_without_recheck(self):
        self.api.ref = {"object": {"sha": SHA, "type": "tag"}}
        calls = []
        original_call = self.api.call

        def call(method, path, data=None, missing=False):
            if "/git/ref/tags/" in path:
                calls.append(path)
            return original_call(method, path, data, missing)

        self.api.call = call
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish(recovery=True)
        self.assertEqual(self.api.writes, [])
        self.assertEqual(len(calls), 1)

    def test_objection_with_trailing_text_blocks_publication(self):
        objection = approval(ident=2)
        objection["body"] = f"SYNTRA-OBJECT v1.0 {SHA} withdrawing: evidence gap"
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_authorization(ISSUE, [approval(), objection], {"alice"}, "v1.0", SHA)
        stale = approval(ident=3)
        stale["body"] = f"SYNTRA-APPROVE v1.0 {SHA}"
        with self.assertRaises(RELEASE.ReleaseError):
            RELEASE.verify_authorization(ISSUE, [stale], {"alice"}, "v1.0", SHA)

    def test_revocation_before_first_write_blocks_publication(self):
        original = self.api.pages
        calls = 0

        def pages(path, key=None):
            nonlocal calls
            if path.endswith("/issues/42/comments"):
                calls += 1
                if calls == 2:
                    return []
            return original(path, key)

        self.api.pages = pages
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish()
        self.assertEqual(self.api.writes, [])

    def test_revocation_after_tag_leaves_tag_in_place(self):
        original = self.api.pages
        calls = 0

        def pages(path, key=None):
            nonlocal calls
            if path.endswith("/issues/42/comments"):
                calls += 1
                if calls == 3:
                    return []
            return original(path, key)

        self.api.pages = pages
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish()
        self.assertEqual([x[0] for x in self.api.writes], ["POST"])

    def test_missing_changelog_section_blocks_tagging(self):
        RELEASE.PREFLIGHT.git.return_value = SimpleNamespace(stdout="## [v0.9]\n\nOld.\n")
        with self.assertRaises(RELEASE.ReleaseError):
            self.publish()
        self.assertEqual(self.api.writes, [])


if __name__ == "__main__":
    unittest.main()
