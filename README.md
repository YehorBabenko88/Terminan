# Terminan

Read-only research terminal for Strattester and Bybit Cluster Grid. No order submission.

Run with Python 3.11 or later: `python -m terminan`. Open http://127.0.0.1:8765.

Optional environment variables:

- `TERMINAN_STRATTESTER_DB`: existing SQLite candles database.
- `TERMINAN_RESULTS_DB`: existing SQLite research results database.
- `TERMINAN_GRID_DSN`: PostgreSQL connection string (install `psycopg[binary]` separately; use read-only database credentials).

Test with `python -m unittest discover -s tests -v`.

The initial UI supports instrument selection, candle chart, footprint rows and research result JSON. DOM, tape and live trading are deliberately disabled pending a versioned streaming adapter and independent validation. The service only binds to loopback and does not modify source databases.

## Grid capability probe (read-only, optional)

Terminan can query the **existing Grid** v1 capability/health endpoints on the
same Windows host without connecting to Bybit or creating a PostgreSQL cluster.
Set `TERMINAN_GRID_API_PORT` to the decimal port already used by
`grid.terminan_gateway` (for example `18766` only when that service is
actually running). Only `127.0.0.1` is contacted; URLs, arbitrary hosts,
redirects, inherited proxies and credentials are not accepted.

- `GET /api/grid/source` returns bounded, version-checked source availability.
- `GET /api/status` includes a `grid_source` field with the same state.
- `CONNECTED_UNQUALIFIED` means the Grid API answered, **not** that candles,
  public WebSocket, live prices, or experiment data are verified.
- `database: READ_ONLY` is a limited Grid health observation, not a market
  completeness or scientific evidence claim.

Existing legacy SQLite and explicit read-only PostgreSQL adapters are retained
temporarily for compatibility and are **not** promoted to qualified/live data.
No new service, market collector, exchange client, database writer or trading
order API is introduced by this probe. Remote fleet access and authentication
remain Unified System's responsibility. Release remains NO_GO.

## Offline paper replay (Stage 8, NO_GO)

The original Terminan screen now has a dedicated **OFFLINE / UNATTESTED**
paper-replay panel. Its POST route is part of the existing loopback server:

- `POST /api/paper/replay` accepts `terminan.paper.replay.v1`, at most
  256 KiB and 1024 ordered market events, never real orders.
- Closed-minute POC is delegated to the installed Math-owned SDK
  `market_compute_api.compute_batch`, not recalculated in Terminan.
- Events are caller supplied, not authenticated Grid market data; outputs
  have `trading_authorized=false`, `execution_authority=false`,
  `status=OFFLINE_UNATTESTED`, deterministic request and result SHA-256.
- Accepted event types: `closed_minute` (published at the next minute
  boundary, with Math profile/close), `trade` (paper prices only),
  and `gap` (invalidate entry reference). JSON Decimal prices are strings.
- `run_id` is a caller's offline identifier, not yet a durable result record.
  There is no database persistence, process supervisor, real data admission
  or live exchange subscription on this route.

Minimal *synthetic offline* example for pasting into Terminan (not Bybit data):

```json
{
  "schema": "terminan.paper.replay.v1",
  "run_id": "offline-sample",
  "source": {
    "snapshot_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "as_of_ms": 0,
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
release acceptance**. Qualified Grid history/live ingestion, durable fenced
results, physical Windows/browser checks and Math-owned P&L domain API are
still required. No live trading route exists.
