# Terminan R4 — isolated session and source-contract acceptance plan

Base: PR #23 exact HEAD `d5a8342168fd8b55c110d5aa7b9b619ae2c97e32`. This is a **plan**, not a claim of R4 implementation or physical PASS.

## Scope and safety

- Keep accepted autonomous R3 G0 immutable. Develop R4 only in its own Draft PR.
- Grid and Strattester are not running; use pinned offline fixtures and synthetic replay only.
- No exchange subscriptions, order execution, production database connections, service/ACL/firewall changes, G1, merge or deployment.
- Preserve historical failures and original evidence.

## P0 — authority and identity

1. Distinguish SYNTHETIC, HISTORICAL_ONLY, UNVERIFIED, STALE, GAP, DISCONNECTED, SESSION_ENDED and LIVE_SOURCE_VERIFIED. A synthetic DOM engine internal LIVE enum must not imply a real exchange feed.
2. Bind each snapshot to source identifier, schema version, source commit/fixture hash, symbol, timeframe, UTC millisecond timestamps, sequence/epoch and freshness.
3. Reject unknown schema, malformed timestamps, nonfinite values, cross-symbol data, future leakage, out-of-order epochs and inconsistent coverage. Never silently substitute synthetic data for unavailable live data.
4. Grid and Strattester adapters must remain read-only with explicit permissions; no actual runtime integration acceptance without separate approved source identity and physical evidence.

## P1 — UI session end

1. Distinguish intentional synthetic harness shutdown from unplanned source failure. Do not infer intentional shutdown solely from connection refusal.
2. Introduce a bounded explicit session state/lease contract so the UI can display SESSION ENDED and stop polling after an authenticated-to-this-session termination signal; absent such signal, use DISCONNECTED with bounded retry/backoff.
3. Ensure cancel/abort does not revive stale frames. Closing and reopening tabs must not leak handlers, timers or pending requests.
4. Keep test and browser contexts isolated. Manual slider interaction must not interfere with Playwright's dedicated benchmark context.

## P1 — measured performance

- Collect p50/p95/p99 render/draw/fetch latency with sample counts and clock domains; FPS, CPU/RSS where available with clear sampling limitations.
- Run bounded 10k/100k replay and long soak; report actual measurement, budget, source SHA, platform, browser/DPR, and all failed/skipped/interrupted attempts.
- Fail closed on missing/stale/partial reports, absent expected DPR projects or incomplete evidence; no PASS based on exit code alone.

## Acceptance gates

- Synthetic contract tests and negative tests across Windows/Linux and supported Python/browser matrix on exact HEAD.
- PS5.1/7 launcher: 15s and 600s physical lifecycle, native/evidence exit agreement, SHA256 manifest verification, no skipped/partial browser tests.
- Manual LS-5 review: zoom/pan/reset, symbol/timeframe, replay slider/Play/Step, DPR/resize, console and subjective responsiveness; instrumented performance separate.
- Historical PR #23 R3 evidence is a baseline, not R4 physical evidence.

## Handoff

Publish exact SHA, PR, CI run/attempt, provenance, evidence SHA256, P0/P1/P2, explicit NOT_RUN gates and rollback to frozen PR #23. No merge without separate authorization.
