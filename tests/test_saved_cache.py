import tempfile
import unittest
from pathlib import Path
from terminan.saved_cache import open_cache, put, get, CacheError, ALGORITHM

IDENTITY = dict(source="grid", source_revision="a"*64, dataset="candles_1m",
                symbol="BTCUSDT", timeframe="15m", from_ms=1767225600000,
                to_ms=1767226500000, algorithm=ALGORITHM, parameters_hash="b"*64)
PAYLOAD = dict(state="HISTORICAL_ONLY", source_revision="a"*64,
               complete=True, candles=[dict(ts=1767225600000, close=100)])

class SavedCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.con = open_cache(Path(self.temp.name)/"cache.sqlite")
    def tearDown(self):
        self.con.close()
        self.temp.cleanup()
    def test_hit_after_reopen(self):
        put(self.con, IDENTITY, PAYLOAD, now=100)
        self.con.close()
        self.con = open_cache(Path(self.temp.name)/"cache.sqlite")
        self.assertEqual(get(self.con, IDENTITY, now=101)["payload"], PAYLOAD)
    def test_revision_change_is_miss(self):
        put(self.con, IDENTITY, PAYLOAD, now=100)
        self.assertEqual(get(self.con, dict(IDENTITY, source_revision="c"*64), now=101)["state"], "MISS")
    def test_expiry(self):
        put(self.con, IDENTITY, PAYLOAD, ttl_seconds=2, now=100)
        self.assertEqual(get(self.con, IDENTITY, now=102)["state"], "EXPIRED")
    def test_corrupt_bytes_fail_closed(self):
        result=put(self.con, IDENTITY, PAYLOAD, now=100)
        self.con.execute("UPDATE cache_entries SET payload=? WHERE cache_key=?", (b"altered",result["cache_key"]))
        self.assertEqual(get(self.con, IDENTITY, now=101)["state"], "CORRUPT")
    def test_unverified_rejected(self):
        with self.assertRaises(CacheError):
            put(self.con, IDENTITY, dict(PAYLOAD,state="LIVE"), now=100)
    def test_partial_rejected(self):
        with self.assertRaises(CacheError):
            put(self.con, IDENTITY, dict(PAYLOAD,complete=False), now=100)
    def test_source_mismatch_rejected(self):
        with self.assertRaises(CacheError):
            put(self.con, IDENTITY, dict(PAYLOAD,source_revision="c"*64), now=100)
    def test_wrong_key_rejected(self):
        with self.assertRaises(CacheError):
            get(self.con, dict(IDENTITY, algorithm="other"), now=100)

if __name__ == "__main__":
    unittest.main()
