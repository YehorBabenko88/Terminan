# Causal paper source execution plan

Base d4bb93436e4184fb3bd031116ae0acd00a2bdeac. Root approved this isolated source stage; no changes to frozen PR102/103 or Root files. One implementer per owner, no new subagent required.

1. [x] Read original cohort and map actual quote/account/strategy/exporter symbols; retain originals until closure.
2. [x] Specify risk-before-decision, newquote-after-latency, sourceepoch/revocation, uncertaincollateral and crossDBcommit semantics.
3. [x] Coordinate canonical market_data.paper_inputs packet market_data.paper-inputs.v2. Micros remain canonical decimal strings on wire; sourcehashes preserved. No legacyacceptance/fallback.
4. [x] Add RED temporal receipt/decision/quote/funding schedule refusal fixtures (5 methods, both runtimes); implement only clock/hash/declaration proof checks. Numeric text remains untrusted until Math validation. No IO or state mutation.
5. [x] Agree Math quote/account/risk/book-tape APIs and quote-book validator; candidate7b2e89b (d88 repair ancestor). No local arithmetic or temporary math helper.
6. [x] Extend the only PaperEngine with atomic quote execution and actual Math metrics/book validation (6 new controller methods both runtimes).
   [ ] Completed causal receipt/journal integration using existing PaperReplayLedger; no parallel simulator/store.
7. [ ] Implement canonical reservationjournal with externally supplied owner identity. Validate all records/replay/digests/budgets; fresh only, no automatic legacyDBadoption. Persist CLOSE_READY before receipt commit and SETTLED only after exactresult verification.
8. [ ] Add crash-boundary purefault injection tests: beforeintent, afterintent, afterreceipt/beforereconciliation; no uncertainrelease/foreignadoption, causalpeak order, concurrentCAS reservations.
9. [ ] Port bounded book-tape history/controller around canonical Math features; preavailability/lookahead/invalidinput leaves history unchanged.
10. [ ] Port causal coordinator using Data packet validator; admission beforefactories/files, mandatoryaudit/publication monotonicity andfailurestop. Preserve16originalbehaviorcases with canonicalowners.
11. [ ] Reviewed pure testsbothPys, no subprocess/os.system/sockets; independentQA; Gitobjectbyteartifactbuild/proof; Draftstackedcandidate+symbol/DBmap. Native qualification NOT_RUN.

Pending owner dependencies are sourcework, not native blockers. No public/runtime authority is granted by this plan or callback fakes.

Data packet consumer now delegates exact Data5bb26e validation, preserves wire microseconds/UNKNOWN qualifiers/hashes, and stages across-packet clocks/epoch/cursor changes atomically (5 actualSDK tests both runtimes). No SQL reader/managed route/provider is assumed.

## Funding domain checkpoint

Every supplied funding event, including events outside the selected holding interval, must pass public Math `paper_quote_funding_valid` before any PaperEngine state change. Pinned SDK: c7f891c2493b27d0a5badaf6ef9e34dff1b6ccc4; wheel SHA256 5160bc7cfac9f81ff6f1ff4452093d7fa4e32228c530ae7924bd2da3aa915892. This closes the reproduced unselected rate/mark acceptance defect; no domain arithmetic is copied into Terminan.

Verification: 107 scoped pure tests passed on Python 3.11 and 3.12 with all child processes, sockets and system calls denied. Includes three invalid future funding cases, unchanged engine-state assertions, actual selected-funding literal, locked-book policy, and cross-packet cursor regressions. Reservation journal, settlement/reconciliation and full causal orchestration remain source work pending; operational data read model and native admission are not qualified.

## Account foundation checkpoint

`causal_replay` supplies canonical v2 request/result codecs by invoking the existing PaperEngine. `causal_account` composes the existing PaperReplayLedger for state and finalized results, exclusively creates a new namespace after policy/current preflight, and requires a separately retained local ownership receipt on reopen. Existing/truncated/foreign/linked/hot namespaces are never adopted or repaired. Reopen and snapshot perform read-only checks without invoking a database constructor. Ownership hashes and file identities do not authenticate market sources or confer production authority.

This checkpoint exposes INITIALIZED_ONLY, with no reservation/settlement entrypoints. Exact financial/risk transitions, causal reservation journal progression, CLOSE_READY intent, cross-database reconciliation and original composed pipeline parity remain pending source work. No actual SQL provider/HTTP/native operation has been qualified.

## Reservation checkpoint

The next isolated descendant implements durable RESERVED/DENIED/UNCERTAIN transitions only. Hash-chained event receipts reuse the existing state PaperReplayLedger table; replay re-evaluates each risk decision with public Math paper_reservation_metrics and paper_account_balances. All collateral/spread/cash/drawdown arithmetic remains in Math. Retrying an exact candidate is idempotent; conflicting candidates are rejected. SOURCE_GAP and other bounded uncertainty reasons retain collateral across reopen. Revocation after INSERT but before commit rolls back exact database bytes. A hash-valid result without a close intent blocks the account without adoption.

Conservative policy relationships from the original controller are mandatory: notional <= maximum reserve <= initial cash; strict nonzero drawdown below one, bounded nonzero spread, latency before both decision windows and bounded hold-plus-exit window. These are input/control admission rules, not duplicated financial formulas.

Scope remains RESERVATIONS_ONLY. Durable opening/closing decisions, entry selection, CLOSE_READY intent, completed result publication and cross-database SETTLED reconciliation are still pending. No original lab pipeline retirement or full behavior-parity claim is made.

## Durable decision and settlement checkpoint

Risk-bound opening decisions, fresh same-epoch post-latency entry quotes, hold-bound closing decisions, CLOSE_READY intents and explicit SETTLED reconciliation now reuse the same event-receipt ledger. Canonical decision source IDs are terminan_paper_risk_decision / terminan_paper_close_decision, binding versioned terminan.paper.*.v2 input hashes. Completed results are produced and later independently recomputed only through the existing PaperEngine. No second simulator or financial evaluator exists.

Cross-database commits remain non-atomic. Missing completed result after durable intent is UNKNOWN_NO_REEXECUTION and retains collateral; a completed result whose acknowledgement failed contributes verified pending PnL to cash, never peak, until a separately timestamped SETTLED event. Reconciliation preserves original admitted_ms and records later settled_at_ms explicitly. A state writer lock serializes publication/admission. Historical risk replay uses only earlier causal SETTLED rows, excluding future profitable results; a literal earlier ETH drawdown denial remains unchanged after later BTC profit.

Representation-only decimal decoding is isolated from ambient Decimal flags before public Math domain predicates. Numeric formulas and exact predicates stay Math-owned. Foreign schemas, noncanonical JSON, hash-valid forged financial results, source gaps, stale entries and conflicting retries fail closed without adoption or repair.

This still does not retire the old lab pipeline: the book_tape_research signal/history controller and final Data-packet-to-decision orchestration need canonical migration and original 16-role composed fixtures. Data operational read model/managed route, protected admission and native crash qualification remain unqualified. No actual user database, network or native process was exercised.

The sole existing PaperReplayLedger.record now explicitly sets synchronous=FULL before BEGIN IMMEDIATE. A synthetic connection deliberately starting with synchronous=OFF reproduces the prior default-dependent publication; the regression verifies FULL is established before the result transaction. This strengthens source durability policy without claiming actual power-loss/native qualification.
