# Terminan #86 — unified release owner audit (2026-11-19)

Status: **NO_GO / SOURCE-ONLY / DRAFT**. Parent: https://github.com/YehorBabenko88/unified-system/issues/111

## Exact baseline
- `main`: `fee79f4b15fc1f9efcff9ca12c403688b0026260` (basic `terminan/server.py`, `contracts.py`, `data.py`, `levels.py`, `monitor.py`, tests).
- Existing UI successor #83: `e23abe3345379e41f979695136fd1261e3cbd238`; stacked on #82, not on main.
- Existing security successor #85: `28227205723c23dcbea2a9a4b7b3a52e99d44b46`; stacked on #83. Do not duplicate action pinning.
- Existing six-workspace runtime #61: `88161de6344f6e6abb03c1fa728c96bd831dc845` (historic candidate, not automatically canonical).
- All open PRs/branches require pagination, lineage, exact-head CI and content review before source promotion. This document is a bounded first-pass, not an exhaustive inventory.

## Ownership / nonduplication proposal (requires MASTER confirmation)
| Capability | Sole owner | Terminan boundary |
| --- | --- | --- |
| Public Bybit history, live subscriptions, raw data custody | Grid (coordinate storage custody with Unified) | read-only versioned Gateway |
| Backtest, strategy lifecycle, paper experiment ledger | Strattester | submit permitted paper experiments; read receipts/results |
| Numeric/scientific kernels and proof | Math | display verified output and provenance |
| Orderflow, market levels, specialized analytics | Meta Analyse | display analytics via versioned contracts |
| Installer, service lifecycle, admission and authorization | Unified System | operator UI only |
| Chart, workspace navigation, source-status/error presentation | Terminan | one canonical UI |

## Candidate overlapping implementations requiring symbol-level audit
- Terminan `server.py`, `unified_server.py`, `r2_server.py`, `r4_server.py`: determine entrypoints, production vs fixture purpose, and imported dependencies; never delete based on names.
- Terminan history/preview/cache modules vs Grid data services: prohibit independent exchange capture or canonical market-data writes; cache must remain derived, bounded and source-versioned.
- Terminan scientific views vs Math computation and Meta Analyse visualizations: render results only, do not duplicate numerical kernels or second final terminal.
- Unified Observer dashboards vs Terminan infrastructure workspace: confirm single read-only data contract and distinct service ownership.

## Gateway contract requirements for next code PR
1. Versioned instrument identity (exchange, market type, symbol, instrument ID), UTC timestamps and timeframes.
2. Coverage window, gaps, partial/unavailable/stale flags, revision, immutable provenance and checksum.
3. Live state explicitly `LIVE_PUBLIC`, `DELAYED`, `DISCONNECTED`, `UNAVAILABLE` or `SYNTHETIC`; synthetic never presented as live.
4. Paper experiment request with idempotency key and immutable Strattester result receipt; no real order submission.
5. Math/Meta result reference with source snapshot, units, uncertainty/tolerances and calculation version.
6. Fail closed on missing source, wrong schema, stale authority or provenance; no direct DB writes, embedded credentials or self-started collectors.

## Evidence and release blockers
- Exact-head hosted CI for this audit PR: NOT_RUN at document creation; no runtime tests claimed.
- Full open PR/branch/head dependency inventory: PENDING.
- Full Git history and PR-head secret scan (gitleaks/trufflehog), dependency and Actions security review: PENDING; security clearance NOT ESTABLISHED.
- Real Grid history -> live reconnect -> Terminan browser -> Strattester paper experiment -> Math/Meta display: NOT_RUN.
- Physical Windows installation/restart/rollback, single shortcut, isolation and recovery: NOT_RUN.
- Existing PR #61 describes six workspaces with synthetic and unavailable source states, not proof of real live E2E.
- No deletions, merges, real orders, service changes, network changes or database mutations performed.

## Next gates
1. Enumerate every open PR, branch and exact SHA; build dependency/keep/replace matrix.
2. Inspect code-level imports and duplicated handlers, with tests before changes.
3. Obtain MASTER ownership and versioned Gateway agreement.
4. Implement only Terminan-owned read-only adapters/UX in a successor PR; exact-head CI and browser evidence.
5. Independent security and physical E2E acceptance before GO.
