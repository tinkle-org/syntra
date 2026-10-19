#!/usr/bin/env python3
"""Run schema tooling and generated-code tests from any working directory.

Requires the versions documented in specifications/schema/generation.md.
Writes only disposable generated/build outputs; never updates baselines/locks.

Codecs smoke tests generate language bindings into the ignored .tmp/
directory (never into the repository tree) and run the neutral codec
fixtures against them. No generated source is committed; see
docs/schema-registry.md §11 and specifications/schema/generation.md.
"""

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TMP_GEN = ROOT / ".tmp" / "bufgen"
GO_OUT = TMP_GEN / "go"
RUST_OUT = TMP_GEN / "rust"

# Pinned generation template. Versions and revisions MUST match the pin
# table in specifications/schema/generation.md; change them together.
GENERATE_TEMPLATE = """\
version: v2
clean: true
plugins:
  - remote: buf.build/community/neoeinstein-prost:v0.4.0
    revision: 1
    out: .tmp/bufgen/rust/gen
  - remote: buf.build/protocolbuffers/go:v1.36.6
    revision: 1
    out: .tmp/bufgen/go/gen
    opt:
      - paths=source_relative
"""

# Throwaway Go module for the generated smoke-test package. The module path
# mirrors the published go_package option (the generated import path is
# derived from it); the directory itself is disposable and ignored.
GO_MOD = """\
module github.com/tinklehq/syntra/bindings/go

go 1.22

require google.golang.org/protobuf v1.36.6
"""


def run(args, cwd=ROOT, timeout=180):
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run(args, cwd=cwd, check=True, timeout=timeout)


def generated_hashes():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for folder in (GO_OUT, RUST_OUT)
        for path in folder.rglob("*") if path.is_file() and path.suffix not in (".mod", ".sum")
    }


def main():
    version = subprocess.check_output(["buf", "--version"], text=True, timeout=10).strip()
    if version != "1.59.0":
        raise SystemExit(f"Expected Buf 1.59.0, got {version}; use the documented toolchain")
    run(["buf", "format", "--diff", "--exit-code"])
    run(["buf", "lint"])
    run(["buf", "build"])
    # Generate language bindings into the ignored temp directory only.
    if TMP_GEN.exists():
        shutil.rmtree(TMP_GEN)
    TMP_GEN.mkdir(parents=True)
    template = TMP_GEN / "buf.gen.ci.yaml"
    template.write_text(GENERATE_TEMPLATE)
    run(["buf", "generate", "--template", str(template)])
    first = generated_hashes()
    if not any(name.endswith(".rs") for name in first) or not any(name.endswith(".pb.go") for name in first):
        raise SystemExit("Missing Rust or Go generated types")
    # Re-run to prove byte-reproducible generation with pinned plugins.
    run(["buf", "generate", "--template", str(template)])
    if first != generated_hashes():
        raise SystemExit("Generation is not byte-reproducible with the pinned plugins")
    print(f"Reproducible generation: {len(first)} files", flush=True)
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests/schema", "-p", "test_*.py", "-v"])
    # Throwaway Go module hosting the generated package for compile checks.
    (GO_OUT / "go.mod").write_text(GO_MOD)
    run(["go", "mod", "tidy"], GO_OUT)
    run(["go", "build", "./..."], GO_OUT)
    run(["go", "test", "-mod=readonly", "-count=1", "-v", "./..."], ROOT / "tests/schema/go")
    run(["cargo", "test", "--locked"], ROOT / "tests/schema/rust")


if __name__ == "__main__":
    main()
