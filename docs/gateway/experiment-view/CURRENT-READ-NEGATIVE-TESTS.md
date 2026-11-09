# Actual current READ / disclosure revocation test plan

Status: ALL actual endpoint cases NOT_RUN until qualified owner services are wired.
No fake server, JSON roles, mock permit/signature, always-allow callback or local
uncommitted artifact substitutes. Root's real endpoint fixture is required.

## Required fixture provenance

Exact ROOT server/composition HEAD/tree; actual A2 issuer/session/TLS source and
revocation inventory; approved new exact READ tool/resource binding; actual A4
committed artifact receipt/read port + owner-verified scientific bytes; actual
job/experiment ownership service. Client certs/CA/session contexts are disposable,
issuer-created, private to the test; never UI assets/logs. No system trust-store or
physical/network configuration changes. Positive control must first prove this
same endpoint returns the actual committed artifact to its legitimate owner.

## Acceptance cases

| Case | Real action | Required outcome |
| --- | --- | --- |
| Positive current READ | Actual same-issuer session, admitted owner/job/resource and committed receipt | Exact owner artifact/descriptor received, BTC chart/levels/units/provenance/limits rendered; no Native/production claim |
| No certificate | Real TLS request without required client identity | TLS denial/no scientific bytes, not a JSON permission fallback |
| Wrong CA/issuer | Real foreign client or opaque cap from another issuer | Refusal before artifact disclosure |
| Expired session | Owner-issued session actually expires under approved issuer clock semantics | Refusal; UI empty; no cached payload fallback |
| Revoked current READ | Actual A2 revoke operation affects real issuer inventory | No new artifact disclosure; generic bounded owner error; old UI cleared |
| Scope substitution | Use real old manifest/query cap or metadata observation context | New result resource refuses; no privilege upgrade |
| Foreign ownership | Real session requests another owner's experiment/job | Deny without artifact/receipt/existence disclosure beyond approved error contract |
| Uncommitted/mismatched storage | Actual owner store has absent/unstaged/uncommitted/foreign receipt or wrong original binding | Unavailable/denied, never hash-only or local-file success |
| Revoke during retrieval | Real test barrier pauses after actual lookup; owner revokes READ, then releases barrier | Final actual disclosure check denies before response artifact bytes; barrier is timing only, not an authority callback |
| Same issuer, changed binding | Actual session but different job/original request/dataset revision/receipt | Typed owner binding check refuses |
| Malformed scientific data | Actual admitted test fixture produces bounded owner-rejected payload/schema/units/digest | No chart; no partial/cached scientific data |
| Older success after newer denial | Hold real response/hash completion, deny newer read, release old completion | Old completion cannot restore any data; no false LIVE |
| Invalid route forms | Percent/slash/query/body/unicode/oversize identifier sent to real Root route | Reject before service/filesystem resource lookup, no normalization |
| Source unavailable/no quorum | Real owner read port reports uncertainty | Clear view; no publication/absence/retry inference |

Revocation semantics are enforced at the approved current-disclosure boundary; data
already lawfully delivered cannot be retroactively undisclosed. Tests must not
claim otherwise. The UI must drop its in-memory view on denial/reset and reject
stale responses. Exact HTTP/error codes and timings require the Root/A2 contract.

Pure client routing/bounds/state tests may be prepared independently after mapping
review. They do not prove any row above. Actual integration cases stay NOT_RUN when
any owner API is NONE; a nonexistent route or fixture-only browser does not pass.
