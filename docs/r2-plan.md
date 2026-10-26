# R2 autonomous synthetic preview — design and plan

Base frozen G0 RC: PR #9, 0ad0f36edce2ac7717c753d35ebe113dc6334fd0.
R2 has its own branch/stacked Draft PR. No commits to the G0 branch.
User authorized autonomous design/implementation; Grid/Strattester availability
is not a dependency. Their immutable SHA/schema files remain contract references.

Approach: pure deterministic Python simulator, stateless bounded replay API and
dedicated synthetic-only server/launcher. Separate browser canvas preview with
explicit SYNTHETIC provenance, historical candles, footprint and offline DOM.
Alternative rejected: wiring synthetic data through real source adapters would
blur provenance and allow accidental DB access. Live-feed integration is excluded.

1. Audit complete G0 source, current refs/Issue #6 and inherited baseline.
2. RED/GREEN deterministic simulator and versioned contract fixtures. Seed,
   symbol/timeframe and replay step fully identify output. Fixed virtual UTC
   clock; no wall-clock randomness/future-bar lookahead. Gap/stale/disconnect/
   reconnect/duplicate/out-of-order schedules exercise the real DOM engine.
3. RED/GREEN isolated HTTP API and runner. Strict request validation, no DB
   dispatch, no exchange or orders, bounded replay/request/concurrency.
4. Browser preview: linked candle/footprint/DOM views; play/pause/seek/scenarios,
   symbol/timeframe, pointer zoom/pan/reset, resize/DPR; abort and generation
   fences; demand-driven single RAF and bounded data/DOM/performance counters.
5. Deterministic Playwright browser regressions (Chromium/Firefox, DPR1/1.5/2),
   negative E2E and stress/leak probes; SHA256 evidence with exact source identity.
6. Windows PS5.1/7 R2 harness, exact-head Windows/Linux Python3.11/3.14 Actions,
   independent review, final test/CI report, physical runbook and rollback to G0.

Verification distinguishes model/hosted/headless evidence from actual physical
browser acceptance. No claims of live L2, historical research execution authority,
real-source interoperability, production readiness or physical PASS.
