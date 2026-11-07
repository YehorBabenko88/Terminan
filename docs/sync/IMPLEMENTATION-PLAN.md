# Terminan Sync v1 implementation plan

Goal: additive fail-closed synchronization consumer and independent UI harness.
Base: 7ed3708df53c8850fd11fc8331440bdfee99aa3e / tree 96963f7e749e73c8c81e7650bdee4f2a0a05923a, Integration Owner approved. Branch feature/terminan-sync-v1-20261106. Only terminan/sync/*, terminan/sync.html, tests/sync/*, docs/sync/* and .github/workflows/terminan-sync.yml. No shared path changes.

Architecture: browser/Node shared pure protocol reducer plus injected read-only transport client. No actual endpoint adapter until exact API ACK. Default client is UNAVAILABLE and never invokes invented routes. UI serves as additive standalone loopback harness, preserves existing runtime unmodified. Production and synthetic evidence are always distinct.

Tech: existing Python stdlib, browser JavaScript, Node built-in test runner, existing Playwright 1.56.1, JSON Schema Draft202012 checks in isolated validation environment.

Spec: DESIGN.md; no auth, consensus or backend replacement. No credential storage, no mutation dispatch. Maximum event 65536 bytes, snapshot 2097152, buffer 256/1048576, freshness 15000ms and reconnect floor 1000ms/6 per minute. Domain interpretation disabled without reviewed validator.

Review focus: stale async snapshot replacing new generation; malformed prototype keys; auth expiry during reconnect; heartbeat falsely extending authority; UI close canceling a job.

## Tasks

1. Protocol and deterministic contract scenarios
- [ ] Write 25 named scenarios plus parsing/freshness boundary tests in tests/sync/test_contract.cjs and fixtures in tests/sync/fixtures.cjs; observe RED before protocol exists.
- [ ] Implement terminan/sync/protocol.js: parseBounded(text,kind), installSnapshot(snapshot,now), applyEvent(view,event,now), freshness(view,now); strict envelope and semantic checks, immutable atomic updates, dataset barrier, dedup/resync. No source-owned domain acceptance unless validator injected.
- [ ] Run node --test tests/sync/test_contract.cjs and schema fixture validation; preserve output; commit scoped changes.

2. Client lifecycle and multi-client continuity
- [ ] Add failing client tests for independently injected adapters, resume cursor, lost response/error handling, expiry, failover/relocation and close without command effects.
- [ ] Implement terminan/sync/client.js SyncClient(adapter,clock) with start, connect, tick, stop, state; async attempt fencing and bounded retry. No mutation API; all controls unavailable.
- [ ] Run Node contract suite. Tests assert real reducer/client behavior with transport-only deterministic doubles.

3. UI and loopback static harness
- [ ] Add browser tests for absent endpoint, disabled controls, separate integrity indicators, keyboard tabs, expired state and deterministic screenshots.
- [ ] Implement terminan/sync.html, terminan/sync/view.js, style.css, serve.py. Existing server/unified_server unmodified. Loopback static files only, strict Host/Origin/paths and no directory listing/API routes.
- [ ] Run Playwright Chromium at desktop/mobile, visually inspect screenshots. Visual result is preliminary UI harness evidence, not six-node acceptance.

4. CI and delivery
- [ ] Add .github/workflows/terminan-sync.yml with Windows/Linux Node tests, schema validation and Windows browser tests; no production endpoints/secrets.
- [ ] Run existing full Python baseline/suite and new tests; report preexisting failures without hiding them. Whole-branch fresh review, meaningful fixes RED/GREEN.
- [ ] Commit exact scope, push feature branch, create Draft PR, record HEAD/tree, attach PR, produce screenshots/results/dependency ACK matrix. No merge/deploy.

Ruling: standalone static harness is additive and temporary until shared route ACK; it creates no competing backend. Synthetic fixtures live only under tests; actual UI starts empty UNAVAILABLE. Main original design baseline is historical only; this plan uses approved PR68.

Execution ledger: independent worktree fallback after managed request stalled; all intended paths additive and approved. TDD RED recorded for 25 protocol cases, 8 lifecycle cases, dataset auth/quorum/snapshot race and buffer regressions. 42 final Node tests green, schema/3 UI checks green. Two reviewer P1 findings and snapshot rejection follow-up fixed. Global suite baseline remains source-environment blocked as documented in README.

A8 follow-up: preserved original audit probe/results outside source tree; F09/F10 regressions RED->GREEN,45totalNode tests/0skip and4receipt guards. Exact-head checkout and source-bound CI artifacts implemented in owned workflow only.
