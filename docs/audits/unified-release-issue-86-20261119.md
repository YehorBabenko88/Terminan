# Terminan #86 — Stage 2 strategy migration ledger (2026-11-19)

**NO_GO / DRAFT — executable code changed, production cutover NOT AUTHORIZED.**
MASTER: https://github.com/YehorBabenko88/unified-system/issues/111
Owner revision: MASTER 2026-11-19 changes the previous mapping. **Terminan owns all strategy definitions, registry, configuration, simulation/backtesting, experiment/result lifecycle and one terminal UI.** Math owns domain computations; Grid owns canonical Bybit history/live, datastore/quality; Unified owns installation/Gateway/lifecycle; Meta Analyse is a source of unique functionality to redistribute, not a second terminal.

## Immutable source baseline
- Terminan main `fee79f4b15fc1f9efcff9ca12c403688b0026260`.
- Strattester main `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea`.
- Candidate UI six-workspace runtime Terminan PR #61 `88161de6344f6e6abb03c1fa728c96bd831dc845`; later stacked #83 `e23abe3345379e41f979695136fd1261e3cbd238`; security #85 `28227205723c23dcbea2a9a4b7b3a52e99d44b46`. None automatically qualified or merged.
- Terminan has 81 open PRs at the time of initial API listing; the first page contained all 81. Other unmerged refs and full history not inventoried.
- Other owner reports: Grid #291, Strattester #87, Math #120, Meta Analyse #80, Unified security #113.

## Exact function/symbol disposition (first bounded migration)
| Original source symbol | Dependencies | Terminan target | Result |
|---|---|---|---|
| `strattester/strategies/base.py:DataRequirement` | `DatasetKind` enum only | `terminan/strategies.py:DataRequirement` | MOVED, enum values accepted without importing marketdata |
| `strattester/strategies/base.py:StrategyDefinition` | Python dataclasses | `terminan/strategies.py:StrategyDefinition` | MOVED |
| `strattester/strategies/base.py:strategy_fingerprint` | `inspect`, `json`, `sha256` | `terminan/strategies.py:strategy_fingerprint` | MOVED, original wire payload preserved |
| `strattester/strategies/base.py:Strategy` | typing Protocol | `terminan/strategies.py:Strategy` | MOVED protocol, no execution |
| `strattester/strategies/registry.py:StrategyRegistry.register/discover/set_enabled` | StrategyDefinition | `terminan/strategies.py:StrategyRegistry` | MOVED, duplicate registration denied |
| `strattester/strategies/builtin/*` | research/mathematical dependencies | NOT MOVED | inspect call graph, separate Math-owned computations |
| `strattester/research/runner.py`, `research/execution.py`, result ledger | Grid data, research imports | NOT MOVED | strategy orchestration/simulation migration pending |
| `terminan/levels.py:untouched_levels/merge_levels` | closed candles | Math ownership candidate | NOT MOVED: existing PR #55 independently hardens it; parity and consumer qualification required |
| `terminan/contracts.py:aggregate_footprint/poc_close_events` | numeric market data | Math ownership candidate | NOT MOVED: semantic comparison with Meta/Math required |
| `terminan/server.py:Handler.do_GET`, `terminan/data.py:candles/grid_candles/footprint/research` | existing SQLite/PG read adapters | Terminan UI/consumer, Grid canonical data | RETAIN pending shared versioned Gateway contract |
| `terminan/unified_server.py`, `r2_server.py`, `r4_server.py` | stacked UI candidates | one Terminan UI | NOT REMOVED: import/entrypoint map and physical parity pending |

### Code impact and safety
- New runtime source: `terminan/strategies.py`; new tests: `tests/test_strategies.py`.
- No new service, database, API listener, job, collector or trading capability; registry remains inert and memory-only.
- Original Strattester code still exists as rollback source; **no legacy import/call sites migrated yet**, so cross-repository removal is **BLOCKED**. It would be unsafe to claim duplicate elimination from this partial import.
- Added input guards for invalid strategy metadata; preserved version/fingerprint payload and insertion order.
- No existing file deleted or overwritten; no data/schema/user history changes.

### Validation
- Local isolated Python 3.11+ unit slice: 5/5 PASS (original-algorithm parity, version and enable toggles, rejection, inertness), without source runtime checkout. Hosted CI for final exact HEAD must be inspected independently; local tests do not attest application compatibility.
- Cross-repository original-Strattester/Terminan side-by-side parity against executable original source: NOT RUN.
- Browser/Gateway/physical/real Bybit data/full test matrix: NOT RUN.
- Secrets history, PR heads, dependencies, full audit and independent acceptance: NOT RUN.
- Release decision: **NO_GO**.

## Required cutover sequence
1. Agree strategy definition schema and receipt ABI with MASTER; isolate all domain computation in Math.
2. Enumerate strategy consumers/imports in Strattester, Grid, Unified and Terminan, with pinned source SHA.
3. Validate original registry fingerprints with actual Strattester source in same CI matrix; preserve legacy IDs for stored runs.
4. Transfer strategy implementations only after removing mathematical kernels and replacing provider access with Grid's read-only versioned data contract.
5. Move simulator, paper execution, experiment ledger and consumer imports to Terminan and exercise crash/rollback with original data unchanged.
6. Only after parity, exact-head CI, history scan and physical acceptance consider removing old Strattester runtime modules in a separate owner PR; retain immutable archive/rollback map.

This is a **limited first code migration**, not a finished unified installer or strategy engine.
