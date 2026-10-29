# Cache queue — isolated physical Windows test

This is an **opt-in offline worker prototype**. It does not run automatically,
does not contact Grid/Strattester/PostgreSQL, and is not attached to Terminan HTTP.
The only database it writes is the explicit local SQLite file selected by operator.

State machine: QUEUED → RUNNING → READY or FAILED.
Claims use SQLite BEGIN IMMEDIATE and unique tokens. Expired claims may be retried
up to three attempts; stale tokens cannot publish results. Cache payload and READY
status commit in one transaction. The input is a bounded, immutable JSON snapshot.
No heavy computation is performed inside Terminan's HTTP request handlers.

## Windows smoke

From a clean checkout, without elevated permissions:

```powershell
py -3.12 -m py_compile .\terminan\saved_cache.py .\terminan\cache_queue.py
if ($LASTEXITCODE -ne 0) { throw 'SYNTAX_FAIL' }
py -3.12 -m unittest tests.test_saved_cache tests.test_cache_queue -v
if ($LASTEXITCODE -ne 0) { throw 'TEST_FAIL' }
```

The queue CLI supports:
- `--db <new-local-sqlite-path> --identity <json> --source <json> submit`
- `--db <same-path> run-once`
- `--db <same-path> --job-id <id> status`
- `--db <same-path> --identity <json> get` is **not** a queue command; use `terminan.saved_cache` for cache read.
- `--db <same-path> --max-seconds 60 work` runs a bounded worker loop.

No existing database should be used for smoke testing. No production service installation.

## Explicit limitations

- Input payload JSON is currently stored in the SQLite job row; it is not a secure store for secrets or full history.
- Worker uses a single process and one transaction for claim/publish; heavy calculation is outside the transaction.
- There is no heartbeat while computing; the 120-second lease is a hard ceiling and stale results are rejected. Long jobs require chunking/renewal in a future PR.
- The queue does not yet expose a read-only HTTP API or UI status.
- The source revision is operator supplied and not independently attested. No live or production authority.
- PostgreSQL backend and role separation remain future, explicitly authorized work.
