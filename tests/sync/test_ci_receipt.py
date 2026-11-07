import unittest
from run_contracts import counts_from_tap
VALID = "# tests 84\n# pass 84\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n"
class ReceiptTests(unittest.TestCase):
    def test_exact_count_accepted(self):
        self.assertEqual(counts_from_tap(VALID)["tests"], 84)
    def test_lower_collection_rejected(self):
        with self.assertRaises(ValueError): counts_from_tap(VALID.replace("84", "83"))
    def test_skips_rejected(self):
        with self.assertRaises(ValueError): counts_from_tap(VALID.replace("skipped 0", "skipped 1"))
    def test_missing_and_duplicate_counts_rejected(self):
        for text in ["", VALID + "# tests 84\n"]:
            with self.assertRaises(ValueError): counts_from_tap(text)
if __name__ == "__main__": unittest.main()
