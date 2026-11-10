# R40-1 benchmark disposal: before-execution unit manifest

2026-11-10. SOURCE PREPARATION ONLY. No test, import, compilation or renderer
execution has occurred in this slice. Root must approve the exact test source,
IDs, tool/runtime/dependency closure and effects before execution. No RED/PASS is
claimed. Production r2_preview.js/r4_preview.js remain byte-unchanged and HELD
until an actual old-source regression and a separately allocated edit phase.

## Immutable base, scope and reviewed finding

Branch feature/preview-benchmark-disposal-20261110, isolated worktree
work/terminan-preview-benchmark-disposal-20261110, exact implementation base
dc810b03c3accf0e6f28fca1d5068f4171bb909d/tree
d5bbb6f73c841ba93ae74354ea72cc0989212d92. Planned later Draft PR stacks on PR82;
no commit/push/PR is authorized by this pre-execution manifest.

Root static review SHA256 f5b859590d93ecc625fe06b93d277ee70f0a412dad8a95d9c638b42bb0173f4f
identifies direct benchmark RAF at r2:196/r4:234, separate from tracked normal
s.raf. Disposal cancels/counts only normal rendering. The benchmark checks
generation/disposal only AFTER its untracked frame arrives. That supports the
P2 hypothesis of pending promise/incorrect metrics in a hidden retained view;
it is not an actual regression result yet.

Allocated source edits now: this NEW document, NEW
tests/test_preview_benchmark_disposal.cjs, and only the existing ops document's
stale 21-pass literal corrected to 22. The latter was statically confirmed against
the actual final workflow/qualifier's 22 IDs / 22 passes. No other file changes.
Old review-base CI failure and historical 45/4, 22 and 30 evidence remain immutable.

## Exact six method IDs (no dynamic expansion)

1. r2_metrics_count_held_benchmark_raf
2. r2_dispose_settles_held_benchmark_without_frame
3. r2_seek_settles_superseded_benchmark_without_frame
4. r4_metrics_count_held_benchmark_raf
5. r4_dispose_settles_held_benchmark_without_frame
6. r4_seek_settles_superseded_benchmark_without_frame

Metrics must account for the one held benchmark RAF. Disposal must reject with
the existing Benchmark cancelled message and remove it without delivering a
frame. Seek must promptly reject the old benchmark while retaining only the new
generation's normal render. A subsequent benchmark must be admitted by the
released local benchmarkRunning lock and cancelled by disposal. This is only
local synthetic workload exclusion, not an execution/admission capability.

The actual old source is expected to fail; no missing module/API is substituted
for the regression. If the harness fails before model/RAF preconditions, classify
that as harness failure and correct/review the source before claiming product RED.

## Actual-code seam and dependency closure

Test builtins: node:test, node:assert/strict, node:fs, node:path, node:vm. No npm,
Playwright, child_process, network, worker_threads, native addon or third-party
module. The Node test runner itself owns finite per-case timeout timers. Default
--test isolation would spawn a child even without a child_process import. The
exact command therefore requires --test-isolation=none: all six cases execute
in the one actual Node process, with no --test-force-exit. The old command/
manifest without this flag is preserved as UNQUALIFIED and is not executable
under this allocation.

Reads are limited to the test file and three exact local production script paths:
terminan/r2_preview.js, terminan/r4_preview.js, terminan/r4_protocol.js. Root's
source receipt must pin their exact baseline bytes and the new test/doc bytes;
later production edits require a new exact source receipt. The authoring
worktree uses CRLF for those three unchanged scripts while Git stores LF. Both
physical and Git-blob SHA256 are frozen separately in the external manifest;
raw-byte-equal execution closure is not yet qualified. Root must select and
seal the exact execution source before approval; no silent normalization occurred. The tests do not
rewrite/replace/extract benchmark, expose closure state, copy an algorithm or
append a test-only export. Actual full script text runs in a VM realm only AFTER
approval. Actual r4_protocol.js supplies R4SessionClient; no fake session class or
positive native/provider/auth callback is substituted.

VM is a seam for trusted reviewed project scripts, not a malicious-code security
boundary. It receives no require/process/module and no production fetch/browser
implementation. Actual rendering executes its existing public API and metrics;
the canvas has hidden zero layout and an inert clearRect only. No visible chart,
browser paint, real frame cadence or benchmark throughput is qualified.

DOM/Event/ResizeObserver doubles are inert. RAF and timeout APIs are manual Maps,
with no host scheduling. One initial normal render is explicitly delivered after
startup. The benchmark frame remains held for the assertion. Each case has a
finite 32-Promise microtask drain, not a real clock sleep or unbounded poll.
Fake RAF queue cap is four, fake response call cap eight. No timer callbacks are
automatically advanced; no actual heartbeat or expiry timer fires.

Closed in-memory fetch function returns SYNTHETIC unit DATA only for:
/api/synthetic/status (R4), /api/session (R4 first capture), and the exact frame/
contracts query with seed17, BTCUSDT,1m,scenario normal and step0/1. All other
routes reject; no URL/socket/HTTP request is issued. It returns ordinary inert
response records and uses no real Response/network transport. R4 receipt schema
is checked by the actual protocol. These fake SYNTHETIC responses are not real
session/authentication, native READ, backend acceptance or production fallback.

## Lifecycle and teardown effects

The test calls actual dispose/seek and observes public metrics and its independent
fake scheduler. Promise rejection handlers are attached immediately. Assertions
about prompt settlement occur before ANY benchmark frame is delivered. After
assertions, test teardown disposes again and delivers any obsolete callback in
the fake queue solely to settle old-source failed cases without retaining a
promise. It then drains finite microtasks and clears fake queues. This fallback
is never used to claim prompt cancellation. No callback/timer survives the owned
test realm. No persistent file, DB, job, native process or authority is created.

Test process output is TAP/assertions only; renderer console is a throwing
tripwire, no input payload/token/log is printed. No stdout/private error relay
or evidence-as-authority logic is added to production. Source receipts/logs must
be external to the worktree and preserved even for RED/harness failure.

## Toolpath and requested future execution boundary

Exact candidate tool: C:/Program Files/nodejs/node.exe, observed file SHA256
d702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5.
Hash was read without launching Node. Version/parents/link/origin/runtime and
ambient NODE_OPTIONS/NODE_PATH/NODE_COMPILE_CACHE/NODE_V8_COVERAGE checks remain
Root execution prerequisites, not satisfied by the hash alone. No PATH/npm use,
dependency installation, interpreter probe or source check/compile was run.

Proposed one bounded old-source command, NOT executed or approved here:

    & 'C:/Program Files/nodejs/node.exe' --no-addons --test --test-isolation=none --test-concurrency=1 --test-reporter=tap tests/test_preview_benchmark_disposal.cjs

Require exact six IDs, zero skip/cancel/todo and original full TAP/stderr/exit
receipt. Per-case timeout is 2s; VM startup deadline is 1s; Root must set a process
wall bound (proposed 15s) and bounded output (proposed 256KiB). No automatic retry,
second test, browser/native fixture, worker, provider send or broad discovery.
Unexpected precondition/dependency/import effects stop this allocation for review.

Next: Root reviews exact source/hash manifest and decides execution allocation.
Only after actual old-source RED may Root allocate the two production JS edits;
then a separately pinned GREEN is required. Full-stack policy and scientific
READ work stay untouched. Overall NO-GO / runtime acceptance NOT_RUN.

## Phase update: Root old-source RED and allocated production source fix

Root executed the exact six cases ONCE at aa9b4e9328382c885ca3cf0cc9b66e6abf1ffe74
from a fresh LF no-hardlink clone, with full raw source maps unchanged before/
after. Fixed Node, --no-addons and --test-isolation=none; one Node process exited
1 in reported 0.125s. All six failed at the intended assertions: two omitted RAF
counts, two pending disposal results, two pending seek results. No bootstrap/
fixture error, timeout or overflow reported. Root original TAP:
C:/Users/LS-5/.codex/terminan-disposal-red-evidence-20261110/node-original.tap,
SHA256 89138c2da7cbf6c39195b87e7b319c105f1f3c4510e52d36ae62c881904a98eb.
A6 read that original TAP and matched its hash; this is Root execution evidence,
ACTUAL_JS_FAKE_DOM_RAF_UNIT_RED, not A6 execution or browser/native/physical proof.
Root's one-run allocation is consumed; no automatic rerun is authorized.

Root then leased source edits ONLY to r2_preview.js, r4_preview.js and this
document on the same branch. Both renderers now retain a private benchmark owner
token and pending frame/rejection record. load/seek, disposal and R4 disconnected
generation invalidation cancel the actual benchmark RAF and reject its awaited
promise with the existing Benchmark cancelled error. Ownership is detached before
settlement. Callback identity checks prevent obsolete callbacks from clearing a
new wait; owner-conditional finally prevents an old benchmark from unlocking or
cancelling its successor. An already delivered frame's continuation checks owner,
generation, identity and disposal before touching the model.

rafPending now counts normal-render plus benchmark RAF (integer zero to two),
instead of omitting the benchmark. Existing public method names, SYNTHETIC scope,
actual r4_protocol.js, request/session logic, 10k/100k accepted workloads, batch/
seed limits, checksum/render algorithm and bounded sample retention stay intact.
No additional transport, timer, source request, provider or authority is added.

All six test bytes remain SHA256
0ad02bc7f756300de21aac34036be27881cc23038a3f6e2500318ebace81d57a.
A6 has NOT executed/imported/compiled the modified scripts or tests. The source
fix is prepared for Root review and a separately allocated ONE post-fix six-case
run after fresh raw-source qualification. No GREEN is claimed. Mandatory existing
browser normal 10k/100k and cancellation cases remain later separate evidence;
six inert unit cases cannot replace them. No push, hosted run, policy edit or
scientific READ change is authorized by this source-fix phase.

## Phase update: exact Root GREEN and additive CI source preparation

Root ran the SAME six CJS bytes once at exact 77fe6dfd85171305930f308f307d1aa2718df2c0
from a fresh LF clone: six PASS, zero skip/cancel/todo, original source maps equal
before/after, one fixed Node process with --test-isolation=none. Original TAP
SHA256 4905dc18ebafcd02d8c8d6b930616552314fa17cc2fac85a8f849ae04617e2d0,
at C:/Users/LS-5/.codex/terminan-disposal-green-evidence-20261110/node-original.tap.
A6 read/rehashed this Root original; no A6 replay. This is local actual-JS/inert
DOM/RAF unit evidence only, not hosted CI or browser/full benchmark/session proof.

The new top-level CJS is not part of Python discovery. Root allocated a separate
additive workflow and qualifier, plus eight pure helper guard controls. An initial
qualifier draft was already authored but unexecuted before the explicit guard-TDD
clarification. Its exact SHA256
23a1c79999bb7cedc630e70e1f4013d27090a1522db377570c60732043d0729a
was preserved externally as UNEXECUTED/HELD, not represented as post-RED work.

Test-only commit 6cbacd1838f112b1e7e8ad5829e10fab1350b8b9 has no qualifier module.
Root allocated ONE A6 prerequisite attempt using a new LF/no-local/no-hardlinks
clone, all 405 raw files equal before/after, exact fixed Python3.12.10 -I-S-B.
Actual eight errors were all FileNotFoundError for that fresh absent helper;
no helper/native/Node/browser execution occurred. This is NEW_FEATURE prerequisite
RED, NOT negative behavior PASS or R40 regression proof. Original stderr SHA256
a638ec5b59174b49e39964387a7c5e76f244684892f4393e427327a845e025e4.
The external controller's initial parser missed CRLF and retained its original
FAILED_OR_UNKNOWN receipt; separate read-only fd028ae8821cfd6caee1a0c6c5e77fcc34f44c33c3f87a6d7fc103986b4761d5
post-parse correlation verifies all eight exact IDs/errors without a rerun.

After Root accepted that boundary, implementation was allocated for:
tests/preview_benchmark_qualification.py and
.github/workflows/preview-benchmark-disposal.yml. The prior pure guard file's
positive TAP case now exercises BOTH LF and CRLF DATA. All original assertions
remain; the eight method IDs are unchanged. The original 2bb5 test bytes remain
immutable at 6cb; the revised DATA extension receives its own new source pin.
No pure test or helper execution has occurred at the new source.

Frozen private helper APIs are ordinary(value,directory=False),
_parse_six_tap(raw:bytes), and _require_node_success(outcome:dict). Pure controls
exercise modeled unsafe-parent metadata before byte/process access, exact six
IDs/result rows/counts/zero-skip/error/fact validation, and rejection of typed
timeout/overflow/cleanup-uncertain evidence. These controls do not execute or prove
actual kill/wait/pipe mechanics or global no-I/O behavior for future helper calls.

The actual qualifier preflights ordinary root/parents/single-link files before
source/tool bytes and Git; requires an exact descendant scope of eight allocated
paths from dc810; verifies every tracked raw blob, no extras, no alternate source
graph and complete pre/post equality. File count comes from the full actual map,
never a hardcoded old 405. The six CJS/production/protocol pins stay fixed.

Source tools: fixed Windows C:/Program Files/Git/bin/git.exe or Linux /usr/bin/git,
no cmd hardlink fallback; setup-python3.12.10 -I-S-B, setup-node24.22.1 x64. Fixed
actions are pinned to immutable revisions, with no pip/npm/browser downloads or
fixture execution in this job. Setup actions run in GitHub's platform envelope;
their runtime processes are not the qualifier's one target Node test process.
Binary hashes/origins and runtime versions are recorded observations, not signed
wheel/binary attestation or host-wide OS containment proof.

The workflow's reviewed primary-source bootstrap checks ordinary metadata first,
then verifies qualifier bytes against primary exact-HEAD Git BEFORE compiling/
loading it. Early/final bootstrap facts and original stdout/stderr/source receipts
are external runner.temp artifacts. The one target Node process uses
--no-addons --test --test-isolation=none --test-concurrency=1 --test-reporter=tap,
plus one fixed externally generated --require preload. That preload checks actual
process.version v24.22.1/x64 and emits one runtime fact in the SAME process; no
extra node --version launch. It is trusted qualifier code, not provider input.

Node execution has a 15s deadline and a combined 256KiB output cap. Immediately
after Popen returns, all thread creation/start/poll/drain work is inside the held
handle's unconditional finally. Every exit attempts held kill as needed, bounded
wait and reader retirement; any exception/timeout/overflow/kill/uncertainty denies
PASS. Cleanup budgets are separate and not a strict real-time/family guarantee.
No assert after Popen can bypass this finalizer. The overall job is ten minutes.

Only this pull_request path cohort is declared; no workflow_dispatch or push
trigger, no old workflow edits, no review-base gate relaxation. Existing mandatory
browser 10k/100k/cancellation evidence remains separately required. Publication,
pure controls and one exact actual helper qualification await Root/independent
source/effect review and a new allocation. No new-head hosted/helper/pure PASS
is transferred from the earlier Root six-case run. Overall runtime NO-GO.
