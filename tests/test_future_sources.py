import copy
import unittest
from terminan.future_sources import (
    SourceContractError, unavailable, validate_envelope,
)

NOW = 1767225600000
BASE = {
    "version": 1, "source": "grid", "kind": "footprint", "symbol": "BTCUSDT",
    "timeframe": "1m", "state": "HISTORICAL_ONLY",
    "authority": "HISTORICAL_ONLY", "runtime_source": "POSTGRESQL_READ_ONLY",
    "source_revision": "a" * 40, "as_of_ms": NOW,
    "coverage": {"from_ms": NOW - 60000, "to_ms": NOW, "complete": True},
    "rows": [{"symbol": "BTCUSDT", "t": NOW - 60000, "price": 100.0,
              "buy_volume": 3.0, "sell_volume": 2.0, "volume": 5.0, "delta": 1.0}],
}

class FutureSourceContractTests(unittest.TestCase):
    def check(self, value):
        return validate_envelope(value, expected_source="grid",
                                 expected_kind="footprint", expected_symbol="BTCUSDT",
                                 now_ms=NOW)

    def test_valid(self):
        self.assertEqual(self.check(copy.deepcopy(BASE))["state"], "HISTORICAL_ONLY")

    def test_unavailable_is_not_live(self):
        self.assertEqual(unavailable("strattester", "research")["authority"], "UNVERIFIED")

    def test_rejects_mismatched_symbol(self):
        v = copy.deepcopy(BASE); v["rows"][0]["symbol"] = "ETHUSDT"
        with self.assertRaises(SourceContractError): self.check(v)

    def test_rejects_wrong_source(self):
        v = copy.deepcopy(BASE); v["source"] = "strattester"
        with self.assertRaises(SourceContractError): self.check(v)

    def test_rejects_bad_volume(self):
        v = copy.deepcopy(BASE); v["rows"][0]["volume"] = 9.0
        with self.assertRaises(SourceContractError): self.check(v)

    def test_rejects_future_data(self):
        v = copy.deepcopy(BASE); v["as_of_ms"] = NOW + 1
        with self.assertRaises(SourceContractError): self.check(v)

    def test_rejects_unbounded_rows(self):
        v = copy.deepcopy(BASE); v["rows"] = v["rows"] * 1001
        with self.assertRaises(SourceContractError): self.check(v)

    def test_rejects_false_live_authority(self):
        v = copy.deepcopy(BASE); v["authority"] = "LIVE"
        with self.assertRaises(SourceContractError): self.check(v)

    def test_rejects_unverified_book(self):
        v = copy.deepcopy(BASE); v["kind"] = "book"
        with self.assertRaises(SourceContractError): self.check(v)

if __name__ == "__main__":
    unittest.main()
