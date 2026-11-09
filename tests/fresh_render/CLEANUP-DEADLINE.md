# F37 — observed monotonic cleanup expiry

Immutable successor from458de55; original18 PURE/mock evidence is retained.
A8/Root source review identified a real predicate gap: relative timers alone do
not reject a synchronously blocking or delayed-event-loop completion that settles
before its overdue timer callback. This is a source finding, NOT actual e RCA or
a demonstrated bypass of Root's external retained-Job watchdog.

One absolute hrtime deadline now covers the entire cleanup invocation, <=10000ms.
Each operation gets min(common deadline, operation start+5000ms). The same monotonic
deadline is checked before scheduling, immediately before invoking an issued
handle, after awaited completion, after telemetry completion and before confirmed.
Equality is expired. No elapsed time is rounded down into an extra allowance.
The existing timer still bounds ordinary asynchronous waits; it is not treated as
a hard event-loop/OS scheduler guarantee.

Any timer/postcompletion/per-operation/common deadline expiry is sticky:
expired:true, expiration_phase fixed ID, and deadline_expired:true when common
deadline was observed. observed_elapsed_ms records the final monotonic interval,
not CPU/UTC/commit authority. Late operations are UNKNOWN; even separately observed
exit facts cannot turn expired cleanup into confirmed. Existing harness classification
therefore stays nonPASS/root_job_teardown_required on these results.

Pure inert tests advance a virtual hrtime clock synchronously without CPU spinning,
native child execution, browser/SDK/PowerShell/Job calls or wall-clock sleeps.
They reproduce late last HTTP completion before timeout callback, per-operation5s
expiry, late telemetry/final confirmation, and the unchanged under-deadline control.
Root20s/USER10s/1GiB, own handles, guard, pins, bootstrap and per-read checks are
unchanged. No additional kill, retry, batching or physical authorization is added.
