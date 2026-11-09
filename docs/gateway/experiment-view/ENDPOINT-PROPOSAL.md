# Authenticated experiment view — proposal before bindings

Status: DESIGN ONLY / actual result-read/storage APIs unavailable / NO-GO.
UI base22e6e7230d2f66fd22dda648a77910579812bd60,
tree1ff5c1f1090fc61170a64f32654a80e51e6c4952. PR73 remains frozen.
ROOT allocated NEW experiment_view.js, tests/experiment_view/**,
docs/gateway/experiment-view/** and experiment-view.yml. This document and the
negative-test plan are the only changes before owner response codec/read admission.

## Responsibilities and current exact seams

ROOT owns the real server route, TLS loading, composition, resource admission,
current disclosure checks and errors. A2 alone owns actual identity/session issuers.
A4 owns real committed scientific artifact/closure/receipt/read semantics. Actual
job/experiment ownership must come from the admitted owner service, not caller JSON.
A6 owns a fixed-route client and validated scientific display; it creates no server,
authentication issuer, role, registry, permission callback or fake success response.

A2 PR53 source31e0351b9f21ac53f3eb47a23bf45d06a58e1fe1 /
tree787be69ece1b533dff284195bbedd34a0ae5196e: gateway_identity SHA84093865...
only admits get_dataset_manifest/query_time_series with bound issuer/store/resource.
It does NOT grant experiment/job/artifact download. Research broker1e9f4bb...
READ_RESEARCH observations are not a scientific payload read grant. New typed
job/result read API is currently NONE. Reuse of old caps is prohibited.
A4 PR50 source3e1b4c7c65174fe5775050449162153213e62a8f /
tree3354fe1f7e130dbaa19a8455b8f21b65f4ec067e: local byte closure/readback only,
committed result receipt/read API NONE; commit/reconcile unavailable and independent
eligible domains not commissioned. PR49 local manifest read is uncommitted.
These are dependency blockers, not missing UI defaults to replace with fixtures.

## Proposed request (route direction ACK only)

GET /api/experiments/{experiment_id}/view, fixed same origin. Proposed identifier
subset: 1..128 ASCII [A-Za-z0-9][A-Za-z0-9._-]*, exact case preserved. This includes
existing fixture.gateway.btc.levels; no slash/backslash/percent/query/fragment,
whitespace/control/unicode or normalization/aliasing. ROOT must ACK exact grammar.
ROOT validates the RAW request target before framework decoding, rejects queries,
non-GET methods and any body/transfer encoding. ID is an opaque service lookup key,
NEVER joined to a filesystem path. No client-selected base URL, headers or provider.

Browser transport must use the actual owner-approved TLS trust/mTLS client/session
path, with real server identity validation; no ignoreHTTPSErrors shortcut. Credentials
stay with the actual A2/ROOT transport, not JSON roles or UI local/sessionStorage.
ROOT selects current READ permission for a NEW exact tool/resource/store binding;
same-issuer ownership, current session/revocation/UTC+monotonic limits and original
job/experiment/artifact ownership are checked using actual owner APIs.
READ authorization is checked before lookup/disclosure and again at the final
response disclosure boundary. Old manifest/query caps, metadata895, a matching hash
or a previous view never authorize this resource. Public submit remains DENY.

## Proposed separate response carrier — NOT a frozen codec

Candidate schema name unified.gateway.experiment-view.v1-review1; exact fields/types
and limits require ROOT/A2/A4/A7 co-ACK. No silent extension of direct result v1,
query-v2 chart or native metadata observation; old parsers stay unchanged.
A success carrier would include exact experiment/job/original-resource identities,
actual A4 committed receipt in its owner-defined codec, exact scientific descriptor
bytes and exact artifact bytes, each with schema/encoding/length/raw digest, and
producer/dataset/algorithm/units/fidelity/limits bindings. Byte parts may use strict
base64 to preserve original preimages; no URLs or paths. Do NOT implement a generic
receipt-shaped object as proof while the actual receipt codec/API is NONE.
No authorized:true/roles/permission flags are accepted as a read grant. Admission
occurs in the actual server/current issuer before bytes are sent, not by body fields.

Proposed consumer ceilings for owner review: complete response<=2MiB, scientific
artifact<=1MiB, descriptor<=64KiB, bounded closed metadata/depth12; exact node/member/
array/string/base64 and scientific decimal/clock limits follow the approved owner
codecs. Check type/size before decode/hash, reject decoded duplicate keys/nonfinite/
unsupported numeric precision/unknown schemas; preserve raw byte/digest identity.
If the real owner payload does not fit, refuse explicitly; never truncate or substitute.

## Scientific presentation

Chart only the actual retrieved owner-validated payload and descriptor with matching
committed receipt/current resource binding. Show BTC observations versus calculated
whole-window levels distinctly, exact price labels and approximation where needed,
dataset identity/revision, algorithm/producer versions, declared clocks, original
statistical units, provenance, quality/fidelity, limitations and finance-unavailable
states. Source knowledge/quality is not promoted by authenticated transport.
Metadata-only native895/f499, cached PR73 fixtures and local closures cannot supply
a chart or units/PnL inference. No calculated values created by the UI/model.
Actual disposable service/mTLS authentication is not native-human/physical approval.

## Client disclosure state

New client stays empty until an admitted actual response passes transport/codec/
resource/payload checks. Pending request replaces the old view. Auth denial,
revocation/expiry/unknown READ, invalid source, missing committed data, malformed or
unsupported response clears all scientific data. No persisted payload/token/logs.
Per-root UI token + AbortController prevent an older response/hash completion from
restoring data after a newer load/denial/reset; token is UI bookkeeping only.
The native UNKNOWN-history clarification remains correct but provides no read grant
or actual payload to this distinct scientific view. No redirects to another origin,
generic URLs, imported HTML/SVG, effect handlers or command dispatch.

## Evidence categories and pending decisions

Actual current owner read/storage/job APIs and exact response/error codecs: PENDING.
Actual TLS/session bootstrap/issuer/CA test pins and server endpoint fixture: PENDING.
Pure request/codec controls, real authenticated endpoint tests, actual browser opening,
Windows CI and native/physical acceptance must be recorded separately. A missing
route/404, mocked authorization or replayed JSON is not an auth/visualization PASS.
No successful endpoint or binding is implemented in this proposal. No production,
native-human, physical, scheduling or storage publication authority is inferred.
