# First physical read-only history integration — evidence-led plan

Baseline Terminan UI PR #27: `7dbc418fa8d41f40ef90db42ace188ff84d15791`.
Observed upstream draft heads at audit: Grid PR #244 `0903f0f8b19c69a7c85d74ccf443276e022416fa`; Strattester PR #21 `11b6c793e6617c3de08e6ca4fa741625c54c1951`. These are *not* proven production deployed heads.

## Verified source facts

- Grid `grid/schema.sql` defines `candles_1m` and `footprint_1m` in PostgreSQL. The current storage implementation writes minute OHLC and price-level aggressive buy/sell volume, delta, trade counts, and POC; actual deployed migrations may add columns. Footprint is executed trade flow, **not** the resting DOM.
- Strattester `strattester/marketdata/schema.py` schema v2 defines SQLite `candles`, `mark_prices`, `index_prices`, `premium_index`, `open_interest`, `funding`, `long_short_ratio`, `public_trade_aggregates`.
- Strattester `strattester/persistence/result_store.py` defines SQLite `research_results` (run_id, symbol, strategy_id, strategy_version, created_at, metrics JSON, optional job_id, lease_token, node_generation) and `staged_research_results`. Staged results are **not** published results; `latest_fenced` requires an external authority validator.
- Terminan R4 `r4_server.py` exposes only synthetic frame/contracts and session routes. `r4_contracts.py` validates offline fixtures with runtime_source NONE and offline authority. **No real historical Grid/Strattester read API exists in this candidate.**

## Minimal physical G0 next

1. Discover the *actual* LS-5 database locations and schema versions via read-only inspection. Do not assume that installed PostgreSQL service implies populated Grid history, or that Strattester files exist.
2. First implement an opt-in, **explicitly configured**, loopback-only history adapter. No automatic scanning of user directories, no default DSN, no broad filesystem access.
3. Prefer bounded, paginated, parameterized SELECT on Grid; separate SQLite URI `mode=ro` for Strattester, with busy_timeout, query_only, no migrations or WAL checkpoints. Never call ResultStore.open() on an existing DB (it creates/migrates).
4. For Grid candles/footprint, preserve symbol, UTC timestamps, original numeric precision, source identity, source/schema version, provenance, row count, interval and coverage; no invented aggregation or trade tape.
5. For Strattester candles and research results, distinguish historical results from executable signals; preserve run/strategy/version, created_at, metrics, and publication authority. Staged rows remain excluded. Legacy unfenced rows must be labeled unverified.
6. Define explicit API responses: `NO_SOURCE`, `SCHEMA_UNSUPPORTED`, `NO_DATA`, `PARTIAL`, `HISTORICAL_ONLY`, `STALE`, `ERROR`. Never advertise LIVE or reuse synthetic identity for actual records.
7. Add a read-only instrument catalog from actual stored symbols and bounded history pagination; do not claim “all saved data” until a table/record inventory proves coverage.
8. Do not expose secrets, DSN, file paths, tokens, hostnames or raw SQL errors in browser/API/evidence. No cross-machine listener.
9. Start with one instrument and a short bounded history window on LS-5; verify count, price-level totals, POC and timestamps against independently run read-only queries.
10. Integrate the two user-marked panels only after source contracts are independently checked. Resting DOM needs a genuine order-book snapshot source, not `footprint_1m` aggregates.

## Physical acceptance

- Exact SHA + clean checkout, separate process and rollback.
- Actual source presence and deployed schema documented; unavailable sources explicitly NOT_RUN.
- No changes to Grid/Strattester services, PostgreSQL configuration, roles, ACL, firewall or tables.
- No order execution or market subscriptions.
- Compare displayed candles/footprints/research to read-only query results; require row counts, timestamps, source state, and fail-closed behavior.
- Preserve synthetic R3/R4 baseline; do not merge or deploy without separate approval.

## Immediate blockers

1. Actual LS-5 Grid data inventory and source version unknown.
2. Actual LS-5 Strattester result DB location/existence unknown.
3. No verified production read-only API for these sources in Terminan.
4. Existing offline R4 fixture pins are not evidence of current runtime schema compatibility.

Outcome: source-level discovery only; physical integration and all-data coverage **NOT VERIFIED**.
