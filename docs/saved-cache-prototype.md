# Offline visualization cache prototype

This is an **opt-in local prototype**, not an active Grid/Strattester integration.

- Storage: separate SQLite file selected by operator, never upstream PostgreSQL/SQLite.
- Producer: offline `compute` action reads one bounded immutable JSON snapshot, computes MTF candle/price-level aggregates, and writes only when every requested period has complete minute/footprint coverage.
- Reader: `get` returns HIT, MISS, EXPIRED, STALE or CORRUPT. Keys include source revision, dataset, symbol, timeframe, UTC bounds, algorithm version and parameters hash.
- Isolation: no source service, network, trading, schema migrations or automatic startup. No cache access in the existing Terminan HTTP server yet.
- Resource bounds: 4 MiB input/output, <=10000 candles, <=50000 footprint levels, <=256 entries, <=30 days TTL. Larger history must later be chunked and streamed through an authorized adapter.
- Source publication authority: NOT IMPLEMENTED. The caller-supplied source_revision is not a cryptographic attestation. Do not point this at production data or treat the result as an authorized live feed.
- SQLite is used for the prototype. PostgreSQL cache schema and separate roles require a future dedicated PR and explicit approval after upstream schema review.
- Cache is derived data, never the authoritative research result. Do not cache staged Strattester results.

## Smoke test (isolated temp directory)

```powershell
py -3.12 -m unittest tests.test_saved_cache -v
```

To exercise CLI, prepare a JSON identity with the exact fields checked by `key_for`, plus a bounded JSON source containing `source_revision`, `candles` and `footprint`. Use `compute` with an explicit `--db` pointing to a new temporary file and `--payload` pointing to that immutable source file. `get` uses the same identity and DB. No automatic writes to existing databases.

## Next implementation gates

1. Independent exact-head tests on Windows/Linux, syntax/negative cases, and real local LS-5 SQLite reopen.
2. Introduce a dedicated worker queue with lease fencing and idempotent chunk generation, avoiding any computation in HTTP request handlers.
3. Add an explicit read-only cache endpoint and bounded UI states `READY/PREPARING/STALE/MISS`.
4. Only then design a PostgreSQL backend in a separate schema/role with migration and rollback; no changes to Grid production schema.
