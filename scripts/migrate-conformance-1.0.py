#!/usr/bin/env python3
"""Check/refresh current public context encoding fixtures (no cryptography).

The filename is retained for existing automation. This generates only the
JSON/YAML fixture pair from its current field values; it performs no historical
format conversion, manifest rewriting, or requirement-registry generation.
"""

import argparse
import json
from pathlib import Path
import struct

import yaml

ROOT = Path(__file__).resolve().parents[1]


def encode_context(case, *, permitted_carriers=(1, 2, 3)):
    """Encode public context; proposal tools may supply an isolated allowlist.

    The current generator always uses the default 1/2/3 set. A tool-only
    allowlist neither registers a carrier nor changes current fixture inputs.
    """
    def uint(name, bits):
        value = case[name]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 1 << bits:
            raise ValueError(f"{case['id']}: {name} must be uint{bits}")
        return value
    mode, carrier = uint("mode", 8), uint("carrier", 8)
    key, epoch = uint("server_key_id", 32), uint("epoch", 64)
    if mode not in (1, 2) or carrier not in permitted_carriers:
        raise ValueError(f"{case['id']}: unsupported mode/carrier")
    handle = bytes.fromhex(case["handle_hex"])
    if len(handle) != 8:
        raise ValueError(f"{case['id']}: handle must be eight bytes")
    if (mode == 1 and (epoch != 0 or handle != bytes(8))) or (
            mode == 2 and (epoch == 0 or handle == bytes(8))):
        raise ValueError(f"{case['id']}: invalid mode-specific epoch/handle")
    scope = case["scope"].encode("utf-8")
    if not 1 <= len(scope) <= 255:
        raise ValueError(f"{case['id']}: scope must contain 1..255 UTF-8 bytes")
    return (b"syntra.1.0" + struct.pack(">BBIQ", mode, carrier, key, epoch)
            + handle + struct.pack(">H", len(scope)) + scope)


def generated_assets():
    """Yield (Path, text) for the current JSON source and YAML mirror only."""
    path = ROOT / "conformance/test-vectors/connection/context-vectors.json"
    data = json.loads(path.read_text())
    cases = data["contexts"]
    seen = set()
    for case in cases:
        if case["id"] in seen:
            raise ValueError(f"duplicate context ID {case['id']}")
        seen.add(case["id"])
        raw = encode_context(case)
        case.update(context_hex=raw.hex(), prologue_hex=raw.hex(),
                    context_bytes=len(raw), m1_bytes=len(raw) + 48)
    for recipe in data["negative_recipes"]:
        if recipe["base"] not in seen or recipe["expected"] != "reject-before-noise":
            raise ValueError(f"invalid negative recipe {recipe['id']}")
    yield path, json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    mirror = {
        "format_version": "1.0",
        "profile": ["SYNTRA-1.0-TCP", "SYNTRA-1.0-WS", "SYNTRA-1.0-WSS"],
        "status": data["status"], "source": data["source"],
        "vectors": cases,
        "negative_recipes": [{k: v for k, v in r.items() if k != "detail"}
                             for r in data["negative_recipes"]],
    }
    yield ROOT / "conformance/test-vectors/connection/context-vectors.yaml", (
        "# Public encoding fixtures only; not Noise ciphertext or execution evidence.\n"
        + yaml.safe_dump(mirror, sort_keys=False, allow_unicode=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        assets = list(generated_assets())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, str(exc) + "\n")
    stale = []
    for path, content in assets:
        if not path.exists() or path.read_text() != content:
            stale.append(str(path.relative_to(ROOT)))
            if args.write:
                path.write_text(content)
    if stale and not args.write:
        parser.exit(1, "stale context assets: " + ", ".join(stale) + "\n")
    print("public context fixture pair synchronized; no cryptographic verdict")


if __name__ == "__main__":
    main()
