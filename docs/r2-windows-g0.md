# R2 Windows G0 — synthetic physical review and rollback

R2 is a separate stacked Draft PR #17. PR #9 remains frozen at
0ad0f36edce2ac7717c753d35ebe113dc6334fd0. Use the exact R2 SHA from the latest
handoff, never a mutable branch name or the source-audit intermediate SHA.

## Runtime and safety

Already installed: Git, Python3.11+, PS5.1 or PS7 and a browser. No database,
PostgreSQL client, Grid, Strattester, exchange account or secret is needed.
The R2 child clears inherited TERMINAN_* only in its own process. Its dedicated
HTTP dispatcher exposes static preview, synthetic frames/contracts and synthetic
status only; legacy DB and monitor routes are404. It binds127.0.0.1 port0 before
publishing the owned port. No free-port/rebind race, listener policy, service,
ACL, firewall, G1 Execute/Cleanup, deployment or order operation is involved.

Run in an ordinary non-admin PowerShell from a dedicated clean exact-SHA checkout:

```powershell
.\scripts\Invoke-R2.ps1 -ExpectedSha '<EXACT_R2_SHA>' -OpenBrowser -ReviewSeconds 600
```

The harness refuses dirty/wrong-SHA checkouts and Python<3.11. It checks exact
synthetic identity, GAP24, STALE48, disconnect72, snapshot recovery80, future
fixture rejection and browser assets, then provides a10-minute browser window.
It sends quit through its own child stdin and requires exit0. If graceful shutdown
times out it can kill only that owned child and records failure. Raw stdout/stderr
and machine/user paths are not persisted as evidence.

Exit codes:0 automated synthetic smoke;10 preflight;20 startup/readiness;
30 smoke or review-child failure;40 shutdown. Shell parameter validation errors
can occur before an evidence directory exists and retain the shell nonzero code.
Preflight failure may not create an evidence directory. No PASS is inferred.

## Browser checklist on the actual PC

1. Confirm permanent SYNTHETIC / OFFLINE badge, virtual UTC and candidate/frame
   fingerprint. All instruments, candles, quantities, footprint and research
   fixtures must remain visibly synthetic. No exchange/DB/order connection.
2. Inspect Edge/Chromium and Firefox if available. Record browser versions and
   Windows display scale100/150/200%; record actual devicePixelRatio separately.
   Headless deviceScaleFactor emulation does not substitute for this observation.
3. Zoom with wheel/buttons around pointer, drag to pan, reset and double-click;
   inspect OHLCV without future bars; check sparse partial candles retain time gaps.
   Resize from wide to narrow; no clipped controls, stale canvas or blurry DPR resize.
4. Switch BTC/ETH/SOL and1m/5m/15m/1h rapidly. Prior panels must clear while loading.
   No older response may restore another symbol. Invalid seed must show a bounded
   error and recover after correction; no raw source path/traceback.
5. Play/pause/step/seek/restart on bounded0..600 replay. Fixed seed/identity/step
   must reproduce the same frame fingerprint. GAP24..31 freezes coherent book,
   STALE48..55 marks it stale, disconnect72..79 requires fresh snapshot80.
   Duplicates/out-of-order must not alter coherent final book. Mixed faults combine
   schedules. Failure fixtures clear invalid market rows and label their state.
6. Inspect DOM best bid/ask around center, integer lots/tick prices and bounded40
   rows. Footprint is one closed1m synthetic minute with six complete price levels,
   deterministic POC (tie lowest price), sum buy+sell and delta buy-sell.
7. Record console errors, responsiveness, memory/CPU observations and resize/rapid
   switch behaviour over a sustained run. The footer reports draw time and a target
   four replay updates/s, not a promise of60 display FPS. Tests enforce minimum
  1.2 completed replay updates/s under hosted stress, avg draw<20ms, p95<50ms,
   zero idle redraw, bounded requests/RAF/history and Chromium main-thread duty<75%.
   These conservative headless budgets are not a benchmark for every Windows PC.
8. Let timer expire or stop the harness. Verify preview becomes unreachable and
   only the owned listener/process stopped. Close browser tabs. No cleanup of
   unrelated processes, data, services or repositories.

## Reproducible automated checks

Python unittest includes inherited pinned schema tests. Place clean Grid and
Strattester source checkouts as siblings grid/strattester or set GRID_REPO and
STRATTESTER_REPO; their running applications are not required. Their immutable
main/source/schema SHA are in contracts.lock.json. Tests create temporary synthetic
SQLite stores only; R2 runtime has no real DB connections.

```powershell
python -m unittest discover -s tests -v
npm ci --ignore-scripts
npx playwright install chromium firefox
npm run test:browser
python -m terminan.r2_evidence bundle --report reports/r2-browser.json --out reports/r2-browser-evidence --sha '<EXACT_R2_SHA>'
python -m terminan.r2_evidence verify '.r2-evidence' --sha '<EXACT_R2_SHA>'
```

Use a fresh output directory for each bundle/candidate; existing evidence is never
overwritten. CI requires all30 browser tests (five assertions suites × six engine/
DPR projects), with zero retries. Browser installation/launch errors are failures.
If Firefox cannot launch locally, preserve that failure; a Chromium-only bundle
must explicitly use --scope chromium and cannot be called all-browser PASS.
Firefox CDP CPU/heap measurements are unavailable and reported as such; lifecycle,
render cadence and idle checks remain mandatory.

## Evidence and acceptance

Harness: ready.json, smoke.json, browser-checklist.txt, summary.json, manifest.json.
Browser bundle: exact candidate/clean state, normalized per-test results including
failure/skip counts, source/schema pins and fixture, per-project screenshot and
performance/lifecycle measurements, SHA256 manifest. Runner-level errors and
missing mandatory assertions prevent PASS even if a summary claims success.
Hashes prove integrity, not independent physical execution or signer identity.

Generated records always retain PHYSICAL=PENDING. Keep automated evidence immutable.
Store actual-PC screenshots/checklist/signoff separately with their own SHA256
manifest referencing candidate SHA and automated manifest hash. Remove usernames,
machine names, private addresses, account IDs, credentials and unrelated browser
content before sharing; use generic filenames. Do not export environment/DSN dumps.

| Gate | Acceptance evidence | Classification |
|---|---|---|
| Frozen G0 rollback | PR9 exact SHA unchanged | Source audit |
| Seed/time/sequence/faults | golden fixtures + negative/replay/HTTP tests | Synthetic |
| Versioned source contracts | pinned source/schema SHA; UTC/dataset/NULL/NaN/freshness/coverage/future tests | Offline fixtures |
| Browser interactions | Chromium/Firefox × DPR1/1.5/2, cancellation, failure/dispose, zoom/pan/resize | Hosted/headless |
| Bounds/performance | completed cadence, render/CPU/heap gates where supported, idle0, bounded lifecycle | Measured synthetic scope |
| Windows launch/shutdown | PS5.1/7 smoke and strict SHA256 manifest | Automated Windows |
| Actual-PC usability/DPR/perf | redacted screenshots, console/observations and reviewer signoff | PHYSICAL PENDING |
| Grid/Strattester running | Not needed | No blocker for R2 |

## Rollback to G0 RC

Stop only the R2 harness/child. Preserve its evidence. Open a separate clean checkout
of Terminan at 0ad0f36edce2ac7717c753d35ebe113dc6334fd0 and run that checkout's original:

```powershell
.\scripts\Invoke-G0.ps1 -ExpectedSha '0ad0f36edce2ac7717c753d35ebe113dc6334fd0' -OpenBrowser -ReviewSeconds 600
```

Do not reset another person's branch, delete working files, migrate/roll back a DB,
or touch service/ACL/firewall configuration. PR9 remains available unchanged.
Any new R2 fix means a new SHA, fresh exact-head CI and fresh evidence. Draft status
and separate merge approval remain in force.
