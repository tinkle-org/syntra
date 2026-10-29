"""Lint proposed public context fixtures; no Noise or runtime conformance claim."""

import json
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance/plans/sc1-context-v1.json"


class Sc1ProposalVectorTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(VECTORS.read_text(encoding="utf-8"))

    def test_status_and_coverage(self):
        self.assertEqual(self.data["status"], "proposal-only")
        self.assertEqual(self.data["domain_ascii"], "syntra.sc1.v1")
        cases = self.data["contexts"]
        self.assertEqual(len({v["id"] for v in cases}), len(cases))
        self.assertEqual({v["mode"] for v in cases}, {1, 2})
        self.assertEqual({v["carrier"] for v in cases}, {1, 2, 3})

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
                    b"syntra.sc1.v1"
                    + struct.pack(">BBIQ", case["mode"], case["carrier"],
                                  case["server_key_id"], case["epoch"])
                    + handle + struct.pack(">H", len(scope)) + scope
                )
                self.assertEqual(bytes.fromhex(case["context_hex"]), expected)
                self.assertEqual(case["prologue_hex"], case["context_hex"])
                self.assertEqual(case["context_bytes"], 37 + len(scope))
                self.assertEqual(case["m1_bytes"], len(expected) + 48)

    def test_negative_recipes_are_traceable_not_crypto_vectors(self):
        cases = {v["id"]: v for v in self.data["contexts"]}
        recipes = self.data["negative_recipes"]
        self.assertEqual(len({r["id"] for r in recipes}), len(recipes))
        required = {"legacy-go-domain", "legacy-rust-magic", "zero-mode",
                    "unknown-carrier", "bootstrap-epoch", "returning-handle",
                    "empty-scope", "oversize-scope", "truncated", "trailing",
                    "invalid-utf8", "scope-byte-length"}
        self.assertEqual({r["mutation"] for r in recipes}, required)
        for recipe in recipes:
            self.assertIn(recipe["base"], cases)
            self.assertEqual(recipe["expected"], "reject-before-noise")
        self.assertNotIn("ciphertext_hex", json.dumps(self.data))


if __name__ == "__main__":
    unittest.main()
