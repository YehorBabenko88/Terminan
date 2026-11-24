# Terminan

Read-only research terminal for Strattester and Bybit Cluster MarketData. No order submission.

Run with Python 3.12 or later: `python -m terminan`. Open http://127.0.0.1:8765.

Optional environment variables:

- `TERMINAN_STRATTESTER_DB`: existing SQLite candles database.
- `TERMINAN_RESULTS_DB`: existing SQLite research results database.
- `MARKET_DATA_DSN`: PostgreSQL connection string (install `psycopg[binary]` separately; use read-only database credentials).

Test with `python -m unittest discover -s tests -v`.

The initial UI supports instrument selection, candle chart, footprint rows and research result JSON. DOM, tape and live trading are deliberately disabled pending a versioned streaming adapter and independent validation. The service only binds to loopback and does not modify source databases.

## MarketData capability probe (read-only, optional)

Terminan can query the **existing MarketData** v1 capability/health endpoints on the
same Windows host without connecting to Bybit or creating a PostgreSQL cluster.
Set `MARKET_DATA_API_PORT` to the decimal port already used by
the canonical `market_data.cli serve` service (for example `18766` only when it is
actually running). Only `127.0.0.1` is contacted; URLs, arbitrary hosts,
redirects, inherited proxies and credentials are not accepted.

- `GET /api/market-data/source` returns bounded, version-checked source availability.
- `GET /api/status` includes a `market_data_source` field with the same state.
- `CONNECTED_UNQUALIFIED` means the MarketData API answered, **not** that candles,
  public WebSocket, live prices, or experiment data are verified.
- `database: READ_ONLY` is a limited MarketData health observation, not a market
  completeness or scientific evidence claim.

Existing legacy SQLite and explicit read-only PostgreSQL adapters are retained
temporarily for compatibility and are **not** promoted to qualified/live data.
No new service, market collector, exchange client, database writer or trading
order API is introduced by this probe. Remote fleet access and authentication
remain Unified System's responsibility. Release remains NO_GO.

## Offline paper replay (Stage 8, NO_GO)

The original Terminan screen now has a dedicated **OFFLINE / UNATTESTED**
paper-replay panel. Its POST route is part of the existing loopback server:

- `POST /api/paper/replay` accepts `terminan.paper.replay.v2`, at most
  256 KiB and 1024 ordered market events, never real orders.
- Closed-minute POC is delegated to the installed Math-owned SDK
  `market_compute_api.compute_batch`, not recalculated in Terminan.
- Events are caller supplied, not authenticated MarketData market data; outputs
  have `trading_authorized=false`, `execution_authority=false`,
  `status=OFFLINE_UNATTESTED`, deterministic request and result SHA-256.
- Accepted event types: `closed_minute` (published at the next minute
  boundary, with Math profile/close), `trade` (paper prices only),
  and `gap` (invalidate entry reference). JSON Decimal prices are strings.
- By default the replay is stateless. If `TERMINAN_PAPER_LEDGER` points
  to a dedicated local SQLite file, `run_id` is bound to an immutable receipt.
  An identical request returns that receipt after restart (without rerunning
  Math); a changed request with the same `run_id` is rejected. Dedicated
  storage is not a MarketData market database, distributed checkpoint, or a
  production PostgreSQL results schema. No real exchange subscription exists.

Minimal *synthetic offline* example for pasting into Terminan (not Bybit data):

```json
{
  "schema": "terminan.paper.replay.v2",
  "run_id": "offline-sample",
  "source": {
    "snapshot_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "as_of_ms": 62000,
    "units": {"price": "quote/base", "volume": "base"}
  },
  "parameters": {},
  "events": [
    {"kind": "closed_minute", "event_ms": 60000, "symbol": "BTCUSDT",
     "profile": [{"price": "100", "volume": "1"}], "close": "100"},
    {"kind": "trade", "event_ms": 61000, "symbol": "BTCUSDT", "price": "102"},
    {"kind": "trade", "event_ms": 62000, "symbol": "BTCUSDT", "price": "100"}
  ]
}
```

The Math package must be installed by the eventual Unified installer; if
missing, Terminan returns `MATH_SDK_UNAVAILABLE` rather than substituting a
second POC algorithm. This is offline development functionality, **not
release acceptance**. Qualified MarketData history/live ingestion, durable fenced
results migration to the final Unified-managed installation, physical
Windows/browser tests, and canonical execution/source acceptance remain release gates.
Math owns POC and financial arithmetic (fees, fill metrics, sizing and equity). Terminan owns simulation state and execution policy. No live trading route exists.

## Independent package (Stage 9 candidate)

Terminan is packaged as `unified-terminan==0.1.0` and remains a separate
module, with no required exchange client, database installer or Math runtime:

```sh
python -m pip wheel --no-deps -w dist .
python -m pip install --no-deps dist/unified_terminan-0.1.0-py3-none-any.whl
terminan
```

The console command binds only to loopback by default. The installed wheel
includes the existing HTML terminal and monitor resources. History and status
UI can run without Math; the offline paper replay returns
`MATH_SDK_UNAVAILABLE` until a separately version-pinned
`unified-math-kernels==0.1.0` is installed by the authorized deployment
process. Do not resolve an unreviewed Math wheel or grant raw database writes.

CI now tests Terminan under Python 3.11 and 3.12 on Windows and Ubuntu,
including independent wheel build + installed-origin import checks. The
separately pinned Math SDK parity job remains Python 3.12 until the Math
distributor qualifies Python 3.11. This proves only package import/resources;
actual installer, authenticated cross-host MarketData and Unified integration,
source-origin acceptance and physical Windows E2E require further gates.

## Optional historical comparison metadata (Stage 12, unqualified)

`terminan.paper.replay.v2` may include a `comparison` object with
`schema: "terminan.market_data.comparison.v1"`, `dataset_id`, `dataset_hash`
(64 lowercase hex), `strategy_name: "poc_next_minute"`,
`setup: "POC"`, `variant: "BASE"`, a nonnegative integer `fold`,
`symbol`, and `comparison_group: "<run_id>:<symbol>:POC"`.

This context **does not** download or attest a MarketData dataset. It is a
caller-supplied historical grouping label for the *only strategy actually
implemented* by Terminan's current offline PaperEngine. REGIME, MARKOV, ML
and other MarketData variants fail closed; the API does not claim to run them.
The result explicitly records `dataset_qualified=false` and marks every
required dataset's coverage `false`. Do not use it for source-qualified
performance claims or live strategy execution.

When `comparison` is provided, the result also includes
`receipt_checkpoint.state=COMPLETE_RESULT_ONLY` with
`resumable=false` and the committed request digest. It documents a
finished, recoverable receipt, **not** an in-progress event cursor or a
distributed resume/checkpoint protocol. Supplying an unknown checkpoint
field on replay is rejected, rather than replaying a partial state.

The existing MarketData-only v1 instrument/history API and Unified Gateway still
require authenticated, version-pinned real-source acceptance before paper
history/live consumers are enabled. No real orders are supported.
