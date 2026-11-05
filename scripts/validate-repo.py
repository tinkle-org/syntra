#!/usr/bin/env python3
"""Syntra repository validation (release-candidate gate).

Repository tooling only — NOT a Syntra protocol implementation. Validates
documents, manifests, and fixtures with the standard library plus PyYAML;
protobuf bytes are checked with a minimal stdlib wire walker keyed off the
published .proto sources (and cross-checked with protoc when available).

Usage:
    python3 scripts/validate-repo.py all
    python3 scripts/validate-repo.py requirements manifests vectors links rfcs markdown boundary

Exit status: 0 when every selected check passes, 1 otherwise. Errors print
as `path[:line]: message` so CI logs point at the defect.
"""

import base64
import binascii
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required (pip install pyyaml)")

ROOT = Path(__file__).resolve().parents[1]
ERRORS = []
_OWNER_SPEC = importlib.util.spec_from_file_location(
    "conformance_owners", Path(__file__).with_name("sync-conformance-owners.py"))
assert _OWNER_SPEC is not None and _OWNER_SPEC.loader is not None
OWNERS = importlib.util.module_from_spec(_OWNER_SPEC)
_OWNER_SPEC.loader.exec_module(OWNERS)

REQ_PATTERN = re.compile(r"\bSNTR-[A-Z]+-\d+[A-Z]*\b|\bSYN-ARCH-\d+\b|\bSYN-URP-\d+\b")
# Naming pattern for structured references (manifest rows, defined IDs).
# Prose mentions keep the freeform REQ_PATTERN below. Reserved SYN-URP-008/009
# are excluded from structured naming and rejected explicitly by the checks.
REQ_NAMING = re.compile(r"^(SNTR-[A-Z]+-\d+[A-Z]*|SYN-ARCH-\d+"
                       r"|SYN-URP-(?:[1-9][0-9]{2,}|0(?:0[1-7]|[1-9][0-9])))$")
BOLD_DEF = re.compile(r"\*\*(SNTR-[A-Z]+-\d+[A-Z]*|SYN-ARCH-\d+|SYN-URP-\d+)\b")
# Reserved recovery IDs (RFC 0006): SYN-URP-008/009 stay unassigned and are
# intentionally NOT registered in requirements.yaml, but the conversation and
# schema text may mention them as reserved.
RESERVED_REQUIREMENTS = {"SYN-URP-008", "SYN-URP-009"}
# Directories that are tool output, vendored deps, or agent config — never
# normative content. Markdown/link checks are scoped to repository content.
# Specification-first policy: no implementation code and no generated language
# types are committed here (implementations are separate projects, out of
# scope for this repository; see MIGRATION.md §10). Legacy gen//generated/ trees
# and implementation roots must not exist at all (see the boundary check).
# The exclusions below are defense in depth so doc checks stay quiet if such
# a tree ever reappears; boundary still fails.
EXCLUDED_PARTS = {".git", ".hg", ".agents", ".opencode", "node_modules", "gen",
                  "generated", "dist", "target", ".venv", "__pycache__",
                  ".tmp"}


def is_content_path(path):
    parts = Path(path).parts
    if any(p in EXCLUDED_PARTS for p in parts):
        return False
    if parts[0] in ("crates", "bindings") if parts else False:
        return False
    return True


PROFILE_PATTERN = re.compile(r"\bSNTR-[A-Z0-9]+(?:-[A-Z0-9]+)*-V1\b|\bSYNTRA-1\.0-[A-Z]+\b")
PROFILE_KINDS = {
    "SNTR-CORE-V1": "MANDATORY_CORE",
    "SNTR-SESS-V1": "MANDATORY_CORE",
    "SNTR-RPC-V1": "MANDATORY_CORE",
    "SNTR-EVENTS-V1": "OPTIONAL_CAPABILITY",
    "SYNTRA-1.0-TCP": "TRANSPORT_PROFILE",
    "SYNTRA-1.0-WS": "TRANSPORT_PROFILE",
    "SYNTRA-1.0-WSS": "TRANSPORT_PROFILE",
}
KNOWN_PROFILES = set(PROFILE_KINDS)
CASE_ID = re.compile(r"^CONF-[A-Z]+-[0-9]+$")
KNOWN_CAPABILITIES = {"syntra.update-recovery/1"}
KNOWN_AUTOMATION = {"automated", "partially_automated", "manual", "not_testable"}
KNOWN_ROLES = {"client", "server"}
KNOWN_CONN_STATES = {"CONNECTED", "NEGOTIATING", "AUTHENTICATING", "ACTIVE", "CLOSING", "CLOSED"}
KNOWN_SESS_STATES = {"none", "active", "unchanged", "terminated_normally",
                     "terminated_abnormally", "withdrawn"}
KNOWN_RFC_STATUS = {"Draft", "Review", "Discussion", "Implementing", "Implemented",
                    "Accepted", "Rejected", "Withdrawn", "Superseded"}


def err(path, msg, line=None):
    loc = str(path)
    if line is not None:
        loc += f":{line}"
    ERRORS.append(f"{loc}: {msg}")


# --------------------------------------------------------------------------
# .proto model (parsed from the published schema sources)
# --------------------------------------------------------------------------

def parse_proto_model():
    """Parse message->{field: number} and enum names from proto/syntra/v1."""
    messages, enums = {}, {}
    proto_dir = ROOT / "proto" / "syntra" / "v1"
    for f in sorted(proto_dir.glob("*.proto")):
        text = f.read_text()
        for m in re.finditer(r"message\s+(\w+)\s*\{(.*?)\n\}", text, re.S):
            name, body = m.group(1), m.group(2)
            fields = {}
            for fm in re.finditer(r"(?:repeated\s+|optional\s+)?[\w.]+\s+(\w+)\s*=\s*(\d+)", body):
                # skip oneof member lines handled the same way (name = number) — good
                fields[fm.group(1)] = int(fm.group(2))
            messages[name] = fields
        for m in re.finditer(r"enum\s+(\w+)\s*\{(.*?)\n\}", text, re.S):
            name, body = m.group(1), m.group(2)
            vals = {}
            for vm in re.finditer(r"(\w+)\s*=\s*(-?\d+)", body):
                vals[vm.group(1)] = int(vm.group(2))
            enums[name] = vals
    return messages, enums


# --------------------------------------------------------------------------
# Minimal protobuf binary walker (stdlib only)
# --------------------------------------------------------------------------

def read_varint(buf, pos):
    result, shift = 0, 0
    while True:
        if pos >= len(buf):
            raise ValueError("truncated varint")
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
        if shift >= 64:
            raise ValueError("varint overflow")


def walk_fields(buf):
    """Return [(field_no, wire_type, value)] where value is int or bytes."""
    fields, pos = [], 0
    while pos < len(buf):
        key, pos = read_varint(buf, pos)
        field_no, wire_type = key >> 3, key & 0x07
        if field_no == 0:
            raise ValueError("field number 0 is illegal")
        if wire_type == 0:
            val, pos = read_varint(buf, pos)
        elif wire_type == 1:
            if pos + 8 > len(buf):
                raise ValueError("truncated fixed64")
            val, pos = buf[pos:pos + 8], pos + 8
        elif wire_type == 2:
            length, pos = read_varint(buf, pos)
            if pos + length > len(buf):
                raise ValueError("truncated length-delimited field")
            val, pos = buf[pos:pos + length], pos + length
        elif wire_type == 5:
            if pos + 4 > len(buf):
                raise ValueError("truncated fixed32")
            val, pos = buf[pos:pos + 4], pos + 4
        else:
            raise ValueError(f"unsupported wire type {wire_type}")
        fields.append((field_no, wire_type, val))
    return fields


def field_map(buf):
    """Map field_no -> list of (wire_type, value)."""
    out = {}
    for no, wt, val in walk_fields(buf):
        out.setdefault(no, []).append((wt, val))
    return out


# --------------------------------------------------------------------------
# Shared loaders
# --------------------------------------------------------------------------

def load_manifest_cases():
    """Return (cases_by_id, requirements_refs). cases: id -> (file, case)."""
    cases, req_refs = {}, []
    for mf in sorted((ROOT / "conformance" / "manifest").glob("*.yaml")):
        if mf.name in ("schema.yaml", "requirements.yaml"):
            continue
        data = yaml.safe_load(mf.read_text())
        if not isinstance(data, dict):
            err(mf, "manifest file must be a map")
            continue
        entries = data.get("cases")
        profiles = data.get("profile")
        profiles = profiles if isinstance(profiles, list) else [profiles]
        if not profiles or any(not _is_allowed_string(p, KNOWN_PROFILES) for p in profiles):
            err(mf, f"manifest references unknown profile {data.get('profile')!r}")
        if "selection_status" in data:
            err(mf, "selection_status is not part of the current manifest format")
        if not isinstance(entries, list):
            err(mf, "cases must be a list of case maps")
            continue
        for case in entries:
            if not isinstance(case, dict):
                err(mf, f"case entry must be a map, got {type(case).__name__}")
                continue
            cid = case.get("id")
            if not isinstance(cid, str):
                err(mf, f"case entry must have a string id, got {cid!r}")
                continue
            if cid in cases:
                err(mf, f"duplicate test ID {cid} (also in {cases[cid][0].name})")
            cases[cid] = (mf, case)
            req_field = case.get("requirement")
            for r in (req_field if isinstance(req_field, list) else []):
                req_refs.append((r, mf, cid))
    return cases, req_refs


def load_requirements():
    path = ROOT / "conformance/manifest/requirements.yaml"
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        err(path, "requirements file must contain a requirements list")
        return []
    rows = []
    for row in data["requirements"]:
        if not isinstance(row, dict):
            err(path, "requirement entry must be a map")
        elif not isinstance(row.get("requirement_id"), str):
            err(path, "requirement entry must have a string requirement_id")
        else:
            rows.append(row)
    return rows


# --------------------------------------------------------------------------
# Check: requirement IDs
# --------------------------------------------------------------------------

def check_requirements():
    defined = {}  # id -> [(file, line)]
    sections = {}
    for rid, definitions in OWNERS.owner_definitions(ROOT).items():
        defined[rid] = [(path, line) for path, line, _ in definitions]
        sections[rid] = {heading for _, _, heading in definitions}
    for rid, locs in sorted(defined.items()):
        if not REQ_NAMING.match(rid):
            err(locs[0][0], f"requirement ID violates naming convention: {rid}", locs[0][1])
        if len(locs) > 1:
            where = ", ".join(f"{p}:{ln}" for p, ln in locs)
            err(locs[0][0], f"requirement ID {rid} defined {len(locs)} times: {where}", locs[0][1])

    reqs = load_requirements()
    cases, _ = load_manifest_cases()
    seen_ids = set()
    for r in reqs:
        rid = r.get("requirement_id")
        if not isinstance(rid, str):
            err("conformance/manifest/requirements.yaml", f"bad requirement_id format: {rid!r}")
            continue
        if rid in seen_ids:
            err("conformance/manifest/requirements.yaml", f"duplicate requirement_id {rid}")
        seen_ids.add(rid)
        if not REQ_NAMING.match(rid or ""):
            err("conformance/manifest/requirements.yaml", f"bad requirement_id format: {rid}")
        if rid in RESERVED_REQUIREMENTS:
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} is reserved and MUST NOT be registered")
        if rid not in defined:
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} has no bold definition in a current owner")
        spec = r.get("specification")
        if not isinstance(spec, str) or not spec:
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} needs a current owner path")
        elif not (ROOT / spec).is_file():
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} references missing document {spec}")
        elif spec and rid in defined and not any(str(p) == spec for p, _ in defined[rid]):
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} is not defined by its declared owner {spec}")
        section = r.get("section")
        if rid in sections and (not isinstance(section, str) or section not in sections[rid]):
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} has stale section {r.get('section')!r}")
        if not _is_allowed_string(r.get("automation_status"), KNOWN_AUTOMATION):
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} has invalid automation_status {r.get('automation_status')}")
        tests = r.get("test_ids")
        if not isinstance(tests, list):
            err("conformance/manifest/requirements.yaml", f"requirement_id {rid} test_ids must be a list")
            continue
        if not tests:
            if not _is_allowed_string(r.get("automation_status"), {"manual", "not_testable"}):
                err("conformance/manifest/requirements.yaml", f"requirement_id {rid} without tests needs a manual/not_testable disposition")
            if not isinstance(r.get("notes"), str) or not r["notes"].strip():
                err("conformance/manifest/requirements.yaml", f"requirement_id {rid} without tests needs explanatory notes")
        for t in tests:
            if not isinstance(t, str) or not CASE_ID.fullmatch(t):
                err("conformance/manifest/requirements.yaml", f"requirement_id {rid} has invalid test ID {t!r}")
            elif t not in cases:
                err("conformance/manifest/requirements.yaml",
                    f"requirement_id {rid} references unknown test {t}")
            elif not isinstance(cases[t][1].get("requirement"), list) or rid not in cases[t][1]["requirement"]:
                err("conformance/manifest/requirements.yaml",
                    f"requirement_id {rid} references test {t} without a reciprocal requirement ref")
    # every defined spec ID should appear in requirements.yaml (no silent gaps)
    for rid in sorted(defined):
        if rid not in seen_ids:
            err("conformance/manifest/requirements.yaml",
                f"defined requirement {rid} has no traceability row")
    print(f"requirements: {len(seen_ids)} rows, {len(defined)} defined IDs")


# --------------------------------------------------------------------------
# Check: manifests
# --------------------------------------------------------------------------

# Two-observer expectations follow specifications/connection.md and the
# manifest schema: detecting-side
# error discriminators and transport-native peer-observation entries.
TRANSPORT_FAMILIES = {"tcp_tls", "ws_wss"}
PEER_SIGNALS = {"transport_close", "ws_close", "http_status", "connection_loss"}
WS_CLOSE_CODES = {1000, 1001, 1002, 1003, 1007, 1008, 1009, 1011}
GENERIC_LOCAL_REPORTS = {"generic_protocol_rejection", "generic_policy_rejection"}
ERROR_OBSERVERS = {"detecting_host", "detecting_peer"}
ERROR_CARRIAGE = {"local_only", "wire"}


def _is_allowed_string(value, allowed):
    """Accept only YAML strings in a known vocabulary; lists/maps are invalid."""
    return isinstance(value, str) and value in allowed


def _is_local_report(value, error_codes):
    return (_is_allowed_string(value, error_codes)
            or _is_allowed_string(value, GENERIC_LOCAL_REPORTS))


def check_transport_expectation(mf, cid, tmap, error_codes):
    """Validate the documented two-observer keys inside an ``expected.transport``
    map; unrelated transport-specific keys stay free-form as before.

    Callers pass this only for a *present* ``transport`` key (absent keys are
    skipped by the caller); a present key whose value is null is rejected here
    rather than silently skipped."""
    if not isinstance(tmap, dict):
        err(mf, f"case {cid} expected.transport must be a map")
        return
    peer = tmap.get("peer_observation")
    if peer is not None:
        if not isinstance(peer, dict) or not all(
                isinstance(v, dict) for v in peer.values()):
            err(mf, f"case {cid} expected.transport.peer_observation "
                    "must be a map of transport-family maps")
        else:
            for fam in sorted(peer, key=str):
                obs = peer[fam]
                if not _is_allowed_string(fam, TRANSPORT_FAMILIES):
                    err(mf, f"case {cid} peer_observation references "
                            f"unknown transport family {fam}")
                unknown = set(obs) - {"signal", "close_code", "status",
                                      "local_report"}
                if unknown:
                    err(mf, f"case {cid} peer_observation[{fam}] has unknown "
                            f"keys {sorted(unknown, key=str)}")
                if "signal" in obs and not _is_allowed_string(obs["signal"], PEER_SIGNALS):
                    err(mf, f"case {cid} peer_observation[{fam}] has unknown "
                            f"signal {obs['signal']}")
                cc = obs.get("close_code")
                if cc is not None and (isinstance(cc, bool)
                                       or not isinstance(cc, int)
                                       or cc not in WS_CLOSE_CODES):
                    err(mf, f"case {cid} peer_observation[{fam}] has invalid "
                            f"close_code {cc}")
                st = obs.get("status")
                if st is not None and (isinstance(st, bool)
                                       or not isinstance(st, int)):
                    err(mf, f"case {cid} peer_observation[{fam}] has invalid "
                            f"status {st}")
                lr = obs.get("local_report")
                if "local_report" in obs and not _is_local_report(lr, error_codes):
                    err(mf, f"case {cid} peer_observation[{fam}] has unknown "
                            f"local_report {lr}")
    lr = tmap.get("local_report")
    if "local_report" in tmap and not _is_local_report(lr, error_codes):
        err(mf, f"case {cid} expected.transport has unknown local_report {lr}")
    renv = tmap.get("result_envelope")
    if "result_envelope" in tmap and not _is_allowed_string(renv, {"absent", "present"}):
        err(mf, f"case {cid} expected.transport has invalid result_envelope "
                f"{renv}")


# Keys allowed inside an `expected.frames` entry (conformance/README.md
# and conformance/manifest/schema.yaml): the emitted Syntra Frame's own
# fields plus the documented assertion helpers. Fixture metadata such as
# `credentials` is not a Frame field and is rejected here.
EXPECTED_FRAME_KEYS = {"request_id", "body", "payload_b64", "shape",
                       "note", "has_connection_id"}


def check_expected_frames(mf, cid, label, frames):
    """Validate ``expected.frames`` (case-level or ``control_connection``):
    a present-but-null value and every non-map entry (including null entries)
    are reported as errors, and entries carry only emitted-Frame keys plus
    the documented assertion helpers — never fixture metadata such as
    ``credentials``."""
    if not isinstance(frames, list):
        err(mf, f"case {cid} {label} frames must be a list of maps")
        return
    for i, frame in enumerate(frames):
        if not isinstance(frame, dict):
            err(mf, f"case {cid} {label} frames[{i}] must be a map")
            continue
        unknown = set(frame) - EXPECTED_FRAME_KEYS
        if unknown:
            err(mf, f"case {cid} {label} frames[{i}] has unknown keys "
                    f"{sorted(map(str, unknown))}; expected.frames entries "
                    "carry only emitted-Frame keys plus documented assertion "
                    "helpers (conformance/README.md "
                    "\"expected.frames entries\")")


def check_error_expectation(err_prefix, cid, emap, error_codes, mf):
    """Validate the documented detecting-side discriminators inside an
    ``expected.error`` map (observer / carriage).

    Callers pass this only for a *present* ``error`` key (absent keys are
    skipped by the caller); a present key whose value is null is rejected
    here rather than silently skipped."""
    if not isinstance(emap, dict):
        err(mf, f"case {cid} {err_prefix} must be a map")
        return
    obs = emap.get("observer")
    if "observer" in emap and not _is_allowed_string(obs, ERROR_OBSERVERS):
        err(mf, f"case {cid} has unknown error observer {obs} "
                f"({err_prefix}; allowed: {sorted(ERROR_OBSERVERS)})")
    car = emap.get("carriage")
    if "carriage" in emap and not _is_allowed_string(car, ERROR_CARRIAGE):
        err(mf, f"case {cid} has unknown error carriage {car} "
                f"({err_prefix}; allowed: {sorted(ERROR_CARRIAGE)})")


def check_manifests():
    messages, enums = parse_proto_model()
    # Manifests use short code names (UNIMPLEMENTED); the IDL uses
    # ERROR_CODE_UNIMPLEMENTED. Accept both spellings.
    error_codes = set(enums.get("ErrorCode", {}))
    error_codes |= {c[len("ERROR_CODE_"):] for c in error_codes
                    if c.startswith("ERROR_CODE_")}
    cases, req_refs = load_manifest_cases()
    reqs = load_requirements()
    req_ids = {r.get("requirement_id") for r in reqs}
    for cid, (mf, case) in sorted(cases.items()):
        if not CASE_ID.fullmatch(cid):
            err(mf, f"case {cid} has invalid case ID")
        for key in ("id", "requirement", "profile", "roles", "capabilities",
                    "mandatory", "preconditions", "input", "expected"):
            if key not in case:
                err(mf, f"case {cid} missing required key '{key}'")
        profiles = case.get("profile")
        profiles = profiles if isinstance(profiles, list) else [profiles]
        if not profiles or any(not isinstance(p, str) or p not in KNOWN_PROFILES
                               for p in profiles):
            err(mf, f"case {cid} references unknown profile {case.get('profile')}")
        req_field = case.get("requirement")
        # The required-key loop above already reports a *missing* key; a
        # present-but-null or otherwise non-list `requirement` is rejected
        # here so the null value cannot slip through the isinstance-only
        # skip.
        if "requirement" in case and (not isinstance(req_field, list) or not req_field):
            err(mf, f"case {cid} requirement must be a non-empty list of requirement IDs")
        for r in req_field if isinstance(req_field, list) else []:
            if not isinstance(r, str):
                err(mf, f"case {cid} has malformed requirement ref {r!r}")
                continue
            if r in RESERVED_REQUIREMENTS:
                err(mf, f"case {cid} references reserved requirement {r}")
            if r not in req_ids:
                err(mf, f"case {cid} references unknown requirement {r}")
            if not REQ_NAMING.match(r):
                err(mf, f"case {cid} has malformed requirement ref {r}")
        if not isinstance(case.get("mandatory"), bool):
            err(mf, f"case {cid} mandatory must be boolean")
        roles = case.get("roles")
        if not isinstance(roles, list) or not roles or any(
                not isinstance(v, str) or v not in KNOWN_ROLES for v in roles):
            err(mf, f"case {cid} has invalid roles {roles!r}")
        caps = case.get("capabilities")
        if caps is None:
            # Absent/null capabilities is handled by the required-key loop;
            # keep the pre-existing silent treatment instead of double-erroring.
            pass
        elif not isinstance(caps, list):
            err(mf, f"case {cid} capabilities must be a list of capability IDs")
        else:
            for c in caps:
                if not isinstance(c, str) or c not in KNOWN_CAPABILITIES:
                    err(mf, f"case {cid} has undeclared capability prerequisite {c}")
        if "applicable_transports" in case:
            at = case.get("applicable_transports")
            if not isinstance(at, list) or not at or not all(
                    _is_allowed_string(t, TRANSPORT_FAMILIES) for t in at):
                err(mf, f"case {cid} applicable_transports must be a non-empty "
                        f"list of known transport families "
                         f"{sorted(TRANSPORT_FAMILIES)}")
        if "applicable_profiles" in case:
            ap = case["applicable_profiles"]
            allowed = {"SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"}
            if not isinstance(ap, list) or not ap or any(
                    not _is_allowed_string(p, allowed) for p in ap):
                err(mf, f"case {cid} applicable_profiles must name canonical bindings")
        pre = case.get("preconditions")
        if not isinstance(pre, list) or not pre:
            err(mf, f"case {cid} needs a non-empty preconditions list")
        exp = case.get("expected", {}) or {}
        if not isinstance(exp, dict) or not exp:
            err(mf, f"case {cid} needs a non-empty expected block")
            exp = {}
        for key in exp:
            if key not in ("connection_state", "session_state", "frames",
                           "error", "transport", "hygiene", "retry"):
                err(mf, f"case {cid} has unknown expected key {key}")
        if "connection_state" in exp and not _is_allowed_string(exp["connection_state"], KNOWN_CONN_STATES):
            err(mf, f"case {cid} has invalid connection_state {exp['connection_state']}")
        if "session_state" in exp and not _is_allowed_string(exp["session_state"], KNOWN_SESS_STATES):
            err(mf, f"case {cid} has invalid session_state {exp['session_state']}")
        if "error" in exp and isinstance(exp["error"], dict) and "code" in exp["error"]:
            if not _is_allowed_string(exp["error"]["code"], error_codes):
                err(mf, f"case {cid} has unknown error code {exp['error']['code']}")
        if "error" in exp:
            check_error_expectation("(expected.error observer/carriage)", cid,
                                    exp["error"], error_codes, mf)
        if "transport" in exp:
            check_transport_expectation(mf, cid, exp["transport"], error_codes)
        if "frames" in exp:
            check_expected_frames(mf, cid, "expected", exp["frames"])
        ctl_specified = "control_connection" in case
        ctl = case.get("control_connection")
        if ctl_specified and not isinstance(ctl, dict):
            # An explicit null or non-map control is not a structured,
            # runner-executable control; the schema defines a map.
            err(mf, f"case {cid} control_connection must be a map")
            ctl = None
        if isinstance(ctl, dict):
            if not isinstance(ctl, dict):
                err(mf, f"case {cid} control_connection must be a map")
            else:
                for key in ctl:
                    if key not in ("preconditions", "frames", "subscriptions",
                                   "replay", "transport", "faults",
                                   "credentials", "expected", "notes"):
                        err(mf, f"case {cid} has unknown control_connection key {key}")
                for key in ("preconditions", "expected"):
                    if key not in ctl:
                        err(mf, f"case {cid} control_connection missing required key '{key}'")
                cpre = ctl.get("preconditions")
                if not isinstance(cpre, list) or not cpre:
                    err(mf, f"case {cid} control_connection needs a non-empty preconditions list")
                cframes = ctl.get("frames")
                cframes_ok = isinstance(cframes, list) and all(
                    isinstance(f, dict) for f in cframes)
                if cframes is not None and not cframes_ok:
                    err(mf, f"case {cid} control_connection frames must be a list of maps")
                if cid == "CONF-URP-001":
                    # The control is the executable attribution for the gate:
                    # it must run Negotiate and then the exact same Subscribe
                    # payload as the case-level probe, so the confirmation
                    # gate is the sole delta between the two connections.
                    neg = "/syntra.v1.UpdateRecovery/Negotiate"
                    sub = "/syntra.v1.UpdateRecovery/Subscribe"
                    ctl_raw = ctl.get("frames")
                    ctl_frames = list(ctl_raw) if isinstance(ctl_raw, list) else []
                    ordered = (len(ctl_frames) >= 2
                               and isinstance(ctl_frames[0], dict)
                               and isinstance(ctl_frames[1], dict)
                               and ctl_frames[0].get("method") == neg
                               and ctl_frames[1].get("method") == sub)
                    if not (isinstance(ctl, dict) and ordered):
                        err(mf, f"case {cid} control_connection must be executable: Negotiate followed by the probe Subscribe request")
                    inp = case.get("input") or {}
                    inp_frames = inp.get("frames") if isinstance(inp, dict) else None
                    inp_frames = inp_frames if isinstance(inp_frames, list) else []
                    probe = next((f["payload_b64"] for f in inp_frames
                                  if isinstance(f, dict) and f.get("method") == sub
                                  and isinstance(f.get("payload_b64"), str)),
                                 None)
                    if probe is None:
                        err(mf, f"case {cid} input must carry a Subscribe probe frame with a payload_b64")
                    ctl_payloads = [f.get("payload_b64") for f in ctl_frames
                                    if isinstance(f, dict) and f.get("method") == sub]
                    if not ctl_payloads or any(not isinstance(p, str) for p in ctl_payloads) \
                            or ctl_payloads[0] != probe:
                        err(mf, f"case {cid} control_connection Subscribe payload must equal the case-level probe payload")
                cexp = ctl.get("expected")
                if not isinstance(cexp, dict) or not cexp:
                    err(mf, f"case {cid} control_connection needs a non-empty expected block")
                    cexp = {}
                for key in cexp:
                    if key not in ("connection_state", "session_state", "frames",
                                   "error", "transport", "hygiene", "retry"):
                        err(mf, f"case {cid} has unknown control_connection expected key {key}")
                if "connection_state" in cexp and not _is_allowed_string(cexp["connection_state"], KNOWN_CONN_STATES):
                    err(mf, f"case {cid} control_connection has invalid connection_state {cexp['connection_state']}")
                if "session_state" in cexp and not _is_allowed_string(cexp["session_state"], KNOWN_SESS_STATES):
                    err(mf, f"case {cid} control_connection has invalid session_state {cexp['session_state']}")
                if "error" in cexp and isinstance(cexp["error"], dict) and "code" in cexp["error"]:
                    if not _is_allowed_string(cexp["error"]["code"], error_codes):
                        err(mf, f"case {cid} control_connection has unknown error code {cexp['error']['code']}")
                if "error" in cexp:
                    check_error_expectation("(control_connection expected.error observer/carriage)", cid,
                                            cexp["error"], error_codes, mf)
                if "transport" in cexp:
                    check_transport_expectation(mf, cid, cexp["transport"], error_codes)
                if "frames" in cexp:
                    check_expected_frames(mf, cid, "control_connection.expected",
                                          cexp["frames"])
        elif cid == "CONF-URP-001":
            # Gate attribution for the negotiation-isolation case depends on
            # executing its declared paired control connection, so the control
            # must be a structured, runner-executable scenario rather than
            # prose-only notes.
            err(mf, f"case {cid} requires a structured control_connection")
        if cid == "CONF-RPC-004":
            # Duplicate-ID detection must be deterministic at race level: the
            # structured barrier fault is mandatory and must use the documented
            # semantics. Prose-only coordination or sleeps do not qualify.
            inp = case.get("input") or {}
            faults = inp.get("faults") if isinstance(inp, dict) else None
            dwp = faults.get("duplicate_while_pending") \
                if isinstance(faults, dict) else None
            if not isinstance(dwp, dict) \
                    or set(dwp) != {"barrier", "release_after"} \
                    or dwp["barrier"] != "first_terminal_result" \
                    or dwp["release_after"] != "violation_and_closure":
                err(mf, f"case {cid} must declare the structured harness fault "
                        "duplicate_while_pending: {barrier: "
                        "first_terminal_result, release_after: "
                        "violation_and_closure} for deterministic duplicate "
                        "injection (no sleeps, no prose-only assumptions)")
    for r, mf, cid in req_refs:
        if not isinstance(r, str) or not REQ_NAMING.match(r):
            err(mf, f"case {cid} has malformed requirement ref {r}")
    print(f"manifests: {len(cases)} cases, {len(req_refs)} requirement refs")


def manifest_reference(ref, base, registered_profiles):
    """Validate a selector/reference before it can exclude any cases."""
    if isinstance(ref, str):
        path, filters = ref, {}
    elif isinstance(ref, dict) and set(ref) == {"path", "select"}:
        path, filters = ref["path"], ref["select"]
    else:
        raise ValueError("manifest reference must be a path string or a map with exactly path and select")
    if not isinstance(path, str) or not path.strip() or "\\" in path or ":" in path:
        raise ValueError("manifest path must be a non-empty relative path")
    relative = Path(path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("manifest path must stay within the conformance directory")
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise ValueError("manifest path must stay within the conformance directory")
    if not isinstance(filters, dict) or set(filters) - {"mandatory", "capabilities", "profile"}:
        raise ValueError("manifest select must be a map containing only mandatory, capabilities and profile")
    if "mandatory" in filters and type(filters["mandatory"]) is not bool:
        raise ValueError("manifest select.mandatory must be boolean")
    if "capabilities" in filters:
        caps = filters["capabilities"]
        if not isinstance(caps, list) or any(not _is_allowed_string(c, KNOWN_CAPABILITIES) for c in caps):
            raise ValueError("manifest select.capabilities must be a list of known capabilities")
    if "profile" in filters:
        pid = filters["profile"]
        if not _is_allowed_string(pid, KNOWN_PROFILES) or pid not in registered_profiles:
            raise ValueError("manifest select.profile must name a known registered profile")
    return resolved, filters


def selected_cases(profile, base=None, capabilities=(), carrier_profile=None,
                   registered_profiles=None):
    """Resolve selectors and declared gates; never execute or infer a verdict."""
    base = Path(base) if base is not None else ROOT / "conformance"
    registered_profiles = KNOWN_PROFILES if registered_profiles is None else registered_profiles
    refs = profile.get("manifests")
    if not isinstance(refs, list) or not refs:
        raise ValueError(f"{profile['id']} manifests must be a non-empty list")
    references = [manifest_reference(ref, base, registered_profiles) for ref in refs]
    selected = {}
    for path, filters in references:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"manifest {path} must be a map")
        if "selection_status" in data:
            raise ValueError(f"{profile['id']} selects a non-current manifest {path}")
        if not isinstance(data.get("cases"), list):
            raise ValueError(f"manifest {path} cases must be a list")
        for case in data["cases"]:
            if not isinstance(case, dict):
                raise ValueError(f"manifest {path} case must be a map")
            if not set(case["capabilities"]) <= set(capabilities):
                continue
            if carrier_profile and "applicable_profiles" in case \
                    and carrier_profile not in case["applicable_profiles"]:
                continue
            matches = True
            for key, value in filters.items():
                actual = case.get(key)
                if key == "profile" and isinstance(actual, list):
                    matches &= value in actual
                else:
                    matches &= actual == value
            if matches:
                selected[case["id"]] = case
    return selected


def check_profiles():
    base = ROOT / "conformance"
    try:
        registry = yaml.safe_load((base / "profiles.yaml").read_text())
    except (OSError, yaml.YAMLError) as exc:
        err("conformance/profiles.yaml", f"cannot load profile registry: {exc}")
        return
    if not isinstance(registry, dict) or not isinstance(registry.get("profiles"), list):
        err("conformance/profiles.yaml", "profile registry must contain a profiles list")
        return
    ids = set()
    profiles = []
    for profile in registry["profiles"]:
        if not isinstance(profile, dict) or not isinstance(profile.get("id"), str):
            err("conformance/profiles.yaml", "profile registration must be a map with a string id")
            continue
        pid = profile["id"]
        if pid in ids or pid not in KNOWN_PROFILES:
            err("conformance/profiles.yaml", f"duplicate or noncanonical profile {pid}")
            continue
        ids.add(pid)
        profiles.append(profile)
        if profile.get("kind") != PROFILE_KINDS[pid]:
            err("conformance/profiles.yaml", f"incorrect kind for {pid}: expected {PROFILE_KINDS[pid]}")
    missing = KNOWN_PROFILES - ids
    if missing:
        err("conformance/profiles.yaml", f"missing required profiles: {', '.join(sorted(missing))}")
    canonical = {"SYNTRA-1.0-TCP": (1, True), "SYNTRA-1.0-WS": (2, False),
                 "SYNTRA-1.0-WSS": (3, True)}
    for profile in profiles:
        pid = profile["id"]
        caps = profile.get("capabilities", [])
        if not isinstance(caps, list) or any(not _is_allowed_string(c, KNOWN_CAPABILITIES) for c in caps):
            err("conformance/profiles.yaml", f"{pid} has undeclared capability prerequisites")
            continue
        try:
            cases = selected_cases(profile, capabilities=caps, registered_profiles=ids)
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
            err("conformance/profiles.yaml", f"{pid}: {exc}")
            continue
        if not cases:
            err("conformance/profiles.yaml", f"{pid} selects no cases")
        for case in cases.values():
            declared = case["profile"]
            declared = declared if isinstance(declared, list) else [declared]
            if PROFILE_KINDS[pid] == "TRANSPORT_PROFILE" and pid not in declared:
                err("conformance/profiles.yaml", f"{pid} selects incompatible {case['id']}")
        if PROFILE_KINDS[pid] == "TRANSPORT_PROFILE":
            if pid not in canonical:
                err("conformance/profiles.yaml", f"undefined 1.0 binding {pid}")
                continue
            carrier, production = canonical[pid]
            if profile.get("carrier") != carrier or profile.get("production_allowed") is not production:
                err("conformance/profiles.yaml", f"incorrect carrier/production policy for {pid}")
            if profile.get("domain") != "syntra.1.0":
                err("conformance/profiles.yaml", f"incorrect context domain for {pid}")
            if carrier in (2, 3) and (profile.get("endpoint"), profile.get("subprotocol")) != (
                    "/syntra/1.0/ws", "syntra.1.0"):
                err("conformance/profiles.yaml", f"incorrect WS selection for {pid}")
    print(f"profiles: {len(ids)} current test suite selectors")


# --------------------------------------------------------------------------
# Check: test vectors
# --------------------------------------------------------------------------

BODY_FIELDS = {"hello": 10, "ready": 11, "request": 12, "result": 13,
               "cancel": 14, "notification": 15}


def check_protobuf_vector(entry, protoc):
    vid = entry.get("id", "<missing-id>")
    base = "conformance/test-vectors/protobuf/vectors.yaml"
    frame_hex = entry.get("frame_hex")
    if frame_hex is None:
        # credential-only entries (e.g. AUTHN-01): hex must still parse
        for key in ("credential_hex",):
            if key in entry:
                try:
                    binascii.unhexlify(entry[key])
                except (binascii.Error, ValueError):
                    err(base, f"vector {vid} has invalid hex in {key}")
        return
    try:
        raw = binascii.unhexlify(frame_hex)
    except (binascii.Error, ValueError):
        err(base, f"vector {vid} frame_hex does not parse as hex")
        return
    if entry.get("frame_length_bytes") != len(raw):
        err(base, f"vector {vid} frame_length_bytes {entry.get('frame_length_bytes')} "
                   f"!= actual {len(raw)}")
    sem = entry.get("semantic_fields", {}) or {}
    if sem.get("invalid_because") == "empty_body":
        try:
            fields = field_map(raw)
        except ValueError as e:
            err(base, f"vector {vid} does not protobuf-decode: {e}")
            return
        if any(no in fields for no in BODY_FIELDS.values()):
            err(base, f"vector {vid} claims empty body but a body field is set")
        return
    if "decodes_to" in sem:
        # unknown-field tolerance vector: unknown field present, rest matches target
        try:
            fields = field_map(raw)
        except ValueError as e:
            err(base, f"vector {vid} does not protobuf-decode: {e}")
            return
        uf = sem.get("unknown_field")
        if uf not in fields:
            err(base, f"vector {vid} missing expected unknown field {uf}")
        return
    try:
        fields = field_map(raw)
    except ValueError as e:
        err(base, f"vector {vid} does not protobuf-decode: {e}")
        return
    if "version" in sem:
        got = fields.get(1, [(None, None)])[0][1]
        if got != sem["version"]:
            err(base, f"vector {vid} version {got} != expected {sem['version']}")
    if "request_id" in sem:
        want = sem["request_id"]
        got_list = fields.get(2, [])
        if want == 0:
            if got_list and got_list[0][1] != 0:
                err(base, f"vector {vid} request_id should be omitted/zero")
        elif not got_list or got_list[0][1] != want:
            err(base, f"vector {vid} request_id mismatch")
    if "body" in sem:
        want_no = BODY_FIELDS.get(sem["body"])
        present = [n for n in BODY_FIELDS.values() if n in fields]
        if present != [want_no]:
            err(base, f"vector {vid} body fields {present} != expected [{want_no}]")
        else:
            _check_body(vid, base, sem, fields[want_no][0][1])
    if protoc:
        p = subprocess.run(
            ["protoc", "--decode=syntra.v1.Frame", "-I", str(ROOT / "proto"),
             "syntra/v1/envelope.proto", "syntra/v1/handshake.proto",
             "syntra/v1/rpc.proto", "syntra/v1/events.proto",
             "syntra/v1/errors.proto"],
            input=raw, capture_output=True)
        if p.returncode != 0:
            err(base, f"vector {vid} rejected by protoc: {p.stderr.decode()[:200]}")


def _check_body(vid, base, sem, payload):
    sub = field_map(payload)
    body = sem.get("body")
    if body == "request":
        if _s(sub.get(1)) != sem.get("method"):
            err(base, f"vector {vid} method mismatch")
        if _b64(sub.get(2)) != (sem.get("payload_b64") or ""):
            err(base, f"vector {vid} request payload mismatch")
        if _v(sub.get(3)) != sem.get("timeout_ms"):
            err(base, f"vector {vid} timeout_ms mismatch")
    elif body == "result":
        if sem.get("outcome") == "payload":
            if _b64(sub.get(1)) != (sem.get("payload_b64") or ""):
                err(base, f"vector {vid} result payload mismatch")
        elif sem.get("outcome") == "error":
            efields = field_map(_raw(sub.get(2)))
            if _v(efields.get(1)) != sem.get("code_number"):
                err(base, f"vector {vid} error code number mismatch")
            if _s(efields.get(2)) != sem.get("message"):
                err(base, f"vector {vid} error message mismatch")
    elif body == "hello":
        if _v(sub.get(1)) != sem.get("min_version"):
            err(base, f"vector {vid} min_version mismatch")
        if _v(sub.get(2)) != sem.get("max_version"):
            err(base, f"vector {vid} max_version mismatch")
        if _b64(sub.get(3)) != sem.get("credential_b64"):
            err(base, f"vector {vid} credential mismatch")
    elif body == "ready":
        if _s(sub.get(1)) != sem.get("connection_id"):
            err(base, f"vector {vid} connection_id mismatch")
    elif body == "notification":
        if _b64(sub.get(1)) != sem.get("payload_b64"):
            err(base, f"vector {vid} notification payload mismatch")
    elif body == "cancel":
        if payload != b"":
            err(base, f"vector {vid} Cancel must be empty")


def _v(items):
    return items[0][1] if items else None


def _raw(items):
    return items[0][1] if items else b""


def _s(items):
    return _raw(items).decode("utf-8", errors="strict") if items else None


def _b64(items):
    if not items:
        return None
    return base64.b64encode(_raw(items)).decode()


def check_vectors():
    protoc = shutil.which("protoc")
    tv = ROOT / "conformance" / "test-vectors"
    vectors = yaml.safe_load((tv / "protobuf" / "vectors.yaml").read_text())
    for entry in vectors.get("vectors", []):
        check_protobuf_vector(entry, protoc)

    bytevec = yaml.safe_load((tv / "tcp" / "byte-vectors.yaml").read_text())
    max_frame = bytevec.get("default_max_frame_bytes", 1048576)
    json_vecs = {v["id"]: v for v in
                 json.loads((tv / "tcp" / "vectors.json").read_text())["vectors"]}
    for unit in bytevec.get("units", []):
        uid = unit.get("id")
        wire = unit.get("wire_hex")
        handling = unit.get("handling", "")
        if wire is None:  # recipe-style unit (V4)
            if "prefix_hex" not in unit:
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    f"unit {uid} has neither wire_hex nor prefix_hex")
            continue
        try:
            raw = binascii.unhexlify(wire)
        except (binascii.Error, ValueError):
            err("conformance/test-vectors/tcp/byte-vectors.yaml",
                f"unit {uid} wire_hex does not parse")
            continue
        if uid in json_vecs and "wire_hex" in json_vecs[uid]:
            if json_vecs[uid]["wire_hex"].lower() != wire.lower():
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    f"unit {uid} wire_hex differs from vectors.json")
        if len(raw) < 4:
            if uid != "V7":
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    f"unit {uid} shorter than a 4-byte prefix (only V7 may be)")
            continue  # V7 truncated prefix: intentionally malformed
        declared = int.from_bytes(raw[0:4], "big")
        payload = raw[4:]
        malformed = any(k in handling for k in
                        ("Truncated", "truncated", "close", "reject", "malformed"))
        if uid == "V5":
            if declared != 0 or payload:
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    "V5 must be a zero-length prefix with no payload")
        elif uid == "V6":
            if len(raw) != 4 or declared <= max_frame:
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    "V6 must be a lone oversized prefix (declared > max, no payload)")
        elif uid in ("V7", "V8"):
            if len(payload) >= declared:
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    f"unit {uid} must be truncated (payload shorter than declared)")
        elif uid == "V9":
            if not (declared < len(payload)):
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    "V9 must declare a shorter length than the bytes present")
        elif not malformed:
            if declared != len(payload):
                err("conformance/test-vectors/tcp/byte-vectors.yaml",
                    f"unit {uid} prefix declares {declared} but carries {len(payload)}")

    # Syntra 1.0 connection context/prologue: public encoding, no keys/ciphertext.
    context_path = tv / "connection" / "context-vectors.yaml"
    if context_path.exists():
        context_fixture = yaml.safe_load(context_path.read_text())
        seen = set()
        for v in context_fixture.get("vectors", []):
            vid = v.get("id")
            if not vid or vid in seen:
                err(context_path, f"connection vector has missing/duplicate id {vid}")
                continue
            seen.add(vid)
            try:
                ctx = binascii.unhexlify(v["context_hex"])
                pro = binascii.unhexlify(v["prologue_hex"])
            except (binascii.Error, ValueError, KeyError):
                err(context_path, f"vector {vid} has invalid hex")
                continue
            if pro != ctx:
                err(context_path, f"vector {vid} prologue differs from context")
            if len(ctx) < 34:
                err(context_path, f"vector {vid} shorter than the 34-byte fixed context")
                continue
            scope_len = int.from_bytes(ctx[32:34], "big")
            if not (1 <= scope_len <= 255):
                err(context_path, f"vector {vid} scope length {scope_len} out of range")
            if len(ctx) != 34 + scope_len:
                err(context_path, f"vector {vid} length {len(ctx)} != 34 + scope length {scope_len}")
            if v.get("context_bytes") != len(ctx):
                err(context_path, f"vector {vid} context_bytes {v.get('context_bytes')} != {len(ctx)}")
            if v.get("m1_bytes") != len(ctx) + 48:
                err(context_path, f"vector {vid} m1_bytes {v.get('m1_bytes')} != context + 48")
            if ctx[:10] != b"syntra.1.0":
                err(context_path, f"vector {vid} domain is not syntra.1.0")
            if ctx[10] != v.get("mode") or ctx[11] != v.get("carrier"):
                err(context_path, f"vector {vid} mode/carrier mismatch")
            if ctx[10] not in (1, 2):
                err(context_path, f"vector {vid} mode {ctx[10]} outside bootstrap 1/returning 2")
            if ctx[11] not in (1, 2, 3):
                err(context_path, f"vector {vid} carrier {ctx[11]} outside TCP 1/WS 2/WSS 3")
            if int.from_bytes(ctx[12:16], "big") != v.get("server_key_id"):
                err(context_path, f"vector {vid} server_key_id mismatch")
            if int.from_bytes(ctx[16:24], "big") != v.get("epoch"):
                err(context_path, f"vector {vid} epoch mismatch")
            if ctx[24:32].hex() != v.get("handle_hex", "").lower():
                err(context_path, f"vector {vid} handle mismatch")
            try:
                scope = ctx[34:34 + scope_len].decode("utf-8")
            except UnicodeDecodeError:
                err(context_path, f"vector {vid} scope is not UTF-8")
                continue
            if scope != v.get("scope"):
                err(context_path, f"vector {vid} scope mismatch")
        for rec in context_fixture.get("negative_recipes", []):
            if rec.get("base") not in seen:
                err(context_path, f"negative recipe {rec.get('id')} references unknown base")
            if rec.get("expected") != "reject-before-noise":
                err(context_path, f"negative recipe {rec.get('id')} has unexpected expectation")
    recovery = yaml.safe_load((ROOT / "conformance/manifest/recovery.yaml").read_text())
    for case in recovery["cases"]:
        if case["id"] in {"CONF-URP-011", "CONF-URP-012"}:
            for frame in case["expected"].get("frames", []):
                if frame["body"] == "notification":
                    try:
                        check_replay_complete_fixture(base64.b64decode(frame["payload_b64"], validate=True))
                    except (ValueError, binascii.Error) as exc:
                        err("conformance/manifest/recovery.yaml", f"{case['id']}: {exc}")
    print("vectors: protobuf/inner-stream/public-context/recovery-wrapper fixtures checked (no runtime verdict)")


def check_replay_complete_fixture(raw):
    """Strict fixture-shape check derived from the current IDL, not a decoder fallback."""
    messages, _ = parse_proto_model()
    wrapper = messages["RecoveryNotification"]
    completion = messages["RecoveryReplayComplete"]
    fields = field_map(raw)
    version = wrapper["profile_version"]
    arm = wrapper["replay_complete"]
    if set(fields) != {version, arm} or fields[version] != [(0, 1)] \
            or len(fields[arm]) != 1 or fields[arm][0][0] != 2:
        raise ValueError("expected versioned RecoveryNotification.replay_complete wrapper")
    inner = field_map(fields[arm][0][1])
    expected = {completion["profile_version"]: [(0, 1)],
                completion["subscription_handle"]: [(2, b"handle-A")],
                completion["generation"]: [(0, 7)],
                completion["live_boundary_checkpoint"]: [(2, b"B")]}
    if inner != expected:
        raise ValueError("completion must preserve version 1, handle-A, generation 7 and boundary B")
    return fields[arm][0][1]


# --------------------------------------------------------------------------
# Check: links, refs, RFCs, markdown hygiene
# --------------------------------------------------------------------------

def github_slug(header):
    # Match github-slugger: lowercase, drop backticks, drop everything that
    # is not a word char, space, or hyphen (notably also "/"), spaces to "-".
    slug = header.strip().lower()
    slug = re.sub(r"`", "", slug)
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    return slug.replace(" ", "-")


def collect_headers(md_path):
    anchors = set()
    for line in md_path.read_text().splitlines():
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m:
            anchors.add(github_slug(m.group(1)))
    return anchors


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def is_current_reference_path(path):
    """Current docs, manifests and IDL use current IDs; process records do not.

    Link targets/anchors in all content still resolve. Historical RFCs, ADRs,
    decision records and audits may discuss the vocabulary of their own time.
    """
    path = Path(path).as_posix()
    if path.startswith(("specifications/decisions/", "docs/decisions/")):
        return False
    return path.startswith(("specifications/", "conformance/", "docs/", "proto/"))


def check_links():
    md_files = sorted((ROOT).rglob("*.md"))
    header_cache = {}
    for f in md_files:
        rel = f.relative_to(ROOT)
        if not is_content_path(rel):
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            err(rel, "file is not UTF-8")
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in LINK_RE.finditer(line):
                target = m.group(1)
                if re.match(r"^(https?|mailto):", target) or target.startswith("#"):
                    if target.startswith("#"):
                        anchor = target[1:]
                        if anchor not in header_cache.setdefault(
                                str(rel), collect_headers(f)):
                            err(rel, f"anchor #{anchor} not found in same file", i)
                    continue
                path_part, _, anchor = target.partition("#")
                if not path_part:
                    continue
                dest = (f.parent / path_part).resolve()
                try:
                    dest_rel = dest.relative_to(ROOT)
                except ValueError:
                    err(rel, f"link escapes repository: {target}", i)
                    continue
                if not dest.exists():
                    # allow extensionless rfcs/NNNN shorthand? No — must resolve.
                    err(rel, f"broken link target: {target}", i)
                    continue
                if anchor and dest.suffix == ".md":
                    if anchor not in header_cache.setdefault(
                            str(dest_rel), collect_headers(dest)):
                        err(rel, f"anchor #{anchor} not found in {dest_rel}", i)
    # requirement + profile references must resolve
    defined = set(OWNERS.owner_definitions(ROOT))
    for f in [x for x in md_files if x.suffix == ".md"] + \
            list((ROOT / "conformance").rglob("*.yaml")) + \
            list((ROOT / "conformance").rglob("*.json")) + \
            list((ROOT / "proto").rglob("*.proto")):
        rel = f.relative_to(ROOT)
        if not is_content_path(rel) or not is_current_reference_path(rel):
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        for m in REQ_PATTERN.finditer(text):
            if m.group(0) in RESERVED_REQUIREMENTS:
                continue
            if m.group(0) not in defined:
                err(rel, f"references undefined requirement {m.group(0)}")
        for m in PROFILE_PATTERN.finditer(text):
            if not profile_reference_known(m.group(0), rel):
                err(rel, f"references unknown transport profile {m.group(0)}")
    print(f"links: {len(md_files)} markdown files checked")


def profile_reference_known(profile, path=None):
    return profile in KNOWN_PROFILES


def check_rfcs():
    allowed = KNOWN_RFC_STATUS
    for f in sorted((ROOT / "rfcs").glob("*.md")):
        if f.name in ("README.md", "template.md"):
            continue
        if not re.match(r"\d{4}-[a-z0-9-]+\.md$", f.name):
            err(f.relative_to(ROOT), "RFC filename must be NNNN-kebab-case.md")
        text = f.read_text()
        m = re.search(r"^-\s*Status:\s*(.+)$", text, re.M)
        if not m:
            err(f.relative_to(ROOT), "RFC missing '- Status:' metadata line")
            continue
        status = m.group(1).strip().split(" ")[0]
        if status not in allowed:
            err(f.relative_to(ROOT),
                f"RFC status {status!r} not in {sorted(allowed)}")
        for field in ("Title", "Author", "Date", "Relates to"):
            if not re.search(rf"^-\s*{field}", text, re.M):
                err(f.relative_to(ROOT), f"RFC missing '- {field}' metadata")
        if not re.search(r"^#\s+RFC\s+\d+", text, re.M):
            err(f.relative_to(ROOT), "RFC missing '# RFC NNNN' heading")
    print("rfcs: metadata checked")


def check_markdown():
    for f in sorted(ROOT.rglob("*.md")):
        rel = f.relative_to(ROOT)
        if not is_content_path(rel):
            continue
        text = f.read_text()
        if "\t" in text:
            err(rel, "tabs found; use spaces")
        for i, line in enumerate(text.splitlines(), 1):
            if line != line.rstrip():
                err(rel, "trailing whitespace", i)
                break
        if text and not text.endswith("\n"):
            err(rel, "file does not end with newline")
        if text.count("```") % 2 != 0:
            err(rel, "unbalanced fenced code blocks")
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"\[[^\]]*\]\(\)", line):
                err(rel, "empty link target", i)
                break
    print("markdown: hygiene checked")

# Specification-first boundary (see MIGRATION.md §10):
#   FORBIDDEN: implementation trees (crates/, bindings/, including any
#            generated language sources) and legacy gen//generated/ trees.
#   Language implementations are separate projects, out of scope here.
#            Schema provenance is released via specification Git tags with
#            a no-asset GitHub Release record (no BSR, no GHCR, no external
#            registries).
LEGACY_GEN_DIRS = ("gen", "generated")

IMPL_ROOTS = ("crates", "bindings")

# Root manifests that imply an in-tree language implementation or committed
# generation template; both are downstream-owned after the extraction.
FORBIDDEN_ROOT_FILES = ("Cargo.toml", "Cargo.lock", "release-plz.toml",
                        "buf.gen.yaml")

# First lines that identify machine-generated language sources. Never allowed
# in this repository; the same header anywhere fails. Never applied to
# documentation, fixtures, or discussion of generated SDKs.
GENERATED_MARKERS = (
    "code generated", "DO NOT EDIT", "do not edit",
    "automatically generated", "@generated",
    "generated by protoc", "generated by prost",
)


def _under(path, prefix):
    return path == prefix or path.startswith(prefix + "/")


def _tracked_files():
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True,
            text=True, timeout=30)
    except (OSError, ValueError):
        return None
    if out.returncode != 0:
        return None
    return [p for p in out.stdout.splitlines() if p]


def check_boundary():
    """Enforce the specification-first repository boundary.

    FORBIDDEN (removed from this repository in MIGRATION.md §10):
      implementation trees (crates/, bindings/), root Cargo manifests,
      release-plz.toml and buf.gen.yaml templates, gen//generated/ legacy
      trees, any generated language sources, and tracked .tmp/ output.
    Text mentions in docs, fixture names, and tooling discussion are NOT
    flagged — only paths that violate the layout contract.
    """
    tracked = _tracked_files()
    if tracked is None:
        print("boundary: not a git checkout; checking working tree only")
        tracked = []

    # 1. Implementation trees reappearing (tracked).
    for path in sorted(tracked):
        for root in IMPL_ROOTS:
            if _under(path, root):
                err(path, f"implementation tree '{root}/' must not return; "
                          "implementations are separate projects, out of "
                          "scope for this repository (see MIGRATION.md §10)")
                break

    # 2. Implementation trees present on disk (untracked counts too).
    for root in IMPL_ROOTS:
        if (ROOT / root).exists():
            err(root + "/",
                "implementation directory exists; remove it "
                "(implementations are out of scope for this repository)")

    # 3. Root manifests that imply in-tree implementations or committed
    # generation templates (tracked and on disk).
    for path in sorted(tracked):
        if path in FORBIDDEN_ROOT_FILES:
            err(path, "root implementation/generation manifest must not be "
                      "tracked here; generation is downstream-owned "
                      "(see MIGRATION.md §10)")
    for name in FORBIDDEN_ROOT_FILES:
        if (ROOT / name).exists():
            err(name, "root implementation/generation manifest exists; "
                      "remove it (generation is downstream-owned)")

    # 4. Legacy gen trees: tracked files and on-disk presence.
    for path in sorted(tracked):
        for forbidden in LEGACY_GEN_DIRS:
            if _under(path, forbidden):
                err(path, f"legacy generated tree '{forbidden}/' must not "
                          "exist; no language types are committed in this "
                          "repository (see MIGRATION.md §10)")
                break
    for forbidden in LEGACY_GEN_DIRS:
        if (ROOT / forbidden).exists():
            err(forbidden + "/",
                "legacy generated directory exists; remove it "
                "(no language types are committed here)")

    # 5. Tracked .tmp/ build output (never committed; .gitignore ignores it).
    for path in sorted(tracked):
        if _under(path, ".tmp"):
            err(path, ".tmp/ build output must not be committed "
                      "(disposable tooling output only)")

    # 6. Generated Go protobuf files anywhere.
    for path in sorted(tracked):
        name = path.rsplit("/", 1)[-1]
        if name.endswith(".pb.go") or name.endswith("_grpc.pb.go"):
            err(path, "generated Go protobuf file must not be committed here; "
                      "no language types are committed in this repository")

    # 7. Generated-code headers in tracked language sources (not docs,
    # fixtures, or prose about generated SDKs). No allowed roots remain.
    for path in sorted(tracked):
        if not path.endswith((".go", ".rs", ".java", ".pyi", ".ts", "_pb2.py")):
            continue
        if path.endswith((".pb.go", "_grpc.pb.go")):
            continue  # reported above
        try:
            with open(ROOT / path, encoding="utf-8", errors="strict") as fh:
                head = "".join(fh.readline() for _ in range(5))
        except OSError:
            continue
        lowered = head.lower()
        if any(m.lower() in lowered for m in GENERATED_MARKERS):
            err(path, "file carries a generated-code header; generated "
                      "language sources are downstream-owned "
                      "(see MIGRATION.md §10)")

    print("boundary: repository boundary checked")


def check_http_candidate():
    """Validate the isolated proposal without registering active requirements."""
    spec = importlib.util.spec_from_file_location(
        "http_candidate", ROOT / "scripts/check-http-candidate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate(ROOT)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, subprocess.SubprocessError) as exc:
        err("rfcs/0013-http-tls", str(exc))
        return
    print("http-candidate: isolated proposal checked; adoption blocked, runtime NOT_EXECUTED")


CHECKS = {
    "requirements": check_requirements,
    "profiles": check_profiles,
    "manifests": check_manifests,
    "vectors": check_vectors,
    "links": check_links,
    "rfcs": check_rfcs,
    "markdown": check_markdown,
    "boundary": check_boundary,
    "http-candidate": check_http_candidate,
}


def main(argv):
    which = argv[1:] or ["all"]
    if which == ["all"]:
        which = list(CHECKS)
    for name in which:
        if name not in CHECKS:
            sys.exit(f"unknown check: {name} (choose from: all, {', '.join(CHECKS)})")
    for name in which:
        print(f"=== {name} ===")
        CHECKS[name]()
    if ERRORS:
        print(f"\n{len(ERRORS)} error(s):")
        for e in ERRORS:
            print(f"  {e}")
        return 1
    print("\nAll selected checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
