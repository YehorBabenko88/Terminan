"""Developer regressions for the optional deny-only sidecar; no network."""
import copy
import unittest
from unittest.mock import patch

from terminan.data import scientific_memory


class MemoryBindingTest(unittest.TestCase):
    def setUp(self):
        self.record = {
            "schema": "math.scientific-memory.record.v1",
            "id": "a" * 64, "symbol": "BTCUSDT",
            "input_hash": "b" * 64, "status": "contradicted",
            "dataset": {"id": "c" * 64, "symbol": "BTCUSDT", "sha256": "b" * 64},
            "provenance": {"execution_authority": False, "trading_authorized": False},
            "result": {"price": "9007199254740993.000100"},
        }
        self.entry = {
            "id": self.record["id"], "descriptive_outcome": "contradicted",
            "source_authenticity": "UNATTESTED", "fit_binding": "NOT_PROVIDED",
            "method_validation": "UNVERIFIED", "empirical_reproduction": "UNKNOWN",
            "formal_proof": "NOT_ESTABLISHED", "causal_eligibility": "UNKNOWN",
            "execution_authority": False, "trading_authorized": False,
        }
        self.payload = {
            "schema": "math.scientific-memory.list.v1", "symbol": "BTCUSDT",
            "records": [self.record],
            "qualification_schema": "math.scientific-memory.qualification.v2",
            "qualifications": [self.entry],
        }

    def read(self):
        with patch("terminan.data.read_source", return_value=self.payload):
            return scientific_memory("http://127.0.0.1:1", "BTCUSDT", 50)

    def refuse(self):
        with self.assertRaises(RuntimeError):
            self.read()

    def test_negative_and_exact_decimal_unchanged(self):
        before = copy.deepcopy(self.payload)
        self.assertEqual(self.read(), [self.record])
        self.assertEqual(self.payload, before)

    def test_legacy_minimal_record(self):
        del self.payload["qualification_schema"], self.payload["qualifications"]
        self.record["dataset"] = {"id": "c" * 64}
        del self.record["provenance"]
        self.assertEqual(self.read(), [self.record])

    def test_empty(self):
        self.payload["records"] = []
        self.payload["qualifications"] = []
        self.assertEqual(self.read(), [])

    def test_missing_schema(self):
        del self.payload["qualification_schema"]
        self.refuse()

    def test_missing_entries(self):
        del self.payload["qualifications"]
        self.refuse()

    def test_wrong_schema(self):
        self.payload["qualification_schema"] = "v3"
        self.refuse()

    def test_wrong_count(self):
        self.payload["qualifications"] = []
        self.refuse()

    def test_duplicate_identity(self):
        self.payload["records"].append(copy.deepcopy(self.record))
        self.payload["qualifications"].append(copy.deepcopy(self.entry))
        self.refuse()

    def test_wrong_dataset_symbol(self):
        self.record["dataset"]["symbol"] = "ETHUSDT"
        self.refuse()

    def test_wrong_dataset_hash(self):
        self.record["dataset"]["sha256"] = "d" * 64
        self.refuse()

    def test_wrong_entry_identity(self):
        self.entry["id"] = "d" * 64
        self.refuse()

    def test_wrong_outcome(self):
        self.entry["descriptive_outcome"] = "reproduced"
        self.refuse()

    def test_positive_and_nonboolean_authority(self):
        for key in ("execution_authority", "trading_authorized"):
            for value in (True, 0, None):
                with self.subTest(key=key, value=value):
                    self.entry[key] = value
                    self.refuse()
            self.entry[key] = False

    def test_positive_source(self):
        self.entry["source_authenticity"] = "VERIFIED"
        self.refuse()

    def test_unknown_field(self):
        self.entry["receipt"] = "untrusted"
        self.refuse()

    def test_missing_provenance(self):
        del self.record["provenance"]
        self.refuse()

    def test_record_authority(self):
        self.record["provenance"]["execution_authority"] = True
        self.refuse()

    def legacy(self):
        del self.payload["qualification_schema"], self.payload["qualifications"]

    def test_legacy_explicit_false_preserved(self):
        self.legacy()
        before = copy.deepcopy(self.record)
        self.assertEqual(self.read(), [before])
        self.assertEqual(self.record, before)

    def test_legacy_positive_or_nonliteral_provenance_refused(self):
        self.legacy()
        for flag in ("execution_authority", "trading_authorized"):
            for value in (True, 0, 1, None, "false", [], {}):
                with self.subTest(flag=flag, value=value):
                    self.record["provenance"][flag] = value
                    self.refuse()
            self.record["provenance"][flag] = False

    def test_legacy_malformed_provenance_refused(self):
        self.legacy()
        for value in (None, [], "unknown", False):
            with self.subTest(value=value):
                self.record["provenance"] = value
                self.refuse()

    def test_top_level_authority_refused_with_or_without_sidecar(self):
        for legacy in (False, True):
            if legacy:
                self.legacy()
            for flag in ("execution_authority", "trading_authorized"):
                for value in (True, 0, None):
                    with self.subTest(legacy=legacy, flag=flag, value=value):
                        self.record[flag] = value
                        self.refuse()
                del self.record[flag]

    def test_legacy_partial_provenance_stays_descriptive(self):
        self.legacy()
        self.record["provenance"] = {"collector": "Grid"}
        self.assertEqual(self.read(), [self.record])
