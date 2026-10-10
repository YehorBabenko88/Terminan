# Source-owned integration contract (proposal v1)

Terminan must not connect to Bybit or run a market-data WebSocket. Cluster Grid owns exchange subscriptions and authoritative data; Strattester owns historical strategies and simulation execution. Both sources should expose authenticated internal read-only APIs / event streams on the existing private network. Terminan consumes them, with no new database.

## Cluster Grid gateway

- GET /internal/v1/instruments: symbol, state (active/delisted), supported timeframes, freshness.
- GET /internal/v1/candles?symbol=&timeframe=&from_ms=&to_ms=: closed/open flag, OHLCV, source timestamps.
- GET /internal/v1/footprint?symbol=&from_ms=&to_ms=: 1m price-level buy/sell volume, POC, source watermark, missing coverage intervals.
- GET /internal/v1/book/snapshot?symbol=: sequence, bids/asks, event timestamp; returns UNAVAILABLE if no source book snapshot.
- GET /internal/v1/tape?symbol=&from_ms=&to_ms=: source-executed trades, not aggregate candle volume.
- GET /internal/v1/events?symbol=&cursor=: incremental book/tape events with sequence and reconnect gap detection; transport is source-owned. Terminan does not open an exchange WebSocket.

## Strattester gateway

- GET /internal/v1/runs?symbol=: immutable run ID, strategy/version, timeframe, dataset fingerprint, parameters, coverage, completion/fencing status.
- GET /internal/v1/runs/{run_id}/trades?cursor=: authoritative per-trade entry/exit timestamps, price, direction, quantity, fees, realized PnL, stop/target, reason, execution assumptions.
- GET /internal/v1/runs/{run_id}/signals?cursor=: evaluated strategy events, including POC-close signals with candle timestamp, POC level, direction, decision reason and whether an order was actually simulated.
- GET /internal/v1/runs/{run_id}/metrics: metrics and denominator, sample count, drawdown, fee/slippage assumptions.
- GET /internal/v1/science?run_id=: method/version, hypotheses, datasets, confidence, out-of-sample splits, charts, artifacts and publication/fencing status.

## Semantics

All event times are UTC Unix milliseconds. Candles are keyed by open time and timeframe. Event markers are not snapped to the nearest candle when timestamps differ. Never invent trades from aggregate metrics or infer real fills from signal events. Filter run results by symbol and exact dataset fingerprint. No look-ahead: a POC-close decision at minute T is available only after that candle closes; a trade fill cannot be backdated to that candle close unless execution evidence exists. Footprint POC ties are resolved deterministically. Distinguish historical, partial, stale, unavailable and live states. For large history, paginate and cap rows; no unbounded queries. API versions evolve additively; unknown fields are ignored. Scientific visualizations must label in-sample vs out-of-sample.

## Security and reliability

Read-only credentials, allowlisted private hosts, no trading keys in Terminan, request timeouts, bounded concurrency, cache headers and explicit stale watermarks. Source workers should publish through their own bounded queues and never block ingestion for a slow viewer. Sequence gaps force resync from snapshot. Tests must cover duplicate events, late/out-of-order messages, restart, delisting, gaps, stale data, absent L2, partial fills, fee accounting, run version drift, source outages, timezones and dataset consistency.
