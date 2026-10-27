# R4 implementation design and execution ledger

Spec: docs/r4-session-contract-acceptance-plan.md at40c3d0f0c3ae75a0cf08a58cfc04239d0c8353dd. Accepted R3d5a8342168fd8b55c110d5aa7b9b619ae2c97e32 remains immutable. Own branch integration/r4-offline-session-20261027.

Architecture: opt-in R4 runner/server/UI; R2/R3 behavior and guards retained. Pure strict versioned contracts with pinned template/source/schema hashes, selected identity and virtual UTC, explicit native timeframe limitations. Per-process session ID/epoch/lease, owner-stdin-only end, bounded HTTP grace; UI only accepts matching end receipt. Unknown failure -> DISCONNECTED with finite retry, never inferred normal end. Same-origin loopback receipt is process/session correlation, not TLS identity or live-source authority.

Plan (inline execution; writing-plans/executing-plans, TDD):
1. Contract RED/implementation/GREEN: source+kind coupling, schema/version/types, UTC ms, selected symbol/timeframe, coverage/freshness, lineage, NULL/nonfinite/future/duplicate/order/epoch tests. Grid native1m only; research historical.
2. Session RED/implementation/GREEN: immutable end, matching ID/SHA/epoch, lease, finite retries/abort/generation fencing, newtab isolation; explicit stop UI, no post-end polling.
3. Browser metrics and regression: reuse exact R3 workloads/budgets unchanged; add fetch quantiles/counts and limitations; R4 strict receipts include session/contract/UI tests. DPR1/1.5/2 mandatory; zero retries/skips/interruption.
4. R4 harness: retain R3 dedicated-host Environment.Exit protection, isolateinvocation, native/evidence agreement, R4 lifecycle end receipt, ownbrowser workload, SHA256.15 then600. Windows/Linux Py3.11/3.14 CI + PS5.1/7 realCtrlC.
5. Wholebranch independent review, exact-head fulltests/CI/artifact validation, ownDraft PR progress, redacted packet/runbook/rollbacktoR3. No physicalPASS until LS-5 evidence.

Rulings: supplied PR24 plan plus explicit implementation instruction is sufficient design authorization; no repeated approval pause. Separate clone avoids shared alternate-depth failure. Grid1m vs selected5m is explicit UNSUPPORTED_TIMEFRAME rather than fabricated source aggregation. No live authority label is granted by synthetic receipts. End grace3s fits existing10s parent shutdown bound but delivery to suspendedtabs is not guaranteed; unobservedend staysDISCONNECTED. Retry budgets count consecutive failures and stop permanently; user reload starts a new view, not a live reconnect.

Findings: R3 contracts endpoint ignores selectedsymbol/tf in fixture values; R3 UI has no session termination protocol, only ERROR/connection refusal. No real source connections used in audit.
