# Unified integration readiness and deferred E2E plan

> **For agentic workers:** Use superpowers:executing-plans after all qualification gates pass. This preparation does not authorize changing #59 or its pins.

**Goal:** Prepare Grid -> one Unified Math revision -> Strattester -> Terminan synthetic acceptance without running an unqualified numerical candidate.

**Architecture:** Preserve #59 as control; inspect raw immutable sources and reuse its completed CI artifacts for contract-only probes. A future separately reviewed adapter must preserve the joint request/result and translate metadata, not calculate model values. Joint historical and scientific kernels must come from one qualified commit/tree.

**Tech stack:** Existing Python/SVG UI, real Strattester JointMathClient and CLI, pinned Python/Node executables, disposable synthetic Grid snapshot, Chromium/Firefox.

**Spec:** User request in this chat, 2026-10-30; this plan records unresolved producer/consumer boundaries rather than assuming compatibility.

## Global constraints

- #59 remains `eafdc320a9bdb218d4bbadc3c590f98906932689`, no branch/PR metadata/pin changes.
- Math #105 `03d31f55dc38c43b044666d712524219eb47a51e` is INSPECTED_ONLY, not admitted as a runtime pin. Development may supersede it.
- No final E2E until current exact-head hosted qualification, full coverage and artifacts pass independent verification.
- No working ADMINIT, production PostgreSQL, order service, merge or deployment.
- No local model fitting, forecast generation, numerical transforms or OOS scoring in Terminan.

## Review focus

- Delayed publication `event < available <= decision` must not be relabeled or rejected by a migrated consumer.
- Joint request/receipt, dataset snapshot and source prefix are separate SHA256 identities.
- Scientific scalar comparison metrics are descriptive diagnostics, never Strattester OOS.
- The one-minute target must remain strictly after decision; scientific fixed maps remain historical.
- Missing/foreign-head receipts, native-only proof, skips and altered raw source bytes block qualification.

## Verified identities

| Component | HEAD | Tree |
| --- | --- | --- |
| Terminan #59 | eafdc320a9bdb218d4bbadc3c590f98906932689 | 472332f81fa2344a0118dbfd468b58b7fd641984 |
| Grid #252 | d2dcffb43e520db75936eb97389b66db2f3e1365 | 78db4513bb300dd0cb4d1993a2854ddfba1ee83a |
| Strattester #66 | c951b3f711780affc8e6936f75fe3796d8ef99eb | fa050d024e68cdbdf0f7f0ce4ac48c80990cf54d |
| Math #105 candidate | 03d31f55dc38c43b044666d712524219eb47a51e | 4862b07713f8bc3ef1418feb928a003266616026 |

Strattester's committed `docs/integration/history-reference-pins.json` still names Math #104 `12e688b...`, tree `6ccb701...`, and Terminan `d10d5a0...`; it does not qualify the requested #105/#59 pair. #105 changes no files under `python/`, `src/` or `scripts/history/` relative to #104, but identical kernels do not transfer source qualification to a different HEAD/tree.

## Confirmed release blockers

1. **P1, #66 export loses market and provenance.** Real `review_packet` + `handoff_packet` applied to the already qualified #59 replay result yields `market={identity,source_revision,epoch}` rather than `{venue,market_type,symbol}`. #59 rejects `MARKET_IDENTITY_REQUIRED`. A test-only market correction admits all 60 preserved forecasts, but model is UNKNOWN and OOS is withheld. Export also omits model/model_version, split_receipts and oos_available_at_ms. Missing top-level units alone is compatible because #59 reads source.units. Necessary producer action: preserve these from the original validated result; do not infer symbol from source identity. Separate #67 already demonstrates a compatible legacy repair; #66 does not contain it.
2. **P1, joint output has no display handoff.** `run_history_composition.py` writes `math.history.scientific.result.v1`; #66 review accepts only `strattester.terminan.result.v1.1`, and #59 display accepts only its history/scientific display envelopes. The normal joint graph emits price series plus scalar MAE; scalar ports must go to descriptive diagnostics, not a price line or OOS. Current exporter rejects joint results; its accepted legacy handoff declares `scientific_api=NOT_EXECUTED`. Necessary action: define/implement a bounded joint display adapter with original request, completion receipt, frozen forecasts and timed Strattester OOS, without inventing a new result or recomputing values.
3. **P1 for migration, delayed-publication semantics differ.** Unified Scientific allows both `timestamp <= asOf` and `availableAt <= asOf`, including `availableAt > timestamp`. #59's HTTP bridge and scientific display adapter still require `availableAt <= timestamp`; a contract-only response fixture with event=60000, availability=61000, asOf=61000 is rejected. The joint worker injects source ID `history`, provenance `{sourceId:source.identity,version:source.source_revision,sha256:prefix_digest}`; #59 expects dataset ID/snapshot provenance instead. Migration must retain full historical observations and bind the scientific prefix separately. No guard is loosened while the new engine is unqualified.

No P0 execution or trading defect was confirmed. Legacy engine-pin rejection is an intentional gate, not a bug to remove. At present real data remains blocked.

## API compatibility map

| Boundary | Actual producer | #59 consumer | Required integration |
| --- | --- | --- | --- |
| Grid selection | `select_snapshot(conn,selection,catalog)` -> `grid.history.v1.1` | saved display packet only | retain operator selection/snapshot ID plus dataset ID/fingerprint in evidence sidecar |
| Unified Math | bounded stdio `math.history.scientific.request.v1` with history + source-free graph | HTTP `/v2/graph/execute` or display upload | call via real JointMathClient, not browser or a second Math checkout |
| Source binding | injected `history.value`, exact event/availability, prefix digest | caller source node with full snapshot binding | preserve original joint request and source prefix; compare canonical digests using producer-specific formats |
| Scientific values | series/scalars, arbitrary compatible units, named ports | price-unit series only in overlay | price series as layers, scalar metrics as diagnostics, non-price series explicitly rejected or separate scale (never relabel units) |
| Historical forecast | one-minute target, immutable decision and request_digest | past/future marker classification | preserve value and target; gate by decision, not target alone |
| OOS | Strattester replay test split, cost/funding/cash accounting | explicit publication clock required | producer-owned metrics and conservative recorded publication timestamp; no Math comparison-as-OOS |

## Completed work (do not rerun)

- Downloaded #59 CI run `41082077112`; `consumer-head.txt` matches eafdc32. Browser JSON contains **18 expected tests: 9 Chromium + 9 Firefox, zero unexpected/skipped/flaky, no report errors**. This replaces the old local Firefox spawn limitation as acceptance evidence for the existing #59 only; it does not qualify Unified integration.
- Five new contract probes run in the separate preparation clone, no Math worker, DB or browser launch. They reuse the downloaded qualified legacy replay result, not a new synthetic numerical run. Assertions characterize the blockers above; their PASS means the incompatibilities are reproduced, not that integration passes.

## Deferred tasks and exact acceptance

### 1. Qualification gate (must finish before any final E2E)

- [ ] Refresh PR #105 HEAD/tree and exact run IDs; discard prior-head evidence if source moved. Keep the inspected candidate separate from admitted runtime pins.
- [ ] Verify all four PostgreSQL Node22/24 x PG16/18 cells and two Windows native Node22/24 companion cells, plus `Full CI coverage`, succeeded on one exact HEAD/tree/run/attempt. A Windows job cannot replace a PG cell.
- [ ] Download the six `strict-*` artifacts via GitHub for that run; validate exact file members and all three unique checksum entries, raw TAP/stderr hashes, full inventory, case dispositions and zero fail/skip/todo/cancel using the immutable source's `scripts/ci-platform-coverage.mjs`. Run it from the exact clean checkout with GITHUB_SHA/RUN_ID/RUN_ATTEMPT taken from actual GitHub metadata, not fabricated local values. Independently compare regenerated aggregate and its SHA256 to hosted `full-ci-coverage.json`/SUMS. Do not treat a caller PASS boolean as proof.
- [ ] Verify exact-head history/scientific receipts/artifacts on Linux/Windows; verify Grid #252 and Strattester #66 current artifact receipts too. Raw SQL remains raw bytes. Read source with git cat-file/show, never git archive EOL conversion. Retain downloaded ZIP SHA256, artifact IDs, run URLs, source SHA/tree and tested/committed file hashes.

### 2. Resolve contracts in separate Draft work, then qualify that adapter

- [ ] Fix producer metadata loss (blocker 1) and add real-export regression.
- [ ] Agree the joint display envelope and diagnostic ports (blocker 2). Preserve original joint request/result, math_source manifest, Python/Node SHA256 and completion_receipt. Bind replay OOS and scientific diagnostics separately.
- [ ] Apply delayed source/output availability rules only with the newly qualified engine; independently bind prefix digests to the original Grid row prefix, retain original clocks and full historical observations. Do not fabricate watermark from scientific timestamp. Keep current bounds and false-authority checks.
- [ ] Test each change RED/GREEN in its own Draft branch; #59 and its pin remain immutable. No candidate code is changed in this preparation branch.

### 3. Real synthetic execution after tasks 1-2

- [ ] Use a new directory and new isolated service processes. Clear all TERMINAN_* production source settings. Prefer the existing deterministic 80-row Grid fixture (epoch-zero UTC is explicitly synthetic), with a second 2000-row capacity fixture only if not already qualified for the same exact adapter.
- [ ] Provision a fixture-owned operator snapshot catalog. Select exact venue/type/BTCUSDT/range/revisions through Grid #252; for SQL coverage use only a disposable local fixture database and a dedicated read-only connection. Never production PostgreSQL. Archive `selection.json`, catalog digest/snapshot_id and resulting `grid.json`; verify dataset ID/fingerprint and row revision/source_receipt_hash order. A file fixture alone must not be labeled a PG selection PASS.
- [ ] Freeze train through 1800000, validation through 3000000 and test through 4800000 UTC ms. Select joint decision 2400500 with event 2400000 and publication 2400500; the original horizon is 2460000. An elapsed decision >=2460000 must be rejected. Use a separately hashed delayed dataset, not a silent edit to an existing snapshot.
- [ ] Run #66 `run_history_composition.py` with operator dataset/prefix/runtime pins and the one qualified Math source. Graph: formula `x*2`, fixed affine gain=2 offset=0, comparison (MAE diagnostic), rolling mean, lag, and an overlay/sum to exercise compatible named ports. All values come from Math; do not locally calculate an expected numerical substitute. Preserve original request as `joint-request.json` and returned `joint.json`.
- [ ] Run real chronological Strattester replay with that SAME Math source; two experiments may vary fee policy 5/10bps but must not be called distinct mathematical models when forecasts coincide. Preserve `replay.json`, producer review and completion receipt, then invoke the real corrected exporter CLI. Freeze at least three forecasts at different decisions before OOS labels are released. Archive `handoff.json` and captured normalized admission `admitted.json`. No test-generated forecasts qualify this path.
- [ ] Compare imported values/units/timestamps/availability byte-for-value with original outputs; preserve source and request hashes. OOS equals producer test metrics and is unpublished until test end plus all required availability/decision times. Diagnostic MAE stays DESCRIPTIVE_NOT_OOS even if zero.

### 4. Browser and evidence acceptance

- [ ] Both Chromium and Firefox: at asOf before/at feature publication, before/at forecast decision, before/at target and before/at OOS publication verify no early facts or scores. Past forecast remains a forecast after its target. Scientific lag requires event AND availability <= asOf. Forward mode retains known facts and only future forecast targets.
- [ ] Multi-model colors/legend/visibility, immutable units/source/model metadata, range/zoom/pan/crosshair/tooltip and receipt-scoped saved view. Reject incompatible datasets, delayed clocks outside asOf, corrupt receipts, changed units, nonfinite/oversized inputs and forged authority; clear/new import must supersede asynchronous old results.
- [ ] Collect real browser JSON `browser.json`, screenshots and normalized import captures. New tests must run against the future real adapter; old #59 browser evidence is reused only for unchanged behavior, not declared as new Unified E2E.
- [ ] Manifest `terminan.unified-e2e.v1`: exact sources, qualification run/attempt, aggregate coverage SHA256, selection/snapshot/dataset/prefix/request/completion/display/file hashes and runtime versions. No local PASS grants source authenticity.
- [ ] Run prepared oracle: `python tests/check_unified_e2e_bundle.py --bundle <new-bundle>`. For each single experiment bundle it checks request/provenance equality, replay Python manifest as a subset of joint Python/JS manifest, all frozen forecast fields through admission, captured scientific values/clocks/receipts and both browser reports; it neither launches the pipeline nor independently qualifies Math. Its proposed normalized `diagnostics` field is a test contract to settle in task 2, not a claim the adapter exists now.

## Prepared probe command

```text
python -m unittest tests.unified_readiness_contracts tests.test_unified_bundle_oracle -v
```

Defaults expect sibling `readiness-strattester` and downloaded `readiness-evidence/terminan59`. Override STRATTESTER_UNIFIED_REPO and CONTROL_EVIDENCE explicitly if relocated. Exact source/evidence mismatches error; no silent skip. No broad legacy suite or mathematical E2E is repeated by this command.
