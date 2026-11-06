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
