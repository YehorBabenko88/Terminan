# Instrument Overlay Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reproducible multi-layer research chart with causal time and trust boundaries.
**Architecture:** Isolated SVG UI, bounded validated imports, unchanged scientific values.
**Tech Stack:** Python stdlib, browser JavaScript/SVG, Playwright Chromium/Firefox.
**Spec:** `docs/superpowers/specs/2026-10-30-instrument-overlay-design.md`

## Global Constraints

No ADMINIT changes, production PostgreSQL, trading, merge or local scientific calculations.
Historical Math #100 and Scientific Math #102 remain distinct immutable pins.

## Review Focus

- Delayed availability and decision/target inversions: no future leakage.
- A correctly rehashed packet with forged trust/units: no trust promotion.
- Incompatible datasets or markets: reject without partial layer commits.
- Corrupt persistence and overlapping async imports: recover without stale evidence.
- Scientific historical output: no invented forecast or OOS semantics.

### Task 1: Producer and P0 regression

- [x] Add executing JS syntax regression; observe failure before correcting P0.
- [x] Confirm producer failure; minimally repair isolated Strattester producer/test syntax.
- [x] Provision exact Grid/Math pins; run real replay/review/export and producer negatives.
- [x] Preserve producer patch/commit and exported receipts in reproducible evidence.

### Task 2: Validated multi-layer consumer

- [x] Write browser acceptance for real export, hash corruption, causal clocks and layers; observe red.
- [x] Implement pure bounded admission in `terminan/history_overlay.js`, including wire SHA256 validation.
- [x] Render model layers, source metadata and producer OOS with publication gating.
- [x] Add explicit Scientific v2.1 display-envelope adapter using real engine outputs and original axes.

### Task 3: View interactions and persistence

- [x] Add interaction/visibility/persistence tests and observe red.
- [x] Implement UTC range/asOf timeline, zoom/pan, crosshair/tooltip and receipt-scoped view settings.
- [x] Test invalid intervals, hidden layers, delayed data and recovery.

### Task 4: Reproducibility and delivery

- [x] Add pinned cross-repository runner and CI; generate real fixtures rather than fabricate forecasts.
- [ ] Obtain Firefox PASS in Linux CI (local Windows spawn UNKNOWN). Python/Node and 9 Chromium E2E pass; screenshot and independent review completed.
- [x] Record limitations and exact evidence, commit/push own branch and create stacked Draft PR.
