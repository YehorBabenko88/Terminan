# Research quality contract — source audit (2026-10-12)

## Verified upstream storage

The Strattester `strattester/persistence/result_store.py` on `main`
creates `research_results(run_id,symbol,strategy_id,strategy_version,created_at,metrics)`
with optional fencing columns `job_id,lease_token,node_generation`.
`created_at` is a Unix timestamp in **seconds** (`time.time()`), not milliseconds.
`metrics` is a JSON string created with `json.dumps(metrics, sort_keys=True)`.
The store does **not** impose a typed schema on keys inside `metrics`.

Staged results are written to `staged_research_results`, then conditionally
promoted via `ResultStore.promote(stage_id, lease_validator)`.
Terminan reads only `research_results`; it does not validate external lease
authority, and cannot infer live validation or trading permission.

## Current Terminan projection

The optional keys `fingerprint`, `coverage`, `fee_rate`,
`slippage_bps`, `execution_model`, `simulation_config_hash`,
`missing_candles`, `data_gap_count`, `invalid_candle_count` are
**proposed source-owned metadata**, NOT guaranteed by ResultStore.
When absent they remain `UNVERIFIED`; no profitability-based inference.

Terminan does not expose `lease_token` in its HTTP projections. An invalid
JSON metrics value is represented by `metrics_state=INVALID_METRICS` and
an empty metrics object, never a fabricated zero/clean record.

## Upstream contract required before authoritative comparisons

Strattester should explicitly version a research-metadata schema with:
- dataset identity and time range, including symbol/timeframe and UTC boundaries;
- data provenance, expected/observed candles, gaps and invalid rows;
- execution/simulation configuration identity and fees/slippage assumptions;
- deterministic replay manifest/seed and code/config revision;
- independently verified publication authority, if required.

Terminan remains read-only. It cannot write these fields into Strattester or
declare them verified without a source-owned producer and validator.

## Renderer boundary based on independent Codex analysis

The CScalp static analysis established a front/back bitmap and UI invalidation
path, but not producer-side exchange semantics, GPU acceleration or race freedom.
Terminan's `render_model.py` independently captures immutable BookView rows,
explicit view/style/DPI/surface generations, bounded physical surface dimensions,
and matching hit testing. Canvas backend, lease ownership and frame scheduler
remain separate implementation stages; this module is not a finished renderer.
