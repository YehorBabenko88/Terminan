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
