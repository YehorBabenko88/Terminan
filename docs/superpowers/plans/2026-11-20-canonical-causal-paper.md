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
