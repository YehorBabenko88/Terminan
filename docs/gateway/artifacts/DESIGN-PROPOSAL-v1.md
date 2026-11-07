# Gateway artifact metadata v1 — PROPOSAL, NOT SHARED API ACK

## Ownership and immutable sources

Terminan implementation base c752dff751d964c57daf3b3afe4987ea3377839b,
tree 8e19a76b13893f5e6d3103fd599f7fcec25644ca.
Owned additive paths only: terminan/gateway_artifacts.js,
tests/gateway_artifacts/**, docs/gateway/artifacts/**,
.github/workflows/gateway-artifacts.yml. Current Sync model remains unchanged.
ROOT-supplied Gateway base6825964bf52375b134c6eb4487808963a0d128ed /
tree2b3988fa4cdd334b6ae63067fdb34987dd0e6840 is a dependency reference,
not an inspected backend or endpoint ACK.

## Design choice

Use a closed metadata-only DTO plus an inert text renderer. An embedded series
format would duplicate producer data semantics and admit fabricated price arrays;
a URL/HTML artifact renderer would introduce retrieval and execution authority.
Neither is included. This proposal supplies no endpoint or authentication design.

Proposed schema identifier: terminan.gateway.artifact-metadata.v1.
Required fields (all objects closed):

- schema_version: exact identifier above.
- experiment_id: bounded opaque identifier, never an authorization credential.
- dataset: {dataset_id, revision}; both bounded opaque references, revision string
  preserves producer representation without Number conversion.
- result_digest: {algorithm: SHA256, hex: lowercase64hex}; advertised digest only,
  not a claim that bytes were fetched or verified.
- instrument: {instrument_id, venue}; producer identifiers, no inferred symbol mapping.
- time: {start_utc, end_utc, as_of_utc}; canonical UTC timestamps; start <= end.
  as_of is producer metadata and never implies live freshness.
- units: [{field, unit}]; unique bounded field names, declared units only;
  no implicit currency conversion or dimensional validation.
- fidelity: {status, limitations}; status UNKNOWN / DECLARED, bounded text list.
- simulation_status: UNKNOWN / RESEARCH_ONLY / PAPER_SIMULATION.
  Real-order execution has no representation.
- provenance: {status: UNATTESTED, producer_id, source_head, evidence_refs};
  source_head lowercase40hex or null, evidence refs opaque IDs only.
- integrity: {status: NOT_VERIFIED}; verification requires actual artifact bytes
  plus an admitted owner verifier, absent in this slice.
- rendering_spec: {kind: METADATA_SUMMARY, artifact_refs}; artifact_refs are unique
  bounded opaque identifiers, no URI, raw HTML, script, templates or data arrays.
- qualification: TEST_ONLY / LOCAL_UNVERIFIED.

Proposed consumer API: parseArtifactMetadata(rawText=null) ->
{status: UNAVAILABLE|UNATTESTED, model:null|detachedFrozenMetadata, error_code}.
renderArtifactMetadata(rootElement,rawText=null) -> same result; textContent only,
no provider argument, IO, URL handling, timers, logging, storage or handlers.
Missing/malformed input clears the prior rendering and returns UNAVAILABLE.
No labels LIVE, authenticated, verified, accepted or operational PASS are emitted.

Proposed limits: 65536 UTF8 bytes; depth8;4096 JSON nodes including keys;
32 members/object;32 units;32 evidence refs;32 artifact refs;16 limitations;
identifiers128 ASCII [A-Za-z0-9._-], text256 characters. Reject decoded duplicate
keys, unknown fields, unsafe numeric values and forbidden URI/HTML fields.
All revision/identifier references are strings. These are local consumer limits,
not backend capacity or retention promises.

## Evidence and input policy

Synthetic executable tests may contain metadata/reference literals only, explicitly
TEST_ONLY. No model-generated prices, observations, calculated returns or fabricated
scientific output. Real artifacts require owner-supplied immutable bytes/digests,
source provenance and admitted backend binding before visualization of their values.
The renderer cannot substantiate content integrity from an advertised digest.

## Dependency ACK matrix

ROOT: composition, ownership/base and final admission; proposal awaiting review.
A2: authenticated artifact metadata/read authorization, expiry/errors and limits:
NONE, no endpoint ACK. A4: actual artifact verification/evidence resolution: NONE.
A7: experiment/dataset/result identity, units/fidelity/simulation mapping: NONE.
No shared field is approved by silence or local test success.

## Next executable step

After local design review: failing Node contract scenarios for closed schema,
limits/duplicates, digest-versus-verification distinction, units/provenance/simulation
labels, malicious HTML/URLs, missing-input reset and zero effects. Implement pure
parser/renderer only in owned new JS. Add isolated TEST_ONLY browser rendering and
source-bound Windows/Ubuntu CI; no production routing or Sync changes.
Runtime integration, production, physical acceptance and real orders remain BLOCKED.

## Direction ACK and series follow-up

ROOT directionACK authorizes this local metadata implementation only. Genuine
computed numerical series are admissible in principle; they are not inherently
fabricated. They require a separate exact owner schema/byte/digest admission before
chart implementation. This v1 does not silently accept series or URLs.
A2 explicitly reports artifact/typed-series readcap NONE; identity API review2 at
unified7575388e822204d135b9791bdae6d609e37b6b3c is proposal only, not chart access.
A4 explicitly reports computed series/results retrieval NONE; PR41f9f2d045 local
objectstore/manifest codecs do not establish scientific provenance or disclosure.
A7 schema/computed-byte request pending. Runtime remains BLOCKED.
