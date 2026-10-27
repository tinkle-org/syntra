"""Descriptor/tooling checks, not a Syntra runtime or transport validator.

Uses Python's standard library and Buf; all subprocesses have bounded waits.
Historical declarations come from the archived immutable descriptor
compatibility/v1-initial/historical.json, generated from the actual unchanged
sources at commit 92e5f281aa7c3adac9ba78588c1140b12d55c1d9 before the old
schema tree was removed. Baseline archive files are never rewritten.
"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "compatibility/v1-initial"


def buf(*args, success=True):
    result = subprocess.run(
        ["buf", *args], cwd=ROOT, text=True, capture_output=True, timeout=60
    )
    if success and result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


def config(root, category="FILE"):
    return json.dumps({
        "version": "v2", "modules": [{"path": root}],
        "lint": {"use": ["STANDARD"]},
        "breaking": {"use": [category]},
    })


def symbols(image, kind):
    return {
        file["package"] + "." + item["name"]: item
        for file in image["file"] for item in file.get(kind, [])
    }


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="syntra-schema-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.manifest = json.loads((BASELINE / "manifest.json").read_text())
        # Archived historical descriptor provenance; no live schema tree.
        historical_path = BASELINE / "historical.json"
        actual_hist = hashlib.sha256(historical_path.read_bytes()).hexdigest()
        if actual_hist != cls.manifest["historical_image_sha256"]:
            raise AssertionError("Archived historical descriptor changed")
        cls.old_path = str(historical_path)
        current = cls.new_path = str(Path(cls.temp.name) / "current.json")
        buf("build", "--as-file-descriptor-set", "--exclude-source-info", "-o", current)
        cls.old = json.loads(Path(cls.old_path).read_text())
        cls.new = json.loads(Path(current).read_text())

    def test_format(self):
        result = buf("format", "--diff", "--exit-code")
        self.assertEqual(result.stdout, "")

    def test_standard_lint(self):
        buf("lint")

    def test_initial_baseline_integrity(self):
        self.assertEqual(
            hashlib.sha256((BASELINE / "image.json").read_bytes()).hexdigest(),
            self.manifest["image_sha256"],
        )

    def test_proto_is_sole_source(self):
        # User-directed migration: no live duplicate schema tree; buf module is proto only.
        self.assertFalse((ROOT / "schema" / "syntra" / "v1" / "error.proto").exists())
        self.assertFalse((ROOT / "schema" / "syntra" / "v1" / "session.proto").exists())
        buf_yaml = (ROOT / "buf.yaml").read_text()
        self.assertIn("path: proto", buf_yaml)
        self.assertNotIn("path: schema", buf_yaml)
        self.assertTrue((BASELINE / "historical.json").is_file())
        self.assertIn("historical_image_sha256", self.manifest)
        self.assertIn("historical_sources", self.manifest)

    def test_file_compatibility_against_initial_snapshot(self):
        buf("breaking", "--against", str(BASELINE / "image.json"))

    def test_historical_binary_wire_compatibility(self):
        # Audit only: this does not replace the default FILE gate.
        buf("breaking", "--against", self.old_path, "--config", config("proto", "WIRE"))

    def test_historical_file_migration_is_detected(self):
        result = buf("breaking", "--against", self.old_path, success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('file "syntra/v1/error.proto" was deleted', result.stdout + result.stderr)
        self.assertIn("Frame", result.stdout + result.stderr)
        self.assertIn("deleted", (result.stdout + result.stderr).lower())

    def test_all_declarations_preserved_exactly(self):
        # File relocation is intentional; compare the entire declaration trees,
        # not just wire types. Detects names, enum values, oneofs, JSON names,
        # optional presence, nested types, reservations and field numbers.
        for kind in ("messageType", "enumType", "service", "extension"):
            self.assertEqual(symbols(self.old, kind), symbols(self.new, kind))

    def test_historical_and_new_fixture_interpretations_match(self):
        fixtures = json.loads((ROOT / "tests/schema/fixtures/frames.json").read_text())
        for name, raw in fixtures.items():
            interpretations = []
            for image in (self.old_path, self.new_path):
                result = subprocess.run(
                    ["buf", "convert", image, "--type", "syntra.v1.Frame",
                     "--from", "-#format=binpb", "--to", "-#format=json"],
                    input=bytes.fromhex(raw), capture_output=True, cwd=ROOT, timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                interpretations.append(json.loads(result.stdout))
            self.assertEqual(interpretations[0], interpretations[1], name)

    def test_file_gate_detects_a_candidate_renumbering(self):
        # Mutate the candidate, never the prior snapshot: this proves the real
        # initial baseline rejects a future accidental field-number change.
        changed = json.loads(json.dumps(self.new))
        symbols(changed, "messageType")["syntra.v1.Frame"]["field"][0]["number"] = 99
        path = Path(self.temp.name) / "renumbered.json"
        path.write_text(json.dumps(changed))
        result = buf("breaking", str(path), "--against", str(BASELINE / "image.json"), success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version", result.stdout + result.stderr)

    def test_package_options_dependencies_and_inventory(self):
        files = {file["name"]: file for file in self.new["file"]}
        self.assertEqual(set(files), {
            f"syntra/v1/{name}.proto" for name in
            ("envelope", "handshake", "session", "rpc", "events", "capabilities",
             "errors", "recovery_profile")
        })
        for file in files.values():
            self.assertEqual(file["syntax"], "proto3")
            self.assertEqual(file["package"], "syntra.v1")
            # Historical module metadata, kept frozen: the committed Go module
            # moved to tinkle-org/syntra-go (see MIGRATION.md §10). Changing
            # this option is FILE-breaking against the initial baseline.
            self.assertEqual(file["options"]["goPackage"],
                             "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1")
            self.assertFalse(file.get("publicDependency"))
            self.assertTrue(set(file.get("dependency", [])) <= set(files))
        for name in ("session", "capabilities"):
            file = files[f"syntra/v1/{name}.proto"]
            self.assertFalse(file.get("messageType"))
            self.assertFalse(file.get("enumType"))
        self.assertEqual(len(symbols(self.new, "messageType")), 31)
        self.assertEqual(len(symbols(self.new, "enumType")), 1)
        self.assertFalse(symbols(self.new, "service"))

    def test_comments_cite_existing_requirements(self):
        # Individual cited IDs (ranges are prose shorthand) must have definitions.
        definitions = set()
        for path in (ROOT / "specifications").rglob("*.md"):
            definitions.update(re.findall(r"\*\*(SNTR-[A-Z]+-\d+)\*\*", path.read_text()))
        for path in (ROOT / "proto").rglob("*.proto"):
            for requirement in re.findall(r"SNTR-[A-Z]+-\d+", path.read_text()):
                self.assertIn(requirement, definitions, f"{path}: {requirement}")

    def test_no_domain_types_or_transport_dependencies(self):
        source = "\n".join(path.read_text() for path in (ROOT / "proto").rglob("*.proto"))
        self.assertNotRegex(source, r"(?i)\b(chat|conversation|contact|receipt|payment|messenger)\b")
        self.assertNotIn("google.protobuf.Any", source)
        self.assertNotRegex(source, r"(?i)\bhttp_status\b|\bgrpc\b|^service\s")


if __name__ == "__main__":
    unittest.main()
