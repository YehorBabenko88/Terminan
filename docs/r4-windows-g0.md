# R4 offline session: Windows LS-5 physical runbook

Baseline: accepted PR23 d5a8342168fd8b55c110d5aa7b9b619ae2c97e32. Spec: PR24 40c3d0f0c3ae75a0cf08a58cfc04239d0c8353dd. Use ONLY the exact R4 HEAD from the current Draft PR25 handoff, a separate clean checkout and explicit Python. No Grid/Strattester runtime, exchange, orders, DB writes, services, ACL/firewall, deployment, merge or G1.

## Preconditions and normal15

Existing pinned Node/Playwright1.56.1 dependencies and Chromium cache. Do not change execution policy/system configuration. Use external dedicated `powershell.exe -File` / `pwsh.exe -File`; embedded &/dot-source calls are deliberately refused before work to preserve the caller host.

```powershell
$sha='<EXACT_R4_HEAD_FROM_HANDOFF>'
if ((git rev-parse HEAD).Trim() -ne $sha) { throw 'SHA mismatch' }
if (git status --porcelain) { throw 'Dirty checkout' }
$python=(& py -3.14 -c 'import sys;print(sys.executable)').Trim()
$root15=Join-Path '.r4-evidence' ('ls5-15-'+[Guid]::NewGuid().ToString('N'))
powershell.exe -NoProfile -File .\scripts\Invoke-R4.ps1 -ExpectedSha $sha -Python $python -EvidenceRoot $root15 -OpenBrowser -ReviewSeconds 15
$native15=$LASTEXITCODE
Write-Host "R4_15_NATIVE_EXIT=$native15"
$runs=@(Get-ChildItem -LiteralPath $root15 -Directory)
if ($runs.Count -ne 1) { throw 'Incomplete invocation' }
$inv=$runs[0].Name
& $python -m terminan.r4_gate verify --sha $sha --invocation $inv --out $runs[0].FullName
$evidence15=$LASTEXITCODE
Write-Host "R4_15_EVIDENCE_EXIT=$evidence15"
if ($native15 -ne 0 -or $evidence15 -ne 0) { throw 'STOP: preserve failure, do not run600' }
(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $runs[0].FullName 'manifest.json')).Hash
```

15 seconds is the manual lifecycle window, NOT total command duration. The independent automatic Chromium DPR1/1.5/2 phase follows and takes about2–3additional minutes. Do not stop it after15s. Manual and benchmark browsers use separate owned processes/contexts. All three tests must PASS with expected3/skipped0/unexpected0/flaky0/retries0; native0 alone and lifecycle-only evidence are never enough.

During the manual window check zoom/pan/reset, symbol/timeframe, seek/Play/Step, resize, visible SYNTHETIC/NOT LIVE L2/HISTORICAL labels, console and responsiveness. Normal owner shutdown publishes SESSION_ENDED during bounded3s HTTP grace, disables controls and stops polling. Connection refusal is never treated as intentional end. If a suspended/background tab misses the receipt, it may show bounded DISCONNECTED instead; do not claim delivery/physical PASS from an unobserved event. Check the normal end in a foreground tab. Close view is local VIEW_CLOSED and cannot end another view or the owner process.

## Only after verified normal15PASS

Create a NEW unique root600 and use the same exact SHA/Python/shell command with `-ReviewSeconds 600`. Capture native immediately; select exactly one invocation, run the same aggregate verifier and hash. Repeat15/600 with pwsh.exe in separate roots. Actual Windows OS display scaling/manual review is separate from automated browser deviceScaleFactor1/1.5/2.

Optional negative run in a new root: Ctrl+C during browser DPR1.5 must give native50 and aggregateFAIL50; summary remains fail-closed at browser_run. Never count interrupted/skipped as PASS or combine files across invocations. Unknown source/network loss must settle DISCONNECTED after finite retries, never SESSION_ENDED without matching receipt. Preserve all failures. Caller wrappers must explicitly `exit $capturedCode`.

## Contract and measurement boundaries

- Contracts v1 are generated offline envelopes with pinned source/schema/template/fixture hashes. Hash scope is canonical sorted JSON UTF8, independent of CRLF/LF. Runtime sourceNONE, permissionsOFFLINE_FIXTURE_READ; no database ACL or runtime schema compatibility is proven.
- Grid PG18 schema has native candles_1m/footprint_1m only. Selected5m/15m/1h returns explicit UNSUPPORTED_TIMEFRAME/emptyrows, not fabricated Grid aggregation. Strattester candles bind timeframe; research's dataset/timeframe is an offline manifest binding, not a native source-column guarantee. Research is HISTORICAL_ONLY with no live authority.
- UTC milliseconds and freshness use a deterministic virtual clock (base2026-01-01), not current wall time or a live market watermark. Revisions/epochs, duplicate/order/future/coverage/schema/provenance errors are fail-closed; no unavailable source silently falls back to live authority.
- Session ID/SHA/epoch/revision correlates same-origin loopback responses to this process, not TLS authentication or resistance to a malicious local process. No HTTP end/write endpoint; only owner stdin terminates a server session. Lease5s, poll500ms; session request timeout1.5s and max5consecutive failures, retry250/500/1000/2000ms. Frame fetch timeout10s, max5attempts per explicit load. Superseded/closed generations cannot update UI.
- FPS is rAF render cadence, NOT display/presentation FPS. Latency is batch-ingress-to-render-complete; fetch is request-to-settled (includes aborted/failed request samples), NOT exchange latency. performance.now clock; bounded240UI samples, workload100/1000frames for10k/100k updates. Quantiles p50/p95/p99 plus counts are retained.
- Chromium CDP CPU is main-thread duty, not host/whole-browser CPU. GC JS heap is not process RAM. Browser-process-tree RSS sum may count shared pages; excludes server/system/GPU memory. Firefox CDP metrics are explicitly UNAVAILABLE, not guessed or silently skipped. Finite tests do not establish indefinite leak-free behavior.
- Budgets: p99batch latency<100ms, p95draw<50ms, render cadence>10fps, Chromium CPU duty<0.75, GC heap growth<12MiB, RSS<2GiB and growth<256MiB; normal-pre-fault fetch p95<2000ms/p99<5000ms. Retain<=240candles,<=20events,<=40bookrows, frame-fetch peak<=4 plus one isolated session poll; disposed requests/timers/listeners0. Required unavailable/skipped/partial measurements fail their applicable gate; Firefox CDP limitation is recorded explicitly.

## Evidence / rollback

Aggregate contains summary/manifest, exactly one lifecycle and one complete browser bundle. Lifecycle includes matching hashed session/end receipt proof and selected ETH5m contract probe; raw session capability, stderr, DSN, environment and personal paths are not exported. Browser evidence binds current invocation/SHA/run/attempt, all projects/tests, pinned fixtures, measured counters and PNG hashes. PHYSICAL remainsPENDING until real LS-5 manual evidence is reviewed.

Rollback: stop only owned processes normally and use a separate clean checkout of accepted PR23 d5a8342168fd8b55c110d5aa7b9b619ae2c97e32 with original Invoke-R3/runbook. Do not reset/edit PR23/24, delete failed evidence, or transfer R3 PHYSICAL PASS to R4. Missing R4 receipt/source acceptance is a blocker, not a waiver.
