"""Execute release shell steps offline; Git operations use disposable repos only."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
PUBLISH = yaml.safe_load((ROOT / ".github/workflows/release-plz.yml").read_text())
CI = yaml.safe_load((ROOT / ".github/workflows/repo-validation.yml").read_text())


def step(job, name, workflow=WORKFLOW):
    return next(s for s in workflow["jobs"][job]["steps"] if s.get("name") == name)


def events(workflow):
    # PyYAML's YAML 1.1 loader treats the unquoted Actions key `on` as True.
    return workflow.get("on", workflow.get(True))


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}")
        self.env.update(GITHUB_OUTPUT=str(self.root / "output"),
                        GITHUB_ENV=str(self.root / "env"),
                        TMPDIR=str(self.root),
                        GITHUB_REPOSITORY="tinklehq/syntra")

    def write(self, path, text="fixture"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def command(self, name, source):
        target = self.write(f"bin/{name}", source)
        target.chmod(0o755)

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE,
        ).strip()

    def git_fixture(self):
        self.git("init", "-b", "main")
        self.write("tracked", "first")
        self.git("add", "tracked")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-m", "fixture")
        sha = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", sha)
        return sha

    def run_step(self, job, name, workflow=WORKFLOW, **env):
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c",
             step(job, name, workflow)["run"]],
            cwd=self.root, env=dict(self.env, **env), text=True,
            capture_output=True, timeout=30,
        )

    def test_tag_resolver_accepts_only_core_and_emits_nothing_for_invalid_input(self):
        sha = self.git_fixture()
        for version in ["0.1.0", "1.2.3", "1.2.3-rc.1"]:
            tag = f"syntra-core-v{version}"
            self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "tag", "-a", tag, "-m", "release", sha)
            for requested in [tag, ""]:
                self.write("output", "")
                result = self.run_step("validate", "Resolve tag identity",
                                       REQUESTED_TAG=requested, GITHUB_REF=f"refs/tags/{tag}")
                self.assertEqual(result.returncode, 0, result.stderr)
                output = (self.root / "output").read_text().splitlines()
                self.assertEqual(output, [f"tag={tag}", f"version={version}", f"sha={sha}"])
        for tag in ["v1.2.3", "bindings/go/v1.2.3", "syntra-ffi-v1.2.3",
                    "syntra-core-v01.2.3", "syntra-core-v1.2.3.4", "syntra-core-v1x2x3",
                    "syntra-core-v1.2.3-rc.01", "syntra-core-v1.2.3-rc.x",
                    "syntra-core-v1.2.3$(touch injected)", "syntra-core-v1.2.3\nsha=bad",
                    "refs/heads/main", "syntra-core-v9.9.9"]:
            self.write("output", "")
            result = self.run_step("validate", "Resolve tag identity",
                                   REQUESTED_TAG=tag, GITHUB_REF="refs/heads/main")
            self.assertNotEqual(result.returncode, 0, tag)
            self.assertEqual((self.root / "output").read_text(), "")
        self.assertFalse((self.root / "injected").exists())

    def test_resolver_checks_out_requested_tag_and_rejects_unmerged_revision(self):
        first = self.git_fixture()
        self.git("tag", "syntra-core-v1.2.3", first)
        self.write("tracked", "second")
        self.git("add", "tracked")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-m", "unmerged")
        self.git("tag", "syntra-core-v1.2.4")
        result = self.run_step("validate", "Resolve tag identity", REQUESTED_TAG="syntra-core-v1.2.4")
        self.assertNotEqual(result.returncode, 0, result.stderr)
        result = self.run_step("validate", "Resolve tag identity", REQUESTED_TAG="syntra-core-v1.2.3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "tracked").read_text(), "first")

    def version_fixture(self, inherited=True):
        self.write("Cargo.toml", '[workspace.package]\nversion = "1.2.3"\n')
        version = 'version.workspace = true' if inherited else 'version = "1.2.3"'
        self.write("crates/syntra-core/Cargo.toml", '[package]\nname = "syntra-core"\n'
                   + version + '\n[dependencies]\nother = { version = "9.8.7" }\n')
        self.write("bindings/go/go.mod", "module github.com/tinklehq/syntra/bindings/go\n")

    def test_package_version_parses_toml_and_workspace_inheritance(self):
        for inherited in [True, False]:
            self.version_fixture(inherited)
            for version in ["1.2.3", "1.2.4"]:
                result = self.run_step("validate", "Validate package version and Go module identity", VERSION=version)
                self.assertEqual(result.returncode == 0, version == "1.2.3", result.stderr)

    def test_package_gate_rejects_missing_manifests_wrong_module_and_go_major(self):
        result = self.run_step("validate", "Validate package version and Go module identity", VERSION="1.2.3")
        self.assertNotEqual(result.returncode, 0)
        self.version_fixture()
        self.write("bindings/go/go.mod", "module example.invalid/wrong\n")
        result = self.run_step("validate", "Validate package version and Go module identity", VERSION="1.2.3")
        self.assertNotEqual(result.returncode, 0)
        self.version_fixture()
        self.write("Cargo.toml", '[workspace.package]\nversion = "2.0.0"\n')
        result = self.run_step("validate", "Validate package version and Go module identity", VERSION="2.0.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("module-path migration", result.stderr)

    @unittest.skipUnless(shutil.which("jq"), "jq required to execute release-plz output selection")
    def test_release_plz_output_selects_core_only(self):
        core = {"package_name": "syntra-core", "tag": "syntra-core-v1.2.3"}
        other = {"package_name": "syntra-ffi", "tag": "syntra-ffi-v5.6.7"}
        for releases, expected in [([], ""), ([other], ""), ([other, core], core["tag"])]:
            self.write("output", "")
            result = self.run_step("release-plz-release", "Select schema release", workflow=PUBLISH,
                                   RELEASES=json.dumps(releases))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((self.root / "output").read_text(), f"tag={expected}\n")
        result = self.run_step("release-plz-release", "Select schema release", workflow=PUBLISH,
                               RELEASES=json.dumps([core, core]))
        self.assertNotEqual(result.returncode, 0)

    def test_event_handoff_and_tag_namespaces_are_explicit(self):
        self.assertEqual(set(events(WORKFLOW)), {"push", "workflow_call", "workflow_dispatch"})
        self.assertEqual(events(WORKFLOW)["push"]["tags"], ["syntra-core-v[0-9]*.[0-9]*.[0-9]*"])
        call = PUBLISH["jobs"]["release-artifacts"]
        self.assertEqual(call["uses"], "./.github/workflows/release.yml")
        self.assertEqual(call["with"]["tag"], "${{ needs.release-plz-release.outputs.schema_tag }}")
        self.assertNotIn("secrets", call)
        config = tomllib.loads((ROOT / "release-plz.toml").read_text())["workspace"]
        self.assertIs(config["release_always"], False)
        self.assertEqual(config["git_tag_name"], "{{ package }}-v{{ version }}")
        self.assertEqual(config["git_release_type"], "auto")
        self.assertNotIn("concurrency", PUBLISH["jobs"]["release-plz-pr"])
        self.assertNotEqual(WORKFLOW["concurrency"]["group"], PUBLISH["concurrency"]["group"])

    def test_secrets_conditions_and_permissions_are_valid_and_scoped(self):
        self.assertEqual(WORKFLOW["permissions"], {"contents": "read"})
        self.assertEqual(WORKFLOW["jobs"]["package-and-release"]["permissions"], {"contents": "write"})
        auth = step("release-plz-release", "Authenticate to crates.io (Trusted Publishing)", PUBLISH)
        self.assertEqual(auth["if"], "env.REGISTRY_TOKEN == ''")
        for workflow in [WORKFLOW, PUBLISH]:
            for job in workflow["jobs"].values():
                self.assertNotIn("secrets.", job.get("if", ""))
                for item in job.get("steps", []):
                    self.assertNotIn("secrets.", item.get("if", ""))
                    self.assertNotRegex(item.get("run", ""), r"\$\{\{")
                    if item.get("uses", "").startswith("actions/checkout@"):
                        self.assertIs(item["with"]["persist-credentials"], False)

    def package_fixture(self, fail=False, omit=False):
        for name in ["bindings/go/go.mod", "conformance/manifest/core.yaml",
                     "conformance/test-vectors/frame.bin", "CHANGELOG.md", "RELEASE.md",
                     "GOVERNANCE.md", "LICENSE"]:
            self.write(name)
        self.command("buf", "#!/bin/sh\nset -eu\nif [ \"$1\" = build ]; then\n"
                     "  printf '{}' > \"$3\"\nelse\n  mkdir -p \"$3\"\nfi\n")
        self.command("git", "#!/bin/sh\nset -eu\ncase \"$1\" in\narchive)\n"
                     "  for arg in \"$@\"; do case \"$arg\" in --output=*)\n"
                     "    printf source > \"${arg#--output=}\" ;; esac; done ;;\nesac\n")
        self.command("cargo", "#!/bin/sh\nset -eu\n"
                     + ("exit 1\n" if fail else "exit 0\n" if omit else
                        "mkdir -p target/package\nprintf crate > target/package/syntra-core-1.2.3.crate\n"))

    def test_cargo_packaging_failure_and_missing_archives_are_fatal(self):
        for fail, omit in [(True, False), (False, True)]:
            self.package_fixture(fail, omit)
            # A stale archive must not hide either failure mode.
            self.write("target/package/stale.crate")
            result = self.run_step("package-and-release", "Assemble release payload", TAG="syntra-core-v1.2.3")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.root / "target/package/stale.crate").exists())

    def test_assets_checksums_and_upload_paths_match(self):
        self.package_fixture()
        tag = "syntra-core-v1.2.3-rc.4"
        out = f"release-staging/syntra-{tag}"
        result = self.run_step("package-and-release", "Assemble release payload", TAG=tag)
        self.assertEqual(result.returncode, 0, result.stderr)
        assets = self.root / out / "assets"
        expected = {"CHANGELOG.md", "RELEASE.md", "GOVERNANCE.md", "LICENSE", "image.json",
                    "syntra-core-1.2.3.crate", f"syntra-source-{tag}.tar.gz",
                    f"syntra-go-bindings-{tag}.tar.gz", f"syntra-schema-{tag}.tar.gz"}
        self.assertEqual({p.name for p in assets.iterdir()}, expected)
        for _ in range(2):
            result = self.run_step("package-and-release", "Write SHA256SUMS", OUT=out)
            self.assertEqual(result.returncode, 0, result.stderr)
            checksums = dict(line.split("  ", 1)[::-1]
                             for line in (assets / "SHA256SUMS").read_text().splitlines())
            self.assertEqual(set(checksums), expected)
            for name, digest in checksums.items():
                self.assertEqual(hashlib.sha256((assets / name).read_bytes()).hexdigest(), digest)
        with tarfile.open(assets / f"syntra-schema-{tag}.tar.gz") as archive:
            self.assertIn("manifests/core.yaml", archive.getnames())
            self.assertIn("test-vectors/frame.bin", archive.getnames())
        self.command("gh", "#!/usr/bin/env python3\nimport json, os, sys\n"
                     "if sys.argv[1:3] == ['release', 'view']:\n"
                     "    sys.exit(0 if os.environ['EXISTS'] == 'yes' else 1)\n"
                     "with open(os.environ['UPLOAD_LOG'], 'w') as f:\n"
                     "    json.dump(sys.argv[1:], f)\n")
        for release_tag in [tag, "syntra-core-v1.2.3"]:
            for exists in ["yes", "no"]:
                log = self.root / "upload.json"
                result = self.run_step("package-and-release", "Attach to GitHub Release",
                                       TAG=release_tag, OUT=out, EXISTS=exists, UPLOAD_LOG=str(log))
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads(log.read_text())
                uploaded = {Path(arg).name for arg in args if arg.startswith(out + "/assets/")}
                self.assertEqual(uploaded, expected | {"SHA256SUMS"})
                self.assertEqual("--prerelease" in args, exists == "no" and release_tag == tag)
                self.assertEqual("--verify-tag" in args, exists == "no")

    def test_checksum_failure_preserves_existing_file(self):
        out = "release-staging/syntra-syntra-core-v1.2.3"
        self.write(f"{out}/assets/image.json", "{}")
        sums = self.write(f"{out}/assets/SHA256SUMS", "previous checksums\n")
        self.command("shasum", "#!/bin/sh\nexit 1\n")
        result = self.run_step("package-and-release", "Write SHA256SUMS", OUT=out)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sums.read_text(), "previous checksums\n")

    def test_go_tag_creation_is_idempotent_and_never_moves_conflicting_tags(self):
        self.command("git", "#!/usr/bin/env python3\nimport os, sys\n"
                     "from pathlib import Path\n"
                     "p = Path('remote-tag')\n"
                     "if sys.argv[1] == 'ls-remote': sys.exit(0 if p.exists() else 2)\n"
                     "if sys.argv[1] == 'rev-parse':\n"
                     "    assert sys.argv[2].endswith('^{commit}')\n"
                     "    print(p.read_text())\n")
        self.command("gh", "#!/usr/bin/env python3\nimport os, sys\nfrom pathlib import Path\n"
                     "assert sys.argv[1:4] == ['api', '--method', 'POST']\n"
                     "assert 'ref=refs/tags/bindings/go/v1.2.3-rc.4' in sys.argv\n"
                     "Path('api-called').write_text('yes')\n"
                     "if os.environ.get('API_FAIL'): sys.exit(1)\n"
                     "Path('remote-tag').write_text(os.environ['SHA'])\n")
        for state in [None, "commit", "other-commit"]:
            remote = self.root / "remote-tag"
            remote.unlink(missing_ok=True)
            (self.root / "api-called").unlink(missing_ok=True)
            if state:
                remote.write_text(state)
            result = self.run_step("package-and-release", "Create or verify nested Go tag",
                                   TAG="syntra-core-v1.2.3-rc.4", VERSION="1.2.3-rc.4", SHA="commit")
            self.assertEqual(result.returncode == 0, state != "other-commit", result.stderr)
            self.assertEqual((self.root / "api-called").exists(), state is None)
            self.assertEqual(remote.read_text(), state or "commit")
        remote.unlink()
        result = self.run_step("package-and-release", "Create or verify nested Go tag",
                               TAG="syntra-core-v1.2.3-rc.4", VERSION="1.2.3-rc.4", SHA="commit", API_FAIL="yes")
        self.assertNotEqual(result.returncode, 0)

    def test_go_proxy_uses_version_prefix_and_fails_on_retry_exhaustion(self):
        log = self.root / "go-log"
        self.command("go", "#!/usr/bin/env python3\nimport os, sys\nfrom pathlib import Path\n"
                     "assert sys.argv[1:] == ['mod', 'download', 'github.com/tinklehq/syntra/bindings/go@v1.2.3-rc.4']\n"
                     "assert os.environ['GOPROXY'] == 'https://proxy.golang.org'\n"
                     "p = Path(os.environ['GO_LOG'])\n"
                     "n = int(p.read_text()) + 1 if p.exists() else 1\np.write_text(str(n))\n"
                     "sys.exit(0 if n >= int(os.environ['SUCCEED_AT']) else 1)\n")
        self.command("sleep", "#!/bin/sh\nexit 0\n")
        self.command("curl", "#!/bin/sh\nexit 1\n")
        for succeed_at, expected_count in [(1, 1), (3, 3), (99, 5)]:
            log.unlink(missing_ok=True)
            result = self.run_step("go-proxy-warmup", "Warm Go module proxy and request pkg.go.dev indexing",
                                   VERSION="1.2.3-rc.4", GO_LOG=str(log), SUCCEED_AT=str(succeed_at))
            self.assertEqual(result.returncode == 0, succeed_at <= 5, result.stderr)
            self.assertEqual(int(log.read_text()), expected_count)

    def test_release_and_drift_regressions_are_wired_into_ci(self):
        commands = [s.get("run", "") for job in CI["jobs"].values() for s in job["steps"]]
        self.assertIn("python3 -m unittest discover -s tests -p 'test_*.py' -v", commands)
        self.assertTrue(any("actionlint" in s.get("uses", "")
                            for job in CI["jobs"].values() for s in job["steps"]))

    def test_ffi_contract_and_fixture_tests_are_wired_into_ci(self):
        commands = [s.get("run", "") for job in CI["jobs"].values() for s in job["steps"]]
        self.assertIn("cargo test --locked --workspace", commands)
        self.assertIn("cargo test --locked -p syntra-ffi --features test-fixture", commands)
        self.assertIn("cargo test --locked -p syntra-ffi --features production", commands)
        self.assertIn("python3 crates/syntra-ffi/tests/build_contract.py", commands)
        # WASM job asserts the expected syntra-ffi failure, not success.
        wasm_runs = " ".join(commands)
        self.assertIn("syntra-ffi does not support WASM", wasm_runs)
        self.assertIn(
            "cargo check --locked -p syntra-core -p syntra-runtime -p syntra-ws -p syntra-web --target wasm32-unknown-unknown",
            commands,
        )
        # Go default tests plus the production native adapter linked
        # against the production Rust library.
        self.assertTrue(any("go test -count=1 -v ./..." in c for c in commands))
        self.assertTrue(any("go test -tags syntranative" in c for c in commands))
        # The syntranative tag must appear only in the dedicated native
        # step, which must build the production library first.
        native = step("go-tests", "go test (production native adapter)", CI)
        native_run = native.get("run", "")
        self.assertIn("cargo build --locked -p syntra-ffi --features production", native_run)
        self.assertIn("go test -tags syntranative", native_run)
        self.assertLess(
            native_run.index("cargo build --locked -p syntra-ffi --features production"),
            native_run.index("go test -tags syntranative"),
        )
        for s in CI["jobs"]["go-tests"]["steps"]:
            if s.get("name") == "go test (production native adapter)":
                continue
            self.assertNotIn("syntranative", s.get("run", ""))
        default_go_test = step("go-tests", "go test (committed bindings, default tags only)", CI)
        self.assertNotIn("syntranative", default_go_test.get("run", ""))

    def test_clean_go_generation_is_scoped_to_generated_files(self):
        template = yaml.safe_load((ROOT / "buf.gen.yaml").read_text())
        plugin = next(p for p in template["plugins"] if "/protocolbuffers/go:" in p["remote"])
        self.assertIs(template["clean"], True)
        self.assertEqual(plugin["out"], "bindings/go/gen")
        self.assertIn("paths=source_relative", plugin["opt"])
        for proto in (ROOT / "proto/syntra/v1").glob("*.proto"):
            self.assertIn(
                'option go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1";',
                proto.read_text(),
            )


if __name__ == "__main__":
    unittest.main()
