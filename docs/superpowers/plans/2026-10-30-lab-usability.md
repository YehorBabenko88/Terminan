# Interactive scientific laboratory — incremental design and plan

Base: PR51 exact 4312d91d4358cbeba368ff997d70d48afb1e09b5. User authorizes immediate implementation without design questions. Existing SVG/JavaScript and Math v2 remain the architecture; no new framework or numerical algorithms.

- [ ] Reproduce Source -> Formula -> Formula in disposable loopback processes on free ports; preserve installed services. Separate automated host observation from a supplied human physical receipt (none located yet).
- [ ] Add bounded undo/redo, duplicate, fit, explicit connection controls and searchable block library. Use Math catalogue methods and pinned knowledge references; empty catalogue remains empty, no fabricated sources. Retain v1 editor documents; knowledge is an additive node kind.
- [ ] Add interactive result viewport (time zoom/pan/reset), UTC ticks, per-output visibility and labels, experiment names and engine trace tables. Only project existing samples, never interpolate or recompute engine metrics.
- [ ] RED/GREEN unit and browser regressions cover catalogue selection, reference binding, multiple branches, recovery, history, chart interactions and engine unavailability. Re-run previous tests.
- [ ] Independent review, separate Draft PR stacked on PR51, exact-head CI snapshots and SHA256 physical acceptance package. No merge/deployment, production DB/trading/Norton/installed ADMINIT changes.

Files: terminan/lab_catalog.js (catalogue validation/presentation definitions); lab_graph.js (additive knowledge nodes); lab_ui.js (editor interactions); lab_results.js (result viewport/traces); math_bridge.py (validated loopback port selection); tests/browser/math_lab.spec.cjs and tests/test_lab_graph.cjs; dedicated workflow and acceptance docs.

Review focus: empty/untrusted catalogue, knowledge definition mutation, history after failed import, stale execution responses, timestamp-aligned chart zoom, test-owned process cleanup/free ports. Catalogue expressions are metadata; AST and all evaluation stay in Math.
