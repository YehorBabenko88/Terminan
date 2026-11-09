# PURE experiment-view request/client state

This is preparation authorized after ROOT route/consumer-cap direction ACK.
It has NO fetch, server, identity provider, authenticated response decoder or chart.
A2 result read/A4 committed artifact APIs and the new response codec remain pending.
No existing PR73/gateway files are changed or silently accepted as the new carrier.

Exports TerminanExperimentView / CommonJS:
- VIEW_LIMITS: maximum response2MiB/artifact1MiB/descriptor64KiB/depth12. Owner
  codecs may narrow. Defensive reader budget8192 chunks includes empty chunks;
  this is not native CPU/time/RSS/resource qualification.
- buildExperimentViewRequest(id): exact 1..128 ASCII alnum-first [A-Za-z0-9._-]
  case preserved, no percent/slash/query/body/options/normalization; fixed relative
  same-origin GET, no-store/error-on-redirect/no-referrer, no credentials in JSON.
- checkViewByteLimit(part, Uint8Array): observed actual bytes only, never JSON
  byte_count claims; no payload integrity/authentication/semantic validation.
- createExperimentViewController(root): begin(id), observe(ticket, Response),
  reset(), snapshot(). Private weak UI ticket record+AbortSignal, not a permission.

Begin clears the root before any request construction, aborts previous client read,
and keeps a maximum of one current ticket. Invalid ID also clears/aborts. Reset and
new load do not cancel jobs, refund, retry, release holds or call any backend API.
Unknown/foreign/stale tickets cannot change current state or touch shape-only
response callbacks. Same root returns its existing controller; use a mount owned by
this component, not concurrently by a legacy renderer.

HTTP401/403 clears/discards, other non200 is unavailable. A200 is checked for bounded
header/body bytes, stream depth/framing and read budget, then always quarantined as
UNAVAILABLE/RESPONSE_CODEC_NOT_FROZEN. Its bytes are discarded and not decoded into
scientific data. A200/role-shaped JSON is never evidence of authenticated success.
Depth scanning is a structural guard, not a complete JSON/scientific/schema codec.
No response/token/payload persistence or logs, imported HTML/URLs, callback auth
proofs or generic providers. Actual endpoint errors/auth/disclosure checks remain
ROOT/A2 owned and must be reviewed before any positive follow-up implementation.

## Evidence categories

14 new PURE scenarios RED then GREEN. Extra cancel control already passed (no fake
RED claim); separate stale shape-only response regression was13PASS1FAIL then14PASS.
Local Response/stream fixtures are explicitly untrusted timing/byte controls, not
mock authenticated successes. No model-generated scientific result is displayed.
Run node --test tests/experiment_view/test_pure_client.cjs.

Own raw-source qualifier requires exactHEAD/base22e, only NEW four allocated paths,
all primary Git bytes before/after, no links/extras/Node injection, exact14 IDs and
zero skips. New workflow pins Node22.14.0 Windows/Ubuntu/actions without dependencies;
runner.temp only in step env/artifact input. Local Node24 tests do not qualify22.
Optional browser_pure.cjs uses an about:blank CSP connect-src none page and actual
Chromium DOM/ReadableStream/AbortController with zero HTTP server/network requests;
this is PURE browser evidence, not authenticated browser/endpoint E2E.

All actual mTLS/current READ/issuer/revocation/committed receipt/job-ownership/
scientific payload/chart cases in CURRENT-READ-NEGATIVE-TESTS.md remain NOT_RUN.
No Root server composition/security changes. Public submit DENY. Actual positive
endpoint/visualization remains blocked until exact A2/A4/A7/Root interfaces qualify.
GO_NO_GO: NO-GO.
