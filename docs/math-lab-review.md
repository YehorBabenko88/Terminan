# Independent review and execution record

Plan: docs/superpowers/plans/2026-10-30-visual-lab.md. User approved inline execution without further design gates.

Task 1 complete: formula POST allowlist RED (404) -> GREEN; real local HTTP cases cover allowed request, malformed JSON, body limit, disabled/unavailable engine, cross-origin and authority refusal. Added later: bounded/nonobject upstream responses and a real loopback 302 redirect rejection.

Task 2 complete: native JavaScript/SVG document/editor tests RED -> GREEN; types, cycles, occupied ports, import transactionality, keyboard/pointer editing, method parameter bounds, view controls and free formula chains. Legacy static string-presence tests were replaced by runtime document/script checks and browser behavior; keeping their fixed-four-node assertions would contradict the approved editor.

Task 3 code complete: Codex №1 agreed separate scientific v2 request/result/catalogue contract; Math PR #101 pinned at 972676e4d2e5ee7bc37411c4c7405cb71b3a8095, tree 2f2da077a9c588f7aec3b3d5708ed9157733a15f. Real offline Math browser E2E exercises a two-formula chain plus a parallel method, multiple outputs, overlays and recovery after invalid AST. Hosted CI evidence is collected separately at the final exact HEAD; this document does not assert hosted success.

Independent reviewer reviewed d10d5a0..6784e22 read-only and raised four important findings. All received reproducing regressions and fixes:

1. Imported n1000 broke future node creation: ID allocation is decoupled from viewport placement and clear resets serial; browser regression passes.
2. Plot index misaligned lagged outputs: charts use shared UTC timestamp domain and separate unit lanes; unequal-time regression passes.
3. Response not bound to request: bridge checks node/output/order/trace identities and causality; browser checks normalized canonical request SHA256. Negative response tests pass. Hash consistency is not independent attestation.
4. Reachable formula bridge had unbounded reads/redirects/nonobject crash: all legacy bridge calls now use bounded object reads with no proxy/redirect opener. Real HTTP/nonobject/oversize/302 tests pass.

Ruling: manual source citations remain local versioned unattested hypotheses; engine knowledge execution requires the separately controlled server catalogue, currently empty. This follows direct coordination and prevents manual metadata from becoming a trusted scientific definition. Cost: this PR does not install books into Math.

Ruling: exact-head workflow's inherited stacked-base check now expects the user-specified PR #48 head rather than the older cache-audit base. Existing tests/workflows remain enabled. New Math browser tests use a dedicated config so existing browser evidence gates keep their established scenario sets.

Local verification: 326 Python tests; 5 document tests; 5 Chromium browser cases including real pinned Math. Existing npm test:ui passes. Firefox downloaded with system CA validation, but local Windows launch returned spawn UNKNOWN; no security controls were changed. Hosted Firefox remains a distinct required CI result. Physical ADMINIT: NOT_RUN. No deferred reviewer findings, deployment, merge, trading or DB change.
