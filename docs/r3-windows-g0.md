# Windows R3 G0 — separate from accepted R2

Base PR18 a10c092825442262149a29e59ea041c6ef5cacc9 remains unchanged. User-reported LS-5 physical PASS applies to that base only. Base manifest SHA256: 337B06AC2D4EEF42CA32C03A8EE1CC40ED1F90D26D86BCF6313AB111D0E3A4F4.

Use the exact R3 SHA in the Draft PR handoff, a clean separate checkout, Python3.11+, Node24 and the pinned Playwright dependencies. Install browser test tooling once (no database or exchange access): `npm ci --ignore-scripts` and `npx playwright install chromium`. No elevation, service or firewall changes.

From a native parent PowerShell, first run 15 seconds, then 600. Replace SHA with the full R3 candidate SHA, never the branch name:

```powershell
powershell.exe -NoProfile -File .\scripts\Invoke-R3.ps1 -ExpectedSha '<R3_SHA>' -OpenBrowser -ReviewSeconds 15
$rc=$LASTEXITCODE
Write-Host "Native exit=$rc"
# After short-run inspection, repeat with a separate evidence root:
powershell.exe -NoProfile -File .\scripts\Invoke-R3.ps1 -ExpectedSha '<R3_SHA>' -EvidenceRoot '.r3-evidence/full' -OpenBrowser -ReviewSeconds 600
$rc=$LASTEXITCODE
Write-Host "Native exit=$rc"
```

PowerShell7: substitute `pwsh.exe`. Capture LASTEXITCODE immediately. Exit0 requires both accepted lifecycle engine smoke/review/shutdown and the three Chromium DPR1/1.5/2 R3 benchmarks plus independently verified SHA256 evidence. Exit10/20/30/31/32/33/40 retain lifecycle meaning;50 means browser benchmark/evidence failure. A caller that does not forward native exit may still hide failure; inspect evidence too.

Harness binds an OS-selected loopback port, sanitizes inherited source settings, closes only its own child via stdin, and retains privacy-safe stage/error codes. OpenBrowser means dispatch, never proof of rendering. Browser benchmark runs headless after manual review; it measures the same candle renderer, not the manually observed browser or physical display FPS. It changes only in-memory synthetic candles. Separate Python stress validates100k linked DOM deltas. No production sources run.

Manual checklist during600s: SYNTHETIC/OFFLINE, no LIVE authority; play mixed scenario; observe GAP24, STALE48, reconnect72 and recovery80; zoom/pan/reset; all symbols and timeframes, rapid switching; resize and Windows100/150/200% scaling; DevTools errors; record observed responsiveness. Do not report quantitative physical performance from subjective smoothness.

Evidence: `.r3-evidence/lifecycle/<run>/summary.json,smoke.json,manifest.json` and `.r3-evidence/<run>/summary.json,manifest.json,<project>.json/png,contract-pins.json,negative-fixtures.json,tests.json`. Summary physical always PENDING until human evidence review. Verify browser bundle independently:

```powershell
python -m terminan.r3_evidence --verify --sha '<R3_SHA>' --out '<benchmark-run-directory>'
Get-FileHash '<benchmark-run-directory>\manifest.json' -Algorithm SHA256
```

Budgets: 10k and100k updates,100 per render, exact checksum, bounded240candles/20events/40bookrows; batch-ingress-to-render p99<100ms; draw p95<50ms; headless RAF cadence>10Hz; Chromium main-thread CPU duty<75%; post-GC JS heap growth<12MiB; summed process RSS<2GiB and growth<256MiB. Shared pages can be counted multiple times in RSS. Firefox CPU/heap/RSS are explicitly unavailable via this CDP sampler; its rendering/cancellation tests still execute in hosted CI. These finite workloads do not establish absence of long-duration leaks;600s physical review and extended overnight soak remain separate acceptance items.

Acceptance matrix: source pins/schema/negative contracts,100k DOM deltas, browser interactions and budgets, exact4-platform CI, native5.1/7 codes and manifests, physical manual checklist. Automated success never grants physical PASS. Missing evidence, failed/skipped required tests or exceeded budgets fail closed.

Rollback: stop only the owned process; close preview. Use a separate clean checkout of accepted PR18 a10c092825442262149a29e59ea041c6ef5cacc9 and its Invoke-R2.ps1. Do not reset another branch, delete failed evidence or change databases/services. No merge/deployment/G1 authorized.
