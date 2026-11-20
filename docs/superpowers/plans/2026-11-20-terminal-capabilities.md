# Terminal capability consolidation implementation plan

> For agentic workers: use executing-plans inline; no delegation.

Goal: preserve unique closed-candle eligibility, ownership reconciliation and external terminal REST transport inside canonical Terminan.
Architecture: analytics/core remains DTO and Math adapter; metascalp_levels remains existing ownership/publication gate. New level_quality supplies bounded fixed-interval completeness reports, level_sync consumes those gates, external_terminal supplies typed injected-client REST methods. No PaperEngine copy, data producer, DB/store, automatic launch or legacy import aliases.
Tech stack: Python3.11+, standard-library Protocol/dataclass/asyncio, existing verified Math SDK fdc5154.
Spec: root task20Nov2026, basef20eef4; authoritative Meta PR82 source b1a4d6a41054f0040a88dc80b585380fb6b4f323.

Constraints: pure fake clients only; no network/native/PG, no actual annotation changes; source-level capability is not release qualification. All destructive reconciliation validates full candidate inputs before effects; uncertain writes never retry automatically. Closure delegates numerical levels to Math, coverage is supplied-input completeness and never source authentication.

Tasks:
- [ ] Add tests/test_terminal_capabilities.py red: missing canonical quality/sync/transport symbols; complete/gap/future/duplicates, typed refusals, owned-only reconciliation, uncertain write reread, concurrency, cancel, read-only retries and malformed terminal state.
- [ ] Add analytics/level_quality.py LevelReport + verified_levels(candles,timeframe,start,end,*,as_of), reuse core.untouched_levels. Fixed M1/H1/D1 only, bounded20k, timezone-aware, exact interval alignment, duplicates refused. Caller source authentication stays separate.
- [ ] Add analytics/level_sync.py LevelSync replace/crossed; reuse metascalp helpers and literal quality gate. Strict bounded IDs/notes/report DTO, staged operation list, stable per-instrument bounded locks. No persistence duplicate or automatic write retry.
- [ ] Add external_terminal.py injected AsyncClient/Response protocols and TerminalClient; fixed localhost discovery ports17845..17855, closed REST methods, no redirects/proxy ambient factory, GET-only bounded retries, cancellation propagates. MetaScalp is actual external vendor protocol name, canonical class TerminalClient.
- [ ] Run reviewed pure tests bothPython; freeze exactsource wheel proof outsidecheckout, DraftstackedPR, independent review. Record exclusions and handoffs.

Review focus: wrong or bool trust markers; invalid later row causing partial deletion; duplicate/foreign ID ambiguities; uncertain POST replay; cancellation swallowed; unbounded locks/response rows; discovery mistaken for authentication.
