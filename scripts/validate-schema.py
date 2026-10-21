#!/usr/bin/env python3
"""Run schema tooling and generated-code tests from any working directory.

Requires the versions documented in specifications/schema/generation.md.
Writes only disposable generated/build outputs; never updates baselines/locks.

Committed-generation model (see docs/schema-registry.md §11): `proto/` is
the sole source of truth; pinned `buf generate` output is COMMITTED into
the tree (crates/** for Rust, bindings/go/** for Go) and drift-checked here
and in CI. Distribution uses crates.io, nested Go module tags, and GitHub
Releases (no BSR push). The ignored .tmp/ directory hosts only disposable
reproducibility smoke tests, never the committed output.
"""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TMP_GEN = ROOT / ".tmp" / "bufgen"
GO_OUT = TMP_GEN / "go"
RUST_OUT = TMP_GEN / "rust"

# Committed-generation roots (tracked by design, drift-checked below).
# Go: module bindings/go (import github.com/tinklehq/syntra/bindings/go),
# files under bindings/go/gen/syntra/v1/*.pb.go (paths=source_relative +
# the go_package option in proto/syntra/v1/*.proto).
# Rust: generated prost types under crates/syntra-core/src/generated/*.rs
# (workspace crate syntra-core; compiled in via include!; FFI re-exports via runtime).
COMMITTED_GO_GEN = ROOT / "bindings" / "go" / "gen"
COMMITTED_RUST_GEN = ROOT / "crates" / "syntra-core" / "src" / "generated"

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

# Throwaway Go module for the disposable smoke-test package. The module path
# mirrors the COMMITTED bindings/go module path (derived from the
# go_package option); the directory itself is disposable and ignored. Once
# bindings/go/ lands, codec tests also run against the committed module
# (see repo-validation.yml go-tests); this throwaway module only proves the
# pinned plugins still reproduce byte-identical output.
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


def _tracked_set():
    """Require a Git checkout so untracked output cannot stand in for commits."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                             text=True, timeout=30, check=True)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"Cannot establish tracked generated files: {exc}") from exc
    return set(out.stdout.split("\0")) - {""}


def _collect_committed_files():
    """Collect both required trees, preserving paths and rejecting missing files."""
    tracked = _tracked_set()
    out = {}
    for language, folder, pattern in (
        ("go", COMMITTED_GO_GEN, "*.pb.go"),
        ("rust", COMMITTED_RUST_GEN, "*.rs"),
    ):
        prefix = folder.relative_to(ROOT).as_posix() + "/"
        paths = set(folder.rglob(pattern))
        paths.update(ROOT / name for name in tracked
                     if name.startswith(prefix) and Path(name).match(pattern))
        for path in sorted(paths):
            rel = path.relative_to(ROOT).as_posix()
            if rel not in tracked:
                raise SystemExit(f"Generated file is not git-tracked: {rel}")
            if not path.is_file() or path.is_symlink():
                raise SystemExit(f"Tracked generated file is missing or not a regular file: {rel}")
            out[f"{language}/{path.relative_to(folder).as_posix()}"] = path.read_bytes()
    return out


def _collect_fresh_files():
    """Return {suffix -> bytes} for the just-generated .tmp output."""
    out = {}
    go_gen = GO_OUT / "gen"
    rust_gen = RUST_OUT / "gen"
    if go_gen.is_dir():
        for path in go_gen.rglob("*.pb.go"):
            out["go/" + path.relative_to(go_gen).as_posix()] = path.read_bytes()
    if rust_gen.is_dir():
        for path in rust_gen.rglob("*.rs"):
            out["rust/" + path.relative_to(rust_gen).as_posix()] = path.read_bytes()
    return out


def generate_to_tmp():
    """Generate into ignored .tmp/ and return the fresh file map."""
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
    return _collect_fresh_files()


def check_drift(fresh=None):
    """Diff pinned regeneration against both required committed trees, fail closed."""
    if fresh is None:
        fresh = generate_to_tmp()
    committed = _collect_committed_files()
    for label, files in (("fresh", fresh), ("committed", committed)):
        for language in ("go", "rust"):
            if not any(key.startswith(language + "/") for key in files):
                raise SystemExit(f"Missing {label} {language} generated types")
    errors = []
    for key, fresh_bytes in sorted(fresh.items()):
        if key not in committed:
            # New file from a schema change: maintainer must commit it.
            errors.append(f"uncommitted generated file: {key} "
                          "(run buf generate --template buf.gen.yaml and commit)")
        elif committed[key] != fresh_bytes:
            errors.append(f"drift in committed generated file: {key} "
                          f"(committed output is stale; regenerate and commit)")
    for key in sorted(committed):
        if key not in fresh:
            errors.append(f"stale committed file with no generated counterpart: {key} "
                          f"(remove it or regenerate)")
    if errors:
        print(f"\n{len(errors)} committed-generation drift error(s):", flush=True)
        for e in errors:
            print(f"  {e}", flush=True)
        raise SystemExit("Committed generated types are stale; see errors above")
    print(f"Committed generation fresh: {len(committed)} files match pinned output",
          flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Syntra schema validation (committed-generation model)")
    parser.add_argument("--drift-only", action="store_true",
                        help="only regenerate into .tmp/ and diff against "
                             "the committed crates//bindings/go/ trees")
    args = parser.parse_args()
    version = subprocess.check_output(["buf", "--version"], text=True, timeout=10).strip()
    if version != "1.59.0":
        raise SystemExit(f"Expected Buf 1.59.0, got {version}; use the documented toolchain")
    if args.drift_only:
        run(["buf", "format", "--diff", "--exit-code"])
        run(["buf", "lint"])
        run(["buf", "build"])
        check_drift(generate_to_tmp())
        return
    run(["buf", "format", "--diff", "--exit-code"])
    run(["buf", "lint"])
    run(["buf", "build"])
    # Generate language bindings into the ignored temp directory for
    # reproducibility + drift comparison (committed output is compared, never
    # overwritten here — maintainers commit regeneration explicitly).
    fresh = generate_to_tmp()
    check_drift(fresh)
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests/schema", "-p", "test_*.py", "-v"])
    # Throwaway Go module hosting the generated package for compile checks.
    (GO_OUT / "go.mod").write_text(GO_MOD)
    run(["go", "mod", "tidy"], GO_OUT)
    run(["go", "build", "./..."], GO_OUT)
    run(["go", "test", "-mod=readonly", "-count=1", "-v", "./..."], ROOT / "tests/schema/go")
    run(["cargo", "test", "--locked"], ROOT / "tests/schema/rust")


if __name__ == "__main__":
    main()
