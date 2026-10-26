# R3 child-health reliability — independent investigation

Frozen base Draft PR19 f401c2dda46ff38ee14004bdbb566fe0a3881014. Own branch only; PR19/18/17/9 unchanged.

LS-5 original run20261026T192206867Z-b9bef878: all four evidence hashes verified; manifest SHA256 A8917DE4FD8405ADB6DB047B98ECD1252637CDA341E74B184FCF86629BA3C525. Python3.12.10, PS5.1; first observed health failure57.609s, stderr689B, code33 CHILD_STDERR, child native C0000409, cleanup CHILD_EXIT_FAILED. Windows Application1000/1001 independently corroborates python.exe/ucrtbase.dll/C0000409. Raw stderr was intentionally discarded and cannot be recovered from this evidence. The original exact exception and ordering of browser errors remain UNKNOWN.

Two defects reproduced on the base: reset during end_headers writes traceback while server remains200; daemon stderr writer at interpreter finalization can produce _enter_buffered_busy and native C0000409 on Python3.12/3.14. These demonstrate mechanisms, not identity with the original689bytes. Independent read-only source review confirmed unprotected header/read/overload paths and daemon request workers not joined at shutdown.

Changes: only actual socket stream calls mark expected peer reset/closed/aborted/timeout. Arbitrary handler RuntimeError or ConnectionResetError remains fatal, emits only an allowlisted diagnostic token and increments a fatal counter. Unknown OSError is never reclassified as benign. Header/body/inherited error-response/read/overload paths use the same bounded policy. Invalid URL syntax is400. No raw exception, request target, client address, path or DSN is recorded.

R2 request workers are non-daemon and joined before runner exit. Socket timeout5s bounds normal incomplete work; the parent10s hard deadline remains authoritative and kills only its owned child on timeout. Worker-start failure releases admission slots. Runner final diagnostics are written only after workers finish; missing/invalid final diagnostics prevents PASS. Unexpected runner failures emit only RUNNER_FAILURE. No generic stderr guard was disabled: ANY child stderr remains FAIL, even a recognized token. Tokens provide diagnostic presence only, never a waiver.

Diagnostics: fixed allowlisted counters, peak/active workers<=16, last16events and first fatal; saturating counts; per-event server-relative elapsed_ms. Summary includes last/final HTTP diagnostics and a monotonic harness timeline (spawn, ready, review, first failure, quit requested, child exit observed, streams drained, finalize). stderr drain records first/last observed offsets and bounded token flags without retaining bytes. Clock domains are explicit: compare parent timing directly; server event offsets and child-drain offsets have their own origins. First-observed timestamps are not exact OS occurrence times.

Native codes unchanged:10preflight,20startup,30smoke,31browser,32review,33health,40shutdown,50evidence. Child native exit is separate; C0000409 must never be called benign. Generic unknown stderr/output overflow/early exit/HTTP fatal counters still fail closed. SYNTHETIC assertions/authority/execution-disabled checks unchanged.

## Physical repro

Use a separate clean checkout of the exact SHA in this PR handoff. Python3.11+ and existing pinned Node/Chromium tooling. First15seconds:

```powershell
powershell.exe -NoProfile -File .\scripts\Invoke-R3.ps1 -ExpectedSha '<CANDIDATE_SHA>' -EvidenceRoot '.r3-reliability-evidence/physical15' -OpenBrowser -ReviewSeconds 15
$rc=$LASTEXITCODE
Write-Host "R3_15_NATIVE_EXIT=$rc"
```

Then600 with a separate root, capture immediately:

```powershell
powershell.exe -NoProfile -File .\scripts\Invoke-R3.ps1 -ExpectedSha '<CANDIDATE_SHA>' -EvidenceRoot '.r3-reliability-evidence/physical600' -OpenBrowser -ReviewSeconds 600
$rc=$LASTEXITCODE
Write-Host "R3_600_NATIVE_EXIT=$rc"
```

Repeat with pwsh.exe. Use explicit -Python executable when reproducing the original3.12.10 environment; record only version in evidence. No execution-policy/service/ACL/firewall change needed. During review use Play, rapid symbols/timeframes, seek cancellation, close/reopen tabs. Keep DevTools network timestamps enabled. Connection-refused after intentional quit is expected; failure before quit is not waived. Automated smoke/benchmarks never grant manual PHYSICAL PASS.

Privacy-safe automated cancellation repro, real15/600 seconds, no browser/source dependencies:

```powershell
python scripts/r3_transport_soak.py --expected-sha '<CANDIDATE_SHA>' --seconds 600 --evidence-root .r3-reliability-evidence/repro
$rc=$LASTEXITCODE
Write-Host "REPRO_NATIVE_EXIT=$rc"
python -m terminan.r2_evidence verify .r3-reliability-evidence/repro --sha '<CANDIDATE_SHA>'
```

Each nested run contains summary/ready/smoke/checklist/child-diagnostics plus manifest. Record manifest Get-FileHash SHA256, native/evidence codes, counters, timeline, Python/PowerShell versions. Share only these bounded artifacts; do not capture raw stderr, dumps, environment or DSNs. Preserve original failed evidence. Real failure stays FAIL.

Rollback: stop owned process, close preview, use a separate clean checkout of accepted PR18 a10c092825442262149a29e59ea041c6ef5cacc9 and its original Invoke-R2. Do not reset or edit accepted branches. PR19 itself remains a preserved failed physical candidate; this fix requires a fresh LS-5 manual run. No merge/deployment/G1/real DB writes/live exchange/orders performed or authorized.
