# Repository integration baseline — 2026-10-30

This branch is deliberately scoped to independent source hardening and inventory.
It does not merge unrelated draft work or enable source connections.

## Ownership and entry points

- `main`: `python -m terminan` serves the original loopback read-only terminal and /monitor. Its /api/levels is a local derived view; /api/logs explicitly reports an unavailable adapter.
- Historical /saved: developed in separate integration branches. Never infer it is deployed on main.
- Cache PR #47: `7e69e76a8733535d6897db92a534e6de118432ff`, independent Draft branch, offline SQLite job queue and cache preview. LS-5 automated audit PASS, hosted Windows job cancelled; not merged.
- Source-owned Grid/Strattester gateways: proposed in `terminan/source_contract.md`. These are **not** verified running services.
- Other workstreams: monitoring dashboard, research overlays, scientific lab and source gateway branches must be independently reviewed before consolidation.

## Consolidation gates

1. Inventory current branch HEADs and compare to main. Do not cherry-pick all drafts indiscriminately.
2. Keep Grid market data and Strattester runs authoritative; Terminan read-only.
3. Validate versioned contracts, source revision, complete historical coverage, UTC and OOS/in-sample labels before overlays.
4. Keep cache-derived data isolated, with immutable source identity and explicit STALE/MISS/UNAVAILABLE.
5. Avoid blocking request handlers; cap pages, concurrency and resource use.
6. Run Python and Node tests on the exact merged candidate, followed by physical LS-5 read-only smoke and rollback.
7. Never auto-start Grid/Strattester, install Windows services, modify PostgreSQL or merge without explicit authorization.

## Known open issues

- /api/monitor queries a Grid `nodes` table: schema compatibility and source availability unverified.
- /api/levels derives from available candles, but historical completeness and source authority are not attested.
- /api/logs has no connected event source.
- Main's direct DB adapters and proposed private gateway architecture are not yet reconciled.
- Draft cache and new scientific/UI workstreams have not been integrated into a single tested candidate.

## Changes in this branch

Historical untouched-level calculations reject duplicate/unaligned timestamps, non-finite prices and invalid tick size, with bounded input. Incomplete candles remain skipped as before. Negative regressions added.
