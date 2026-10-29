PR44: Offline cache result inspection

The new read-only endpoint accepts a 32-character hexadecimal job ID and returns at most 64 cached OHLCV rows. It checks job READY, TTL, identity and SHA256. It never runs computation or modifies Grid, Strattester or PostgreSQL.

LS-5: use a clean checkout, run Python compilation and `py -3.12 -m unittest tests.test_saved_cache tests.test_cache_queue tests.test_cache_monitor -v`. Then run `py -3.12 -m terminan.saved_runner --demo --cache-db <existing isolated PR42 SQLite path> --port 0`. In `/saved`, refresh the cache panel and choose View cached candles on the READY row. No results are inserted into authoritative charts. Physical acceptance and CI remain pending.
