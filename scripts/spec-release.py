#!/usr/bin/env python3
"""Tag an explicitly approved specification release; see RELEASE.md.

Publication requires a protected environment, a public SHA-bound decision,
successful validation of the target and an environment-scoped write token.
This tool cannot judge conformance evidence or resolve unstructured objections.
"""

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("preflight", ROOT / "scripts/spec-release-preflight.py")
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)
REPO = "tinkle-org/syntra"
PREFIX = f"/repos/{REPO}"


class ReleaseError(ValueError):
    """Release validation or publication failed."""


def parse_roster(text):
    roster = set()
    pattern = re.compile(r"^\|\s*\[([A-Za-z0-9-]+)\]\(https://github\.com/([A-Za-z0-9-]+)\)\s*\|\s*Active maintainer\b")
    for line in text.splitlines():
        if "Active maintainer" not in line:
            continue
        match = pattern.match(line)
        if not match or match.group(1).lower() != match.group(2).lower():
            raise ReleaseError("unparseable active maintainer row")
        login = match.group(1).lower()
        if login in roster:
            raise ReleaseError("duplicate active maintainer")
        roster.add(login)
    if not roster:
        raise ReleaseError("no active maintainer")
    return roster


def verify_environment(environment, policies, roster):
    if environment.get("name") != "spec-release":
        raise ReleaseError("missing release environment")
    branch_policy = environment.get("deployment_branch_policy")
    if branch_policy != {"protected_branches": False, "custom_branch_policies": True}:
        raise ReleaseError("environment requires explicit branch policies")
    if len(policies) != 1 or policies[0].get("type") != "branch" or policies[0].get("name") != "main":
        raise ReleaseError("environment must allow only the main branch")
    rules = [x for x in environment.get("protection_rules", []) if x.get("type") == "required_reviewers"]
    if len(rules) != 1 or not rules[0].get("reviewers"):
        raise ReleaseError("environment must require a maintainer reviewer")
    for item in rules[0]["reviewers"]:
        login = item.get("reviewer", {}).get("login", "").lower()
        if item.get("type") != "User" or login not in roster:
            raise ReleaseError("environment reviewer is not an active maintainer")
    if len(roster) == 1 and rules[0].get("prevent_self_review") is not False:
        raise ReleaseError("sole maintainer must be allowed to self-approve")


def issue_fields(body):
    names = ("Tag", "Commit", "Scope", "Freeze", "Evidence", "Security", "Objections", "Self-Review")
    fields = {}
    for line in body.splitlines():
        match = re.fullmatch(r"Release-([A-Za-z-]+):\s*(\S.*)", line)
        if match and match.group(1) in names:
            key, value = match.groups()
            if key in fields:
                raise ReleaseError(f"duplicate Release-{key}")
            fields[key] = value.strip()
    if set(fields) != set(names):
        raise ReleaseError("release decision is missing required fields")
    return fields


def verify_authorization(issue, comments, roster, tag, sha):
    candidate = PREFLIGHT.validate_tag(tag)
    PREFLIGHT.validate_sha(sha)
    if issue.get("state") != "open" or not isinstance(issue.get("body"), str):
        raise ReleaseError("release decision must be an open public issue")
    body = issue["body"]
    fields = issue_fields(body)
    if fields["Tag"] != tag or fields["Commit"] != sha:
        raise ReleaseError("release decision does not match tag and commit")
    if not candidate:
        for key in ("Freeze", "Evidence", "Security"):
            url = parse.urlparse(fields[key])
            if url.scheme != "https" or not url.netloc:
                raise ReleaseError(f"stable release requires an HTTPS {key} evidence link")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    states = {}
    ordered = []
    for comment in comments:
        user = comment.get("user") or {}
        login = user.get("login", "").lower()
        text = comment.get("body")
        if user.get("type") != "User" or login not in roster or not isinstance(text, str):
            continue
        text = text.strip()
        if not text.startswith("SYNTRA-"):
            continue
        try:
            timestamp = datetime.fromisoformat(comment["updated_at"].replace("Z", "+00:00"))
            ident = int(comment["id"])
            if timestamp.utcoffset() is None:
                raise ValueError("timezone required")
        except (KeyError, TypeError, ValueError) as exc:
            raise ReleaseError("malformed maintainer decision timestamp") from exc
        ordered.append((timestamp, ident, login, text))
    for _, _, login, text in sorted(ordered):
        parts = text.split()
        if len(parts) >= 3 and parts[:3] == ["SYNTRA-OBJECT", tag, sha]:
            states[login] = "object"
        elif len(parts) >= 3 and parts[:3] == ["SYNTRA-APPROVE", tag, sha]:
            if len(parts) == 4 and parts[3] == digest:
                states[login] = "approve"
            elif states.get(login) != "object":
                states[login] = "stale"
        elif text.startswith(("SYNTRA-APPROVE", "SYNTRA-OBJECT")):
            # Decisions for other versions do not approve this one.
            continue
    if "object" in states.values():
        raise ReleaseError("unresolved maintainer objection")
    approved = {login for login, state in states.items() if state == "approve"}
    if len(approved) < (1 if len(roster) == 1 else 2):
        raise ReleaseError("insufficient revision-bound maintainer approvals")
    author = (issue.get("user") or {}).get("login", "").lower()
    if author in approved and fields["Self-Review"].lower() != "yes":
        raise ReleaseError("self-review must be disclosed")
    return approved


def extract_notes(changelog, tag):
    heading = re.compile(rf"^## \[{re.escape(tag)}\](?:[ \t].*)?$", re.MULTILINE)
    matches = list(heading.finditer(changelog))
    if len(matches) != 1:
        raise ReleaseError("changelog must have exactly one matching release section")
    start = matches[0].end()
    following = re.search(r"^## ", changelog[start:], re.MULTILINE)
    end = start + following.start() if following else len(changelog)
    notes = changelog[start:end].strip()
    if not notes:
        raise ReleaseError("release notes are empty")
    return notes


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReleaseError("GitHub API redirect refused")


class GitHub:
    def __init__(self, token):
        if not token:
            raise ReleaseError("required GitHub token is not configured")
        self.token = token
        self.opener = request.build_opener(NoRedirect())

    def call(self, method, path, data=None, missing=False):
        if not path.startswith(PREFIX + "/"):
            raise ReleaseError("invalid API path")
        payload = json.dumps(data).encode() if data is not None else None
        req = request.Request("https://api.github.com" + path, data=payload, method=method,
                              headers={"Authorization": "Bearer " + self.token,
                                       "Accept": "application/vnd.github+json",
                                       "Content-Type": "application/json",
                                       "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with self.opener.open(req, timeout=30) as response:
                return json.load(response)
        except error.HTTPError as exc:
            if missing and exc.code == 404:
                return None
            raise ReleaseError(f"GitHub API request failed with HTTP {exc.code}") from exc
        except (OSError, ValueError) as exc:
            raise ReleaseError("GitHub API request failed") from exc

    def pages(self, path, key=None):
        result = []
        for page in range(1, 51):
            value = self.call("GET", f"{path}?per_page=100&page={page}")
            if value is None:
                raise ReleaseError("missing paginated API response")
            if key and not isinstance(value, dict):
                raise ReleaseError("invalid paginated API response")
            items = value.get(key) if key else value
            if not isinstance(items, list):
                raise ReleaseError("invalid paginated API response")
            result.extend(items)
            if len(items) < 100:
                return result
        raise ReleaseError("GitHub API pagination limit exceeded")


def decision(api, issue_number, tag, sha, roster):
    issue = api.call("GET", f"{PREFIX}/issues/{issue_number}")
    comments = api.pages(f"{PREFIX}/issues/{issue_number}/comments")
    verify_authorization(issue, comments, roster, tag, sha)
    return issue


def verify_main(api, trusted_head):
    if api.call("GET", f"{PREFIX}/commits/main").get("sha") != trusted_head:
        raise ReleaseError("main changed since dispatch; rerun validation")


def publish(read_api, write_api, tag, sha, trusted_head, issue_number, recovery=False):
    if not re.search(r"^- Status: Accepted\s*$", (ROOT / "rfcs/0011-specification-release-versioning.md").read_text(), re.MULTILINE):
        raise ReleaseError("RFC 0011 is not accepted on trusted main")
    roster = parse_roster((ROOT / "MAINTAINERS.md").read_text())
    verify_main(read_api, trusted_head)
    environment = read_api.call("GET", f"{PREFIX}/environments/spec-release")
    policies = read_api.pages(f"{PREFIX}/environments/spec-release/deployment-branch-policies", "branch_policies")
    verify_environment(environment, policies, roster)
    issue = decision(read_api, issue_number, tag, sha, roster)
    digest = hashlib.sha256(issue["body"].encode("utf-8")).hexdigest()
    extract_notes(PREFLIGHT.git(ROOT, "show", f"{sha}:CHANGELOG.md").stdout, tag)
    candidate = PREFLIGHT.validate_tag(tag)
    _ = candidate
    ref = read_api.call("GET", f"{PREFIX}/git/ref/tags/{tag}", missing=True)
    if recovery:
        if not ref or ref.get("object", {}).get("sha") != sha or ref["object"].get("type") != "commit":
            raise ReleaseError("recovery requires the existing tag at the approved commit")
    elif ref:
        raise ReleaseError("tag already exists")
    verify_main(read_api, trusted_head)
    if hashlib.sha256(decision(read_api, issue_number, tag, sha, roster)["body"].encode()).hexdigest() != digest:
        raise ReleaseError("release decision changed during validation")
    if not ref:
        write_api.call("POST", f"{PREFIX}/git/refs", {"ref": f"refs/tags/{tag}", "sha": sha})
    current = read_api.call("GET", f"{PREFIX}/git/ref/tags/{tag}")
    if current.get("object", {}).get("sha") != sha or current["object"].get("type") != "commit":
        raise ReleaseError("tag changed after creation")
    verify_main(read_api, trusted_head)
    if hashlib.sha256(decision(read_api, issue_number, tag, sha, roster)["body"].encode()).hexdigest() != digest:
        raise ReleaseError("release decision changed after tag creation")
    print(f"Tagged {tag}: {sha}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("approval", "publish"))
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--trusted-head", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--recovery", action="store_true")
    args = parser.parse_args()
    try:
        if args.issue < 1 or args.issue > 2_147_483_647:
            raise ReleaseError("invalid issue number")
        PREFLIGHT.validate_tag(args.tag)
        PREFLIGHT.validate_sha(args.target)
        read_api = GitHub(os.environ.get("GITHUB_TOKEN", ""))
        if args.action == "approval":
            issue = read_api.call("GET", f"{PREFIX}/issues/{args.issue}")
            if issue is None:
                raise ReleaseError("release decision not found")
            fields = issue_fields(issue.get("body") or "")
            if fields["Tag"] != args.tag or fields["Commit"] != args.target:
                raise ReleaseError("release decision does not match tag and commit")
            digest = hashlib.sha256(issue["body"].encode("utf-8")).hexdigest()
            print(f"SYNTRA-APPROVE {args.tag} {args.target} {digest}")
        else:
            if os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_REF") != "refs/heads/main":
                raise ReleaseError("publication requires upstream main")
            PREFLIGHT.validate_sha(args.trusted_head)
            PREFLIGHT.verify_candidate(ROOT, args.tag, args.target, args.trusted_head,
                                       allow_existing=args.recovery)
            publish(read_api, GitHub(os.environ.get("SPEC_RELEASE_TOKEN", "")), args.tag,
                    args.target, args.trusted_head, args.issue, args.recovery)
    except (ReleaseError, PREFLIGHT.PreflightError) as exc:
        print(f"release failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
