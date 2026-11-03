"""Lint candidate public encodings; no Noise or runtime conformance claim."""

import json
import importlib.util
from pathlib import Path
import struct
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance/test-vectors/connection/context-vectors.json"
SPEC = importlib.util.spec_from_file_location("context_sync", ROOT / "scripts/migrate-conformance-1.0.py")
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class ConnectionVectorTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(VECTORS.read_text(encoding="utf-8"))

    def test_current_input_paths_resolve(self):
        paths = json.loads((ROOT / "compatibility/syntra-1.0.json").read_text())["input_paths"]
        self.assertEqual(paths, {
            "connection_context_json": "conformance/test-vectors/connection/context-vectors.json",
            "connection_context_yaml": "conformance/test-vectors/connection/context-vectors.yaml",
            "connection_manifest": "conformance/manifest/connection.yaml",
            "connection_vector_tests": "tests/test_connection_vectors.py",
        })
        for path in paths.values():
            self.assertTrue((ROOT / path).is_file(), path)
        manifest = yaml.safe_load((ROOT / paths["connection_manifest"]).read_text())
        self.assertTrue(manifest["cases"])
        for case in manifest["cases"]:
            vector_path = case["input"].get("transport", {}).get("vectors")
            if vector_path is not None:
                self.assertEqual(vector_path, paths["connection_context_yaml"])

    def test_status_and_coverage(self):
        self.assertEqual(self.data["status"], "candidate-sdd")
        self.assertEqual(self.data["domain_ascii"], "syntra.1.0")
        cases = self.data["contexts"]
        for case in cases:
            self.assertRegex(case["id"], r"^SYNTRA-CONTEXT-\d{2}$")
        self.assertEqual(len({v["id"] for v in cases}), len(cases))
        self.assertEqual({v["id"] for v in cases},
                         {f"SYNTRA-CONTEXT-{n:02d}" for n in range(1, 10)})
        self.assertEqual({v["mode"] for v in cases}, {1, 2})
        self.assertEqual({v["carrier"] for v in cases}, {1, 2, 3})
        self.assertEqual({(v["mode"], v["carrier"]) for v in cases},
                         {(m, c) for m in (1, 2) for c in (1, 2, 3)})

    def test_json_yaml_pair_is_identical(self):
        mirror = yaml.safe_load((ROOT / "conformance/test-vectors/connection/context-vectors.yaml").read_text())
        self.assertEqual(mirror["vectors"], self.data["contexts"])
        self.assertEqual(mirror["negative_recipes"], [
            {k: v for k, v in r.items() if k != "detail"}
            for r in self.data["negative_recipes"]])

    def test_golden_context_and_prologue_bytes(self):
        for case in self.data["contexts"]:
            with self.subTest(case=case["id"]):
                scope = case["scope"].encode("utf-8")
                handle = bytes.fromhex(case["handle_hex"])
                self.assertEqual(len(handle), 8)
                self.assertTrue(1 <= len(scope) <= 255)
                self.assertIn(case["mode"], (1, 2))
                self.assertIn(case["carrier"], (1, 2, 3))
                if case["mode"] == 1:
                    self.assertEqual((case["epoch"], handle), (0, bytes(8)))
                else:
                    self.assertGreater(case["epoch"], 0)
                    self.assertNotEqual(handle, bytes(8))
                expected = (
                    b"syntra.1.0"
                    + struct.pack(">BBIQ", case["mode"], case["carrier"],
                                  case["server_key_id"], case["epoch"])
                    + handle + struct.pack(">H", len(scope)) + scope
                )
                self.assertEqual(bytes.fromhex(case["context_hex"]), expected)
                self.assertEqual(case["prologue_hex"], case["context_hex"])
                self.assertEqual(case["context_bytes"], 34 + len(scope))
                self.assertEqual(case["m1_bytes"], len(expected) + 48)

    def test_boundary_sizes_and_offsets(self):
        layout = json.loads((ROOT / "compatibility/syntra-1.0.json").read_text())["context_layout"]
        self.assertEqual(layout["mode"], [10, 11])
        self.assertEqual(layout["carrier"], [11, 12])
        self.assertEqual(layout["scope_length_u16be"], [32, 34])
        for length, context_size, m1_size in ((1, 35, 83), (255, 289, 337)):
            raw = (b"syntra.1.0" + struct.pack(">BBIQ", 1, 1, 0, 0)
                   + bytes(8) + struct.pack(">H", length) + b"a" * length)
            self.assertEqual(len(raw), context_size)
            self.assertEqual(len(raw) + 48, m1_size)
            self.assertEqual(raw[34:], b"a" * length)

    def test_negative_recipes_are_traceable_not_crypto_vectors(self):
        cases = {v["id"]: v for v in self.data["contexts"]}
        recipes = self.data["negative_recipes"]
        self.assertEqual(len({r["id"] for r in recipes}), len(recipes))
        self.assertEqual({r["id"] for r in recipes},
                         {f"SYNTRA-N{n:02d}" for n in range(1, 37)})
        required = {"unsupported-domain", "unsupported-format", "zero-mode",
                    "unknown-carrier", "bootstrap-epoch", "returning-handle",
                     "empty-scope", "oversize-scope", "truncated", "trailing",
                    "invalid-utf8", "scope-byte-length"}
        self.assertEqual({r["mutation"] for r in recipes}, required)
        for recipe in recipes:
            self.assertRegex(recipe["id"], r"^SYNTRA-N\d{2}$")
            self.assertIn(recipe["base"], cases)
            self.assertEqual(recipe["expected"], "reject-before-noise")
        self.assertNotIn("ciphertext_hex", json.dumps(self.data))

    def test_generator_only_updates_current_pair_and_is_in_sync(self):
        assets = list(SYNC.generated_assets())
        self.assertEqual({p.relative_to(ROOT).as_posix() for p, _ in assets}, {
            "conformance/test-vectors/connection/context-vectors.json",
            "conformance/test-vectors/connection/context-vectors.yaml"})
        for path, content in assets:
            self.assertEqual(path.read_text(), content)

    def test_generator_rejects_invalid_source_fields_instead_of_blessing_them(self):
        valid = self.data["contexts"][0]
        for changes in ({"mode": 0}, {"carrier": 4}, {"scope": ""},
                        {"scope": "é" * 128}, {"epoch": 1}, {"server_key_id": True},
                        {"handle_hex": "01"}, {"mode": 2, "epoch": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                SYNC.encode_context(dict(valid, **changes))


if __name__ == "__main__":
    unittest.main()
