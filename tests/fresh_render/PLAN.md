# Fresh disposable render harness plan

Root's 2026-11-09 instruction selects a separate test-only package from immutable
22e6e7230d2f66fd22dda648a77910579812bd60. No renderer, auth, PR73/74 or Root file changes.

Use `harness.cjs`, `test_harness.cjs` and this directory's documentation only.
Fresh request/envelope/artifact paths and expected raw SHA256 come from Root's
exclusive absolute test directory. Never fall back to committed fixture inputs.
Validate ordinary single-link files and ancestor identities, reject reparse/link,
cap reads and compare exact artifact bytes to the envelope's canonical result.
Only the pinned existing renderer's public parse/render functions are consumed.

1. Write unit/structural tests for fresh-byte binding, path/link/size refusals,
   fixed route/CSP boundaries, sandbox options, owned cleanup and bounded outputs.
   Observe RED before adding implementation.
2. Add preflight and explicit run CLI. Preflight never imports Playwright or starts
   any server/browser. Run is for Root's separately admitted serialized lane only.
3. Pin Node24.22.1 binary, installed Playwright1.56.1 package tree/lock, Chromium1194
   binary. No install/download. Owned BrowserServer handle supplies PID and cleanup;
   no process enumeration or foreign PID kill. Fixed loopback routes, page request
   allowlist, CSP connect-src none. Remove SDK security-disabling switches.
4. Confine temp/profile/output under a new exclusive run directory. Cap fixed
   screenshot/JSON outputs and render duration; structured receipt records fresh
   raw input hashes, rendered model agreement and confirmed owned process exit.
5. Run only unit/structural tests and syntax checks, review, commit, Draft PR.
   Real browser/physical run NOT_RUN pending Root/A8 isolation admission.

Local tests do not qualify ACL/filesystem adversarial races, hard CPU/RAM/disk
containment, authentication, scientific READ, verified market data or fresh producer
execution. SHA agreement cannot prove when/how the upstream files were produced.
