# PR43: cache status inside /saved

This is a **read-only, opt-in** integration. The existing saved workspace
accepts `--cache-db` only when the operator explicitly points to an already
initialized local SQLite queue/cache file.

- The saved server adds `GET /api/saved/cache-status` under its existing
  loopback Host/Origin/session controls.
- With no `--cache-db`, the endpoint reports DISABLED, no entries or jobs.
- With a cache DB, it reads via `cache_monitor.read_status` (SQLite mode=ro,
  query_only) and never creates tables or enqueues work.
- The UI has a manually refreshed status panel; it shows job ID, state,
  attempts and safe error code. No automatic polling or heavy calculation.
- The queue worker remains an **independent process**. The UI cannot submit
  or cancel jobs.
- There is no direct Grid/Strattester or PostgreSQL integration.

## Physical LS-5

Use a new clean exact-head checkout. Reuse only the isolated SQLite file
created for PR42 (not a production database):

```powershell
py -3.12 -m py_compile .\terminan\saved_runner.py .\terminan\saved_server.py
if ($LASTEXITCODE -ne 0) { throw 'SYNTAX_FAIL' }
py -3.12 -m unittest tests.test_saved_cache tests.test_cache_queue tests.test_cache_monitor -v
if ($LASTEXITCODE -ne 0) { throw 'TEST_FAIL' }
py -3.12 -m terminan.saved_runner --demo --cache-db "$env:TEMP\terminan-cache-pr42\local-monitor-test.sqlite" --port 0
```

Open the printed `/saved` URL and inspect the Background cache jobs panel.
It should show the already completed job READY and one cache entry. Refresh
manually; the UI must remain responsive. Stop through Enter in the owner console.

Do not assume the existence of the local file or success until the physical
run confirms it. If missing, the runner fails closed without creating it.
