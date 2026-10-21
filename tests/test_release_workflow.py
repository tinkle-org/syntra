"""Exercise release shell steps offline, without building or publishing."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())


def step(job, name):
    return next(s for s in WORKFLOW["jobs"][job]["steps"] if s.get("name") == name)


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}")
        self.env.update(GITHUB_OUTPUT=str(self.root / "output"),
                        GITHUB_ENV=str(self.root / "env"))

    def write(self, path, text="fixture"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def command(self, name, source):
        target = self.write(f"bin/{name}", source)
        target.chmod(0o755)

    def run_step(self, job, name, **env):
        return subprocess.run(
            # The workflow's implicit Linux shell is bash -e, not explicit
            # shell: bash (which would also enable pipefail).
            ["bash", "-e", "-c", step(job, name)["run"]],
            cwd=self.root, env=dict(self.env, **env), text=True,
            capture_output=True, timeout=30,
        )

    def test_versions_are_anchored_and_invalid_identity_has_no_version_output(self):
        self.command("git", "#!/bin/sh\nexit 0\n")
        for version in ["1.2.3", "1.2.3-rc.1", "12.34.56-rc.78",
                        "1.2.3.4", "1x2x3", "1.2.3-rc.x", "1.2.3-extra",
                        "1.2.3$(touch injected)", "1.2.3\n4.5.6", ""]:
            valid = version in ["1.2.3", "1.2.3-rc.1", "12.34.56-rc.78"]
            check = self.run_step("validate", "Validate version string", VERSION=version)
            self.assertEqual(check.returncode == 0, valid, check.stderr)
            for prefix in ["v", "bindings/go/v"]:
                Path(self.env["GITHUB_OUTPUT"]).write_text("")
                result = self.run_step(
                    "validate", "Resolve tag identity (CI never creates tags)",
                    GITHUB_REF=f"refs/tags/{prefix}{version}",
                )
                self.assertEqual(result.returncode == 0, valid, result.stderr)
                outputs = Path(self.env["GITHUB_OUTPUT"]).read_text().splitlines()
                self.assertEqual(f"version={version}" in outputs, valid)
            self.assertFalse((self.root / "injected").exists())

    def test_outputs_never_interpolated_into_shell_and_permissions_are_scoped(self):
        self.assertEqual(WORKFLOW["permissions"], {"contents": "read"})
        for name, job in WORKFLOW["jobs"].items():
            if name == "package-and-release":
                self.assertEqual(job["permissions"], {"contents": "write"})
            else:
                self.assertNotIn("permissions", job)
            for item in job["steps"]:
                self.assertNotRegex(item.get("run", ""), r"\$\{\{\s*(steps|needs)\.")
                if item.get("uses", "").startswith("actions/checkout@"):
                    self.assertIs(item["with"]["persist-credentials"], False)

    def test_nested_tags_compare_commits_not_annotated_tag_objects(self):
        self.command("git", "#!/usr/bin/env python3\nimport os, sys\n"
                     "if sys.argv[1] == 'rev-parse':\n"
                     "    ref = sys.argv[2]\n"
                     "    if ref.endswith('^{commit}'):\n"
                     "        print('other' if 'bindings/go/' in ref and os.environ['MISMATCH'] == 'yes' else 'commit')\n"
                     "    else:\n        print(ref)\n")
        self.write("bindings/go/go.mod")
        for version in ["1.2.3", "1.2.3-rc.4"]:
            for mismatch in ["yes", "no"]:
                result = self.run_step(
                    "validate", "Verify nested Go module tag resolves to the same revision",
                    IS_MAIN="true", VERSION=version, MISMATCH=mismatch,
                )
                self.assertEqual(result.returncode == 0, mismatch == "no", result.stderr)

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

    def test_checksum_failure_does_not_replace_existing_checksums(self):
        out = "release-staging/syntra-v1.2.3"
        self.write(f"{out}/assets/image.json", "{}")
        sums = self.write(f"{out}/assets/SHA256SUMS", "previous checksums\n")
        self.command("shasum", "#!/bin/sh\nexit 1\n")
        result = self.run_step("package-and-release", "Write SHA256SUMS", OUT=out)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sums.read_text(), "previous checksums\n")

    def test_flat_assets_checksums_and_both_upload_paths_match(self):
        tag = "v1.2.3-rc.4"
        out = f"release-staging/syntra-{tag}"
        for name in ["Cargo.toml", "Cargo.lock", "release-plz.toml", "buf.yaml",
                     "proto/example.proto", "crates/example/Cargo.toml",
                     "bindings/go/go.mod", "conformance/manifest/core.yaml",
                     "conformance/test-vectors/frame.bin", "CHANGELOG.md",
                     "RELEASE.md", "GOVERNANCE.md", "LICENSE"]:
            self.write(name)
        for arch in ["linux-amd64", "linux-arm64"]:
            for name in ["libsyntra_ffi.so", "libsyntra_ffi.a", "syntra_ffi.h"]:
                self.write(f"release-staging/native/{arch}/{name}", arch)
        self.write(f"release-staging/wasm/syntra-wasm-{tag}.tar.gz")
        self.write("release-staging/wasm/syntra_ffi.wasm")
        self.command("cargo", "#!/bin/sh\nexit 1\n")
        self.command("buf", "#!/bin/sh\nset -eu\nif [ \"$1\" = build ]; then\n"
                     "  printf '{}' > \"$3\"\nelse\n  mkdir -p \"$3\"\nfi\n")
        result = self.run_step("package-and-release", "Assemble release payload", TAG=tag)
        self.assertEqual(result.returncode, 0, result.stderr)
        assets = self.root / out / "assets"
        checksums = {}
        for _ in range(2):  # Rewriting checksums must not checksum SHA256SUMS itself.
            result = self.run_step("package-and-release", "Write SHA256SUMS", OUT=out)
            self.assertEqual(result.returncode, 0, result.stderr)
            checksums = dict(line.split("  ", 1)[::-1]
                             for line in (assets / "SHA256SUMS").read_text().splitlines())
            self.assertEqual(set(checksums), {p.name for p in assets.iterdir()} - {"SHA256SUMS"})
            for name, digest in checksums.items():
                self.assertEqual(hashlib.sha256((assets / name).read_bytes()).hexdigest(), digest)
        self.assertIn("image.json", checksums)
        self.assertNotIn("libsyntra_ffi.so", checksums)
        for arch in ["linux-amd64", "linux-arm64"]:
            with tarfile.open(assets / f"syntra-native-{arch}-{tag}.tar.gz") as archive:
                library = archive.extractfile("./libsyntra_ffi.so")
                assert library is not None
                self.assertEqual(library.read().decode(), arch)
        with tarfile.open(assets / f"syntra-schema-{tag}.tar.gz") as archive:
            self.assertIn("manifests/core.yaml", archive.getnames())
            self.assertIn("test-vectors/frame.bin", archive.getnames())
        self.command("git", "#!/bin/sh\nprintf 'commit-sha\\n'\n")
        self.command("gh", "#!/usr/bin/env python3\nimport json, os, sys\n"
                     "if sys.argv[1:3] == ['release', 'view']:\n"
                     "    sys.exit(0 if os.environ['EXISTS'] == 'yes' else 1)\n"
                     "with open(os.environ['UPLOAD_LOG'], 'w') as f:\n"
                     "    json.dump(sys.argv[1:], f)\n")
        for release_tag in [tag, "v1.2.3"]:
            for exists in ["yes", "no"]:
                log = self.root / "upload.json"
                result = self.run_step(
                    "package-and-release", "Attach to GitHub Release (tag already exists; CI creates no tags)",
                    TAG=release_tag, OUT=out, EXISTS=exists, UPLOAD_LOG=str(log),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads(log.read_text())
                uploaded = {Path(arg).name for arg in args if arg.startswith(out + "/assets/")}
                self.assertEqual(uploaded, set(checksums) | {"SHA256SUMS"})
                self.assertEqual("--prerelease" in args, exists == "no" and release_tag == tag)


if __name__ == "__main__":
    unittest.main()
