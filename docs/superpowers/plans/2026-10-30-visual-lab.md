# Visual Laboratory Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A working SVG scientific graph editor delegated exclusively to Math.
**Architecture:** Static SVG/JavaScript editor, pure document validation, bounded same-origin Python bridge.
**Tech Stack:** Python stdlib, browser JavaScript, SVG, existing Playwright.
**Spec:** docs/superpowers/specs/2026-10-30-visual-lab-design.md

## Global Constraints
No merge/deployment, ADMINIT changes, Norton changes, trading, production DB access or numerical algorithms in Terminan. Own branch starts at d10d5a0e2f00fcd68e284d2b6e743f61430997c9.

## Review Focus
Stale responses after edits; malicious imports/labels; unit mismatch; upstream authority escalation/malformed responses; disconnected graphs and occupied input ports.

### Task 1: Formula HTTP regression
Files: tests/test_math_formula_http.py, terminan/server.py, terminan/math_bridge.py.
Interface: POST /api/math/formula -> evaluate_formula(bytes), preserving same-origin and limits.
- [x] Write real HTTP tests for success, malformed JSON, size, engine absent, authority refusal, cross-origin.
- [x] Run RED, repair route, run GREEN and full Python suite; commit.

### Task 2: Document and SVG editor
Files: terminan/math_lab.html, terminan/lab_graph.js, tests/test_lab_graph.cjs, tests/browser/math_lab.spec.cjs, playwright.math.config.cjs.
Interface: LabGraph validates bounded documents and builds only the coordinated Math request; UI consumes it without evaluating formulas.
- [x] Write unit/browser tests for free creation, typed mouse/keyboard connections, cycle, relink/delete, drag/zoom/pan, transactional import, stale responses.
- [x] Observe RED, implement document validator and editor, run GREEN. Keep legacy formula/evaluation features accessible; commit.

### Task 3: Engine integration and evidence
Files: bridge/server, tests/test_math_scientific_bridge.py, scripts/math_lab_integration.*, .github/workflows/math-lab.yml, docs/math-lab-contract.md, docs/math-lab-adminit-acceptance.md.
Interface: agreed versioned Math graph request/result; same-origin route, fixed loopback upstream, engine-owned validation.
- [x] Pin agreed Math SHA and contract; add negative bridge and real-engine browser tests before implementation.
- [x] Observe RED, implement forwarding and safe result rendering, run all relevant suites.
- [ ] Publish own Draft PR, run exact-head CI, independently collect run/job/artifact pins and SHA256 evidence; document remaining physical NOT_RUN.
