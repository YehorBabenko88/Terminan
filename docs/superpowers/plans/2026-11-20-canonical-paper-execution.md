# Canonical paper execution implementation plan

> For agentic workers: execute task-by-task using the executing-plans workflow. No additional agent is required; existing owners review independently.

Goal: migrate bounded Strattester signal/OHLC execution into the existing PaperEngine while moving numerical kernels to Math.
Architecture: one engine, one registry and existing ledger; typed immutable DTO/source admission plus canonical Math functions. Active identities/schemas are canonical v2; historical bytes are explicit read-only migration input.
Tech stack: Python3.11/3.12 stdlib, canonical Math SDK, SQLite fixture ledger.
Spec: ../specs/2026-11-20-canonical-paper-execution-design.md

Global constraints: no PS/CMD/native services/sockets/user-data writes; no duplicate simulator, no legacy active alias, no disabled tests; all market arithmetic Math. Frozen f20 private client files remain untouched except separately authorized ID consumers.
Review focus: invalid final bar leaves state unchanged; intrabar pre-entry wick cannot grant TP; caller Decimal context cannot change fills; changed retry cannot overwrite a receipt; old journal bytes survive identity migration.

## Task1: inventory and typed source policy
- [x] Record exact source blobs/symbols and concrete canonical owner; mark unported graphs retained.
- [x] Add failing typed signal/bar validation and no-lookahead controller fixtures.
- [x] Implement only DTO/source/time admission in new research module; no execution copy.
- [x] Verify refusal cases with native execution denied.

## Task2: existing PaperEngine numerical delegation
- [x] Pin current hand vectors and invalid-event atomicity tests before implementation.
- [x] Consume the frozen six Math APIs; move local entry/stop/fee/PnL arithmetic and stage event mutations.
- [x] Coordinate Math float helpers; keep policy loops, remove local pure net formula API and migrate consumers.
- [x] Run existing paper/historical vectors plus hostile-context fixtures; commit verified source.

## Task3: canonical identity and historical persistence
- [x] Add failing old-active-ID/schema refusal and historical-byte preservation tests.
- [x] Rename registry/UI/API consumers, version active journal/replay contracts, preserve original tables/records without silent rewriting.
- [x] Add explicit read-only v1 receipt/event export and isolated restore proof; no old active alias.
- [x] Verify restart/changed-retry/disabled-strategy behavior and source backup hashes.

## Task4: signal/OHLC execution and replay
- [x] Add failing long/short market/limit SL/TP/EOD, opening-gap and intrabar conservative/optimistic policy tests.
- [x] Implement PaperEngine.execute_signal using existing Position/PaperFill and Math kernels, all batch preflighted before commit.
- [x] Add bounded run_signal_replay/offline CLI using existing ledger, and restart/conflict/no-lookahead tests.
- [x] Verify reviewed pure paper/receipt/private-client suite on both Python versions (86 tests each).
- [ ] Publish exact SHA/Draft PR and limits.
