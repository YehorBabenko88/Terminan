# R3 browser fail-closed implementation plan

Base: PR20 3ed51d908b80a0fa9fee5d72999ca2184f309bec. Scope: offline synthetic reliability only.

1. Reproduce base PipelineStoppedException -> native0 in PS5.1 and PS7 after lifecycle0 (done). Preserve original LS-5 partial report privately; publish only fixed status/identity counts.
2. RED tests for cancellation/native0, incomplete report statistics, projects/statuses, stale invocation/source, missing artifacts and incomplete aggregate evidence.
3. Keep launcher fail code50 until aggregate verified. Terminate from outer finally, including pipeline cancellation. Isolate every invocation workspace/report; atomic browser bundle + aggregate publication.
4. Require exact three Chromium DPR identities (six in hosted all scope), one expected test/result each, zero skipped/interrupted/unexpected/flaky/errors/retries, current invocation/source provenance. Retain assertions and budgets.
5. Verify lifecycle manifest and browser bundle together; reject lifecycle-only evidence. Bounded privacy-safe failure summary. Native false0 cannot grant PASS.
6. Run Python/Node, deterministic native shell regressions PS5.1/7, real15s browsers; hosted Windows/Linux Python3.11/3.14 exact HEAD. Preserve failures/skips. Gate600 behind successful15s aggregate.
7. Independent code review; own Draft PR, physical15/600 runbook, checksums and rollback with base falsePASS caveat.
