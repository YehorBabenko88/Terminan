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

## Stage 4 P0 registry conflict and exact-head independent evidence

**Canonical ownership decision for this one existing candidate PR #87:** `terminan/contracts.py` is the sole metadata/registry implementation. It contains `DataRequirement`, `StrategyDefinition`, `strategy_fingerprint`, `StrategyRegistry`, `Strategy`, `HypothesisSpec` and `executable_hypotheses`. `terminan/strategies.py` is absent from this candidate tree. This deliberately chooses the smaller 3-file delta rather than importing PR #88's four-file successor. Neither PR is authorized for independent merge yet.

**PR heads freshly verified:**
- Terminan #87 `cf3bb664c131d4c44517218a3cb23fdbc5d189e9` (registry in contracts; 3 net files vs main, including this ledger).
- Terminan #88 `603ae1d9a05087a2640564885b0b47388980e9ff` (registry in `terminan/strategies.py`, imported by `contracts.py`; 4 files). Both branch candidates had individual Python success on PREVIOUS exact heads (`c19085c...` and `603ae1d...`) but cannot be merged together; #88 is **SUPERSEDED AS AN INTEGRATION CANDIDATE**, NOT APPROVED FOR MERGE OR AUTO-CLOSE. Its unique `HypothesisSpec/executable_hypotheses` are already included and independently tested in #87. Preserve #88 as source evidence. A future actual branch merge requires resolving the conflict against the selected layout and rerunning the complete exact-head suite.
- Grid #292 `ddec89c48c0153b3da07a48a9f71147fe0f1e6ec`, Math #121 `f41d5018e2b79d91f7934e7e838691725ce78277`, Meta #81 `7f443466211eb6789f63ebba1d3f5b2ca8e68d50`, Strattester #87 `bae61d0a40f44b420366d664f2e7098c1f88bd7f`, Unified security #113 `768ee659340a1a9e11d1a259fad283ac8900d64b`. Check their current head again before actually binding any runtime.
- Independent import test in `tests/test_contracts.py:SingleRegistryImportContractTests`: AST check requires exactly one implementation of four strategy symbols, in `contracts.py`; fails for `terminan.strategies` or relative `from .strategies` imports; verifies identity of public Python symbols; three additional unit tests. This test currently scans **the candidate Terminan source tree only**. It does not certify the full six-repo import graph.
- Exact-head source-only CI `cf3bb664c131d4c44517218a3cb23fdbc5d189e9`: GitHub Actions run IDs `44514800014` / `44514810168` were QUEUED when first checked; no final PASS claimed for that SHA until direct verification. Older #87 `c19085cee84539855c51d492772bf7e0124e46dc` workflow `44513739020`: SUCCESS, 19 Python unittest tests OK. #88 `603ae1d9a05087a2640564885b0b47388980e9ff` workflow `44512820734`: SUCCESS (its *independent* tree only); neither result demonstrates combined-tree compatibility.

**KEEP:** original source Strattester and Meta/Math/Grid code, historic immutable results, all PRs/branches and rollback sources. **MOVE/MERGE:** strategy metadata/spec/registry into the *single existing* `contracts.py`, with versioned fingerprint and consumer-proof tests. **DELETE:** candidate-only duplicate `strategies.py` and its redundant test module eliminated from PR #87 branch; nothing deleted from `main` or other repos. **REPLACE IMPORTS:** in #87 candidate tests only, all strategy symbols imported from `terminan.contracts`; no legacy `terminan.strategies` import in candidate Python source. **NOT SWITCHED:** Grid strategy plugin/worker callers, Strattester strategy/research clients, Meta paper strategy, staged R4 UI branch entrypoints, persistent experiment ledger, actual Grid/Math producer consumers. Deployment/Windows one-installer/public REST->WS/real-time UI/physical recovery/historical secret scan: NOT VERIFIED.

**Merge readiness:** NO. **Release:** NO_GO.

## Stage 6 — Meta Analyse absorption map (Terminan owner surface)

**Source pinned:** Meta #81 `b49505da42a274f7232fabe5d847c91f7218a0ce`, stacked on Meta #78 `f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1`. Meta has 83 Python modules under `src/meta_analyse` according to its own migration ledger; a whole-module UNUSED/DELETE conclusion is not justified from names alone. Original Meta/Terminan user DBs, settings, source refs and all PR history remain unchanged.

### Exact symbol disposition and live consumer blockers

| Meta source path/symbol | Observed original consumer / behavior | Decision/owner | Replacement state | DELETE gate |
| --- | --- | --- | --- | --- |
| `level_sync.py:signature,owned_id,parse_rows` | `LevelSync.replace/crossed` owns only `meta_analyse:`-prefixed level annotations | MOVE Terminan | Staged as pure `terminan/metascalp_levels.py`, preserving signature SHA256 prefix and parser/owner IDs | Verify persisted notes, physical MetaScalp readback, all old imports and no foreign level removal |
| `level_publish.py:publication_decision,LevelPublication` | LevelSync publication admission | MOVE Terminan | Staged in same pure Terminan module, same reason/limit/verified gate | Physical authenticated connection/instrument map + old/new behavior parity |
| `crossing_quality.py:crossed_prices` + `level_sync.py:LevelSync.crossed` | Reject discontinuous/unqualified price jumps; previously removes owned lines | MERGE Terminan | `crossed_owned_ids` produces read-only candidate IDs only on contiguous exchange executions; **never issues DELETE/POST** | Qualified Grid event continuity, MetaScalp readback, no missed/false crossings and explicit authorization |
| `ports.py:MetaScalp.levels/add_level/remove_level/open_combos` | Independent loopback MetaScalp client; mutation effects | MOVE Terminan UI/control integration | NOT MOVED. Avoid second side-effect client until Unified authn/fencing and Terminan single terminal approved | Effect idempotency, uncertain POST/DELETE reconciliation, consent/permissions and real Windows acceptance |
| `core.py:PaperEngine.on_closed_minute/on_trade` | `runtime.py:Runtime`, `desktop_service.py:configure_paper` | MOVE Terminan strategy engine | Issue #89 only; NOT MOVED to PR #87, because current owner contracts contain metadata, not engine | Same-input entry/exit/PnL fee/slippage parity with Math, persisted results and rollback |
| `desktop.py:Window/main`, `desktop_service.py:DesktopService/snapshot`, `flow_style.py:flow_cell_style`, `flow_diff.py:changed_rows`, `freshness_style.py`, `metascalp_locator.py:find_metascalp` | Qt market/orderflow view, control parameters, MetaScalp discover | MOVE Terminan single UI | Issue #90; **no second Qt app or terminal migrated/deployed yet** | Browser/Windows visual parity, settings and controls migration, no Qt/Bybit process |
| `core.py:price_bucket/Minute.poc/untouched_levels/RollingFlow`, `footprint.py:Footprint.poc/FootprintCell.delta` | `Minute.add`, PaperEngine, footprint analytics | MOVE Math | Math #121 API `market_compute_api.compute_batch` candidate; Meta callers still unchanged | Exact source wheel pin, strict Decimal/zero-price, separate tie modes, event-time parity and real consumer imports |
| `orderflow_metrics.py:calculate`, `tape_velocity.py:TapeVelocity.add`, `wall_tracker.py:WallTracker.observe`, `orderflow_aggregation.py`, `book_summary.py` | AnalysisCoordinator/AnalysisSession, display statistics | MOVE Math (data from Grid) | NOT CUT OVER; retained as Meta evidence | Identical-input event-time/clock gap, unknown-side, threshold, stale-book cases and Math API |
| `market_collector.py:MarketCollector`, `raw_trades.py:RawTradeStream`, `exchange.py:BybitPublic`, `runtime.py:Runtime.receive`, archive/history/store readers | Meta independent Bybit sessions and writes | MERGE Grid | Existing Grid #292 is partial data migration, not full source parity | Grid sole writer and provider, all consumers redirected, full historical continuity and rollback |
| `flow_history_storage.py:read_flow_history`, `orderflow_archive_reader.py:read_orderflow_trades` | Meta read-only historical SQL consumers | MERGE Grid | Meta #81 internal SQL dedup only | Grid dataset/Decimal/readback schema, immutable export, consumer cutover |
| `headless_service.py:PrivateServer/Handler/main`, `pg_cluster_plan.py`, `storage_migrations.py`, `install.ps1` | independent transport/PG preparation/service | MERGE or retire under Unified | NOT CUT OVER; launcher main fenced in Meta #81 only | Verified Unified installer/SCM/PG roles, data restoration, split-brain/SSH, no old running services |
| All Meta tests/evidence/Git refs/user data | historical reproducibility | KEEP | Never delete on current evidence | Independent all-refs security, archive manifest, owner approval |

### Stage 6 code change and boundaries

- `terminan/metascalp_levels.py`: single pure **MetaScalp user-level compatibility adapter**. It is NOT a second MetaScalp client, level computation or terminal. It preserves the old ownership note prefix/24-hex digest and refusal when unknown response layout is encountered. It does not talk to MetaScalp, Bybit, PostgreSQL, filesystem or Unified network.
- `crossed_owned_ids` intentionally strengthens old `LevelSync.crossed` by requiring a *contiguous* explicitly sourced `exchange_execution` observation (per `crossing_quality.py`) and finite positive prices. It returns IDs for review rather than mutating remote levels. This is a **safety refinement**, not a claim of exact behavior parity under legacy unqualified crossing events.
- `tests/test_metascalp_levels.py` adds closed fixtures for original note hashes, owner detection, response parsing, publication denials, gap/source crossing, foreign row preservation, invalid prices and absence of effectful dependencies. No old Meta executable is loaded. Same-input *full* source parity, GUI render parity, persistent state and live MetaScalp effects remain NOT RUN.
- **Used/Unused conclusion:** observed source relationships show used functionality (not safe deletion); unreferenced functionality remains UNKNOWN until #114 dynamic/static full import/entrypoint proof. Therefore **DELETE now: NONE** in source Meta and no actual Meta runtime consumers switched by this PR. Only transient Terminan candidate duplicate registry was removed previously.
- **Retrofit/rollback:** revert Terminan PR #87's Stage6 additions to return to earlier Terminan behavior. Retain Meta #78/#81 intact with all saved level annotations, paper settings and fills; do not execute any Meta LevelSync.replace/crossed against a running terminal without independent operator admission. Historical ID signature must remain stable. No DB migration or user data modification.
- **Retirement #115:** Meta is a candidate for absorption, but **NOT_READY_TO_ARCHIVE/DELETE** until Grid/Math/Terminan/Unified all migrate consumers, matched source/target tests and physical Windows/Bybit/PG/SSH acceptance #116 + full history security + explicit named repository owner approval.

