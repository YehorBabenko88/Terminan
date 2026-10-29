import tempfile
import unittest
from pathlib import Path
from terminan.saved_cache import open_cache, put, get, compute_mtf, CacheError, ALGORITHM

IDENTITY = dict(source="grid",source_revision="a"*64,dataset="candles_1m",symbol="BTCUSDT",
 timeframe="5m",from_ms=1767225600000,to_ms=1767225840000,algorithm=ALGORITHM,parameters_hash="b"*64)
# A complete fixture must cover every minute and account for every footprint volume.
PAYLOAD=compute_mtf(IDENTITY,dict(source_revision="a"*64,
 candles=[dict(symbol="BTCUSDT",ts=1767225600000+i*60000,open=100,high=102,low=99,close=101,buy_volume=2,sell_volume=1) for i in range(5)],
 footprint=[dict(symbol="BTCUSDT",ts=1767225600000+i*60000,price=100,buy_volume=2,sell_volume=1) for i in range(5)]))

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
    def test_compute_complete_five_minute(self):
        ident = dict(IDENTITY, timeframe="5m", to_ms=1767225840000)
        candles = [dict(symbol="BTCUSDT", ts=1767225600000+i*60000,
                        open=100+i, high=102+i, low=99+i, close=101+i,
                        buy_volume=2, sell_volume=1) for i in range(5)]
        footprint = [dict(symbol="BTCUSDT", ts=c["ts"], price=100,
                          buy_volume=2, sell_volume=1) for c in candles]
        result = compute_mtf(ident, dict(source_revision="a"*64,
                                        candles=candles, footprint=footprint))
        self.assertTrue(result["complete"])
        self.assertEqual(result["candles"][0]["volume"], 15)
        self.assertEqual(result["candles"][0]["poc_price"], 100)
        put(self.con, ident, result, now=100)
        self.assertEqual(get(self.con, ident, now=101)["state"], "HIT")
    def test_compute_partial_is_not_cached(self):
        ident = dict(IDENTITY, timeframe="5m", to_ms=1767225840000)
        source = dict(source_revision="a"*64, candles=[
            dict(symbol="BTCUSDT", ts=1767225600000, open=100, high=102,
                 low=99, close=101, buy_volume=2, sell_volume=1)], footprint=[])
        result = compute_mtf(ident, source)
        self.assertFalse(result["complete"])
        with self.assertRaises(CacheError):
            put(self.con, ident, result, now=100)
    def test_wrong_key_rejected(self):
        with self.assertRaises(CacheError):
            get(self.con, dict(IDENTITY, algorithm="other"), now=100)

if __name__ == "__main__":
    unittest.main()
