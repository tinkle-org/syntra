#!/usr/bin/env python3
"""Run schema validation from any working directory.

Requires the versions documented in specifications/schema/generation.md.
Read-only over proto/, compatibility/, and tests/schema; writes nothing.

This repository is specification-first: `proto/` is the sole IDL source of
truth and no language bindings are committed or generated here. Regenerating
Rust/Go types is a downstream responsibility owned by the implementation
repositories (tinkle-org/syntra-rs, tinkle-org/syntra-go), which pin the
generator template documented in specifications/schema/generation.md.
"""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "compatibility" / "v1-initial" / "image.json"


def run(args, cwd=ROOT, timeout=180):
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run(args, cwd=cwd, check=True, timeout=timeout)


def main():
    version = subprocess.check_output(["buf", "--version"], text=True, timeout=10).strip()
    if version != "1.59.0":
        raise SystemExit(f"Expected Buf 1.59.0, got {version}; use the documented toolchain")
    if not BASELINE.is_file():
        raise SystemExit(f"Missing compatibility baseline: {BASELINE}")
    run(["buf", "format", "--diff", "--exit-code"])
    run(["buf", "lint"])
    run(["buf", "build"])
    run(["buf", "breaking", "--against", str(BASELINE)])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests/schema", "-p", "test_*.py", "-v"])


if __name__ == "__main__":
    main()
