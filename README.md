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
