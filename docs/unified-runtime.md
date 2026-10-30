# Unified runtime / LS-5

One Python3.12 owner, one127.0.0.1 listener, default8765. Six real existing workspaces in bounded lazy same-origin frames, max6. Main uses R4 SYNTHETIC candles/price-aligned clusters/single ASK→BID ladder. Saved historical footprint never becomes L2. Math/history use existing research components; no engine auto-start or substitute results. Infrastructure uses a manual source snapshot; absent source is UNAVAILABLE. Cache uses PR47 offline v2 read-only projections; no worker launched by HTTP.

Sources verified2026-10-30: PR60 `1bc9bf20d18ea371cdacdd974762bad20edf907d`; PR47 `7e69e76a8733535d6897db92a534e6de118432ff` already ancestor; PR58 `75a8fdb72cd8b7f712f2f421c576901e965d8f32` superseded by PR60 navigation; instrument research `eafdc320a9bdb218d4bbadc3c590f98906932689` and usability `0d0bb679a279fd251d3d2cc8a5ad763b0cc24910` already ancestors. Dashboard source `6cfa160c0df2c812cae4d94d451e83d8446e0e1b`: infrastructure.py/html/test preserved byte-for-byte. PR55 `1222a60dc779213d5e2b718fa4265d7a12e5ac83`: add missing ignore entries, retain newer closed-level/telemetry contracts (wholesale old monitor.py would restore direct DB query). PR57 `c48f854229c06bdc2102fe4220c80993f6612df3`: minimal ladder row bound and CSS patch, retain existing visual engine. No other branch changed.

Dispatcher gates Host/Origin/relative request target/2048bytes before existing handlers. Same-origin frames explicitly allowed only by unified handler CSP; external framing forbidden. /api/status preserves legacy READ_ONLY contract. Unified terminal explicitly uses /api/synthetic/status for unchanged R4 SYNTHETIC protocol; standalone R4 keeps its original /api/status. Legacy status also at /api/legacy/status. Existing Saved, synthetic, Math, history, sources, monitor APIs retained. /infrastructure is preserved for direct consumers; /monitor shell shows expanded infrastructure; old fleet API remains /api/monitor. Initial legacy DB environment credentials are removed in this process; actual Saved sources require explicit --config. No live subscriptions or execution endpoints.

R4 session gates all data APIs, POST before admission and again after body read. Diagnostics wrap read/write/flush; peer reset benign counters remain separate from fatal handler failures.16worker admission,5s absolute socket budget (not inactivity), joined workers with6s bound,3s SESSION_ENDED receipt grace; residual active/fatal => exit40. Repeated SIGINT ignored during cleanup. Root pages retained, Play pauses on switch, finite replay and existing stale-cancellation fences retained. Session polls from retained terminal/saved remain bounded; this is not a full browser tab suspension policy. Reload starts a new document and does not persist private data.

## Run

Use a clean exact checkout and replace `<HEAD>` with reported candidate SHA. Python3.12 and Node24 required for tests; normal runtime uses Python stdlib. Start in dedicated File host:

```powershell
powershell.exe -NoProfile -File .\scripts\Invoke-Terminan.ps1 -ExpectedSha <HEAD>
```

Open http://127.0.0.1:8765. Port collision fails50 without killing another process. Enter or Ctrl+C stops owner. Explicit offline fixture preview: append `-Demo`. Never uses fixtures as a hidden fallback. Optional `-SourceConfig <operator-file>` / `-CacheDb <isolated-v2-cache>`; neither required. Bad/legacy cache shows UNAVAILABLE and is never migrated. Cache version admission verifies v2 projection/index structure and algorithm, not producer authenticity. Real source qualification NOT_RUN.

## Physical automated evidence

Fresh paths only; harness uses explicit SYNTHETIC fixtures and a free loopback port, not production sources. No overwritten/deleted evidence.15must PASS before600;600 verifies all previous hashes, exact SHA/tree and all three Chromium project identities.

```powershell
$sha='<HEAD>'
$smoke=Join-Path $env:TEMP ('terminan-unified15-'+[guid]::NewGuid().ToString('N'))
powershell.exe -NoProfile -File .\scripts\Invoke-Terminan.ps1 -ExpectedSha $sha -ReviewSeconds 15 -EvidenceRoot $smoke
$native=$LASTEXITCODE
$s=Get-Content -Raw (Join-Path $smoke 'summary.json') | ConvertFrom-Json
if ($native -ne 0 -or $s.exit_code -ne 0 -or $s.result -ne 'AUTOMATED_PASS') { throw 'SMOKE_FAIL' }
foreach ($f in @(Get-Content -Raw (Join-Path $smoke 'manifest.json') | ConvertFrom-Json)) {
 if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $smoke $f.path)).Hash.ToLowerInvariant() -ne $f.sha256) { throw 'SHA256_FAIL' }
}
$long=Join-Path $env:TEMP ('terminan-unified600-'+[guid]::NewGuid().ToString('N'))
powershell.exe -NoProfile -File .\scripts\Invoke-Terminan.ps1 -ExpectedSha $sha -ReviewSeconds 600 -PreviousSmoke $smoke -EvidenceRoot $long
$LASTEXITCODE
(Get-FileHash -Algorithm SHA256 (Join-Path $long 'manifest.json')).Hash
```

Install pinned browser dependency before physical tests: `npm ci --ignore-scripts`, `node node_modules/@playwright/test/cli.js install chromium`. PS7 uses pwsh.exe with a new evidence root. Each invocation requires exact source SHA/tree, all3DPR1/1.5/2 tests passed, no skips/interruption/retry/missing/stale report,12HTTP routes, duration polls, SESSION_ENDED, native0, zero fatal stderr and closed listener. Failures are preserved. Exit20startup,30smoke,31browser,33child health,40shutdown,50source/evidence,130cancel. Manifest excludes itself; record its SHA separately. No raw child stderr persisted; summary uses allowlisted stage/class and byte counter. Browser report private local paths redacted; no secrets/data sources in synthetic evidence.

Manual acceptance remains PENDING even when automated tests pass. Review six tabs, candle/footprint geometry, ASK above BID, zoom/pan, resize100/150/200%, symbol/timeframe, Saved replay/Play/Step, preserved chart state and laboratory graph across navigation. Engine/source absent must be visible, Console no unexpected errors. Stop via Enter and separately Ctrl+C; verify native0/closed listener/no owned PID. Human observations should reference exact invocation and SHA; no fake physical PASS.

Rollback: stop this owner, use a separate clean PR60 checkout pinned `1bc9bf20d18ea371cdacdd974762bad20edf907d`; its four main pages and separate saved_runner remain original. PR47 cache v2 can still be used by original saved_runner. No migrations, source writes, services, ACL/firewall, deployment, merge or G1.

Final recheck: R4 branch advanced to `dbbc1c6c3b3982280af6f20b70980e4caf151b4c`; imported only Saved explicit timeframe option identities and1–3candle zoom bound. Existing R2 evidence changes on that branch are unrelated to this runtime/harness and not imported. Added a2candle actual browser regression. Preliminary ff62040 had15/600native PASS; qualification repeated on final exact HEAD after this patch. Ctrl+C in dedicated PS5.1/7 host closes listener and owned Python PID; interrupted launcher conservatively returns50, not normal automation PASS.

Windows port ownership: use SO_EXCLUSIVEADDRUSE and disable SO_REUSEADDR in the unified listener. Occupied8765 is a fail-closed startup50, never a second shared bind or connection to an older owner. Existing8765 listener on LS-5 was observed during audit; it is left untouched. Stop its original owner normally before using default8765; use free `-Port 0` for isolated checks. Regression reproduces old double-bind and rejects it after this fix.
