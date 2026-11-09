# PURE request/client-state implementation plan

ROOT ACK: exact case-preserving ASCII request grammar1..128; fixed same-origin GET,
clear-before-load, AbortController/stale suppression; maximum caps2MiB response,
1MiB artifact,64KiB descriptor,depth12. Actual carrier/issuer/store APIs NOT frozen.

New module exports frozen limits, buildExperimentViewRequest, checkViewByteLimit,
createExperimentViewController. No fetch/endpoint/provider/auth callbacks or server.
A ticket is only client request+AbortSignal, tracked privately, never a read grant.
States PENDING/UNAVAILABLE only; no scientific payload or authenticated success.
HTTP401/403/non200 discard data; bounded200 is quarantined/unavailable because
RESPONSE_CODEC_NOT_FROZEN. This is explicit preparation, not a permanent production
endpoint or substitute for an owner-authorized successful read path.

Read bounds use observed bytes, not declared JSON sizes; complete headers/body caps,
stream depth/framing and bounded read count. Bytes are discarded, never cached or
parsed as scientific data. Actual future owner codecs may narrow limits and require
an explicit follow-up before rendering. Reset/new load abort only the client read,
never a backend job or native hold. Cross-controller/stale tickets cannot alter view.

TDD:14 PURE scenarios RED then GREEN for routing/options/types, bytecaps, clearing,
abort, denial, unapproved200, streamed limits/depth, stale success/failure, ticket
isolation, zero network/storage/logs and unknown-response payload non-retention.
Synthetic Response objects are timing/byte controls only, NOT fake auth successes.
Then source-bound new workflow (step-level runner.temp only), independent review,
optional real browser PURE DOM/Abort checks without HTTP server. Actual mTLS/READ/
revocation/storage/endpoint E2E remains NOT_RUN. Old PR73/shared code unchanged.
