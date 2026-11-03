#!/usr/bin/env python3
"""Check/refresh existing requirement owner locations from current definitions.

This is metadata generation, not requirement acceptance or execution evidence.
Only specification/section fields are synchronized. Unknown or duplicate IDs
fail closed; adding/removing registry rows and reviewing coverage are explicit
authoring tasks. No Git history, archived inventory or path aliases are used.
"""

import argparse
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = re.compile(r"\*\*(SNTR-[A-Z]+-\d+[A-Z]*|SYN-ARCH-\d+|SYN-URP-\d+)\b")
OWNERS = tuple("specifications/" + name + ".md" for name in (
    "connection", "wire-format", "rpc", "security", "transports", "recovery")) + (
    "conformance/README.md",)
# Tooling-only verification IDs may be owned by this supporting guide.
OPTIONAL_OWNERS = ("docs/schema-tooling.md",)


def owner_definitions(root=None):
    """Return id -> [(repo-relative Path, line, heading)] for current owners.

    The six protocol pages and test guide are required. An optional schema
    tooling guide participates only when present. Historical records are never
    definition sources, even when they contain bold IDs.
    """
    root = ROOT if root is None else Path(root)
    definitions = {}
    for name in OWNERS + OPTIONAL_OWNERS:
        path = root / name
        if name in OPTIONAL_OWNERS and not path.exists():
            continue
        section = ""
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.startswith("#"):
                section = line.lstrip("# ")
            for rid in DEFINITION.findall(line):
                definitions.setdefault(rid, []).append((Path(name), number, section))
    return definitions


def owner_locations(root=None):
    """Return id -> (owner path string, heading); reject duplicate definitions."""
    locations = {}
    for rid, definitions in owner_definitions(root).items():
        if len(definitions) != 1:
            where = ", ".join(f"{path}:{line}" for path, line, _ in definitions)
            raise ValueError(f"duplicate owner for {rid}: {where}")
        path, _, section = definitions[0]
        locations[rid] = (path.as_posix(), section)
    return locations


def synchronized(text, locations):
    """Update owner metadata of existing rows, preserving all other values.

    Supports the registry's flow and block rows without discarding comments.
    Does not drop removed IDs, add definitions, infer tests, or change evidence
    status. Callers must explicitly reconcile registry membership first.
    """
    before = yaml.safe_load(text)["requirements"]
    seen = set()
    for entry in before:
        rid = entry["requirement_id"]
        if rid in seen:
            raise ValueError(f"duplicate registry requirement {rid}")
        seen.add(rid)
    missing = sorted(seen - locations.keys())
    if missing:
        raise ValueError("no definition in the current owners: " + ", ".join(missing))
    rows = re.split(r"(?=^  - (?:\{ )?requirement_id:)", text, flags=re.M)
    for i, row in enumerate(rows):
        found = re.match(r"  - (?:\{ )?requirement_id:\s*([A-Z0-9-]+)", row)
        if not found:
            continue
        path, section = locations[found[1]]
        row = re.sub(r"specification:\s*[^,\n }]+", "specification: " + path, row)
        # Flow-map sections are quoted; block-map sections may be plain or
        # quoted. JSON quoting handles quotes, colons and Unicode headings.
        value = json.dumps(section, ensure_ascii=False)
        if row.startswith("  - {"):
            row = re.sub(r'''section:\s*(?:"(?:\\.|[^"\\])*"|'(?:''|[^'])*'|[^,}\n]+)''',
                         lambda _: "section: " + value, row)
        else:
            row = re.sub(r"(?m)^    section:.*$", lambda _: "    section: " + value, row)
        rows[i] = row
    result = "".join(rows)
    after = yaml.safe_load(result)["requirements"]
    strip = lambda entries: [{k: v for k, v in entry.items()
                              if k not in ("specification", "section")}
                             for entry in entries]
    if strip(before) != strip(after):
        raise ValueError("owner synchronization changed non-location metadata")
    for entry in after:
        if (entry.get("specification"), entry.get("section")) != locations[entry["requirement_id"]]:
            raise ValueError(f"unsupported registry row layout for {entry['requirement_id']}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = ROOT / "conformance/manifest/requirements.yaml"
    try:
        old = path.read_text()
        new = synchronized(old, owner_locations())
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        sys.exit(str(exc))
    if new != old:
        if not args.write:
            sys.exit("requirement owner metadata is stale; run with --write")
        path.write_text(new)
    print("current requirement owner locations synchronized; IDs and evidence unchanged")


if __name__ == "__main__":
    main()
