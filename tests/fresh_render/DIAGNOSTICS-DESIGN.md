# Diagnostic and owned-lifecycle successor — 2026-11-10

Immutable implementation base161ea1e0fc3a3a4cd64783b0e111e1e119e14d71.
Root explicitly ACKed diagnostics and own lifecycle source changes, not PS batching.
Files remain in tests/fresh_render. Renderer, SDK, guard, routing, sandbox and
Root20s/USER10s/1GiB admission are unchanged. No physical rerun by A6.

## Evidence, not a completed RCA

Original Root smoke e203-e reports direct backend exit0/artifact2070B/f499,
frontend retained primary exit73 at own watchdog20s and aggregate failure.
The frontend's own receipt exists: render NOT_RUN, page_requests1/blocked0,
HARNESS_FAILED_DETAILS_WITHHELD; issued browser exit confirmed, fallbackfalse,
guard denied0. Owned-browser/receipt file mtimes are respectively
23:10:47.478Z/23:10:48.228Z; stream files end around23:10:54.289Z. File mtimes
are observations, NOT monotonic phase timing or commit/freshness proof.

The local render failure and later primary-process watchdog death are separate
facts. Source reaches page request handling, but these artifacts cannot identify
whether goto, another awaited operation, policy, network or runtime caused failure.
There is no safe raw error retained. Repeated PS startups are an overhead hypothesis,
not sole-cause RCA. No attribution of all31 Job processes to PowerShell is made.

Source gaps: no explicit close of the connected SDK browser client on failure;
context scoped inside try and unavailable to finally; consumed GO stdin is paused
but not explicitly closed. These are lifecycle gaps, not proof of the actual
retained-handle cause. Exact pinned SDK source shows connect marks
_shouldCloseConnectionOnClose=true; its public browser.close closes that connection
and waits for disconnect. It does NOT establish browser-process exit. Separate
owned BrowserServer.close and actual ChildProcess exit observation remain needed.

## Authorized implementation

1. After matching GO only, boundedly destroy/observe close of OWN stdin before
   importing fixed harness. No extra argv, preloads, pre-GO target import, forced
   process.exit or blanket unref. Parent never sends subsequent commands on this
   single-frame protocol. Failure prevents target import.
2. Fixed phase IDs emit BEGIN/OK/FAIL with monotonic milliseconds since this Node
   process started (same process.uptime origin in bootstrap/harness, NOT UTC). At most
   56 harness events, total<=6144B diagnostic stdout, each<=256B; bootstrap stdin
   and one beforeExit observation keep the complete stream below64 events and
   Root's existing16KiB capture limit. Receipt remains<=64KiB. Overflow is failure.
3. Closed error_name enum, timeout bool, finite known internal error codes and
   exact whitelisted net::ERR_* tokens only. No raw error/message/stack, URLs,
   headers, environment, argv or arbitrary error strings. HTTP status only numeric
   100..599; existing counters retained. Unknown remains UNKNOWN, never guessed.
4. Finally closes actual issued OWN context, connected browser client, BrowserServer
   and HTTP server. No object/JSON permit or PID reopening. Only public SDK APIs;
   client disconnect and browser exit are independently recorded. No explicit SDK
   kill fallback is added. Existing sync guard still denies its internal taskkill.
   Aggregate cleanup<=10s cooperative, each operation<=existing5s, Root watchdog
   remains authoritative. Late/unknown cleanup or diagnostic overflow stays nonPASS.
5. Final mandatory diagnostic intent is RECEIPT_WRITE/BEGIN. Validate telemetry
   before publishing a final receipt; it snapshots ENDED_BEFORE_FINAL_WRITE.
   There are no mandatory diagnostic writes after publication. File existence,
   actual write success and retained primary exit are separately observed; no
   RECEIPT_WRITE/OK is invented before IO completes. Optional natural-idle stdout
   is not receipt commit or a condition manufacturing local render PASS.
6. Natural beforeExit observation is diagnostic only; no process.exit to manufacture
   retirement. Root's retained Popen exit/Job accounting still decide actual success.

Exact copied SDK source semantics evidence (read, never imported/executed by A6):
browserType.js SHAa5c3aa4c7580393175b900c6931ba1c7fc28d65757d46d9bf8b22080475961c2
sets the connected client's close-connection flag (lines124–146); browser.js
SHA17be22b81b9aaed6dd9cb9d7d774007ef1d911db986ce9ee597677f5b3ce3d29
closes that connection and awaits closedPromise (lines141–148). This evidence does
not identify which handles actually remained live in e203-e.

Pure/error/stream and nonexecuting issued-handle doubles only. No SDK import, native
PS/browser/process/Job fixtures or performance benchmark by A6 under this ACK.

## PS batching — DESIGN_PENDING, not implemented

Current static successful-prepare path launches8 PS checks (3 fresh files plus
renderer, each before/after), tooling9, run-root1, owned-PID output1; later output
and final input rereads add more. The reported failure path is consistent with20
calls including final receipt, but actual per-child counts/times are NOT known.

Recommended later option, only if diagnostics justify it: invocation-local bounded
multi-file read phases, never a cross-phase cache or persistent PS broker. Gather
the COMPLETE deduplicated ancestor pathset for the phase, run identical Node and
Windows attribute checks before opening any phase file, retain same per-file
open/fstat/nlink/size/EOF/mtime/ctime/hash checks, then repeat the complete phase
ancestor checks AFTER the LAST read and BEFORE publishing phase bytes. Compare
every ancestor dev/ino before/after; any failure discards the whole phase. This
widens the attribute-check interval and therefore changes freshness semantics;
Root/Integration Owner must explicitly ACK that tradeoff before implementation.

Proposed pathsets: P1 fresh request/envelope/artifact/renderer + all ancestors;
P2 node binary/module/executable/lock/browsers JSON + all ancestors (full521-file
SDK digest/link checks still retained); P3 new run directory before SDK launch;
P4 output root before exclusive writes (unchanged per-write or explicit later ACK);
P5 FINAL fresh3-file re-read, NEW pre/post checks, no P1 cache reuse. No whole-run
approval covers newly created temp/profile/output paths or later input mutations.
No checks, generations, Root admission, hashes or limits may be dropped.

Alternative: keep all per-read checks and first fix diagnostic/lifecycle gaps.
Selected now: this alternative. A long-lived PS process, broad allowlist cache,
skipping checks or increasing budgets is rejected. If Root later requests batching,
its bounded request/response/path count/sequence and failure semantics need their
own review; source-only performance estimates cannot count as physical acceptance.

GO_NO_GO: source implementation authorized for diagnostics/own lifecycle only;
batching DESIGN_PENDING; actual new package/runtime/physical acceptance NO-GO.
