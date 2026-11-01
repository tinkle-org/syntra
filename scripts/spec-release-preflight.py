#!/usr/bin/env python3
"""Read-only input and Git checks for the draft specification release process.

This does not check release authorization, required evidence, environment
protection, or the remote tag state. It must not be used to authorize or
publish a release. See Draft RFC 0011.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


TAG = re.compile(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-rc[1-9][0-9]*)?\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


class PreflightError(ValueError):
    """An input or Git preflight check failed."""


def validate_tag(tag):
    """Validate the proposed tag syntax and return whether it is a candidate."""
    if not isinstance(tag, str) or not TAG.fullmatch(tag):
        raise PreflightError("tag must use vMAJOR.MINOR or vMAJOR.MINOR-rcN")
    return "-rc" in tag


def validate_sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise PreflightError("commit must be a full lowercase 40-character Git SHA")
    return value


def git(repo, *args, allowed=(0,)):
    try:
        result = subprocess.run(["git", *args], cwd=repo, text=True,
                                capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(f"unable to run Git: {exc}") from exc
    if result.returncode not in allowed:
        raise PreflightError(f"Git check failed: {args[0]} (exit {result.returncode})")
    return result


def verify_candidate(repo, tag, target, trusted_head, allow_existing=False):
    candidate = validate_tag(tag)
    validate_sha(target)
    validate_sha(trusted_head)

    head = git(repo, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    if head != trusted_head:
        raise PreflightError("trusted head must equal the checked-out HEAD")

    resolved = git(repo, "rev-parse", "--verify", f"{target}^{{commit}}").stdout.strip()
    if resolved != target:
        raise PreflightError("target must name a commit directly")

    ancestry = git(repo, "merge-base", "--is-ancestor", target, trusted_head,
                   allowed=(0, 1))
    if ancestry.returncode != 0:
        raise PreflightError("target is not an ancestor of the trusted head")

    existing = git(repo, "show-ref", "--verify", "--quiet", f"refs/tags/{tag}",
                   allowed=(0, 1))
    if existing.returncode == 0:
        if not allow_existing:
            raise PreflightError("tag already exists locally")
        actual = git(repo, "rev-parse", "--verify", f"refs/tags/{tag}").stdout.strip()
        if actual != target:
            raise PreflightError("existing tag does not directly name the target commit")

    return {"tag": tag, "target": target, "trusted_head": trusted_head,
            "candidate": candidate, "authorized": False, "published": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--trusted-head", required=True)
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = verify_candidate(args.repo, args.tag, args.target, args.trusted_head,
                                  allow_existing=args.recovery)
    except PreflightError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    print("Read-only rehearsal: no approval, evidence, remote tag or release was checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
