"""Offline tests for the proposed, read-only specification release preflight."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "spec-release-preflight.py"
SPEC = importlib.util.spec_from_file_location("spec_release_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class TagValidationTests(unittest.TestCase):
    def test_canonical_versions_and_candidates(self):
        for tag, candidate in (("v1.0", False), ("v1.10", False),
                               ("v0.1", False), ("v2.0-rc1", True),
                               ("v1.0-rc12", True)):
            with self.subTest(tag=tag):
                self.assertEqual(PREFLIGHT.validate_tag(tag), candidate)

    def test_invalid_tags_are_rejected(self):
        for tag in ("1.0", "v1", "v1.0.0", "v01.0", "v1.01", "v1.0-rc0",
                    "v1.0-rc01", "v1.0-rc.1", "v1.0-beta", "v1.0\n",
                    "v1.0; touch injected", "v1.0/other"):
            with self.subTest(tag=tag):
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_tag(tag)

    def test_commit_requires_full_lowercase_sha(self):
        self.assertEqual(PREFLIGHT.validate_sha("a" * 40), "a" * 40)
        for value in ("a" * 39, "A" * 40, "g" * 40, "a" * 41,
                      "a" * 40 + "\n", "main", "--help"):
            with self.subTest(value=value):
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_sha(value)


class GitPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.env = dict(os.environ, GIT_AUTHOR_NAME="Test Author",
                        GIT_AUTHOR_EMAIL="test@example.invalid",
                        GIT_COMMITTER_NAME="Test Author",
                        GIT_COMMITTER_EMAIL="test@example.invalid")
        self.git("init", "-q")
        self.first = self.commit("first")
        self.second = self.commit("second")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
             "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args],
            cwd=self.repo, env=self.env, text=True,
            stderr=subprocess.PIPE, timeout=15).strip()

    def commit(self, text):
        (self.repo / "document.txt").write_text(text + "\n")
        self.git("add", "document.txt")
        self.git("commit", "-q", "-m", text)
        return self.git("rev-parse", "HEAD")

    def test_ancestor_and_head_are_accepted_without_writing(self):
        for target in (self.first, self.second):
            with self.subTest(target=target):
                result = PREFLIGHT.verify_candidate(self.repo, "v1.0-rc1", target,
                                                    self.second)
                self.assertTrue(result["candidate"])
                self.assertEqual(result["target"], target)
                self.assertEqual(self.git("rev-parse", "HEAD"), self.second)
                self.assertEqual(self.git("status", "--porcelain"), "")

    def test_existing_tag_fails_even_when_it_points_at_the_target(self):
        self.git("tag", "v1.0", self.first)
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "already exists"):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", self.first, self.second)
        PREFLIGHT.verify_candidate(self.repo, "v1.0", self.first, self.second,
                                   allow_existing=True)
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "does not directly name"):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", self.second, self.second,
                                       allow_existing=True)

    def test_annotated_existing_tag_is_rejected_even_in_recovery(self):
        self.git("tag", "-a", "v1.0", "-m", "release", self.first)
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "does not directly name"):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", self.first, self.second,
                                       allow_existing=True)

    def test_unrelated_commit_is_rejected(self):
        self.git("checkout", "-q", "--detach", self.first)
        divergent = self.commit("divergent")
        self.git("checkout", "-q", "--detach", self.second)
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "not an ancestor"):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", divergent, self.second)

    def test_missing_commit_is_rejected(self):
        with self.assertRaises(PREFLIGHT.PreflightError):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", "a" * 40, self.second)

    def test_annotated_tag_object_is_not_a_commit_sha(self):
        self.git("tag", "-a", "historical", "-m", "historical", self.first)
        tag_object = self.git("rev-parse", "refs/tags/historical")
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "commit directly"):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", tag_object, self.second)

    def test_trusted_head_must_be_the_checked_out_commit(self):
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "checked-out HEAD"):
            PREFLIGHT.verify_candidate(self.repo, "v1.0", self.first, self.first)


class WorkflowSafetyTests(unittest.TestCase):
    def test_release_workflow_isolates_the_protected_publisher(self):
        workflow = SCRIPT.parents[1] / ".github/workflows/spec-release.yml"
        config = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(config["permissions"], {"contents": "read"})
        self.assertEqual(set(config["on"]), {"workflow_dispatch"})
        self.assertEqual(set(config["jobs"]), {"validate", "publish"})
        self.assertNotIn("environment", config["jobs"]["validate"])
        self.assertEqual(config["jobs"]["publish"]["environment"], "spec-release")
        self.assertEqual(config["jobs"]["publish"]["needs"], "validate")
        self.assertEqual(config["jobs"]["publish"]["permissions"], {
            "contents": "read", "issues": "read", "pull-requests": "read", "actions": "read"})
        for step in config["jobs"]["validate"]["steps"]:
            self.assertNotIn("secrets.", str(step))

    def test_main_and_target_are_checked_before_running_target_code(self):
        workflow = SCRIPT.parents[1] / ".github/workflows/spec-release.yml"
        config = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)
        steps = config["jobs"]["validate"]["steps"]
        self.assertEqual(steps[0]["run"], 'test "$GITHUB_REF" = refs/heads/main')
        check = next(i for i, step in enumerate(steps)
                     if step.get("name") == "Check proposed tag and target against trusted main")
        checkout = next(i for i, step in enumerate(steps)
                        if step.get("name") == "Check out the validated target for read-only checks")
        self.assertLess(check, checkout)
        self.assertIn('--trusted-head "$GITHUB_SHA"', steps[check]["run"])
        for step in steps:
            self.assertNotIn("${{ inputs.", step.get("run", ""))


if __name__ == "__main__":
    unittest.main()
