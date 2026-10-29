# Saved market and research workspace

Own branch above PR29; PR27's single synthetic ladder and R4 endpoints are preserved. `/saved` is served by a separate opt-in runner. It never feeds historical footprint or book snapshots into that ladder.

## Windows local launch (PowerShell 5.1 or 7, Python3.11+)

From the checkout at the published exact PR HEAD:

```powershell
git rev-parse HEAD
git status --porcelain
py -3.14 -m terminan.saved_runner --demo --port 0
```

The first JSON line prints the actual free loopback URL ending `/saved`, candidate SHA and SYNTHETIC mode. Open that URL in the browser. Return to the owner console and press Enter for graceful shutdown; capture `$LASTEXITCODE` immediately (expected0). The foreground view receives SESSION_ENDED during3s grace and stops requests. Close view only disposes that tab; it does not terminate the owner. Ctrl+C is also a graceful owner-stop request. This preview command is **not** a physical acceptance harness or a PHYSICAL PASS.

Without `--demo` or `--config`, the page is SOURCES DISABLED: no DB drivers, connections or upstream service startup. Do not run both flags together. No external exchange clients, execution routes or write endpoints exist.

```powershell
py -3.14 -m terminan.saved_runner --port 0
```

## Future explicit source configuration

`examples/saved-sources.example.json` is a template, not an active configuration. Replace paths only after a separately authorized source/snapshot is available. Keep files private; never put a DSN/password in the JSON or command line. PostgreSQL uses an explicit environment-variable **name**, not its contents, and lazily imports optional psycopg only on a configured read. No real sources or PostgreSQL were connected during development.

```powershell
# Later, for an explicitly authorized local snapshot/config only:
py -3.14 -m terminan.saved_runner --config C:\private\saved-sources.json --port 0
```

Profiles:

- Grid `grid46`: PostgreSQL18 only, exact migration version/name set and reviewed column/type/PK shape. Client connections request read-only transactions,3s connect timeout,2s statement timeout,500ms lock timeout. This does not prove the role's ACL. No migrations/Store bootstrap imports.
- Strattester `market2`: SQLite schema_meta schema_version2 plus exact dataset shape/PK. Includes candles, mark/index/premium, open interest, funding, long/short ratios and public trade aggregates. Premium-index OHLC can be negative; price candles cannot.
- Strattester `legacy-candles1`: explicit structural profile for legacy `candles(symbol,ts,OHLCV,turnover)`, native1m. Not a migration or an automatic fallback.
- Strattester `results1`: local structural name, not an upstream migration number. Only published research_results; staged_research_results is excluded. `created_at` seconds are converted to integer UTC milliseconds; metrics/coverage/fingerprint, strategy/version/run_id and unverified publication provenance are retained. PnL/drawdown retain source units; no currency or execution authority is invented.
- `sqlite-shards`/market2: pinned64-bucket algorithm by default (explicit buckets supported), manifest.sqlite3 must say SHARD_READY. Never initialize a shard, merge legacy and shard data, or guess a fallback during migration. Configure legacy monolith separately if needed. Root/path traversal and symlink escape are rejected.

SQLite opens `mode=ro`, query_only and bounded read transactions. No upstream `open()` methods (which create schemas, change journal modes and checkpoint) are called. Writable WAL-source readers can require existing shared-memory/sidecar access; use an authorized consistent snapshot if such access is prohibited. Tests use isolated temporary DBs only and verify database bytes remain unchanged.

## UI and contracts

Source/dataset/symbol/timeframe/UTC window/page size are explicit. Symbol is editable; timeframe is validated and preserved. Global research datasets display GLOBAL/UNSCOPED rather than claiming the selected symbol/timeframe. Grid minute tables reject higher timeframes instead of fabricating aggregation. Numeric precision is converted for visualization only, never order sizing/execution.

OHLCV has volume bars and persisted candle POC. Footprint displays multiple UTC minutes with sell×buy, volume/delta and a **visible-page** maximum-volume highlight. Pagination can cut a minute; that highlight is not a full-minute POC guarantee. Research tables expose strategy/run, net PnL, win rate, drawdown, trades/wins/losses/fees/profit factor/coverage; selecting a row reveals every projected field. Missing metrics show an em dash, not zero.

Wheel/buttons zoom, pointer drag pans, reset, finite replay/step/seek, refresh/first and next-page controls are implemented. Each page replaces memory; no unbounded append/history or automatic retry loop. Source changes abort/ignore old generations, clear old detail/provenance and reset replay. Data fetch timeout3.5s; the reused host session client has a5-attempt bounded lease/backoff. A missed end receipt remains DISCONNECTED, never a fabricated normal end.

API: GET `/api/saved/catalog` and `/api/saved/page?source=grid-demo&dataset=candles_1m&symbol=BTCUSDT&timeframe=1m&limit=100`. Optional from_ms/cutoff_ms/cursor. All clocks are UTC milliseconds; fixture as-of is virtual2026-01-01, not current/live freshness. No-data, partial, stale, unavailable, schema/identity/cursor/source-changed errors stay explicit, with no fallback to synthetic or live authority.

Pagination uses ascending primary-key tuples and HMAC cursors bound to process/source/dataset/schema SHA/symbol/timeframe/UTC cutoff/epoch/sequence. Pass the returned from_ms and cutoff_ms on subsequent DB pages. Cursor from another invocation or changed source is rejected. Page coverage always `complete=false`, PAGE_ONLY_NOT_FULL_HISTORY. Historical datasets do not expose exchange sequence numbers; these are adapter pagination sequences, not live-feed continuity.

Bounds:8 providers,200 rows/page,1MiB response,16KiB selected SQL row (server-side size rejection before returning large cells),4MiB/2000-row fixture, bounded JSON depth8 and collections512; source strings4096. Query timeouts plus inherited bounded HTTP workers; no persistent DB pool or accumulating UI rows. Source SHA is an **operator pin**, not runtime attestation; fixture pins are synthetic. SQLite epoch covers main/WAL and shard-manifest files. PostgreSQL WAL epoch is deliberately conservative: concurrent writes can invalidate a page/cursor; obtain a stable snapshot/refresh rather than combining potentially inconsistent pages. True cross-page snapshot leases and live PG18 runtime qualification remain future work.

## Coverage and limitations

`fixtures/saved-catalog-v1.json` inventories78 Grid tables and12 Strattester entries (11 upstream tables plus the explicit legacy profile), with39/10 permitted dataset projections. Catalog generation reads pinned SQL/AST only. `saved-data-coverage.csv` lists each dataset and omitted fields. Internal job/lease/control/enrollment/log/staging tables and sensitive/operational columns are deliberately not exposed; this is not a claim of all operational state or every persisted byte. New schemas/unknown columns fail closed until reviewed.

Demo fixtures include Grid candles/footprint/derivatives, eight Strattester market datasets and published research; other catalog entries have an intentionally empty synthetic dataset, not proof that real source data is empty. Current upstream Grid gateway exposes only latest limited snapshots, lacks keyset/provenance and converts nullable POC through float(None); it is not used for historical pagination. Strattester constructors/migrations are write-capable and are never imported by adapters. Source pins and LF-normalized text SHA256 are in the catalog; the generation scripts expect sibling Grid/Strattester checkouts at those exact pins.

Real Grid PG18/API compatibility, service startup, roles/ACL, continuous-write pagination, sharded-production consistency and Windows manual acceptance are **NOT TESTED**. Upstream research may serialize Infinity for profit_factor; nonfinite numbers are rejected, not converted to a misleading finite value. Such a page needs corrected/exported finite-or-null data before acceptance. Labels remain SYNTHETIC or HISTORICAL_ONLY, never LIVE/LIVE L2 authority.

## Verification and evidence

```powershell
py -3.14 -m unittest discover -s tests -v
$env:R2_PYTHON=(& py -3.14 -c 'import sys;print(sys.executable)').Trim()
$env:SAVED_INVOCATION=[guid]::NewGuid().ToString('N')
$env:SAVED_STARTED_MS=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
node node_modules/@playwright/test/cli.js test --config playwright.saved.config.cjs
$browser=$LASTEXITCODE
py -3.14 -m terminan.saved_evidence --report reports/saved-browser.json --sha (git rev-parse HEAD).Trim() --invocation $env:SAVED_INVOCATION --started-ms $env:SAVED_STARTED_MS --out ('reports/saved-'+$env:SAVED_INVOCATION)
$evidence=$LASTEXITCODE
Write-Output "BROWSER_NATIVE=$browser EVIDENCE_NATIVE=$evidence"
```

Browser tests require all six Chromium/Firefox DPR1/1.5/2 identities with zero skipped/interrupted/retry/flaky/unexpected; screenshots and fixtures are hashed. Missing/stale/partial/malformed report, false-zero statistics or dirty source cannot pass. Publication is atomic and existing output is never overwritten. Optional `--scope chromium` applies only to an explicitly Chromium-only invocation, never reclassifies a failed all-browser run. PHYSICAL remains PENDING. Keep all failed reports; do not repeatedly benchmark until choosing a convenient result.

CI runs Windows/Linux Python3.11/3.14, all original R2/R3/R4 gates/budgets and the new saved-data/browser gate. No threshold is relaxed. Rollback is a separate clean checkout of PR29 a2019e83d456ef2b6b2d52608b26322b36d402e3 (or accepted earlier R3); do not reset another branch or discard failed evidence. No merge/deployment/G1/trading/system-policy/production writes.
