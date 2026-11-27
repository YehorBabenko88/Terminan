# Terminan

Read-only research terminal for Strattester and Bybit Cluster Grid. No order submission.

Run with Python 3.11 or later: `python -m terminan`. Open http://127.0.0.1:8765.

Optional environment variables:

- `TERMINAN_STRATTESTER_DB`: existing SQLite candles database.
- `TERMINAN_MEMORY_URL`: optional loopback HTTP origin for Math Scientific Memory, such as `http://127.0.0.1:8080`. The research panel reads up to 50 records for the selected symbol from that source.
- `TERMINAN_RESULTS_DB`: existing SQLite research results database used when `TERMINAN_MEMORY_URL` is unset.
- `TERMINAN_GRID_DSN`: PostgreSQL connection string (install `psycopg[binary]` separately; use read-only database credentials).

Test with `python -m unittest discover -s tests -v`.

The initial UI supports instrument selection, candle chart, footprint rows and research result JSON. DOM, tape and live trading are deliberately disabled pending a versioned streaming adapter and independent validation. The service only binds to loopback and does not modify source databases.
