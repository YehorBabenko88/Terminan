# Terminan as a read-only frontend for Strattester and Bybit Cluster Grid

Evidence checked against source repositories on 2026-10-12.

## Ownership and data lineage

**Bybit Cluster Grid** owns market ingestion, coordinator PostgreSQL, live features,
minute candles and price-level footprints. In `grid/schema.sql`, `candles_1m`
is keyed by (symbol,ts), and `footprint_1m` is keyed by (symbol,ts,price).
Source storage replaces footprint for a more complete accepted minute and avoids
regressive trade-count updates. These rows are minute *trade aggregates*, **not**
a current L2 orderbook.

**Strattester** owns historical candles and research execution, experiment
identity, strategy-versioned outputs, and simulation. Its SQLite `candles`
table has symbol/timeframe/open_time primary key. `research_results` is keyed
by run_id/symbol/strategy_id/strategy_version, and may carry job_id, lease_token
and node_generation fencing fields. A stored result is not proof of simulation
pass, live validation, or authority for trading.

**Terminan** reads views only. It does not collect exchange data or maintain
a second market-data database. The DOM demo is clearly SYNTHETIC_FIXTURE and
must not appear as Bybit L2. Do not infer market depth from footprint or use
historical liquidity proxies as LIVE_ONLY features.

## Research lifecycle

INFRASTRUCTURE -> MARKET_HISTORY_SYNC -> HISTORICAL_STRATEGY_RESEARCH ->
HISTORICAL_SCIENCE_BOOTSTRAP -> GRID_IMPORT -> LIVE_LEARNING ->
PAPER_TRADING. Bootstrap bundles provide historical priors only; live evidence
is explicitly separate. Validated science and successful simulation are
independent promotion gates.

## Next integration contracts

Prefer source-owned, authenticated read-only endpoints rather than direct
database reads across nodes. Until such endpoints actually exist and are
verified, keep Terminan's existing optional bounded read-only database adapters.
A source response should declare origin, data age, coverage, quality, UTC event
timestamp, schema version, and symbol identity. Never silently substitute
Strattester history for Grid live data.

Suggested panels: combined historical candles; Grid footprint heatmap, POC and
delta; Grid fleet health and WAL replay; Strattester strategy runs with
version/fingerprint and research-stage labels; optional L2 DOM if an actual
source-owned book snapshot and sequenced deltas become available. Provide
explicit unavailable/stale status otherwise.

## Safety invariants

No trade/order endpoints or exchange credentials in the frontend. No writes
to Grid or Strattester database. Bound queries and enforce database read-only
session permissions. Handle schema mismatches as UNAVAILABLE rather than
inventing data. Do not treat stored research metrics as per-trade fills.
