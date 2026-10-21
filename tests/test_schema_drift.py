"""Regressions for missing/untracked/relocated committed-generation output."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_schema", ROOT / "scripts/validate-schema.py")
assert SPEC is not None and SPEC.loader is not None
SCHEMA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCHEMA)


class SchemaDriftTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.go = self.root / "bindings/go/gen"
        self.rust = self.root / "crates/syntra-core/src/generated"
        for name, value in [("ROOT", self.root), ("COMMITTED_GO_GEN", self.go),
                            ("COMMITTED_RUST_GEN", self.rust),
                            ("GO_OUT", self.root / ".tmp/go"), ("RUST_OUT", self.root / ".tmp/rust")]:
            patcher = patch.object(SCHEMA, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.git("init")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, path, content=b"generated", track=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        if track:
            self.git("add", str(path.relative_to(self.root)))

    def fixture(self):
        self.write(self.go / "syntra/v1/envelope.pb.go")
        self.write(self.rust / "syntra.v1.rs")
        return {"go/syntra/v1/envelope.pb.go": b"generated", "rust/syntra.v1.rs": b"generated"}

    def test_matching_tracked_trees_pass(self):
        SCHEMA.check_drift(self.fixture())

    def test_empty_committed_map_never_skips(self):
        with self.assertRaisesRegex(SystemExit, "Missing committed"):
            SCHEMA.check_drift({"go/a.pb.go": b"a", "rust/a.rs": b"a"})

    def test_missing_one_language_fails(self):
        fresh = self.fixture()
        self.git("rm", "--cached", "crates/syntra-core/src/generated/syntra.v1.rs")
        (self.rust / "syntra.v1.rs").unlink()
        with self.assertRaisesRegex(SystemExit, "Missing committed rust"):
            SCHEMA.check_drift(fresh)

    def test_deleted_tracked_files_fail_even_without_fresh_counterpart(self):
        fresh = self.fixture()
        self.write(self.go / "old.pb.go")
        (self.go / "old.pb.go").unlink()
        with self.assertRaisesRegex(SystemExit, "missing or not a regular file"):
            SCHEMA.check_drift(fresh)

    def test_empty_fresh_map_and_missing_fresh_language_fail(self):
        fresh = self.fixture()
        for invalid in [{}, {k: v for k, v in fresh.items() if k.startswith("go/")}]:
            with self.assertRaisesRegex(SystemExit, "Missing fresh"):
                SCHEMA.check_drift(invalid)

    def test_untracked_output_is_not_a_substitute_for_commits(self):
        fresh = self.fixture()
        self.git("rm", "--cached", "bindings/go/gen/syntra/v1/envelope.pb.go")
        with self.assertRaisesRegex(SystemExit, "not git-tracked"):
            SCHEMA.check_drift(fresh)

    def test_modified_added_stale_and_relocated_files_fail(self):
        fresh = self.fixture()
        for invalid in [dict(fresh, **{"rust/syntra.v1.rs": b"changed"}),
                        dict(fresh, **{"go/added.pb.go": b"new"}),
                        {"rust/syntra.v1.rs": b"generated", "go/elsewhere/envelope.pb.go": b"generated"}]:
            with self.assertRaisesRegex(SystemExit, "stale"):
                SCHEMA.check_drift(invalid)

    def test_same_basenames_remain_distinct_in_both_collectors(self):
        self.fixture()
        self.write(self.go / "other/envelope.pb.go", b"different")
        committed = SCHEMA._collect_committed_files()
        self.assertEqual(committed["go/other/envelope.pb.go"], b"different")
        self.assertEqual(committed["go/syntra/v1/envelope.pb.go"], b"generated")
        for key, content in committed.items():
            language, suffix = key.split("/", 1)
            out = SCHEMA.GO_OUT if language == "go" else SCHEMA.RUST_OUT
            self.write(out / "gen" / suffix, content, track=False)
        self.assertEqual(SCHEMA._collect_fresh_files(), committed)

    def test_git_inventory_failure_is_fatal(self):
        self.fixture()
        with patch.object(SCHEMA.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "git")):
            with self.assertRaisesRegex(SystemExit, "Cannot establish tracked"):
                SCHEMA._collect_committed_files()


if __name__ == "__main__":
    unittest.main()
