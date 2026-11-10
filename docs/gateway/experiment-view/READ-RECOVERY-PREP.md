# Local UI invalidation/recovery preparation

Source-only successor of8599630. Root02285186 prioritizes LEVEL2 scientific READ
while allowing independent owned offline work, not fake grants/shared API adoption.
This is an OWN UI bookkeeping extension; backend wire error/status mappings remain
NOT_FROZEN and are not implemented here.

invalidate(reason) accepts only READ_UNAVAILABLE, READ_DENIED, SESSION_EXPIRED,
AUTHORITY_STALE, REVISION_STALE, GENERATION_CHANGED, OFFLINE or RECONNECTING.
These are local application signals, NOT actual backend enums or proof of a cause.
Calling any signal stops the current UI read, clears display/experiment identity
and leaves UNAVAILABLE with no scientific payload. Unknown/type/extra-argument
signals clear/abort first, then fail closed. No token, provider or identity is issued.

Recovery requires an explicit new begin(); there is no automatic fetch/retry,
command resend, original rekey, job cancellation, quota/hold release or permission
renewal. All200 responses still quarantine under RESPONSE_CODEC_NOT_FROZEN. Each
root owns independent tickets; invalidation in one window cannot authorize another.
Actual cross-window session invalidation must later use the approved application/
identity lifecycle. Nothing is broadcast or persisted by this module.

Six PURE controls exercise synchronous clear/abort, invalid signals, late bytes,
manual recovery still without a grant, old failure vs newer pending state and
client isolation. They do not prove actual session expiry/RBAC/current revision/
failover/browser behavior. Selector includes only three named PURE files (30IDs),
never browser_pure.cjs. No SDK/browser/native/office fixtures or g rerun.

A2 actual scientific READ/final visibility API remains explicit NONE. Actual A4
controlled reader/mode/receipt/revision and Root endpoint/error/source ACK remain
dependencies. This local extension cannot close them or promote f499/g into
committed/verified market data. Root's existing MissionController owns durable
tasks; no scheduler, ledger, storage or authority is created. StrictD4logical
DISABLED/publicDENY/realordersPROHIBITED, physical lane Root-only. Overall NO-GO.
