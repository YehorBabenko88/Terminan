# Local cache status monitor — LS-5

The monitor is **opt-in** and runs as a normal Python process on Windows, no VM, service installation or administrator privileges. It never runs cache calculations, never enqueues jobs, and never opens Grid or Strattester databases.

## Verify from a clean exact-head checkout

```powershell
py -3.12 -m py_compile .\terminan\cache_monitor.py
if ($LASTEXITCODE -ne 0) { throw 'SYNTAX_FAIL' }
py -3.12 -m unittest tests.test_saved_cache tests.test_cache_queue tests.test_cache_monitor -v
if ($LASTEXITCODE -ne 0) { throw 'TEST_FAIL' }
```

## Start a separate local monitor

Use only a **new test cache DB**, initialized by the isolated queue tests or explicitly through `init_queue(open_cache(path))`. Do not point this at Grid PostgreSQL or Strattester SQLite.

```powershell
py -3.12 -m terminan.cache_monitor --db "C:\path\to\isolated-test-cache.sqlite" --port 0
```

The monitor prints the actual `http://127.0.0.1:<port>/` URL. It reads only `cache_jobs` and `cache_entries`. Open in a local browser, refresh to see QUEUED/RUNNING/READY/FAILED. Stop with Ctrl+C.

## Boundaries and limitations

- HTTP is bound to 127.0.0.1, Host/Origin restricted, no-store, CSP, JSON fields limited to job ID/state/attempt/error code.
- SQLite URI `mode=ro`, `PRAGMA query_only`; missing database fails without creating it.
- Monitor is **not** yet embedded in the existing `/saved` UI, and is not a production integration.
- It displays cache states only, not authoritative market data or results from upstream services.
- No background worker auto-start, PostgreSQL migration, network service, trading or source changes.
- No claim of exact-head CI or LS-5 acceptance before those tests are run.
