# R2 harness fail-closed hotfix

Base: PR17 frozen at7ff974b3b2db694e4b8e4d044cf0844b5d384fc4; PR9 unchanged.
Issue6 physical evidence:9 smoke routes200, summary30/FAIL, four hashes valid.
Original physical cause remains UNKNOWN; no browser-launch hypothesis is proven.
User-supplied manifest hash9039666388024016b0994011eebac287da30891ab43cecc0e09e081bff718a09.

Reproduced baseline: induced post-smoke browser failure gives summary30 and all9
routes200. In PS7 an outer script without explicit exit returns0, even though its
immediate LASTEXITCODE is30; explicit forwarding returns30. In local PS5.1 a
Get-FileHash failure inside unguarded finally bypasses final exit and leaves0.
The latter is a separate observed environment failure, not the LS-5 root cause.

Design: retain Invoke-R2.ps1 public parameters; use a stdlib Python lifecycle
engine (Python3.11+ already required). This avoids shell-dependent finally,
hash cmdlet and array-pipeline serialization. The PS entrypoint captures native
exit immediately, independently inspects committed evidence, then exits explicitly.
An arbitrary caller that discards exit status cannot be fixed by killing its host;
document/test -File and explicit -Command forwarding.

Stages: preflight10, startup20, smoke30, browser_launch31, review_wait32,
child_health33, graceful_shutdown40, evidence_finalize50. Only controlled enum
failure_stage/error_class and optional numeric OS code; no raw exceptions, paths,
DSNs or environment dumps. Preserve primary failures and secondary cleanup errors.
Use monotonic review timing, bounded health probes and constant-memory pipe drains.
Only the owned child may be stopped; never the browser or another service.

Write evidence in an owned pending directory, atomically publish complete JSON/
array manifest after validation. Finalization error is nonzero; incomplete evidence
is never a PASS. Missing/invalid evidence overrides native success. No synthetic
assertion is weakened. Physical remains PENDING.

Plan: regressions RED; lifecycle/writer implementation GREEN; shell propagation
matrix PS5.1/7 + Windows/Linux Python3.11/3.14; independent review; exact-head CI,
safe15-second repro then600-second runbook; immutable evidence/report/rollback.
