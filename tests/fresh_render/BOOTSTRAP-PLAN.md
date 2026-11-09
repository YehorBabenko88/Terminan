# Direct Node pre-GO bootstrap plan

Root's 2026-11-09 request selects a successor branch from immutable c44bc15.
Only a new fixed bootstrap/test/doc plus the existing harness's `run` export.
No renderer/auth changes. c44bc15 and PR73/74/75 remain immutable.

1. Test the bounded exact GO protocol, prefix/chunk handling, mismatch/oversize,
   EOF/error and fixed5s deadline. Test direct Node READY then EOF with nonexistent
   inputs: no PowerShell, browser, renderer or harness import may precede GO.
2. Implement bootstrap using Node builtins only before GO; exact --no-addons and
   version/ambient guards; nonce is a Root-selected correlation value, not authority.
   Keep a single fixed lazy require('./harness.cjs') AFTER matching GO.
3. Export the same run function from the existing harness without changing its
   renderer, input/transport/sandbox/cleanup logic. Root's private copied tooling
   layout is supported by current dynamic modulePath/executable arguments and pins.
4. Unit/structural tests only; commit, raw-source verification and static review;
   Draft PR successor and exact usage to Root before any physical run.
5. Root additionally requires a fixed nonissuing spawnSync guard before SDK import,
   without SDK file patches. Test original tripwire never executes for taskkill or
   shell; preserve builtin execFileSync fixed PowerShell checks. Record every denied
   attempt and force FAIL_OR_UNCONFIRMED/root own-Job teardown requirement; no
   generic OS security/retained-handle claim. Independent source review before GO.

Root must retain its ORIGINAL native Popen HANDLE, inspect creation/image/token,
assign/read back its NEW owned Job and child non-elevation/membership BEFORE GO.
No PID reopen or authority is performed by this JavaScript bootstrap. Its PID/nonce
cannot attest OS containment. Own-Job pilot limits and parent chain must stay
UNKNOWN until actual Root observations; this is not scheduler worker admission.
