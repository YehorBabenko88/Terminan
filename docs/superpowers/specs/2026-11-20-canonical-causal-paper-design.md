# Canonical causal quote paper migration

Approved owner architecture: Terminan owns causal paper state and the only PaperEngine; Math owns every numerical market/risk/account operation; market_data owns observation packet, persisted-source and funding-field validation; Unified owns admission, lifecycle and publication infrastructure. This is source-only work. No network/native/source database action is admitted.

## Exact retained provenance

Unified retained lab_paper_pipeline.py blob ad73f7d6529f83fec8153e5ab882def298295cb9, tests/test_lab_paper_pipeline.py and mandatory scripts/ci_paper_causal.py define sixteen original synthetic composition behaviors. Actual original CI cohort is Grid204897c9f3f6ccaf33ae6d02415b97d0049d7e1e, Stratt25eb939f8a816a80ac7c042ce75ec4d9173cd4ce and Termde89c9be291cf89f389698aa9b43045ecd636447. This differs from Stratt PR90 baseline13998, which contains no PaperAccount.

- Grid book_tape_research.py blobd53b2b23feeb0360b4b599ea44fb6dafcb509027: bounded past-only controller -> Terminan; features/POC/volume/votes -> Math.
- Grid lab_observation_export.py blobdc0e19e4e9b8968e5ea284e60fb5736757bce40d: source request/payload/connection/field-proof export and validation -> market_data (currently unported).
- Stratt paper_account.py blobfe284e7dfe12b4cc00be8cbe020a2503bd5806f9: causal reservation states, ownership, monotonic journal, reconciliation -> Terminan; balances/spread/collateral/risk arithmetic -> Math.
- Stratt quote_paper.py blob77687980026485c9db5cc883f6135978bc72f933: typed receipt/schedule/latency validation -> Terminan; quote metrics/funding -> Math; completed receipt storage -> existing Terminan PaperReplayLedger (no copied PaperLedger/evaluate engine).

## Required state and proof semantics

A risk reservation precedes a durable opening decision. A reference quote already fetched for risk cannot become the entry fill. Entry requires a NEW same-epoch increasing-sequence quote whose event and observed clocks are at least decision+latency. A durable close decision follows the hold interval and entry observation. Closing requires another NEW quote after that decision+latency. Stale/gapped/reconnected/revoked/expired source makes the reservation UNCERTAIN and retains collateral. No synthetic gap price or automatic release.

The canonical account journal is distinct state, not a second financial calculator. Completed results use the existing receipt ledger. Cross-database commit is not atomic: persist CLOSE_READY with exact request before receipt commit; on a later failure retain uncertainty/collateral. Reconciliation may settle only an exact verified receipt bound to a previously recorded request. Foreign completed receipts or changed request identities block the account. Cash realization peak uses causal SETTLED journal order, not caller-backdated admission timestamps. Pending exact completed receipts can be reconciled; missing/corrupt ones cannot release reserves.

All callbacks must return literal True; public source declarations and hashes grant no authenticity. Pipeline imports/factories/files follow admitted current source gate. Missing canonical Data protocol or numeric SDK fails before side effects, without importing old packages. Original account/ledger files are not automatically adopted; no user-data conversion in this stage. Dedicated fresh test-owned databases only.

## Acceptance fixtures before retirement

Preserve all sixteen original behaviors with canonical owners: ten symbols reserve then later quotes settle; missing funding/legacy context refuses; processing delay cannot refresh history/funding; fractional funding units exact; risk processing cannot refresh strategy TTL; reconnect retains collateral; publication failure stops reads/retries; capacity preflight before creation; prelatency quote not reused; revocation before next source read; elapsed run window does not claim qualification; failed provider retains cursor; foreign receipt blocks writer; verified result reaches existing writer and Term reader.

Additional negative fixtures: malformed later event leaves state/DB unchanged; bounded history and finite domain; concurrent reservation CAS cannot overspend; restart after receipt commit before SETTLED reconciles exact result once; uncertainty without exact receipt never releases collateral; replayed/duplicate quote cannot advance; funding-boundary fill ambiguity refuses; single PaperEngine class and single completed receipt store; no active old imports or schemas. No claims of real exchange ordering/completeness or native acceptance.

## Numerical policy

New active schema is canonical Terminan v2 family and Decimal fixed28 HALF_EVEN financial policy unless explicit Math owner contract states otherwise. Original binary64 result bytes remain historical input, not a parity promise. Canonical Math validators and exact threshold predicates must precede state mutation. Numeric helper signatures are coordinated with Math owner; no temporary local formulas.

Status: design/source map only, implementation pending canonical Data packet and Math numeric contracts. Originals remain retained and are not redundant demo code. New branch base d4bb93436e4184fb3bd031116ae0acd00a2bdeac; frozen PR102/103 are not edited by this work.
