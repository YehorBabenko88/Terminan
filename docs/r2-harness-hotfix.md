# R2 harness P0 — diagnostic release and LS-5 repro

This is a separate Draft PR18 based on frozen PR17
7ff974b3b2db694e4b8e4d044cf0844b5d384fc4. PR17 and PR9 are unchanged.
Use the exact hotfix SHA from the handoff/PR checkpoint below; do not test a
mutable ref or attribute old screenshots to a new candidate.

## What is known

Issue6 reports actual LS-5 evidence: all9 smoke routes200, R2 screenshot,
summary exit30/FAIL, physicalPENDING, four file hashes valid. The reported
original manifest SHA256 is
9039666388024016b0994011eebac287da30891ab43cecc0e09e081bff718a09.
Original files were not available in this workspace; that hash is user-provided,
not a claim of independent verification. Preserve that evidence unchanged.

The original manifest was a valid JSON array; nested PowerShell display/property
expansion did not establish corruption. The physical post-smoke exception remains
UNKNOWN. It may not be identified retrospectively from the original redacted record.

Reproduced at the original exact source using an induced browser failure:
PS7 nested harness reports30/FAIL with9 routes200; an outer script without
explicit exit returns0, and one with explicit forwarding returns30. A separate
local PS5.1 failure in Get-FileHash inside the old unguarded finally bypassed the
final exit. This second reproduction is not evidence of the same LS-5 cause.

## Changed boundary

Invoke-R2.ps1 retains its public parameters. It invokes a stdlib Python lifecycle
engine by absolute script path without changing/restoring caller location, captures
native status immediately, independently verifies the committed evidence and exits
explicitly. No Get-FileHash/cmdlet pipeline serialization is required.
Native error preference is controlled in script scope only.

An arbitrary parent that omits forwarding or runs another native command before
reading LASTEXITCODE can still report0. A child cannot safely fix that by exiting
the user's host. Use native -File or explicit parent exit forwarding. The test
outer_no_forward is an intentionally unsafe counterexample, not accepted usage.

| failure_stage | Exit | Examples of safe error_class |
|---|---:|---|
| preflight |10| INVALID_SHA, SHA_MISMATCH, DIRTY_SOURCE |
| startup |20| READY_TIMEOUT, READY_INVALID |
| smoke |30| SMOKE_HTTP_FAILED, SMOKE_ASSERTION_FAILED |
| browser_launch |31| BROWSER_LAUNCH_FAILED |
| review_wait |32| REVIEW_WAIT_FAILED |
| child_health |33| CHILD_EARLY_EXIT, CHILD_HEALTH_FAILED, CHILD_STDERR |
| graceful_shutdown |40| SHUTDOWN_TIMEOUT, SHUTDOWN_FAILED |
| evidence_finalize |50| EVIDENCE_FINALIZE_FAILED, EVIDENCE_PATH_REDIRECTED |

Successful summary has exit0, failure_stageNONE, error_classNONE and
AUTOMATED_SYNTHETIC_SMOKE_PASS. Physical always remainsPENDING. Browser
DISPATCHED only means OS launch dispatch, not proof that a visible page rendered.
Safe versions, elapsed monotonic review time, health probe count, child exit code,
bounded byte counters, stage states and numeric OS error code are allowed.
No raw exceptions, paths, DSNs, command lines, machine names or payloads are saved.

Primary failure is retained if cleanup also fails; secondary_failures records
the cleanup class/code. An early child exit0 is still a failure33. Timeout kills
only the owned child, never the browser or another service. SIGINT is deferred
only during bounded owned-child cleanup, with nested finally kill/drain/close.
No database, exchange, Grid/Strattester, service/ACL/firewall or G1 action occurs.

Evidence is staged in an owned .pending-run-id and atomically published only
after serialization/hash/schema checks. Manifest is always an array, including
one-entry preflight failures. Existing evidence is never overwritten; symlink/
junction redirection is refused. A finalization failure returns50 and can leave
an unpublished pending directory. If writing is impossible there may be no summary;
absence is a failure, never implicit PASS. Keep pending data for triage, not release.
Use ordinary local storage and default ignored .r2-evidence, or an output folder
outside the checkout. Do not use an unignored generated directory as clean source.

## Short LS-5 repro —15 seconds

Use an ordinary non-admin terminal and clean dedicated hotfix checkout, Python3.11+.
No ExecutionPolicy, ACL, services, browser association or firewall change is needed.
Replace EXACT_HOTFIX_SHA with the full handoff SHA. In PowerShell:

```powershell
$r2Sha = '<EXACT_HOTFIX_SHA>'
$r2Lines = & powershell.exe -NoProfile -NonInteractive -File .\scripts\Invoke-R2.ps1 -ExpectedSha $r2Sha -EvidenceRoot '.r2-evidence/ls5-15' -OpenBrowser -ReviewSeconds 15
$r2Exit = $LASTEXITCODE
$r2Lines
"R2_NATIVE_EXIT=$r2Exit"
```

Capture r2Exit immediately, BEFORE Python verification or any other native program.
Do not pipe the harness into another process. Find the exact run_id printed as
R2 evidence run_id=..., not a guessed latest folder:

```powershell
$r2Run = '<PRINTED_RUN_ID>'
$r2Dir = Join-Path '.r2-evidence/ls5-15' $r2Run
$r2Summary = Get-Content -LiteralPath (Join-Path $r2Dir 'summary.json') -Raw | ConvertFrom-Json
$r2Summary | Select-Object candidate_sha,exit_code,result,failure_stage,error_class,os_error_code,physical,powershell_version,python_version,review_elapsed_seconds,child_exit_code
if ($r2Exit -ne $r2Summary.exit_code) { throw 'STOP: native/evidence mismatch' }
if ($r2Exit -ne 0) { throw 'STOP: preserve FAIL evidence; do not start600-second review' }
python -m terminan.r2_evidence verify $r2Dir --sha $r2Sha
$r2VerifyExit = $LASTEXITCODE
if ($r2VerifyExit -ne 0) { throw 'STOP: evidence verification failed' }
```

If the final directory does not exist, keep the printed stage/class and native
nonzero code, plus any pending folder. Do not fabricate files or copy a prior PASS.
Share only the selected safe fields, run_id, native code and manifest SHA256.
Do not send raw shell ErrorRecords, environment dumps, paths or raw child output.
The Python verifier hashes the array entry-by-entry; no array-property Join-Path
expansion is needed. A verifier failure returns50 with a generic diagnostic.

PS7 alternative: substitute pwsh.exe for powershell.exe; both use native -File.
If a parent must use -Command, explicitly capture and exit its child code:

```powershell
# Inside the parent -Command/script:
& .\scripts\Invoke-R2.ps1 -ExpectedSha $r2Sha -ReviewSeconds 15 -OpenBrowser
$r2Exit = $LASTEXITCODE
exit $r2Exit
```

That last form is for a dedicated parent process/script, not for closing an
interactive working terminal after unrelated commands.

## Full600-second physical review

Only after15-second native/evidence/manifest checks pass:

```powershell
$r2Lines = & powershell.exe -NoProfile -NonInteractive -File .\scripts\Invoke-R2.ps1 -ExpectedSha $r2Sha -EvidenceRoot '.r2-evidence/ls5-600' -OpenBrowser -ReviewSeconds 600
$r2Exit = $LASTEXITCODE
$r2Lines
"R2_NATIVE_EXIT=$r2Exit"
```

Repeat the exact run-id and summary comparison/verification against ls5-600.
Use the R2 Windows checklist for actual browser, DPR100/150/200%, resize, zoom/pan,
switch/cancellation, console and sustained responsiveness. Store redacted
screenshots/signoff separately, referencing the new SHA and evidence manifest.
Any failure stays FAIL. A15-second pass does not establish600-second acceptance,
and neither automated run alone grants PHYSICAL PASS.

## Severity and rollback

P0: false-success boundary in the original caller/finally path is reproduced;
supported native invocation now requires native/evidence agreement.
P1: original LS-5 post-smoke cause still UNKNOWN until diagnostic repro; owned-child
cancellation leak found in implementation review was reproduced and fixed.
P2: pending-directory ownership collision found in review was reproduced and
fixed; original four-entry manifest was valid, with new one-entry array guards.

Rollback: stop only the owned hotfix child and preserve all evidence. Use a
separate clean PR17 checkout at7ff974b3b2db694e4b8e4d044cf0844b5d384fc4 for UI
comparison only; its old harness/native code is not an acceptance oracle.
Frozen PR9 at0ad0f36edce2ac7717c753d35ebe113dc6334fd0 remains the prior G0 option.
Do not reset another branch, delete evidence, migrate a DB, stop services, deploy
or merge. Physical acceptance remains blocked until new LS-5 evidence is reviewed.
