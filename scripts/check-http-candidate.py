#!/usr/bin/env python3
"""Lint the isolated RFC 0013 candidate; never activate or implement a peer.

Uses stdlib + the repository's pinned PyYAML. HTTP checking below is offline
fixture-shape lint, not a general HTTP parser or a network/conformance harness.
No output files, commits, protocol input rewrites or approval records are made.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = "rfcs/0013-http-tls"
BASE = "3f7e8ea037fefcc5c86101d23e7722c83e28a0d3"
STATUS = "accepted-unadopted"
ACCEPTANCE_REFERENCE = {
    "public_approval_url": "https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482",
    "reviewed_revision": "cfab7655c348f1d04f4e1d57e28cc1a634478854",
    "record_path": "docs/decisions/0004-rfc-0011-0014-acceptance.md",
}
MAX_FILE = 1024 * 1024
FILES = ("README.md", "contract.json", "profiles.yaml", "cases.yaml",
         "requirements.yaml", "context-vectors.json", "http-vectors.json", "owner-delta.md", "review.md")
SOURCE_FILES = tuple(f"{BUNDLE}/{name}" for name in FILES) + (
    "rfcs/0013-http-tls-carriers.md", "rfcs/README.md",
    "docs/decisions/0003-http-tls-consent.md",
    ACCEPTANCE_REFERENCE["record_path"],
    "scripts/check-http-candidate.py", "scripts/migrate-conformance-1.0.py",
    "scripts/validate-repo.py", "tests/test_http_candidate.py",
    "rfcs/0014-scoped-terminal-receipt.md", "tests/test_terminal_receipt_adoption.py",
    "conformance/manifest/rpc.yaml", "conformance/manifest/requirements.yaml",
    *(f"specifications/{name}.md" for name in ("connection", "rpc", "security", "transports")))
BASE_FILES = tuple(f"specifications/{name}.md" for name in (
    "transports", "security", "connection", "rpc", "wire-format", "recovery")) + (
    "compatibility/syntra-1.0.json", "conformance/profiles.yaml",
    "conformance/test-vectors/connection/context-vectors.json",
    "conformance/test-vectors/connection/context-vectors.yaml",
    "conformance/manifest/requirements.yaml", "conformance/manifest/schema.yaml",
    "CONTRIBUTING.md", "GOVERNANCE.md", "MAINTAINERS.md")
# The original BASE and every pre-existing byte remain immutable. These six
# exact appendices implement only accepted RFC0014, not RFC0013 adoption. Pins
# cover the entire suffix, including prose, IDs, cases and registry metadata;
# markers alone never authorize content. Updating a pin is an explicit reviewed
# tooling change, not a rebaseline mode or an approval/execution claim.
TERMINAL_APPENDICES = {
    "specifications/connection.md": "90c2f110b3113dca11d6dea6e11a5caf4bc82695483ae8ce8d54a9c528d4fe65",
    "specifications/rpc.md": "6cfd3937bc955f94e3673db95a41cdb3f40306d868ecaa7b251b87e8c1f626d6",
    "specifications/security.md": "81ede9de6502133af520848b5667941a22ade75ba0351c6c9457b7c64ccb10b5",
    "specifications/transports.md": "f4fb202ff5d1e7d232f8fe292dac6e2e2912ef468717fc012a428cede06de111",
    "conformance/manifest/requirements.yaml": "eaf56c3c6c2bc683d3cedc949ede5ac56493a45031da712381bbee384926d3ee",
    "conformance/manifest/rpc.yaml": "c43d9f93d222a68a71392b47c04a1e67d3a888146d0ce5666bbae5d585a09d45",
}
TERMINAL_OWNERS = {
    "connection": (1, 2, 12), "rpc": (8, 10, 13),
    "security": (3, 4, 5), "transports": (6, 7, 9, 11),
}
TERMINAL_TRACES = ((1, 2), (2, 3), (3, 8, 11), (3, 4), (4, 5, 11), (4, 5),
                   (5, 6), (6, 7), (7, 11), (8, 9), (10, 12), (9, 12), (11, 13),
                   tuple(range(1, 14)))
GATES = {
    "maintainer_consent_reported": True, "self_approval_disclosed": True,
    "public_approval": True, "human_security_review": True,
    "accepted": True, "active": False, "freeze": False,
    "release_authorized": False, "formal_conformance": "NOT_EXECUTED",
}
LIMITS = {
    "total_attempt_ms_max": 15000, "noise_hello_ms_max": 5000,
    "headers_bytes_max": 16384, "header_fields_max": 64,
    "start_line_bytes_max": 2048, "field_line_bytes_max": 4096,
    "headers_assembly_ms_max": 5000, "m1_bytes": [83, 337], "m2_bytes": 48,
    "ciphertext_bytes": [17, 65535], "plaintext_bytes_max": 65519,
    "frame_bytes_max": 1048576, "open_send_ms_default": 5000,
    "poll_hold_ms_max": 25000, "poll_exchange_ms_max": 30000,
    "poll_gap_ms_max": 5000, "frame_output_ms_max": 10000,
    "next_record_ms_default": 60000, "frame_assembly_ms_default": 30000,
    "teardown_ms_default": 2000, "channel_age_ms_max": 86400000,
    "records_per_direction_max": 4294967296, "pending_operations_default": 64,
    "buffered_frames_default": 64, "pending_operations_max": 1024,
    "buffered_frames_max": 1024, "input_bytes_default": 4194304,
    "output_bytes_default": 4194304, "associations_default": 128,
    "unauthenticated_handshakes_default": 32, "unbound_streams_default": 32,
    "unbound_stream_ms_default": 5000, "host_io_bytes_default": 268435456,
    "open_rate_default": 32, "open_burst_default": 32,
    "source_open_rate_default": 4, "source_open_burst_default": 8,
    "principal_associations_default": 16, "reconnect_attempts_default": 5,
    "outage_ms_default": 120000, "backoff_base_ms_default": 250,
    "backoff_cap_ms_default": 30000, "backoff_floor_ms": 1,
    "active_reset_ms_default": 30000,
}


def require(condition, message):
    """Raise ValueError unless the candidate invariant holds."""
    if not condition:
        raise ValueError(message)


def exact(actual, expected, message):
    """Compare JSON-normalized values so bool and int cannot alias."""
    # JSON serialization distinguishes bool/int, unlike Python dict equality.
    require(json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True), message)


def unique_pairs(pairs):
    """Collect mapping pairs while rejecting duplicate keys."""
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate key {key}")
        result[key] = value
    return result


class UniqueYaml(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def unique_yaml(loader, node):
    """Construct a mapping with duplicate-key detection."""
    return unique_pairs((loader.construct_object(k), loader.construct_object(v))
                        for k, v in node.value)


UniqueYaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_yaml)


def read_bounded(root, relative):
    """Read a repository-relative file with path, symlink, and size bounds."""
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and ".." not in parts.parts, "input path escapes root")
    path = root
    for part in parts.parts:
        path = path / part
        require(not path.is_symlink(), "symlink input is not permitted")
    require(path.resolve().is_relative_to(root.resolve()), "input path escapes root")
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE + 1)
    require(len(raw) <= MAX_FILE, "candidate input exceeds file bound")
    return raw


def load(root, relative):
    """Load bounded JSON or YAML with duplicate-key detection."""
    text = read_bounded(root, relative).decode("utf-8")
    return (json.loads(text, object_pairs_hook=unique_pairs) if relative.endswith(".json")
            else yaml.load(text, Loader=UniqueYaml))


def context_encoder(root):
    """Load the canonical context encoder without writing bytecode."""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(
            "r13_context_source", root / "scripts/migrate-conformance-1.0.py")
        require(spec is not None and spec.loader is not None, "missing context encoder")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module.encode_context


def validate_contract(data):
    """Validate accepted design constants without granting canonical adoption."""
    top_fields = {
        "format_version": 1, "kind": "rfc-candidate", "status": STATUS,
        "protocol": "Syntra 1.0", "base_revision": BASE, "domain_ascii": "syntra.1.0",
        "core_wire_version": 1, "protobuf_package": "syntra.v1", "authority": GATES,
        "acceptance_reference": ACCEPTANCE_REFERENCE,
        "limits": LIMITS, "browser_support_claimed": False,
        "pause": "retire-generation-bounded-stop",
        "resume": "fresh-attempt-with-remaining-budget",
        "fixture_scope": "public-encoding-and-structural-HTTP-only",
        "proxies": ["explicit-direct", "socks5-connect", "http-connect"],
    }
    require(set(data) == set(top_fields) | {"proposed_carriers", "http", "tls_provider"}, "unknown contract fields")
    for key, expected in top_fields.items():
        exact(data[key], expected, f"candidate contract/gate drift: {key}")
    carriers = data["proposed_carriers"]
    exact(sorted(carriers), ["SYNTRA-1.0-HTTP", "SYNTRA-1.0-HTTPS"], "carrier names")
    for name, code, binding, tls in (
            ("SYNTRA-1.0-HTTP", 4, "http-h1-post-poll-noise", False),
            ("SYNTRA-1.0-HTTPS", 5, "http-h1-post-poll-verified-tls13-noise", True)):
        exact(carriers[name], {
            "code": code, "binding": binding, "production_allowed_if_adopted": True,
            "integral_noise": True, "outer_tls_required": tls}, "proposed carrier drift")
    http = data["http"]
    http_fields = {
        "version": "HTTP/1.1", "method": "POST", "streams": 2, "in_flight_per_stream": 1,
        "route_header": "Syntra-Route", "route_bytes": 32, "route_encoding": "lowercase-hex",
        "route_authority": "association-selector-only", "counter_encoding": "canonical-u64-decimal",
        "content_type": "application/octet-stream",
        "body_mapping": "one-M1-or-M2-or-ciphertext-no-outer-prefix",
        "send_ack": "complete-carrier-record-input-admission",
        "send_ack_requires_decryption": False, "send_ack_requires_runtime_consumption": False,
        "input_slots_default": 1, "uncertain_exchange": "retire-both-streams-no-replay",
        "automatic_rpc_replay": False, "redirects": False, "compression": False,
        "transfer_encoding": False, "status_204_content_length": "forbidden",
    }
    require(set(http) == set(http_fields) | {"operations"}, "unknown HTTP mapping fields")
    for key, value in http_fields.items():
        exact(http[key], value, f"HTTP mapping drift: {key}")
    operations = {
        "open": ("U-new", "M1", [201], "M2", [], ["Syntra-Route"]),
        "send": ("U-bound", "ciphertext", [204], "empty", ["Syntra-Route", "Syntra-Upload"], ["Syntra-Upload"]),
        "poll": ("D-bound-once", "empty", [200, 204], "ciphertext-or-empty", ["Syntra-Route", "Syntra-Poll"], ["Syntra-Poll"]),
        "close": ("U-bound", "empty", [204], "empty", ["Syntra-Route"], []),
    }
    exact(sorted(http["operations"]), sorted(operations), "operation set")
    for name, (stream, body, statuses, output, request, response) in operations.items():
        expected = {"path": f"/syntra/1.0/http/{name}", "stream": stream, "input": body,
                    "success": statuses, "output": output, "response_headers": response}
        if request:
            expected["request_headers"] = request
        exact(http["operations"][name], expected, "operation mapping drift")
    exact(data["tls_provider"], {
        "termination": "trusted-in-process", "stream_bound_evidence": True,
        "minimum_version": "1.3", "alpn_if_present": "http/1.1",
        "alpn_absence": "explicit-H1-provider-only",
        "chain_hostname_validity_revocation_checks": True, "early_syntra_data": False,
        "forwarded_claims": False, "resumption_bypasses_current_verification": False,
        "wss_carrier": 3, "wss_endpoint": "/syntra/1.0/ws", "wss_subprotocol": "syntra.1.0",
    }, "TLS-provider boundary drift")


def validate_acceptance_reference(root, reference):
    """Check bounded local reference consistency, not GitHub authorization."""
    exact(reference, ACCEPTANCE_REFERENCE, "acceptance reference drift")
    record = read_bounded(root, reference["record_path"]).decode("utf-8")
    require(reference["public_approval_url"] in record and
            reference["reviewed_revision"] in record,
            "acceptance record missing exact public URL or reviewed revision")
    sections = re.findall(r"^### RFC 0013:[^\n]*(?:\n|$)(.*?)(?=^#{1,3} |\Z)",
                          record, re.MULTILINE | re.DOTALL)
    require(len(sections) == 1, "acceptance record must contain exactly one RFC 0013 section")
    disposition = re.match(r"\s*\*\*(.*?)\*\*", sections[0], re.DOTALL)
    exact(" ".join(disposition[1].split()) if disposition else None,
          "Accepted as an optional additive pre-release design; canonical adoption deferred.",
          "RFC 0013 disposition must be Accepted with canonical adoption deferred")


def validate_contexts(data, base, encode):
    """Validate derived public contexts and negative recipes."""
    require(data["status"] == STATUS, "context authority label")
    require(data["source"] == "conformance/test-vectors/connection/context-vectors.json", "context source")
    require(data["transformation"] == "base-context-with-proposed-carrier-only", "context transformation")
    require(data["scope"] == "public-context-encoding-only-not-Noise-ciphertext", "context scope")
    require(data["prologue_equals_context"] is True, "context/prologue binding")
    source = {item["id"]: item for item in base["contexts"]}
    derived, pairs = {}, set()
    for item in data["contexts"]:
        require(item["id"] not in derived, "duplicate context ID")
        original = source[item["base"]]
        case = dict(original, carrier=item["carrier"])
        raw = encode(case, permitted_carriers=(4, 5))
        require(raw.hex() == item["context_hex"], "derived context bytes drift")
        # Context is the entire prologue. No alternate offsets or crypto schedule.
        derived[item["id"]] = case
        pairs.add((case["mode"], case["carrier"]))
    require(pairs == {(m, c) for m in (1, 2) for c in (4, 5)}, "context mode/carrier coverage")
    require(set(derived) == {f"R13-CONTEXT-{n:02d}" for n in range(1, 5)}, "context ID coverage")
    seen = set()
    for recipe in data["negative_recipes"]:
        require(recipe["id"] not in seen, "duplicate negative ID")
        seen.add(recipe["id"])
        require(set(recipe["changes"]) <= {"mode", "carrier", "server_key_id", "epoch", "handle_hex", "scope"}, "unknown context mutation")
        case = dict(derived[recipe["base"]], **recipe["changes"])
        try:
            encode(case, permitted_carriers=(4, 5))
        except ValueError:
            outcome = "reject-before-noise"
        else:
            require(case["carrier"] != recipe.get("expected_carrier", case["carrier"]), "negative recipe accepts")
            outcome = "reject-before-lookup"
        require(recipe["expected"] == outcome, "negative recipe outcome drift")
    require(len(seen) == 8, "negative context coverage")


def materialize_http(rows):
    """Resolve explicit one-level mutations of preceding direct fixtures only."""
    result = {}
    for row in rows:
        require(row["id"] not in result, "duplicate HTTP ID")
        if "base" in row:
            require(row["base"] in result and "base" not in result[row["base"]], "HTTP mutation base")
            item = copy.deepcopy(result[row["base"]])
            replacements = row.get("replace_headers", {})
            require(set(replacements) <= {name for name, _ in item["headers"]}, "unknown header replacement")
            item["headers"] = [[name, replacements.get(name, value)] for name, value in item["headers"]]
            item["headers"].extend(row.get("append_headers", []))
            item.update({k: v for k, v in row.items() if k not in ("append_headers", "replace_headers")})
        else:
            item = copy.deepcopy(row)
        if "append_zero_bytes" in row:
            count = row["append_zero_bytes"]
            require(type(count) is int and 0 <= count <= 65536, "synthetic fixture fill bound")
            item["body_hex"] += "00" * count
        result[row["id"]] = item
    return result


def lint_http_shape(item):
    """Classify the authored fixture subset, not arbitrary network messages."""
    start, headers = item["start_line"], item["headers"]
    require("\r" not in start and "\n" not in start, "start-line injection")
    require(len((start + "\r\n").encode("ascii")) <= 2048, "start-line bound")
    require(len(headers) <= 64, "field count")
    pairs = []
    for name, value in headers:
        require(re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) is not None, "field name")
        require(all(32 <= ord(c) < 127 for c in value), "field injection/control")
        require(len(f"{name}: {value}\r\n".encode("ascii")) <= 4096, "field bound")
        pairs.append((name.lower(), value))
    block = start + "\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers) + "\r\n"
    require(len(block.encode("ascii")) <= 16384, "header block bound")
    fields = unique_pairs(pairs)
    operation, direction = item["operation"], item["direction"]
    body = bytes.fromhex(item["body_hex"])
    status = None
    if direction == "response":
        match = re.fullmatch(r"HTTP/1\.1 ([1-5][0-9]{2}) [^\r\n]*", start)
        require(match is not None, "response version/status")
        status = int(match[1])
    if operation == "connect":
        require(direction == "response" and 200 <= status < 300 and not body, "CONNECT failure")
        # The fixture's read-ahead is tunnel input, not an HTTP response body.
        bytes.fromhex(item.get("read_ahead_hex", ""))
        return "tunnel"
    require(operation in ("open", "send", "poll", "close"), "unknown operation")
    if direction == "request":
        require(start == f"POST /syntra/1.0/http/{operation} HTTP/1.1", "request target/version")
        require(fields.get("host") == "example.invalid:80", "fixture authority")
        require(fields.get("accept") == "application/octet-stream", "accept")
    else:
        require(direction == "response", "direction")
        require(status in {"open": [201], "send": [204], "poll": [200, 204], "close": [204]}[operation], "success status")
    require(fields.get("cache-control") == "no-store", "cache policy")
    require(not set(fields) & {"transfer-encoding", "content-encoding", "trailer", "expect", "upgrade", "te",
                               "authorization", "cookie", "proxy-authorization", "set-cookie"}, "forbidden header")
    connection_tokens = [token.strip().lower() for token in fields.get("connection", "").split(",")]
    require("close" not in connection_tokens, "connection retirement")
    require("origin" not in fields or fields["origin"] == "https://client.invalid", "fixture Origin allowlist")
    if status == 204:
        require(not body and "content-length" not in fields and "content-type" not in fields, "204 framing")
    else:
        length = fields.get("content-length", "")
        require(re.fullmatch(r"0|[1-9][0-9]{0,4}", length) is not None, "canonical body length")
        require(int(length) == len(body), "body count")
        require(fields.get("content-type") == "application/octet-stream" if body else "content-type" not in fields, "content type")
    association = {
        "request": {"open": set(), "send": {"syntra-route", "syntra-upload"},
                    "poll": {"syntra-route", "syntra-poll"}, "close": {"syntra-route"}},
        "response": {"open": {"syntra-route"}, "send": {"syntra-upload"},
                     "poll": {"syntra-poll"}, "close": set()},
    }[direction][operation]
    require({k for k in fields if k.startswith("syntra-")} == association, "association headers")
    for name in association:
        value = fields[name]
        if name == "syntra-route":
            require(re.fullmatch(r"[0-9a-f]{64}", value) is not None, "route grammar")
        else:
            require(re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None and int(value) < 1 << 64, "counter grammar")
    bounds = ((83, 337) if operation == "open" and direction == "request" else
              (48, 48) if operation == "open" else
              (17, 65535) if (operation == "send" and direction == "request") or status == 200 else (0, 0))
    require(bounds[0] <= len(body) <= bounds[1], "operation body bounds")
    return "accept"


def validate_http(data):
    """Validate structural HTTP fixtures and ACK semantics."""
    require(data["status"] == STATUS and data["scope"] == "structural-HTTP-only-synthetic-bodies-not-valid-Noise", "HTTP fixture scope")
    rows = materialize_http(data["vectors"])
    require(set(rows) == {f"R13-H{n:02d}" for n in range(1, 26)}, "HTTP fixture coverage")
    for item in rows.values():
        try:
            outcome = lint_http_shape(item)
        except ValueError:
            outcome = "reject"
        require(outcome == item["expected"], f"HTTP fixture mismatch: {item['id']} ({outcome})")
    exact(rows["R13-H02"]["attests"], {"complete_carrier_record_input": True,
          "noise_authenticated": False, "runtime_consumed": False, "effects": False}, "ACK authority drift")
    require(rows["R13-H15"]["read_ahead_hex"] == "160303", "CONNECT read-ahead fixture")


def validate_tls_variants(case):
    """Lint carrier-specific definitions; this does not execute a TLS harness."""
    groups = case["input"]["variants"]
    require(isinstance(groups, list) and len(groups) == 2, "TLS carrier group coverage")
    shared = {"verified_h1", "explicit_h1_absent_alpn", "wrong_chain_name_sni",
              "expired_revoked", "tls12", "early_data", "alpn_h2", "forged_evidence",
              "selected_policy_withdrawal", "resumed_ticket_current_policy", "forwarded_claim"}
    paired = {"wrong_d_identity", "wrong_d_policy_generation",
              "equal_authority_deadline_different_generation", "policy_replacement_between_handshakes"}
    for group, carrier in zip(groups, (3, 5)):
        require(isinstance(group, dict) and set(group) == {
            "carriers", "scenarios", "positive_expected", "negative_expected"}, "TLS variant group shape")
        exact(group["carriers"], [carrier], "TLS variant carrier scope")
        scenarios = group["scenarios"]
        require(isinstance(scenarios, list) and all(isinstance(s, str) for s in scenarios),
                "TLS scenario names")
        require(len(scenarios) == len(set(scenarios)) and
                set(scenarios) == shared | (paired if carrier == 5 else set()), "TLS scenario carrier coverage")
        exact(group["positive_expected"], {"single_verified_stream": True} if carrier == 3 else
              {"independent_u_d_verification": True}, "TLS carrier positive assertions")
        exact(group["negative_expected"], {"d_stream_required": False} if carrier == 3 else
              {"mixed_generation_pair_accepted": False}, "TLS carrier negative assertions")
    require("mixed_generation_pair_accepted" not in case["negative_expected"],
            "HTTPS pair assertion cannot apply to WSS")


def validate_cases(data, rfc):
    """Validate case coverage, traces, and direction-specific expectations."""
    require(data["status"] == STATUS and data["runtime_verdict"] == "NOT_EXECUTED", "case authority/verdict")
    definitions = set(re.findall(r"\*\*(R13-[0-9]{2}) \(", rfc))
    require(definitions == {f"R13-{n:02d}" for n in range(1, 30)}, "RFC requirement definitions")
    seen, covered = set(), set()
    for case in data["cases"]:
        require(case["id"] not in seen, "duplicate candidate case")
        seen.add(case["id"])
        exact(case["roles"], ["client", "server"], "candidate role coverage")
        exact(case["modes"], ["bootstrap", "returning"], "candidate mode coverage")
        exact(case["carriers"], [3, 5] if case["id"] == "R13-T10" else [4, 5], "case carrier coverage")
        refs = case["requirements"]
        require(refs and len(refs) == len(set(refs)) and set(refs) <= definitions, "case requirement refs")
        covered.update(refs)
        require(case["input"]["action"] and case["input"]["variants"], "missing test stimuli")
        require(case["positive_expected"] and all(v is True for v in case["positive_expected"].values()),
                "positive expectations must be True")
        require(case["negative_expected"] and all(v is False for v in case["negative_expected"].values()),
                "negative expectations must be False")
        if case["id"] == "R13-T10":
            validate_tls_variants(case)
        # The RFC's table and machine trace must agree reciprocally.
        require(re.fullmatch(r"R13-T(?:0[1-9]|1[0-4])", case["id"]) is not None, "candidate case ID")
        row = re.search(rf"^\| {case['id']} \| ([^|]+)\|", rfc, re.MULTILINE)
        require(row is not None and set(re.findall(r"R13-[0-9]{2}", row[1])) == set(refs), "RFC/case trace drift")
    require(seen == {f"R13-T{n:02d}" for n in range(1, 15)} and covered == definitions, "candidate case/requirement coverage")
    ack = next(case for case in data["cases"] if case["id"] == "R13-T06")
    require(ack["positive_expected"]["ack_without_driver_decryption"] is True and
            ack["negative_expected"]["ack_proves_authentication"] is False, "ACK test semantics")


def validate_profiles(data, contract, current):
    """Validate the isolated carrier registry without claiming allocation."""
    require(data["status"] == STATUS, "registry authority label")
    seen, codes = set(), set()
    for profile in data["profiles"]:
        name, code = profile["id"], profile["carrier"]
        require(name not in seen and code not in codes, "duplicate carrier registry entry")
        seen.add(name)
        codes.add(code)
        carrier = contract["proposed_carriers"][name]
        require(name not in {p["id"] for p in current["profiles"]} and
                code not in {p.get("carrier") for p in current["profiles"]}, "active allocation conflict")
        expected = {"id": name, "kind": "CARRIER", "carrier": carrier["code"],
                    "binding": carrier["binding"], "domain": "syntra.1.0",
                    "endpoint_prefix": "/syntra/1.0/http/", "secure": True,
                    "integral_noise": True, "production_allowed_if_adopted": True,
                    "claimable": False, "manifests": ["cases.yaml"],
                    "vectors": ["context-vectors.json", "http-vectors.json"]}
        if code == 5:
            expected.update(tls_minimum="1.3", tls_termination="trusted-in-process")
        exact(profile, expected, "proposed registry drift")
    require(seen == set(contract["proposed_carriers"]) and codes == {4, 5}, "registry coverage")


def validate_requirements(data, cases, current):
    """Validate local requirement IDs and reciprocal case traces."""
    require(data["status"] == STATUS and data["runtime_verdict"] == "NOT_EXECUTED", "requirement authority/verdict")
    active = {row["requirement_id"] for row in current["requirements"]}
    seen, proposed = set(), set()
    for row in data["requirements"]:
        rid, pid = row["requirement_id"], row["proposed_requirement_id"]
        require(rid not in seen and pid not in proposed and pid not in active, "requirement ID collision")
        require(re.fullmatch(r"R13-(?:0[1-9]|[12][0-9])", rid) is not None, "local requirement ID")
        seen.add(rid)
        proposed.add(pid)
        number = int(rid.removeprefix("R13-"))
        require(pid == f"SNTR-HPC-{number:03d}", "proposed ID mapping")
        owner = "security" if number in (18, 19, 20, 21, 29) else "transports"
        require(row["owner"] == f"specifications/{owner}.md", "proposed owner mapping")
        expected = sorted(case["id"] for case in cases["cases"] if rid in case["requirements"])
        exact(row["test_ids"], expected, "nonreciprocal candidate requirement/case trace")
    require(seen == {f"R13-{n:02d}" for n in range(1, 30)}, "requirement coverage")


def git(root, *args):
    """Run a bounded Git command for base and worktree verification."""
    return subprocess.check_output(["git", *args], cwd=root, timeout=30)


def sha(raw):
    """Return the SHA-256 hex digest for fingerprint inputs."""
    return hashlib.sha256(raw).hexdigest()


def verify_base(root):
    """Preserve every base byte, allowing only exact RFC0014 appendices."""
    result = {}
    schema_paths = git(root, "ls-tree", "-r", "--name-only", BASE, "--", "proto").decode().splitlines()
    require(len(schema_paths) == 8, "base schema inventory")
    for path in (*BASE_FILES, *schema_paths, "conformance/manifest/rpc.yaml"):
        original = git(root, "show", f"{BASE}:{path}")
        current = read_bounded(root, path)
        if path in TERMINAL_APPENDICES:
            require(current.startswith(original) and
                    sha(current[len(original):]) == TERMINAL_APPENDICES[path],
                    f"active input changed before adoption: {path} (only exact RFC0014 appendix permitted)")
        else:
            require(current == original, f"active input changed before adoption: {path}")
        result[path] = sha(original)
    return result


def validate_terminal_adoption(root):
    """Check the accepted RFC0014 ID translation, owners and reciprocal traces.

    This is static adoption validation, never a protocol runner. Exact appendix
    pins in verify_base protect the requirement text and every case assertion;
    these independent checks prevent trace mistakes from being hidden by a pin.
    """
    rfc = read_bounded(root, "rfcs/0014-scoped-terminal-receipt.md").decode()
    definitions = re.findall(r"\*\*(R14-[0-9]{2}) \(", rfc)
    exact(sorted(definitions), [f"R14-{n:02d}" for n in range(1, 14)],
          "RFC0014 accepted requirement inventory drift")
    rfc_rows = re.findall(r"^\| (R14-T[0-9]{2}) \|[^|]+\| ([^|]+)\|", rfc, re.MULTILINE)
    exact(sorted(cid for cid, _ in rfc_rows), [f"R14-T{n:02d}" for n in range(1, 15)],
          "RFC0014 accepted case inventory drift")
    rfc_traces = dict(rfc_rows)
    cases = [c for c in load(root, "conformance/manifest/rpc.yaml")["cases"]
             if c["id"].startswith("CONF-TRC-")]
    exact(sorted(c["id"] for c in cases), [f"CONF-TRC-{n:03d}" for n in range(1, 15)],
          "RFC0014 case inventory drift")
    for case in cases:
        n = int(case["id"].removeprefix("CONF-TRC-"))
        refs = TERMINAL_TRACES[n - 1]
        exact(case["requirement"], [f"SNTR-TRC-{r:03d}" for r in refs], "RFC0014 case trace drift")
        trace = rfc_traces[f"R14-T{n:02d}"].strip()
        if n == 14:
            exact(trace, "R14-01 through R14-13", "RFC0014 accepted requirement range drift")
            labels = list(range(1, 14))
        else:
            labels = [int(r) for r in re.findall(r"R14-([0-9]{2})", trace)]
        exact(sorted(labels), sorted(refs), "RFC0014 accepted RFC/case trace drift")
        exact(case["roles"], ["client", "server"], "RFC0014 role drift")
        exact(case["capabilities"], [], "RFC0014 must not allocate capability")
        exact(case["mandatory"], n == 1, "RFC0014 default/opt-in execution gate drift")
        require("NOT_EXECUTED" in case["notes"] and "verdict" not in case and "results" not in case,
                "RFC0014 registration is not execution")
        scenario = case["input"]["faults"]["terminal_receipt"]
        exact(scenario["rfc_case"], f"R14-T{n:02d}", "RFC0014 case alias drift")
        require(scenario["barrier"] and scenario["variants"], "RFC0014 missing structured stimuli")
        for label, value in (("positive_assertions", True), ("negative_assertions", False)):
            assertions = case["expected"]["transport"][label]
            require(assertions and all(type(v) is bool and v is value for v in assertions.values()),
                    "RFC0014 positive/negative assertion drift")
    rows = [r for r in load(root, "conformance/manifest/requirements.yaml")["requirements"]
            if r["requirement_id"].startswith("SNTR-TRC-")]
    exact(sorted(r["requirement_id"] for r in rows), [f"SNTR-TRC-{n:03d}" for n in range(1, 14)],
          "RFC0014 requirement inventory drift")
    owners = {n: f"specifications/{owner}.md" for owner, numbers in TERMINAL_OWNERS.items()
              for n in numbers}
    for owner, numbers in TERMINAL_OWNERS.items():
        text = read_bounded(root, f"specifications/{owner}.md").decode()
        exact(sorted(re.findall(r"\*\*(SNTR-TRC-[0-9]+)\*\*", text)),
              sorted(f"SNTR-TRC-{n:03d}" for n in numbers), "RFC0014 owner definitions drift")
    for row in rows:
        rid = row["requirement_id"]
        n = int(rid.removeprefix("SNTR-TRC-"))
        exact(row["specification"], owners[n], "RFC0014 requirement owner drift")
        exact(row["test_ids"], sorted(c["id"] for c in cases if rid in c["requirement"]),
              "RFC0014 nonreciprocal case trace")
        exact(row["automation_status"], "partially_automated", "RFC0014 review disposition drift")
        require("NOT_EXECUTED" in row["notes"], "RFC0014 requirement registration is not execution")


def validate(root=ROOT):
    """Validate the isolated candidate and report its static fingerprint."""
    head = git(root, "rev-parse", "HEAD").decode().strip()
    files = {path: sha(read_bounded(root, path)) for path in SOURCE_FILES}
    base_hashes = verify_base(root)
    validate_terminal_adoption(root)
    contract = load(root, f"{BUNDLE}/contract.json")
    validate_contract(contract)
    validate_acceptance_reference(root, contract["acceptance_reference"])
    validate_profiles(load(root, f"{BUNDLE}/profiles.yaml"), contract,
                      load(root, "conformance/profiles.yaml"))
    validate_contexts(load(root, f"{BUNDLE}/context-vectors.json"),
                      load(root, "conformance/test-vectors/connection/context-vectors.json"),
                      context_encoder(root))
    validate_http(load(root, f"{BUNDLE}/http-vectors.json"))
    rfc = read_bounded(root, "rfcs/0013-http-tls-carriers.md").decode()
    exact(re.findall(r"^- Status: (.*)$", rfc, re.MULTILINE), ["Accepted"],
          "RFC status must be Accepted; canonical adoption remains pending")
    cases = load(root, f"{BUNDLE}/cases.yaml")
    validate_cases(cases, rfc)
    validate_requirements(load(root, f"{BUNDLE}/requirements.yaml"), cases,
                          load(root, "conformance/manifest/requirements.yaml"))
    require(files == {path: sha(read_bounded(root, path)) for path in SOURCE_FILES},
            "candidate source changed during validation; rerun on a stable worktree")
    require(base_hashes == verify_base(root), "active source changed during validation")
    require(head == git(root, "rev-parse", "HEAD").decode().strip(), "HEAD changed during validation")
    return {
        "format_version": 1, "kind": "worktree-not-release",
        "status": STATUS,
        "scope": "isolated-RFC0013-not-canonical-inputs", "authority": GATES,
        "acceptance_reference": contract["acceptance_reference"],
        "acceptance_reference_validation": "local-reference-consistency-only-not-GitHub-authorization",
        "source": {"base_revision": BASE, "head": head,
                   "dirty": bool(git(root, "status", "--porcelain", "--untracked-files=all")),
                   "candidate_revision": None},
        "static_validation": "PASS", "runtime_conformance": "NOT_EXECUTED",
        "base_git_blobs_sha256": base_hashes,
        "files_sha256": files,
        "worktree_fingerprint_sha256": sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
        "fingerprint_encoding": "path-to-raw-sha256-json-sorted-compact-v1",
        "coverage": {"proposed_carriers": 2, "contexts": 4, "context_negatives": 8,
                      "http_shapes": 25, "case_groups": 14, "requirements": 29},
    }


def main():
    """Parse candidate validation modes and report isolated results."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--record-worktree", action="store_true", help="emit fingerprint JSON to stdout; no writes")
    mode.add_argument("--require-adoption", action="store_true", help="fail closed while canonical adoption is pending")
    args = parser.parse_args()
    try:
        report = validate()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"HTTP candidate invalid: {exc}\n")
    if args.require_adoption:
        parser.exit(2, "BLOCKED: canonical adoption pending; public approval and human security self-review recorded; activation and publisher authorization deferred; no release pin\n")
    if args.record_worktree:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("isolated RFC0013 static checks passed: 4 contexts, 8 negatives, 25 HTTP shapes, 14 case groups")
        print("adoption BLOCKED; runtime/formal conformance NOT_EXECUTED; active carriers remain 1/2/3")


if __name__ == "__main__":
    main()
