# Terminan #86 — Stage 3 consolidation and ownership / NO_GO

MASTER: https://github.com/YehorBabenko88/unified-system/issues/111
Imports: https://github.com/YehorBabenko88/unified-system/issues/114
Retirement: https://github.com/YehorBabenko88/unified-system/issues/115
Independent E2E: https://github.com/YehorBabenko88/unified-system/issues/116

## Immutable sources reviewed

- Terminan main: `fee79f4b15fc1f9efcff9ca12c403688b0026260`.
- Source strategy metadata: Strattester main `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea`; current Strattester candidate #83 `d6293f75db7fcc8eed0900521a1ba6bd46b3468e`.
- Independent target PR #88: `db979e5bc9ec6c0cb520df229781a533a2cf6d7b`, same Terminan main base; provides original source metadata and HypothesisSpec in existing `contracts.py`, tests. Exact-head CI #44510619371 SUCCESS (only baseline Python qualification).
- Terminan prior PR #87 before Stage 3: `08f3c12fdc2d989d8f13f757f73ecc298631089f`, duplicate `terminan/strategies.py`, tests; Python CI #44510621865 SUCCESS at that old HEAD.
- Other relevant owners: Grid #292, Math #121, Meta #81, security Unified #113. Later stacked UI branches #61/#83/#85 must be separately qualified and preserved.

## Stage 3 actual consolidation within Terminan PR #87

Canonical strategy metadata API: **`terminan/contracts.py`**. It now includes the complete PR #88 metadata/registry/hypothesis subset, plus the stricter metadata validation and legacy-wire fingerprint regression tests formerly in PR #87. **Only ONE class named StrategyRegistry is present in the PR #87 source tree.** No new service or module.

| Original symbol | Source dependency / purpose | Final location | Disposition |
| --- | --- | --- | --- |
| `strattester/strategies/base.py:DataRequirement` | `DatasetKind`, allowed historical feeds | `terminan/contracts.py:DataRequirement` | MOVE; string values normalize enum, strict timeframe/required validation |
| `strattester/strategies/base.py:StrategyDefinition` | strategy id/version, Python class, feature versions | `terminan/contracts.py:StrategyDefinition` | MOVE; fail-closed input metadata |
| `strattester/strategies/base.py:strategy_fingerprint` | hashlib/inspect/json, stable persisted identity | `terminan/contracts.py:strategy_fingerprint` | MOVE; same wire serialization, independent test oracle |
| `strattester/strategies/base.py:Strategy` | typing.Protocol for strategy.run | `terminan/contracts.py:Strategy` | MOVE inert interface, no executor |
| `strattester/strategies/registry.py:StrategyRegistry.register/discover/set_enabled` | unique id/version, enabled state | `terminan/contracts.py:StrategyRegistry` | MERGE; duplicate registration refused, one in-memory registry |
| `strattester/strategies/builtin/research_common.py:HypothesisSpec/executable_hypotheses` | declarative candidate vs executable status | `terminan/contracts.py` | MOVE; SPEC_ONLY remains non-executable |
| `terminan/strategies.py` from earlier PR #87 | duplicate registry/metadata implementation | **deleted from PR #87** | DELETE duplicate file from candidate (not from deployed main) |
| `tests/test_strategies.py` from earlier PR #87 | separate duplicated test suite | merged into `tests/test_contracts.py`, **file deleted from PR** | MERGE/DELETE after exact test source transferred |
| `terminan/contracts.py:TradeEvent/align_trades` | external trade-view presentation | same | KEEP; no strategy execution |
| `terminan/contracts.py:aggregate_footprint/poc_close_events` | domain POC math, overlaps Meta/Math | pending Math API | KEEP temporarily; Math owner must validate parity before removal |
| `terminan/levels.py:untouched_levels/merge_levels` | closed-candle high/low algorithm | Math target after parity | MOVE candidate; old code retained, separate Terminan #55 hardens input |
| `terminan/data.py:sqlite_ro/candles/instruments/research/grid_query/grid_candles/footprint` | read-only adapters for SQLite/PG | future Unified Gateway consumer, Grid sole data producer | KEEP until ABI and independent actual-source acceptance |
| `terminan/server.py:Handler.do_GET/run` | original read-only loopback UI | one Terminan UI | KEEP until six-workspace successor and physical cutover accepted |
| Terminan PR #61 `unified_server.py/r4_server.py/r2_server.py/saved_server.py` | several candidates/fixture entrypoints | single UI vs test harness to be classified | KEEP refs, no deletion until #114/#116 proof |
| Grid #288 `grid/strategy_plugins.py:register_plugin/get_plugin/list_plugins` | competing strategy registry | Terminan API after consumer cutover | MOVE candidate; old Grid code must remain until acknowledged |
| Grid #288 `grid/strategy_runner.py:strategy_worker`, `strategy_executor.py:materialize_plugin/execute_job_subprocess` | remote execution/resource bridge | Terminan strategy orchestration vs Unified runtime authority | SPLIT by single-owner interface; don't copy unsafe worker primitives |
| Strattester `research/runner.py:ResearchRunner.run/_sync_definition` | direct SyncEngine collection + strategy execution | Terminan orchestration using Grid immutable dataset | MOVE candidate; remove direct collection only after receipt parity |
| Strattester `research/execution.py:simulate_trade/simulate_scale_trade` | paper simulation, embedded PnL math | Terminan paper orchestration, Math calculation contract | MOVE candidate; numeric parity and lookahead tests required |
| Strattester `research/result_persistence.py:persist_report/persist_report_fenced` | result metrics + fenced stage/promotion | Terminan experiment ledger with Unified/Storage fencing | MOVE candidate; preserve run ids, fingerprints, crash-safety |
| Meta #78 `core.PaperEngine`, `level_sync.LevelSync`, `level_publish.publication_decision`, `flow_style.flow_cell_style`, `flow_diff.changed_rows` | paper strategy/level presentation | Terminan non-math logic/UI | MOVE candidate; original remains until separately verified |
| Meta #78 `core.untouched_levels` and orderflow metrics | numerical model | Math | MOVE candidate, Terminan must not fork math |

## Import and consumer evidence

- On pinned Terminan main `server.py` invokes `data.instruments/candles/research/grid_candles/footprint` and `levels.merge_levels`; it does **not** execute registered strategies.
- In this PR #87, metadata test imports point **only** to `terminan.contracts`. `terminan/strategies.py` is removed, including its independent test import. The source tree contains a single in-process strategy registry implementation.
- Existing Strattester consumers still depend on old `strattester.strategies.*` and research/engine code. Old Grid strategy workers and external install/CLI calls are **not migrated**. A repository-wide import/entrypoint graph and consumer matrix must be completed by #114 before deleting any upstream implementation.
- Preserve original fingerprint payload including `impl` module/qualname; relocating a strategy *implementation class* can change that identity. Never silently recompute persistent run identity under a different class path. Approval requires exact original-vs-target parity and stable migration/alias receipt.

## Tests, rollback and release gates

- Python tests in `tests/test_contracts.py` now combine source #88 registry/hypothesis checks and PR #87 additional fingerprint/invalid-input/inertness tests. Static path inventory confirms old standalone test and registry module are absent from PR #87 candidate.
- **Exact-head CI:** check independently for latest PR #87 head. Earlier 16/16 PASS was for a superseded commit; do not reuse it as qualification of the new HEAD.
- Revert stage3 commits in PR #87 to restore standalone old candidate, or cherry-pick source #88 file changes into an isolated branch. **Do not** roll back user data or the original Strattester repository.
- Source/target runtime imports, real Bybit continuity, Grid/Math exact source integration, Windows one-installer/one-terminal E2E, security all-history scan, old consumer cutover and resource/data preservation: NOT VERIFIED.
- Repository archival evidence for #115: Strattester and Meta Analyse **NOT_READY_TO_ARCHIVE** until all unique symbols and consumers mapped, old data preserved, tests and independent physical restore evidence accepted. No GitHub repository deletion or branch purge.
- No real orders, DB writes, deployment, service changes, host/ACL/firewall changes, branch deletion or merges.

**Release: NO_GO.**
