# Unified runtime implementation plan

User authorizes architecture selection and autonomous implementation. Base PR60 1bc9bf20d18ea371cdacdd974762bad20edf907d. PR47 and scientific usability already ancestors. No merge or main changes.

Architecture: one process / SavedServer (R4/R2 bounded admission, transport diagnostics and joined workers), explicit dispatcher with all origin/target gates before routing. Six real workspaces mounted in same-origin lazy frames retained across navigation to preserve chart/graph state. Main terminal uses existing explicitly SYNTHETIC R4 visualization. No database auto-connect; Saved sources opt-in. Cache read-only, no worker launched by HTTP. Math engine absent => unavailable.

Alternatives: supervisor/proxy introduces extra listeners and duplicate lifecycle/security; wholesale handler replacement loses session/diagnostics. Neither needed. Shared dispatcher invokes existing handlers directly after gates.

1. Add failing runtime tests for six pages, source-disabled APIs, origin/path gates, session shutdown, cache and transport disconnect. Record baseline full tests.
2. Add unified_server/runner, shell assets; import only infrastructure adapter/page/tests from pinned dashboard source, retain newer levels validation and add missing telemetry hardening. Add provenance ledger.
3. Add strict PS5.1/Python3.12 launcher and exact invocation harness with atomic summary/manifests and bounded graceful stop.
4. Add Node navigation test, Chromium DPR1/1.5/2 E2E (six routes, actual charts, viewport retention, source unavailability, session end). Test cache through existing reliability suite.
5. Run full Python/Node/browser, Windows native15 then600 only if15 PASS, independent review, commit exact HEAD/tree, Draft PR, exact evidence and rollback. Automated results do not substitute human acceptance.
