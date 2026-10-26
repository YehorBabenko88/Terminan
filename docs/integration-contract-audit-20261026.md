# Integration architecture audit — 2026-10-26

Scope: offline review of Terminan main pinned at `fee79f4b15fc1f9efcff9ca12c403688b0026260`. Related immutable checkpoint pins: Grid `d537d525296ef34f727996e240ae6c60102c6082`; Strattester `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea`. These are historical baseline pins, not current integration PR heads. No source database accessed.

## Actual Terminan read path (source: terminan/data.py)

* `TERMINAN_STRATTESTER_DB` -> SQLite URI `mode=ro` -> `candles` table, symbol/timeframe filtered, descending `open_time`, bounded to 1000 -> `/api/candles` -> chart and levels.
* `TERMINAN_RESULTS_DB` -> SQLite URI `mode=ro` -> `research_results`, symbol filtered, descending `created_at`, bounded to 100 -> `/api/research` -> research JSON. This is historical research only, not trading authority.
* `TERMINAN_GRID_DSN` -> psycopg `default_transaction_read_only=on`, `statement_timeout=3000`, `connect_timeout=3` -> `candles_1m` and `footprint_1m` by symbol, bounded to 1000 -> `/api/grid/candles` and `/api/grid/footprint`. Footprint is aggregated trades, never LIVE L2.
* `/api/status` reports configured environment variables, **not** verified source health, coverage, freshness, or producer identity.

## Unresolved compatibility and safety gaps

1. No schema version negotiation or source identity attestation in the observed Terminan adapter.
2. Grid `extract(epoch from ts)*1000` is cast to float; timestamps are not checked as integral UTC milliseconds. SQLite `open_time` and `created_at` have no unit checks.
3. No producer source timestamp, ingestion timestamp, freshness, completeness or coverage metadata is carried through the existing adapter.
4. No Grid WAL ownership/fencing provenance is validated by Terminan.
5. Numeric values from Grid are cast to float without finite-value rejection; SQLite values are passed through without semantic OHLC validation. JSON serialization rejects nonfinite floats at the HTTP boundary, but no row-level quality state is returned.
6. Research `metrics` JSON is decoded without run provenance, future-leakage controls or nonfinite recursive validation. Treat as untrusted historical diagnostics.
7. Missing source configuration returns `[]`, indistinguishable from a valid empty dataset at these API endpoints. The HTTP server converts unexpected adapter exceptions to 503.
8. Read-only SQLite URI and PostgreSQL session settings are present, but server-side DB role permissions and immutable snapshots are not proven.
9. `grid_query` limits statement runtime but uses a synchronous DB call; cancellation and concurrent request budget are not demonstrated.

## Evidence classification

* Synthetic tests in this PR: only boundary behavior and SQL query construction, **not** schema compatibility with real Grid or Strattester.
* Hosted CI PASS: only when checked against the exact PR HEAD.
* Physical Windows G0: NOT_RUN; no deployment, DB write, ACL change, G1, or order execution.

Before integration acceptance, pin current producer PR HEADs, obtain their exact schema definitions and migration provenance, add explicit quality metadata and fail-closed adapters, then run offline cross-repo fixtures and physical read-only G0.
