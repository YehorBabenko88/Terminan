# R3 aggregate browser gate / LS-5 repro

Frozen base PR20 3ed51d908b80a0fa9fee5d72999ca2184f309bec. Separate fix branch; accepted branches remain unchanged.

## Reproduced failure

Original LS-5 report: Chromium DPR1 passed, DPR1.5 interrupted, DPR2 did not run; stats expected1/skipped2/unexpected0. Lifecycle0 is NOT R3 PASS. On the base, injecting PipelineStoppedException at the browser call returns native0 on both PS5.1 and PS7 and skips browser evidence. PowerShell cancellation bypasses catch and statements after finally; the outer exit was after finally, and code had already been set to lifecycle0. This reproduces the mechanism; original input/signal source is not recorded and remains unknown.

Actual isolated Windows console Ctrl+C also reproduced native0 even with language exit50 inside finally. Direct Environment.Exit is required in the dedicated -File host; embedded/dot-sourced invocation is refused to protect the caller host. The launcher now retains50 until complete evidence is verified and exits INSIDE outer finally. Cancellation remains FAIL/INCOMPLETE. Every invocation has its own random32hex ID, lifecycle root, browser workspace/report and aggregate summary. Shared old reports are never consumed. Initial summary is FAIL50; even abrupt process kill cannot leave an authorized aggregate PASS without a matching manifest and both verified components.

Browser evidence version2 checks exact Chromium DPR1/1.5/2 (CI all adds Firefox3), exact test title/file/project identity, one passed result each, expectedStatus passed, retries0, stats expected3/6, skipped/unexpected/flaky0, no report/result errors, current invocation and source SHA. Existing browser assertions/resource budgets are unchanged. Workload artifacts must match invocation/source/run/attempt and all checksums/limits. Bundles publish by same-directory rename after verification. Sanitized report facts retain the raw-report SHA256 without exporting raw exceptions, paths or attachments. Version1 browser bundles cannot certify this new gate.

`python -m terminan.r3_gate verify` requires exactly one verified lifecycle, complete browser bundle, matching provenance and all aggregate hashes. A lifecycle-only directory fails. An outer shell can discard ANY native code; capture immediately and forward it explicitly when using another wrapper. Never infer R3 success from a nested lifecycle or a partial Playwright console summary.

## Physical15 first

Use a new clean checkout at the exact fix SHA from the PR handoff. Install the pinned npm dependencies and Chromium using the existing approved development setup. Do not change execution policy, ACL, services or firewall. Set `$sha` to the exact handoff SHA:

```powershell
$sha='<EXACT_FIX_SHA>'
if ((git rev-parse HEAD).Trim() -ne $sha) { throw 'SHA mismatch' }
if (git status --porcelain) { throw 'Dirty source' }
$py312=(& py -3.12 -c 'import sys;print(sys.executable)').Trim()
$root15=Join-Path '.r3-reliability-evidence' ('physical15-'+[Guid]::NewGuid().ToString('N'))
powershell.exe -NoProfile -File .\scripts\Invoke-R3.ps1 -ExpectedSha $sha -Python $py312 -EvidenceRoot $root15 -OpenBrowser -ReviewSeconds 15
$native15=$LASTEXITCODE
Write-Host "R3_15_NATIVE_EXIT=$native15"
$runs=@(Get-ChildItem -LiteralPath $root15 -Directory)
if ($runs.Count -ne 1) { throw 'Incomplete invocation' }
$inv=$runs[0].Name
& $py312 -m terminan.r3_gate verify --sha $sha --invocation $inv --out $runs[0].FullName
$evidence15=$LASTEXITCODE
Write-Host "R3_15_EVIDENCE_EXIT=$evidence15"
if ($native15 -ne 0 -or $evidence15 -ne 0) { throw 'STOP: preserve failed evidence; do not run600' }
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $runs[0].FullName 'manifest.json')
```

Observe ALL THREE Chromium project results. The automated browser phase follows the interactive lifecycle review, takes additional time and uses its own short-lived loopback server. Do not terminate it after the manual15s timer. Confirm aggregate summary result AUTOMATED_R3_PASS, native0/evidence0, Chromium3/3, no skipped/interrupted/retries. PHYSICAL stays PENDING until human review evidence is supplied. Repeat native shell with `pwsh.exe`; preserve separate roots.

## Only after verified15 PASS

Run the same command with a NEW unique root600 and `-ReviewSeconds 600`. Capture native immediately, select exactly one invocation, run the same aggregate verifier, hash its manifest. Never reuse an old report/run directory or accept lifecycle-only output. Preserve FAIL and interruptions as failures; reruns get new invocation IDs.

Negative repro (on disposable development checkout): `python scripts/test_r3_shells.py --shell powershell --report reports/r3-shell-ps51.json` then pwsh. It deliberately supplies lifecycle0 and browser interruption/false0/stale/missing/partial reports; every case must native50/summaryFAIL50. No browser/DB connection is made by this synthetic shell contract.

## Rollback

Close only this invocation's preview and owned processes normally. Use a separate checkout at PR20 3ed51d908b80a0fa9fee5d72999ca2184f309bec for source comparison; it contains the known falsePASS and must NOT be used as an R3 acceptance gate. The prior physically accepted offline G0 reference is PR18 a10c092825442262149a29e59ea041c6ef5cacc9 with its original Invoke-R2; it retains the older transport/daemon risk. Do not reset/edit PR20/19/18, erase failed evidence or kill unrelated processes. No merge/deploy/G1/live sources/trades/DB writes are authorized.

Real OS cancellation regression: `python scripts/test_r3_console_cancel.py --report reports/r3-console-cancel.json`. Mandatory Windows CI, hidden newly owned console only, verifies sole ownership before broadcasting Ctrl+C; never signals an existing user console. Synthetic PipelineStoppedException alone is insufficient.
