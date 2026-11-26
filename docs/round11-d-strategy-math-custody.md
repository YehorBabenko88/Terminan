# ROUND 11 — D independent strategy / Math source-custody matrix

Workstream: unified-system#154. Source review snapshot 2026-11-26. **Review only**; this document cannot grant strategy execution, paper/live trading, source authenticity, or native DB authorization.

## Exact source pins

- Terminan PR #126: `90eeefa4904012d750e77ffd9b1fec6a226791fa`. Canonical catalog blob `89944ed95e84c5cede148b94f385e715825b36aa`; large-history test blob `08a1e92ad9fb0128ebc0c73a56295a36d4b779ca`.
- Canonical Math SDK PR #141: `9e6acbd9e12a91189f57234828e31640983af553`.
- Strattester **main source tree**: `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea`; scalp hypothesis source `strattester/strategies/builtin/research_scalp.py` blob `47ee2fb1611ee21cb85f8d4f8204f6ec25d6dd2f`; scalp generators `strattester/research/scalp_entries.py` blob `533904ce3b28f5d9d69f5bfc72efda168f6674ee`.
- Meta Analyse F draft PR #86: `902db7e28571e851de09d127a9ebad6f120efecd`; `src/meta_analyse/crossing_service.py` blob `81791e39e22c00adedf311bf5d2896c2603dfaa8`. Historical source `b1a4d6a41054f0040a88dc80b585380fb6b4f323` previously inventoried in `docs/meta-analyse-transfer-inventory.md`.
- Scope warning: Strattester source is **main**, not its every current working PR; Meta is F draft, not automatically equivalent to all historic Meta commits.

## Canonical ownership / acceptance matrix

| Historical source function or class | Historical source | Canonical owner / destination | Source evidence | Outcome / remaining acceptance |
| --- | --- | --- | --- | --- |
| Eight scalp `HypothesisSpec` entries | Strattester `strategies/builtin/research_scalp.py` | Terminan `strategy_catalog.py` | Old eight literal ids; new eight closed descriptors in `tests/test_strategy_catalog.py` | **Descriptor-level transferred**: four callable research generators; four spec-only. IDs differ by explicit canonical map; source generator semantics need differential review. Catalog is NOT an executable strategy grant. |
| `sweep_reclaim_entries` | Strattester `research/scalp_entries.py` | Terminan `strategy_entries.generate_sweep_reclaim_entries` | New catalog binds callable `sweep_reclaim_v2` | Causal/decision-known-at, stop/target, gaps and output event shape must be differential tested. NOT claimed byte-identical. |
| `breakout_retest_volume_entries` | Same | Terminan `strategy_entries.generate_breakout_retest_entries` | New `breakout_retest_v2` generator | Check BOS known-at, first retest, max wait, volume threshold, tie-handling. No declared full semantic equivalence. |
| `volatility_expansion_entries` | Same | Terminan `continuation_strategy.generate_continuation_entries` | New `volatility_continuation_v2` generator | **Known intentional DTO difference:** canonical continuation returns `ResearchSignal`, three peers `ResearchEntry` (documented). Do not mark equal without normalized causal vectors. |
| `poc_reclaim_entries` | Same | Terminan `strategy_entries.generate_profile_reclaim_entries` | New `profile_reclaim_v2` generator | Check POC known-at, optional flow/delta, gaps and absence of synthetic flow. Original missing flow ≠ zero-delta evidence. |
| Four spec-only scalp ideas | Same | Terminan catalog | `level_impulse`, `level_impulse_delta`, `failed_breakout`, `open_interest_delta_impulse` | **Specification preserved only**. No generator and no execution grant; missing OI/delta must not be fabricated. |
| Strategy registration | Strattester `strategies/registry.py` | Terminan catalog | Old `StrategyRegistry` mutable version-keyed; new closed frozen typed catalogue | Different lifecycle and runtime capabilities. Old registry retirement NOT proven; check old consumers and enablement semantics. |
| `CrossingService` | Meta `src/meta_analyse/crossing_service.py` | Terminan `analytics/crossing_service.py` | Existing `tests/test_crossing_service.py` Meta vectors + 200 seeded 60-step walks | **Regression authored** for contiguous/gap/uncertain terminal and protected owned levels; historical local differential stated in inventory. No source-authenticated live feed E2E. |
| Historical Meta `PaperEngine`/Position/PaperFill | Meta `core.py` | Terminan single `paper.py` and ledger | `tests/test_meta_paper_differential.py`, inventory notes D1–D6 | Valid ordered-event vector parity previously established; stricter input policy intentional. No second PaperEngine; full funding/slippage/liquidity equivalence not asserted. |
| Meta level durability/UI | Meta `durable_sync.py`, `desktop_service.py`, `analysis_session.py` | Terminan UI/service with Grid read-only SDK, Unified for service hosting | `docs/meta-analyse-transfer-inventory.md` | **Open**. Do not replace Meta polling with direct Bybit or create own service supervisor. Historic durable sync not proven replaced. |
| Math time/price orderflow, cumulative delta | Strattester research + historical Meta orderflow | Math `market_compute_api.aggregate_orderflow_stream`, Terminan `analytics/orderflow_aggregation.py` DTO only | `STREAM_ABI=math.market.orderflow.stream.v1` and `tests/test_orderflow_large_history.py` | **Owner boundary source-confirmed**. Large-history tests authored for 19,999/20,000/20,001 and 100,000 events, unknown sides, Decimal precision, late events, bucket cap. Fresh exact-head standalone test outcome not separately asserted beyond named CI jobs. |
| Remaining Meta migration scope | Meta original b1a4d6 | Split among Grid / Unified / Math / Terminan | `docs/meta-analyse-transfer-inventory.md`: 231 top-level definitions, 68 AST-identical, 29 same-name differing, 134 absent at historical comparison | This is a **historical snapshot**, not current exhaustiveness or proof of equivalent behavior; requires per-function dynamic parity and dependency closure before deletion. |

## Math streaming acceptance observations

Source at Terminan `terminan/analytics/orderflow_aggregation.py` uses `market_compute_api.aggregate_orderflow_stream`; it does not implement independent bucket arithmetic. Historical large-history tests assert **100,000** events, single-pass generators, 20,001 boundary, delayed cross-bucket events, and exact Decimal cumulative delta. They also assert canonical `MAX_ORDERFLOW_BATCH == 20_000`, and `STREAM_BUCKET_LIMIT` rejection for over 20,000 *distinct buckets*. This is bounded Math streaming, not silent cap inflation. For rigorous acceptance still test chunk permutations, fixture canonicalization, event identity, timestamp monotonicity policy, memory peaks and independently executed exact-head wheel tests; written assertions are not measured runtime proof.

## Current B/C/E interoperability note (outside D ownership)

C `verify_existing_lab_checkpoint` on `32e4f583` validates `symbol` in SQL but **omits `symbol` from its returned receipt**. B `COwnedLabJournal.exact_existing_checkpoint` requires the literal symbol and correctly rejects the C return. C must add exact symbol to return and cross-owner native test; D will not weaken the B guard or patch C. B async sync-SQL event-loop calls and native collector start/revoke remain blocked by B/E/C owner contracts. F's #166 remains the only integration branch.

## Next required D proof

1. Pin exact current Strattester active PR and Meta F archive revisions; produce canonical old→new identifier matrix, real input fixtures, and execution/non-execution differences.
2. Independently differential-run four scalp generators on **identical causal features**: timestamp/known-at, signal side, level, SL/TP, commissions, optional flow, nulls, gaps, reproducibility. Classify `EQUIVALENT`, `INTENTIONAL_DIVERGENCE`, or `BLOCKED` with exact vectors, never by name alone.
3. Normalize output DTO only at Terminan boundary; Math must own all numerical kernels and stream buckets. Preserve source archives until replacement evidence.
4. In E/C/F real Root child+PG18 crash cohort assert old D token+epoch rejected before SQL, new managed chart only `PARTIAL`, no v1 fallback, no paper/live execution.

**Gate: CODE NO_GO / PRODUCTION NO_GO.** No tests executed by authoring this document; no user DB/services/trading, no main merge, no production grant.
