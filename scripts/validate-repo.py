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

REQ_PATTERN = re.compile(r"\bSNTR-[A-Z]+-\d+\b|\bSYN-ARCH-\d+\b")
REQ_NAMING = re.compile(r"^(SNTR-[A-Z]+-\d+|SYN-ARCH-\d+)$")
BOLD_DEF = re.compile(r"\*\*(SNTR-[A-Z]+-\d+|SYN-ARCH-\d+)\b")
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


PROFILE_PATTERN = re.compile(r"\bSNTR-[A-Z0-9]+(?:-[A-Z0-9]+)*-V1\b")
KNOWN_PROFILES = {
    "SNTR-CORE-V1", "SNTR-SESS-V1", "SNTR-RPC-V1", "SNTR-EVENTS-V1",
    "SNTR-TCP-V1", "SNTR-TLS-TCP-V1", "SNTR-HTTP-V1", "SNTR-HTTPS-H1-V1",
    "SNTR-HTTPS-H2-V1", "SNTR-WS-V1", "SNTR-WSS-H1-V1",
    "SNTR-SC1-WSS-V1",
}
KNOWN_CAPABILITIES = {"events-v1", "events-replay-v1", "resume-v1", "syntra.update-recovery/1", "syntra.reliable-session/1"}
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
        for case in data.get("cases", []):
            cid = case.get("id")
            if cid in cases:
                err(mf, f"duplicate test ID {cid} (also in {cases[cid][0].name})")
            cases[cid] = (mf, case)
            for r in case.get("requirement", []) or []:
                req_refs.append((r, mf, cid))
    return cases, req_refs


def load_requirements():
    data = yaml.safe_load((ROOT / "conformance" / "manifest" / "requirements.yaml").read_text())
    return data.get("requirements", [])


# --------------------------------------------------------------------------
# Check: requirement IDs
# --------------------------------------------------------------------------

def check_requirements():
    spec_files = sorted((ROOT / "specifications").rglob("*.md"))
    defined = {}  # id -> [(file, line)]
    for f in spec_files:
        if not is_content_path(f.relative_to(ROOT)):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            for m in BOLD_DEF.finditer(line):
                defined.setdefault(m.group(1), []).append((f.relative_to(ROOT), i))
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
        if rid in seen_ids:
            err("conformance/manifest/requirements.yaml", f"duplicate requirement_id {rid}")
        seen_ids.add(rid)
        if not REQ_NAMING.match(rid or ""):
            err("conformance/manifest/requirements.yaml", f"bad requirement_id format: {rid}")
        if rid not in defined:
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} has no bold definition in specifications/")
        spec = r.get("specification")
        if spec and not (ROOT / spec).exists():
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} references missing document {spec}")
        if r.get("automation_status") not in KNOWN_AUTOMATION:
            err("conformance/manifest/requirements.yaml",
                f"requirement_id {rid} has invalid automation_status {r.get('automation_status')}")
        for t in r.get("test_ids", []) or []:
            if t not in cases:
                err("conformance/manifest/requirements.yaml",
                    f"requirement_id {rid} references unknown test {t}")
    # every defined spec ID should appear in requirements.yaml (no silent gaps)
    for rid in sorted(defined):
        if rid not in seen_ids:
            err("conformance/manifest/requirements.yaml",
                f"defined requirement {rid} has no traceability row")
    print(f"requirements: {len(seen_ids)} rows, {len(defined)} defined IDs")


# --------------------------------------------------------------------------
# Check: manifests
# --------------------------------------------------------------------------

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
        for key in ("id", "requirement", "profile", "roles", "capabilities",
                    "mandatory", "preconditions", "input", "expected"):
            if key not in case:
                err(mf, f"case {cid} missing required key '{key}'")
        profiles = case.get("profile")
        profiles = profiles if isinstance(profiles, list) else [profiles]
        if not profiles or any(not isinstance(p, str) or p not in KNOWN_PROFILES
                               for p in profiles):
            err(mf, f"case {cid} references unknown profile {case.get('profile')}")
        for r in case.get("requirement", []) or []:
            if r not in req_ids:
                err(mf, f"case {cid} references unknown requirement {r}")
            if not REQ_NAMING.match(r):
                err(mf, f"case {cid} has malformed requirement ref {r}")
        if not isinstance(case.get("mandatory"), bool):
            err(mf, f"case {cid} mandatory must be boolean")
        if not set(case.get("roles", []) or []) <= KNOWN_ROLES or not case.get("roles"):
            err(mf, f"case {cid} has invalid roles {case.get('roles')}")
        for c in case.get("capabilities", []) or []:
            if c not in KNOWN_CAPABILITIES:
                err(mf, f"case {cid} has undeclared capability prerequisite {c}")
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
        if "connection_state" in exp and exp["connection_state"] not in KNOWN_CONN_STATES:
            err(mf, f"case {cid} has invalid connection_state {exp['connection_state']}")
        if "session_state" in exp and exp["session_state"] not in KNOWN_SESS_STATES:
            err(mf, f"case {cid} has invalid session_state {exp['session_state']}")
        if "error" in exp and isinstance(exp["error"], dict) and "code" in exp["error"]:
            if exp["error"]["code"] not in error_codes:
                err(mf, f"case {cid} has unknown error code {exp['error']['code']}")
    for r, mf, cid in req_refs:
        if not REQ_NAMING.match(r):
            err(mf, f"case {cid} has malformed requirement ref {r}")
    print(f"manifests: {len(cases)} cases, {len(req_refs)} requirement refs")


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
                 __import__("json").loads((tv / "tcp" / "vectors.json").read_text())["vectors"]}
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

    http_fix = yaml.safe_load((tv / "http" / "fixtures.yaml").read_text())
    frames = {f["id"]: f for f in http_fix.get("fixtures", [])}
    for fid, f in frames.items():
        try:
            raw = base64.b64decode(f["frame_b64"], validate=True)
        except (binascii.Error, ValueError):
            err("conformance/test-vectors/http/fixtures.yaml",
                f"fixture {fid} frame_b64 does not parse")
            continue
        if f.get("frame_length_bytes") != len(raw):
            err("conformance/test-vectors/http/fixtures.yaml",
                f"fixture {fid} frame_length_bytes != actual {len(raw)}")
        try:
            field_map(raw)
        except ValueError as e:
            err("conformance/test-vectors/http/fixtures.yaml",
                f"fixture {fid} does not protobuf-decode: {e}")
    for ex in http_fix.get("exchanges", []):
        for m in re.finditer(r"Content-Length:\s*(\d+)", ex.get("request", "") + ex.get("response", "")):
            pass  # lengths are asserted against fixtures below
        for ref in re.finditer(r"body is (\d+) raw", ex.get("request", "")):
            pass
        # cross-check: exchanges that name a body_ref-equivalent length
        req, resp = ex.get("request", ""), ex.get("response", "")
        for text, label in ((req, "request"), (resp, "response")):
            m = re.search(r"Content-Length:\s*(\d+)", text)
            if m:
                declared = int(m.group(1))
                # find which fixture this exchange carries by matching known lengths
                known = sorted({f.get("frame_length_bytes") for f in frames.values()})
                if declared not in known and "1048577" not in text and declared != 0:
                    # 1048577 = MAX+1 oversize fixture; 0 = empty error bodies
                    err("conformance/test-vectors/http/fixtures.yaml",
                        f"exchange {ex.get('id')} {label} Content-Length {declared} "
                        f"matches no fixture length {known}")

    ws_fix = yaml.safe_load((tv / "websocket" / "fixtures.yaml").read_text())
    kinds = {"upgrade_request": ["GET ", "Sec-WebSocket-Key"],
             "upgrade_response": ["101", "Sec-WebSocket-Accept"],
             "binary_message": ["0x82", "protobuf(Frame)"],
             "fragmented_message": ["0x02", "FIN=1"],
             "ping_pong": ["0x89", "0x8A"],
             "close_handshake": ["0x88", "Close"],
             # close_codes mapping must enumerate every normative WS close
             # code; 1000 (normal) lives on the close_handshake fixture.
             "close_codes": ["1001", "1002", "1003", "1007", "1008",
                             "1009", "1011"],
             "oversize_boundary": ["1048576", "1048577"],
             "no_length_prefix_negative_proof": ["protobuf(Frame)"]}
    for fx in ws_fix.get("fixtures", []):
        kind = fx.get("kind")
        if kind not in kinds:
            err("conformance/test-vectors/websocket/fixtures.yaml",
                f"fixture {fx.get('id')} has unknown kind {kind}")
            continue
        blob = (fx.get("text", "") or "") + (fx.get("shape", "") or "") + \
               (fx.get("rule", "") or "") + (fx.get("good", "") or "")
        for needle in kinds[kind]:
            if needle not in blob and needle not in str(fx.get("mapping", "")) \
                    and needle not in str(fx.get("bad", "")):
                err("conformance/test-vectors/websocket/fixtures.yaml",
                    f"fixture {fx.get('id')} kind {kind} missing marker {needle!r}")
    # SC1 v1 context/prologue fixtures: public encoding only, no keys/ciphertext.
    sc1_path = tv / "sc1" / "context-vectors.yaml"
    if sc1_path.exists():
        sc1 = yaml.safe_load(sc1_path.read_text())
        seen = set()
        for v in sc1.get("vectors", []):
            vid = v.get("id")
            if not vid or vid in seen:
                err(sc1_path, f"SC1 vector has missing/duplicate id {vid}")
                continue
            seen.add(vid)
            try:
                ctx = binascii.unhexlify(v["context_hex"])
                pro = binascii.unhexlify(v["prologue_hex"])
            except (binascii.Error, ValueError, KeyError):
                err(sc1_path, f"vector {vid} has invalid hex")
                continue
            if pro != ctx:
                err(sc1_path, f"vector {vid} prologue differs from context")
            if len(ctx) < 37:
                err(sc1_path, f"vector {vid} shorter than the 37-byte fixed context")
                continue
            scope_len = int.from_bytes(ctx[35:37], "big")
            if not (1 <= scope_len <= 255):
                err(sc1_path, f"vector {vid} scope length {scope_len} out of range")
            if len(ctx) != 37 + scope_len:
                err(sc1_path, f"vector {vid} length {len(ctx)} != 37 + scope length {scope_len}")
            if v.get("context_bytes") != len(ctx):
                err(sc1_path, f"vector {vid} context_bytes {v.get('context_bytes')} != {len(ctx)}")
            if v.get("m1_bytes") != len(ctx) + 48:
                err(sc1_path, f"vector {vid} m1_bytes {v.get('m1_bytes')} != context + 48")
            if ctx[:13] != b"syntra.sc1.v1":
                err(sc1_path, f"vector {vid} domain is not syntra.sc1.v1")
            if ctx[13] != v.get("mode") or ctx[14] != v.get("carrier"):
                err(sc1_path, f"vector {vid} mode/carrier mismatch")
            if int.from_bytes(ctx[15:19], "big") != v.get("server_key_id"):
                err(sc1_path, f"vector {vid} server_key_id mismatch")
            if int.from_bytes(ctx[19:27], "big") != v.get("epoch"):
                err(sc1_path, f"vector {vid} epoch mismatch")
            if ctx[27:35].hex() != v.get("handle_hex", "").lower():
                err(sc1_path, f"vector {vid} handle mismatch")
            try:
                scope = ctx[37:37 + scope_len].decode("utf-8")
            except UnicodeDecodeError:
                err(sc1_path, f"vector {vid} scope is not UTF-8")
                continue
            if scope != v.get("scope"):
                err(sc1_path, f"vector {vid} scope mismatch")
        for rec in sc1.get("negative_recipes", []):
            if rec.get("base") not in seen:
                err(sc1_path, f"negative recipe {rec.get('id')} references unknown base")
            if rec.get("expected") != "reject-before-noise":
                err(sc1_path, f"negative recipe {rec.get('id')} has unexpected expectation")
    print("vectors: protobuf/TCP/HTTP/WS/SC1 fixtures checked")


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


# Requirement/profile reference existence is enforced for normative and user
# documentation. audits/ and rfcs/ deliberately discuss proposed, placeholder,
# or conflicting identifiers, so they get naming-convention checks only.
REF_EXISTENCE_SCOPE = ("specifications/", "conformance/", "docs/")


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
    defined = set()
    for f in sorted((ROOT / "specifications").rglob("*.md")):
        for m in BOLD_DEF.finditer(f.read_text()):
            defined.add(m.group(1))
    req_ids = {r.get("requirement_id") for r in load_requirements()}
    defined |= req_ids
    for f in [x for x in md_files if x.suffix == ".md"] + \
            list((ROOT / "conformance").rglob("*.yaml")):
        rel = f.relative_to(ROOT)
        if not is_content_path(rel):
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        in_scope = str(rel).startswith(REF_EXISTENCE_SCOPE)
        for m in REQ_PATTERN.finditer(text):
            if m.group(0) not in defined and in_scope:
                err(rel, f"references undefined requirement {m.group(0)}")
        for m in PROFILE_PATTERN.finditer(text):
            if m.group(0) not in KNOWN_PROFILES and in_scope:
                err(rel, f"references unknown transport profile {m.group(0)}")
    print(f"links: {len(md_files)} markdown files checked")


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
#            Schema asset distribution is via GitHub Release assets (no
#            BSR, no GHCR, no external registries).
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


CHECKS = {
    "requirements": check_requirements,
    "manifests": check_manifests,
    "vectors": check_vectors,
    "links": check_links,
    "rfcs": check_rfcs,
    "markdown": check_markdown,
    "boundary": check_boundary,
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
