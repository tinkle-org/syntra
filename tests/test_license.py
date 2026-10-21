"""Keep the complete Apache-2.0 terms and appendix in distributed source."""

import hashlib
from pathlib import Path
import unittest


class LicenseTests(unittest.TestCase):
    def test_canonical_apache_2_text(self):
        # Canonical source: https://www.apache.org/licenses/LICENSE-2.0.txt
        # Ignore whitespace differences, but preserve every word/punctuation mark.
        license_text = (Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()
        self.assertEqual(
            hashlib.sha256(b" ".join(license_text.split())).hexdigest(),
            "0ffddef9e48f8a09aed5caf2d44f7ba1c1be2d9b8e0a6f693b1635b2d5566645",
        )


if __name__ == "__main__":
    unittest.main()
