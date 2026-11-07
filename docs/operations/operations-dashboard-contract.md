# Operations Dashboard: exact LOCAL read-only view proposal

STATUS: ROOT_ACKED_ISOLATED_LOCAL_PROTOTYPE. No operational/native/endpoint admission.
Local schema artifact SHA256: e7b90440767e7c33ed8acb2c310a5bd502ce5a727d527488350922ae0c61fcab
This is a UI input DTO, NOT C3 wire, backend endpoint, native authentication,
Node Operation, financial/profile schema, or an authority record.

## Scope and isolation

New worktree work/terminan-operations-dashboard-20261107, branch
feature/terminan-operations-dashboard-20261107, exact Terminan base
10e07ef108d155b9ca2278eec6a8361cb92fa488 / tree
899ab6ec331784aa4e512050c75665cecfa9385e. All4 reserved paths absent at base.
Existing Sync/control-get branches and two WIP files untouched. No main merge.
Reserved files: terminan/operations/dashboard.js; tests/operations/test_dashboard.cjs;
docs/operations/operations-dashboard-contract.md. Optional workflow remains absent
until ROOT approves exact test scope. No other shared source or producer edits.

Chosen approach for approval: detached bounded JSON parser + inert DOM renderer.
Direct Python object/controller callbacks and network/native API binding are
excluded from this first slice because they are not read-only UI projection
contracts. ROOT-owned collection/normalization stays outside this allocation.

## Exact local public UI API (proposal)

UMD export TerminanOperations / CommonJS with exactly:
- parseLocalProjection(rawText = null): returns frozen local result with
  status UNAVAILABLE or REPORTED_ONLY, model=null or detached frozen validated
  projection, errorCode=null or bounded local enum NO_LOCAL_PROJECTION,
  BODY_LIMIT, DUPLICATE_KEY, UNSUPPORTED_SCHEMA, INVALID_PROJECTION.
- renderOperations(rootElement, rawText = null): parses then synchronously replaces
  the target DOM with safe text and disabled controls. Returns the local result.
  No retained prior successful capture after invalid/missing input.

No provider/callback/factory argument, transport handle, fetch, URL, auth header,
credential, IPC, filesystem, journal or controller call. No timer/poll/retry/run/
submit/observe/reconcile/install/update/rollback/approval/dispatch method.
In particular NodeSupervisorV2.run_readonly WRITES receipts and CI.observe WRITES
observations, so the VIEW must never invoke either despite their safe prototype
scope. It does not open/create journals or turn development tasks into NodeOps.
Renderer has no effect handlers; visible action buttons are disabled and cannot
become enabled from input. Existing Tailscale/ADMINIT restrictions unchanged.

## Closed input shape

LOCAL-PROJECTION.schema.PROPOSAL.json is the exact Draft2020-12 companion. Top keys:
schema, data_mode, captured_at_utc, coverage, effects_authorized, source_pins,
sections, operational_axes. All objects closed; every listed field required.
schema=terminan.operations.local-view.v1. data_mode TEST_ONLY or
LOCAL_CAPTURE_UNVERIFIED. effects_authorized=false always.
coverage=BOUNDED_CAPTURE_NOT_COMPLETE_HISTORY. Missing provider is represented by
null input, not a guessed URL or synthetic successful projection.

source_pins has at most5 unique IDs from inventory/supervisor/mission/ci/deployment;
repository, exact head/tree and capture_sha256 are unverified references, not
cryptographic/native admission. Each REPORTED section references an existing pin;
source bytes/producer provenance are ROOT collection obligations. UNAVAILABLE
sections have empty rows and has_more=null. REPORTED rows are bounded captures,
not complete history; has_more is explicit bool/null, never inferred complete.

Section contracts and local meaning:

| Section | Cap | Display / meaning |
|---|---:|---|
| inventory |6| Declared node/role/OS inventory only; supervisor_version=null, installed_release_sha=null, service_state=UNAVAILABLE until a separately acknowledged operational producer revision. Do not map source schema/version to installed software. |
| node_journal |128| Local task/operation/state/release/approval/generation REFERENCE, sequence, result code and local journal chain report. AUTHORIZED/COMPLETED never imply native grant or OS health. effects_authorized=false, physical_acceptance=NOT_RUN. |
| development_tasks |128| Task/mission/owner/repository/base/allowed files, blockers/next actions and separate source/tested/integrated/windows/physical CLAIMS. grants_node_operations=false and native_authority=false. Even claimed physical PASS is prominently unverified development data. |
| ci |64| Exact immutable pin, reported state, runner scalar/state, observed/next timestamps, conclusion, artifact IDs and raw capture digest. data_origin=UNVERIFIED_CAPTURE. CONSUMED or NOT_APPLICABLE are historical/non-authorizing classifications. |
| approvals |128| Public approval/target references and REPORTED_APPROVAL/CONSUMED/NOT_APPLICABLE/UNKNOWN; effective_grant=false. No approval token or authority boolean. |
| lifecycle |32| Recovery/update/rollback/deployment PLAN_ONLY/BLOCKED/UNKNOWN, target release reference and bounded reason; no effect or actual installed outcome. |

All five operational axes are independent UNKNOWN/UNAVAILABLE in this initial
local prototype contract: local_health, authority_freshness, compatibility,
integrity, replication. A local journal_integrity=PASS stays scoped to its receipt
chain row; it does not promote any axis. No HEALTHY/LIVE/current-authority label,
combined green score or Pro/Home/physical qualification is inferred. Separate
future source/mapping ACK is required to widen operational-axis values.

## Additional semantic checks beyond structural schema

Maximum raw input262144 UTF8 bytes; container depth12; nodes including keys16384;
32members/object;128array elements except tighter schema caps; strings per-schema.
Reject duplicate decoded keys before ordinary JSON parse. No unsupported numbers:
all local integer metadata must be exact safe integers0..9007199254740991,
positive where specified. These ordinary JSON integers are NOT profile integers
converted into C3. Monetary/financial fields are not part of this local contract.
UTC capture syntax requires actual valid UTC calendar/time and preserves declared
capture time only; age is not authority freshness or clock qualification.

Source IDs unique and all section references resolve. Inventory node IDs unique.
One captured journal snapshot per node may contain multiple latest-per-task rows.
Both (node_id, task_id) and (node_id, journal_sequence) are unique tuples; the
sequence belongs to that node journal capture, never authority. Mission task
identity is the two-element (mission_id, task_id) tuple, not delimiter concatenation. CI pin identity
is repository/workflow/run/attempt/source/job; duplicate current rows reject.
Allowed-file metadata remains repository-relative (no absolute/drive/traversal).
Reject overlimit input; do not silently truncate/drop rows. Empty or failed source
is UNAVAILABLE; absence of rows does not prove absence of backend work.

CI runner0/null means UNASSIGNED; positive integer means reported ASSIGNED.
Queued API started_at or age does not imply RUNNING/SUCCESS/INFRA_BLOCKED.
Contradictory runner state rejects. Preserve UNKNOWN terminal conflict. The exact
protected Math original pin remains CONSUMED; different fields with that run ID
reject as in the pinned controller. Ordinary CI is NOT_APPLICABLE; no fabricated
authorization or consumption. INFRA_BLOCKED is not inferred by UI. A claimed
SUCCESS remains an unverified CI observation, not hosted CI acceptance.

Render textContent only; no innerHTML, arbitrary href/script, filesystem path,
raw captured logs, stack traces, cookies, tokens, native handles or proof payloads.
Evidence is limited to public ref IDs plus optional SHA256, not credentials or
URLs. ROOT collector must explicitly whitelist public metadata; UI logs no raw
projection or error text. Unknown keys/flags deny rather than declassify secrets.

## Actual producer mapping and missing sources

| Producer pin | Actual existing source | Admissible local projection boundary |
|---|---|---|
| PR38 b6f58f42690966814bae3f723766f15b45c5c077 | NodeTaskJournal snapshot/get and NodeSupervisorV2.inspect output, local operation.v2 intents / journal.v1 receipts | Detached selected public fields only; authority_generation UUID REFERENCE_ONLY; no call to submit/run_readonly/reconcile. Journal-only integrity, UNKNOWN source/freshness/authority. |
| PR40 d22677736dc862c344a54fe9105d336fa02abe83 | MissionController.projection() schema_version1/sequence/tasks/grants_node_operations=false/native_authority=false | Extract development claims, never NodeOps/execution. Fresh pin has marker2/capacity correction; development task projection remains schema_version1. Not native or operational admission. |
| PR39 48e38a2eeea32ddb3836a27871959814843bb6c6 | Already captured sanitized CI OBSERVATION receipt / exact Pin | Read an externally supplied capture; no Controller.observe/create/open or GitHub write/poll/retry by UI. Actual protected runner0 remains UNASSIGNED. |
| ROOT supervisor_deployment.py | Draft42 4cfdc31f63ff32ab251464e89ff1aa6becd471fa / tree e7904c9ffc76971395ab1965067b75f1adbc03aa | Inactive capsule/install/rollback/service PLAN_ONLY; still no installed-release/service fact. |
| ROOT inventory / operational service state | No new exact UI producer/mapping ACK | Inventory claims optional; actual health/version/release/service/compatibility/replication facts UNAVAILABLE. |

All three prototypes share development base49a970270570548e5d4f0c5a440d30e238bb21f1;
this does not make them a shared native wire. Full per-file raw pins and trees are
in ALLOCATION-AND-PRODUCER-PINS.json. No producer import/normalizer implementation
is supplied by this proposal. ROOT must ACK semantic extraction and own the
collector; otherwise only labeled test fixture inputs are available.

## Presentation and verification proposal

Persistent TEST_ONLY fixture banner or LOCAL CAPTURE UNVERIFIED banner; separate
panels for declared inventory/unavailable operational slots, local receipts,
development mission, CI, approval references, recovery/update/rollback plans,
public evidence, and the five independent operational axes. No hidden effect
handlers or enabled control. Tabular data is bounded; no live simulation data.

ROOT approved18 original Node scenario IDs. Independent review added3 identity
regressions: latest task per node capture, delimiter-free mission/task tuple, and
CI pin key-order independence. Actual mandatory inventory is22/zero skip.
Tests cover the parser and a model DOM; actual isolated Chromium TEST_ONLY
missing/fixture/hostile/mobile preview is separate evidence. Source-bound runner
checks all tracked raw Git blobs before/after, exact22TAP IDs and counts, no
unexpected files or ambient Node options/path/cache/coverage, no addons. Workflow
pins Node22.14.0 and immutable actions, Windows/Ubuntu, no npm/dependencies.
No local preview or hosted component check qualifies native/Home/physical use.

ROOT ACK received for this exact local artifact/API/data-vs-fact boundary,
external projection collector ownership, original18scenarios and fourth workflow
path. Only the four reserved files change; discovered regression IDs are recorded. No native bridge is required to
implement this inert view; actual operational facts remain unavailable until
separately supplied and acknowledged. No shared/source/native/office/provider or
physical action, production admission or P0 closure is implied.

## Approved implementation plan

ROOT approved the exact LOCAL DTO/API/extraction boundaries,18scenario IDs and the fourth workflow path. Use superpowers:executing-plans inline.

- [x] Original18 RED then PASS; independent3identity regressions RED18/3 then PASS21.
- [x] Bounded decoded-key parser/schema/semantics, frozen model, inert textContent render.
- [x] Verify22PASS/zero skip and separate isolated TEST_ONLY Chromium stand.
- [x] Add pinned-actions Node-only Windows/Ubuntu workflow with primary Git-blob source bootstrap, ambient Node/addon rejection and before/after complete raw inventory. No npm/dependencies.
- [ ] Independent bounded source review, fix meaningful findings, source-bound receipt and Draft PR; no merge or operational admission.

Workflow tests Node-only behavior; actual visual/browser evidence remains separate. All source/installed/native facts remain unverified/unavailable. Original contract schema SHA e7b90440767e7c33ed8acb2c310a5bd502ce5a727d527488350922ae0c61fcab. Producer pin fulltrees/source hashes are recorded externally; no raw proof/authorization factory.

## Qualification limits

The schema is embedded in dashboard.js because this allocation has no extra runtime
schema file. Only ordinary local integer tokens are accepted; exponent/fraction/
negative metadata tokens are refused before any Number rounding. Original approved
LOCAL schema artifact remains externally pinned; these are conservative local
parser checks, not a C3 conversion or financial profile. No schema success proves
source identity or operational truth. Source guard assumes a controlled isolated
workspace, not protection against a malicious OS/kernel or private-directory owner.

Run component tests: node --no-addons --test tests/operations/test_dashboard.cjs.
Source-bound mode requires a clean immutable commit with only the four approved
additions, raw Git-equal checkout, --no-addons and external evidence directory.
Workflow first compiles primary test-runner bytes from that exact Git commit; a
workspace shadow cannot bootstrap qualification. Child TAP must contain exactly
the22 frozen IDs,21passes,0fail/cancel/skip/todo. Source receipts are LOCAL component
engineering evidence, never provider/native or full release admission.

## Read-only presentation refinement

Tables use readable labels and separate CI run, attempt, job and source columns. Native details are collapsed initially and retain complete row data, source pins and evidence hashes. Development axes always say reported/unverified; they never qualify operational axes. No event handlers, links, new fields or schema changes are introduced.

Current NodeSupervisor source: `840511a8567e8b016733d7dc2566d7890dff39b9`, tree `5529a7fe006f430ec11a72791ecca37bd2e94544`. Compared with historical b6f58f4: local receipt v2 requires immutable cluster_id/node_id/node_incarnation scope; receipt v1/unbound histories reject unchanged. Snapshot/get projections remain reference-only extraction candidates. UI must never construct controllers or journals or call reconciliation. This source comparison is not endpoint, installed-version, enrollment or runtime ACK.
