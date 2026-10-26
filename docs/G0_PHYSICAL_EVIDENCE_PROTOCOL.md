# G0 Physical Acceptance — Evidence and Provenance Contract

Status: **NOT_RUN** until evidence is captured on a real Windows host. This document is a read-only protocol, not physical evidence.

## Immutable inputs

Pin full commit SHA and tree SHA for Terminan, Grid, and Strattester. Record each tested PR's head and base SHA separately. Do not infer PR results from main. Record GitHub workflow run ID, run attempt, job ID, step conclusion, runner OS and log/artifact SHA256. A re-run must retain attempt identity; a green run never overwrites an earlier failed attempt.

## Required gates

| Gate | Required observation | Failure handling |
| --- | --- | --- |
| Preflight | Windows version, PS 5.1 and 7 availability, Python >=3.11, pinned SHAs | NOT_RUN if unavailable |
| Startup | Explicit Python interpreter, process PID, exit code, readiness timeout | FAIL on timeout |
| Loopback | Listener is exclusively 127.0.0.1 or ::1; verify no wildcard/non-loopback bind | FAIL closed |
| Ports | Default 8765, alternative 8766, occupied-port negative case | FAIL if unexpected listener or wrong process |
| HTTP | Bounded requests, read-only endpoints, schema validation, error/timeout status | FAIL on unbounded or unexpected response |
| Browser | Chrome and Edge startup, blank screen, symbol/timeframe switching, resize, high-DPI, console, screenshots | NOT_RUN without actual browser |
| DOM | snapshot/delta epoch and sequence, GAP/STALE, reconnect, race and cancellation | SYNTHETIC only without host evidence |
| Grid PG18 | Read-only credentials; source identity, schema version, UTC milliseconds, freshness, coverage, WAL fencing provenance | FAIL closed on ambiguity |
| Strattester SQLite | immutable read-only URI, no DB creation, research run identity, no future leakage | FAIL closed on ambiguity |
| Shutdown | graceful stop of only the process launched by harness; port released | FAIL if leaked |
| Privacy | no tokens, DSNs, usernames, machine names, absolute home paths, IP addresses other than loopback | FAIL and quarantine evidence |

Never label Grid footprint as LIVE L2 or historical Strattester research as live trading authority.

## Evidence bundle

Use a unique output directory outside source repositories. Write redacted JSON UTF-8 with sorted keys and LF line endings. File list must be sorted by relative POSIX path. For each file include SHA256 of **redacted bytes**, size, media type and producing test ID. Save manifest SHA256 in a separate checksum file; do not hash the manifest inside itself. Screenshots and console logs require manual privacy review before upload. Avoid recording raw environment variables or connection strings.

Minimal manifest fields:

```json
{
  "schema_version": "g0-evidence-v1",
  "classification": "PHYSICAL_NOT_VERIFIED",
  "source": {"terminan_commit": null, "terminan_tree": null, "grid_commit": null, "grid_tree": null, "strattester_commit": null, "strattester_tree": null},
  "github_actions": [],
  "environment": {"windows_version": null, "powershell": [], "python": null, "browsers": []},
  "tests": [],
  "evidence": [],
  "privacy_redaction": "NOT_VERIFIED"
}
```

Each test records `test_id`, `status` (SYNTHETIC_PASS, HOSTED_CI_PASS, PHYSICAL_PASS, FAIL, NOT_RUN), `exit_code`, `duration_ms`, `source_sha`, and `evidence_paths`. Only the physical host operator's signed-off, integrity-checked bundle may yield PHYSICAL_PASS. CI cannot upgrade a physical gate.

## Failure and skipped gate triage

For every failed, cancelled, timed-out, neutral or skipped job, record exact head SHA, run ID, attempt, job ID, conditional expression and logs. Inspect job-level `system.txt` evaluation when skipped. A failed assertion must be compared to the documented contract; never silently change test expectations to green the pipeline.

## Exit codes (proposed harness)

0 = all required physical checks pass; 10 = prerequisite missing; 20 = startup/port/binding failure; 30 = HTTP/API failure; 40 = browser failure; 50 = source/read-only contract failure; 60 = privacy/evidence integrity failure; 70 = shutdown failure; 90 = internal harness error. If required gates were not run, return nonzero and retain NOT_RUN.

## Release / rollback

Release candidate is BLOCKED unless all mandatory gates are verified on pinned source/tree SHA and every failed/skipped gate is dispositioned. Rollback stops only harness-owned child processes, verifies loopback ports released and reverts the candidate by selecting a previously pinned immutable build. No `git reset --hard`, service modifications, ACL changes, database writes, migrations, order execution, G1, deployment or changes to another PR branch.
