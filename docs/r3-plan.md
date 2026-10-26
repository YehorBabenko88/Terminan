# R3 implementation plan

Base: immutable accepted PR18 a10c092825442262149a29e59ea041c6ef5cacc9. Do not alter source branches.

1. Regression-first contract hardening: row identity, ordered candles, availability lower bound; versioned negative fixtures pinned to unchanged upstream sources.
2. Browser benchmark uses the actual renderer and bounded model; 10k/100k deterministic in-memory updates, 500 updates/frame, no HTTP per event. Report throughput separately from RAF cadence, bounded latency samples, draw quantiles, CPU and heap via Chromium CDP (explicit unavailable elsewhere). No production connections.
3. Run inherited interaction/fault/cancellation/DPR tests and new sustained benchmark, with strict budgets and manifests. Preserve failures.
4. New R3 Windows wrapper retains accepted lifecycle engine, adds benchmark evidence workflow; physical remains pending.
5. Independent source review, exact-head Windows/Linux Python3.11/3.14 Actions and handoff.
