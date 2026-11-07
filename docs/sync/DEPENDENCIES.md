# Integration dependency matrix

All rows PENDING_ACK. Runtime endpoint ACK NOT_RUN. Integration Owner approval required for all interfaces.

| Owner | Required interface | Consumer boundary | Blocking evidence |
|---|---|---|---|
| Integration Owner | Exact Terminan and source HEAD/tree, topology, version registry | No implicit branch composition | Approved pins and schema hashes |
| Agent 2 | Atomic snapshot/read barrier, global event order, resume/error API | Sole control authority | Authenticated endpoint tests including no quorum/generation |
| Agent 2 | Operator provider, RBAC, session revocation/expiry, reauth, command receipts and discovery | No client-derived authority | Forgery/expiry/replay/revision/unknown-outcome tests |
| Agent 4 | Four-dimensional integrity summaries, evidence resolution, committed metadata anchors | No integrity mutation in UI | Domain schema, freshness and evidence ACK |
| Agent 5 | Durable job/node/schedule projection at metadata revision | Closing UI never cancels jobs | Revision schema, durable job and lifecycle acceptance |
| Agent 3 | Instrument version, ingestion progress, watermarks and explicit gaps | Completeness comes from source rules | Versioned schema, progress/evidence limits |
| Agent 7 | Dataset-pinned research/paper results and progress | No fabricated results or real-order submission | Exact dataset roots/result schema |

P0: agreed base, API/auth/order/discovery contracts, source domain schemas, full design approval.
P1: runtime multi-client/failover/relocation/job persistence, Windows, accessibility and visual regression qualification.
P2: presentation tuning and performance optimization after measured correctness.
GO_NO_GO: NO-GO. No deployment, merge or destructive operation authorized by this document.

Update: Integration Owner selected PR68 HEAD7ed3708df53c8850fd11fc8331440bdfee99aa3e and ACKed additive file scope. Agent 2 ACKs fail-closed consumer direction only; actual endpoints unavailable and auth-provider owner pending. Agent 7 ACKs read-only domain consumption only; Sync metadata mapping pending. See README.md for current matrix; original table is initial dependency request, not runtime ACK.

2026-11-07 continuation: Review4 closed model scoped ACK recorded; immutable unified-system publication 360c5cdc9dae88416d69f8765f3dff5ab8828945, tree c8cc05a06cd2c9cfca6317ad06e1af1efefd0050. This is separate from the existing Terminan implementation base. A2 implements new unified_system/control_mux/**; PR31 experimental ABI is not consumed. ROOT owns native Windows operator identity; browser credentials and endpoint attachment remain PENDING exact agreement. Neither schema nor codec admission establishes authority.

Executable browser components c3.js and mux-stream.js are additive, with no default transport or authentication. C3 accepts canonical ASCII text and exposes opaque tokens plus immutable detached values; it never accepts host object graphs and claims no portable Proxy detector. SSE decoder accepts only exact `data: <C3>\n\n`, at most 133128 bytes per record, 2097152 characters per feed and 16 records per feed. These are conservative client limits, not measured service capacity. On malformed/oversize input it closes and discards pending records; a reconnect requires a new decoder. Envelope/schema/domain/epoch/order/freshness checks remain required before applying output. The frozen v1 reducer never receives v3 frames.

Preliminary suite: 84 Node tests (45 original + 39 C3/framing), 4 receipt guards and 4 Chromium tests. The 28 Review4 vectors are pinned by SHA256 c83dd5a0ac22bc9e3d29151774e560b6a7a2fc0879ef7579dbbde166c9565d81. Local Chromium runs on Windows are engineering evidence only; endpoint, physical Windows and multi-PC acceptance remain NOT_RUN / NO-GO.
