# Query-bound v2 chart: explicit consumer mapping/design diff

STATUS: DESIGN_REVIEW_PENDING; behavior unchanged.
BASE: Terminan8eef1a256081d987ff7c1b4024efe2cb16048680 /
tree4b2d48ff361eb2817b4cac15eaa63e2adeeaa742.
BRANCH: feature/gateway-query-v2-chart-20261107.
Only this new design document changes before ROOT review. Prior27/browser evidence
belongs to8eef, not this proposal or any future v2 behavior.

## Immutable owner boundaries

A7 committed packet1610e149643c1a6817cd739b26fbb2bec4ce2cc2 /
tree00caae1b3e56acbad4018f5e509177382fb42c39; execution source is separately
5b4d9fafbc3ef64454f23e3c48621536b67f42dc/tree92552685dfc3d88b16e3a66610d749109dc1861c.
Research request1227B/fb9284c1751e3cb147c3bc075810d72179befc4fd087ec7174816bb12c04dd27;
artifact1757B/4c6b5b3a07e51dabfbeadd9173d2224c87dfc664f95fe23258ad29d4294d1c82;
descriptor4044B/425673aa56713cba81286026aae2092c6f2b50e35611e43a50b0e720df351198.
Retained upstream request917B/004de0e4d15860dec5d28c179bf3b4e18905e42e61ce23a85f1b28e2633a9c27;
result1810B/f68a558021205e79b2ee61d5b4d636dc13aeefb75521e4ca11c6d28f315d73e5.
Actual computed levels are high102@0 and low99@0; rows are input replay.

Frozen producer schema SHA256:
query-v2-request f4918d49e2755927044bbad2b8226e5df3961767a384ba15b4a3f14d5af8fb36;
query-v2-result d274eec55193939b0cb5aa243d564f06b7b882d4ebad4f22f60ed91e1c599745;
embedded Meta result8a831f84129eb3ba06034ca88e081703d2c07db4da96281d555021f4961a156e.
Consumer schema validation never substitutes for owner semantic validation.

## API diff (proposed local API only)

Add a distinct async export:
renderQueryComputedLevels(root, researchRequestRawText, descriptorRawText,
  artifactRawText, upstreamQueryRequestRawText, upstreamQueryResultRawText).
All five payloads are bounded immutable ASCII UTF8 text from retained owner bytes.
No URL, object graph, provider, callback or generic fetch. Missing any dependency
returns UNAVAILABLE and clears the old view. No effect on backend jobs.
Existing parseArtifactMetadata/renderArtifactMetadata/renderComputedLevels APIs,
v1 schemas and immutable v1 fixtures stay closed and unchanged. V1 rejects v2;
v2 rejects v1. Never strip fields, relabel a v2 descriptor as v1 or silently upgrade.
Share only already validated scalar geometry/inert presentation helpers if useful.

## Explicit mapping and checks

| Source | Consumer binding / display |
| --- | --- |
| Research request bytes | SHA256 equals descriptor.request_raw_sha256; experiment matches descriptor; exact v2 request schema |
| Artifact bytes | byte_count + SHA256 equal descriptor.artifact; existing Meta schema; BYTE_MATCH_ONLY |
| Upstream request bytes | raw SHA256 equals research/descriptor upstream_binding.query_request_sha256; full typed request equals descriptor.upstream_binding.request |
| Upstream result bytes | raw SHA256 equals both bindings.query_result_sha256; echoed request/hash match retained request |
| Result metadata | exact complete result minus rows/cells/request equals descriptor.upstream_binding.result_metadata; unknown fields reject |
| A3 implementation | exact f19f7feee0f63da34a20607a8cae59191180aa7c reference; input pin alone is not source admission |
| A4 identity | upstream dataset UUID + revision7, instrument/version, schema/profile hashes, manifest revision/hash, event cut and knowledge cut shown separately |
| Meta identity | content digest + request digest; provenance.dataset_revision remains UNAVAILABLE_A4_BINDING_PENDING; never copy upstream revision7 here |
| Experiment | caller declaration/revision only; no job/attempt/registry authority |
| Input mapping | one PRESENT cell per closed contiguous minute, exact seven columns; canonical integral strings for ALL six numeric columns including retained turnover, <=1e15; OHLC positive/consistent |
| Computation payload | upstream timestamp/OHLC/volume equal research Meta payload and artifact replay rows; turnover retained upstream only, no invented Meta field |
| Source/clocks | source.raw_sha256 equals upstream result hash, source_revision is A3 pin; end<=event_cut<=retrieval<=decision<=asof<=analysis; artifact/descriptor clocks agree |
| Derived levels | positive finite exact price/source-row correspondence; whole-window results, not signals known at source_start; plotting precision/collapse refusal retained |

Preflight ALL five inputs for exact string type/size before hashing or decoding:
research128KiB, descriptor64KiB, artifact1MiB, upstream request16KiB, result1MiB.
Then strict bounded duplicate-free decoding and exact closed schemas. Existing
numeric lexeme loss refusal applies. Keep depth12/nodes32768/members64/rows256/
levels512; per-field/string/array bounds follow pinned schemas. All hash agreement
is local byte agreement, never producer authentication/publication/authority.
Hash awaits use one per-root UI token shared with both prior rendering APIs;
older success/failure cannot overwrite newer v1/v2/metadata/reset. Check token after
every await. No authority/generation semantics; bounded WeakMap entry per root.

## Display delta

Add an upstream lineage block and native collapsed complete raw dependencies.
Always separate SYNTHETIC_SESSION_AUTHENTICATED_ONLY from native_authenticated=false.
Display provider_coverage/gaps UNKNOWN, publication/registry/source_completeness
UNPROVEN, integrity LOCAL_HASH_MATCHED_NOT_REPLICA_VERIFIED, committed_revision null.
No aggregate green indicator or upgrade to LIVE/PIT/provider completeness.
Keep TEST_ONLY_SYNTHETIC/UNATTESTED, unknown quality, synthetic unmeasured fidelity,
NO_ORDERS_NO_LEDGER_NO_EXECUTION_SIGNALS and null/unavailable finance explicit.
Use the v2 packet's source/receipt history, not v1 historical6360 cancellation text.
No A7 callable/job/commit/publication admission from displaying a receipt.
SVG scatter + exact accessible table/input replay use existing local design; no
raw HTML/imported SVG/links/effect handlers. Full upstream raw text is textContent
in native details, not UI logs. No secrets/tokens accepted or manufactured.

## Test and delivery delta after scoped ROOT design ACK

Copy only exact committed1610 fixture/schema bytes into a separate v2 fixture dir.
RED scenarios: two actual computed markers/exact labels; all five raw joins;
lineage/metadata promotion mismatch; upstream gaps/missing/duplicates/order;
all-six-column decimal refusal; stale hash completion against v1/v2/reset;
unsupported numeric/time/geometry; missing dependencies; v1/v2 mutual rejection;
no IO/markup/effects. Extend mandatory inventory/owned CI explicitly, preserving
original27 scenario IDs. New exact-source Node/browser/visual evidence is required.
Update existing owned workflow for this branch, no shared workflow changes.

Only terminan/gateway_artifacts.js, tests/gateway_artifacts/**,
docs/gateway/artifacts/** and .github/workflows/gateway-artifacts.yml may change.
No retrieval/auth/job/storage/Sync effects. Local checks, actual upstream read,
source qualification, hosted CI and physical/runtime acceptance remain distinct.
Current runtime/production/physical/real orders: NO-GO.
