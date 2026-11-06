# Terminan Sync v1 independent consumer

Status: independent implementation / CONTROL_API_BLOCKED / runtime NO-GO.
Base: PR68 7ed3708df53c8850fd11fc8331440bdfee99aa3e, tree 96963f7e749e73c8c81e7650bdee4f2a0a05923a. Integration Owner approved additive paths; no existing runtime files changed. Earlier main SHA in DESIGN.md is inspection history only.

Run independent static UI: `python terminan/sync/serve.py --port 8896`, then open http://127.0.0.1:8896/sync.html. No API adapter is configured. Requests to absent endpoints remain unavailable. connect-src is none; no credentials/session storage, production fixtures or mutation dispatch. This is an additive preview beside the existing Terminan runtime, not a replacement launcher or integrated control center. Tab navigation is present; domain functionality remains source-blocked.

Run contracts: `node --test tests/sync/test_contract.cjs tests/sync/test_client.cjs`. Schema fixtures: install jsonschema==4.25.1 in an isolated environment then run `python tests/sync/validate_schema.py`. UI/visual checks: `npm ci --ignore-scripts`, `npx --no-install playwright install chromium`, `npx --no-install playwright test -c tests/sync/playwright.config.cjs`.

## Evidence

41 deterministic Node tests pass locally on Windows, including 25 original scenario names and additional dataset/auth/race/queue regressions. All fixtures are synthetic transport inputs; assertions exercise the actual consumer. PC1->LS7 and backend continuation cases model independent clients only, not real relocation/durability or backend RBAC. Client command() always rejects; it cannot qualify a production authorization provider.

Three schemas pass Draft202012 meta-schema validation, positive fixtures and empty/unknown-field rejection. Three Chromium tests pass, including keyboard navigation, no horizontal page overflow, four independent indicators and session redaction. Two screenshot baselines were generated, visually inspected and compared unchanged on a second run. This is narrow preliminary accessibility/visual evidence, not comprehensive WCAG or physical runtime acceptance.

PR68 full baseline before edits: 441 tests, 1 failure, 16 errors, 1 skipped. Missing pinned Grid/Strattester checkouts cause g0_sources and pinned_repositories errors; missing upstream integration.source_guard causes protected_source_startup errors; test_saved_sources.test_catalog_source_hashes fails because pinned checkout is absent. Preserve these as existing environment blockers; full suite is not green.

## Dependency ACK matrix

| Dependency | Status | Evidence/limit |
|---|---|---|
| Integration Owner base/branch/additive ownership | ACK via coordination message | PR68 exact SHA; ownership registry immutable revision still pending |
| Agent 2 consumer direction | ACK_CONSUMER_FAIL_CLOSED_DIRECTION_ONLY | SYNC-AUTHORITY-REVIEW, reviewed design hash af8ac441a1f4aa51a9074f6e790f0ac411135be286cf1a8ceda7673f13734379 |
| Agent 2 endpoints | NOT_AVAILABLE / runtime NOT_RUN | Grid55e74863c3c28bf4cbcb4ded4d3359f98bf93f71/tree9ab7433ff11766d18fb30cd2d50381472e8d6035: proposed Sync routes missing |
| Auth/RBAC/provider owner | PENDING Integration Owner assignment | Agent 2 does not implicitly own human provider; no runtime expiry/reauth qualification |
| Ordering/read barrier/retention/freshness/limits | PROPOSED_ONLY | Heartbeat durability, RBAC filtered continuity and logical revision allocation need producer ACK |
| Agent 4 integrity domain | DESIGN ONLY | Four dimensions remain separate; evidence/domain mapping pending |
| Agent 3 ingestion and Agent 5 jobs | PENDING | Domain schemas and source-bound metadata projection ACK required |
| Agent 7 research/paper | READ_ONLY_DOMAIN_BOUNDARY_ACK | Strattester25eb939f8a816a80ac7c042ce75ec4d9173cd4ce, Meta2c4db055e56e36384a2661d443f9abc7b2331e90 lack agreed Sync generation/metadata bindings; no invented mapping |

## Design qualification after Agent 2 review

The +1 global event sequence including heartbeat is a MODEL_CONTRACT assumption only. A producer must choose durable replayable heartbeat ordering and represent RBAC-filtered positions, or negotiate a new stream version; client code cannot manufacture those guarantees. 5/15-second and 600-second limits are consumer proposal bounds, not measured server promises. A snapshot observes a consistent authority barrier, never proves that no later commit exists. Current-head continuous guarantees are not claimed. Canonical command translation and auth provider remain outside this read-only consumer. No health/status route is treated as a Sync endpoint.

## Risks and remaining work

P0: actual Control API, auth owner/provider, source projection/read barrier/order/retention and exact protocol ACK; immutable ownership registry pin.
P1: full source-enabled baseline, Windows CI, actual two-client/failover/relocation/job continuity, comprehensive accessibility and real integrity evidence acceptance.
P2: integrate the additive page into existing unified navigation after shared-route review, performance/UX tuning.

Windows local harness evidence is not Windows six-node acceptance. Physical fault injection, production deployment, merge, network changes and Tailscale removal are blocked. GO_NO_GO: NO-GO.
