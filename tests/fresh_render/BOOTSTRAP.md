# Root-supervised direct Node gate

Successor of immutable c44bc15/PR75. Adds bootstrap, its unit tests/docs, the same
harness's `run` export and Root-requested fixed nonissuing spawnSync guard with
fail-closed cleanup classification. Renderer/auth logic remains unchanged.
This is prepared source, NOT physical/runtime acceptance.

Root launches the NORMAL direct Node executable, without shell, flags beyond
`--no-addons`, preloads or environment injection. Example argument vector (native
canonical absolute paths selected by Root, not typed by a UI operator):

```text
<pinned-private-node.exe> --no-addons <private-package>/tests/fresh_render/bootstrap.cjs
<32-lowercase-hex-nonce> <testRoot> <request> <envelope> <artifact>
<requestSHA256> <envelopeSHA256> <artifactSHA256>
<private-package>/node_modules/@playwright/test <private-canonical-headless.exe>
```

All ten bootstrap args are nonempty strings<=2048 characters; combined<=12288.
Three digests are64 lowercase hex. Nonce is32 lowercase hex. It is correlation,
NOT a permit, identity, Root role, Job grant, kernel-handle proof or auth token.
Root chooses it before launch. No arbitrary module/script/callback argument exists.
The only post-GO code target is the sibling committed harness's SAME `run` function.

Before GO the sole import is builtin `node:buffer`. No harness/renderer/SDK import,
file/path inspection, PowerShell, HTTP listener or child process is started. Node
version24.22.1, exact process.execArgv `['--no-addons']` and ambient injection
variables are checked first. Root must ALSO reject injected Node options BEFORE
creating the interpreter: JavaScript checks cannot undo an already executed preload.

Ready stdout is one JSON line<=128B, exactly `{ "pid": <this-process-id>,
"nonce": <Root-selected-value> }` (actual JSON is compact). Parent must retain the
ORIGINAL native Popen HANDLE and validate image/hash/creation identity/nonadmin
token, attach THIS same process to its NEW owned Job, and read back expected
membership/resource fields/child non-elevation before releasing the gate. No PID
reopen is provided or required by bootstrap; pid is reporting only. Verify that
Job assignment itself is race-free using the retained HANDLE before GO.

Parent writes ONLY ASCII `GO <same-nonce>\n`, and flushes. No CRLF, JSON, extra
command, arbitrary script, mismatched nonce or trailing bytes in the command.
Input buffer<=1024B; silent parent times out after fixed5000ms; pre-GO EOF, close,
stream error or malformed/oversize input exits1 with fixed BOOTSTRAP_REFUSED.
No automatic retry or weak-security fallback. The supervisor should fail if
assignment cannot be established within this window. After matching GO, stdin is
paused; Root owns post-GO parent-failure/Job lifetime/watchdog policy.

The gate is not OS containment. No live Job/elevation/membership assertion is
made by JavaScript. Until Root performs/readbacks the actual admission, Job
ceilings, current resource fields and parent chain remain UNKNOWN. Hard scheduler
worker CPU/RAM containment, user worker admission, authentication and scientific
READ stay NOT_QUALIFIED/NOT_RUN. Sending GO does not upgrade any of those states.

## Private copied dependency package

Root may COPY (ordinary single-link files, no reparse) the pinned Node executable,
browser directory and521-file closure of @playwright/test, playwright and
playwright-core, preserving `<package>/node_modules/<package-name>` and the exact
ee92d25c... lock at `<package>/package-lock.json`. Pass the COPIED absolute module
and executable paths. Nothing in runtime validator hardcodes the original install
location: package tree digests use paths relative to passed node_modules. Node,
browser, lock, browsers.json and complete selected package tree SHA pins must all
pass unchanged. Root must separately validate extra browser directory resources
and exclusive private package custody; A6 currently pins the selected executable,
not a signed whole-browser installation. No npm or download is performed.

Keep testRoot outside source/package checkout and dedicated to this pilot. The
fixed existing harness still confines TEMP/TMP/TMPDIR, generated profile and
evidence below its new testRoot run directory. ChromiumSandbox remains true;
launch option flags are unchanged. Source is committed first; no edits during run.

## Exact SDK cleanup boundary

The harness retains SDK BrowserServer.process()/close()/kill() handles; it never
accepts user-supplied PIDs or performs process enumeration. However, STATIC
inspection of the pinned Playwright1.56.1 processLauncher.js shows that on Windows
its internal forced cleanup can call `taskkill /pid <its-recorded-child> /T /F`
via spawnSync(shell:true), including close failure or kill fallback. The old
README's no-taskkill wording describes A6 harness code, NOT all SDK internals.
SDK Windows launch uses detached:false and requests no breakaway flag.

The new committed sync_spawn_guard.cjs is installed by run AFTER bootstrap GO and
BEFORE preparing inputs or importing ANY SDK. It refuses already cached SDKs,
replaces the builtin module's exported spawnSync with a nonissuing throw/counter,
makes that property nonwritable/nonconfigurable and syncs builtin ESM exports.
Original spawnSync is never called by this guard; taskkill/shell args are never
executed or logged. A fixed one-time stderr notice reports a denial. No SDK files
are edited and521-file dependency digest3a122fd6... remains unchanged. The pinned
actual callsite processLauncher.js SHA256 is
da9cb41cc1605fca1e26c6a6212f01ef0af0125a9e97eecb70671bb3a8f1fd07.

Unit probes prove blocked taskkill/shell calls do not execute an original tripwire,
CommonJS and ESM aliases see the denial, overwrites refuse, and the existing Node
execFileSync's lexical internal spawnSync still permits a FIXED read-only
PowerShell Get-Item check. The harness's static read-only PowerShell path checks
are unchanged. This exception is deliberate: exported spawnSync interception is
NOT generic subprocess prevention, a hostile-code boundary, kernel isolation or
proof of handle ownership. Other builtin issuing APIs remain available to the
trusted primary source; the restriction targets the exact pinned SDK callsite.

Normal graceful protocol close may run. Any denied attempt, missing guard state
or unconfirmed SDK exit forces FAIL_OR_UNCONFIRMED and
root_job_teardown_required:true, even after render agreement. Root alone may then
terminate its retained OWN Job and descendants; that teardown does NOT retroactively
turn render/SDK cleanup failure into PASS. The harness performs no native Job
termination, foreign PID reopen or SDK patch. Root/A8 must still review the exact
source plus actual membership/no-breakaway/readback and watchdog evidence. Runtime
behavior of graceful close, denied startup fallback and Job teardown remains
NOT_RUN; the source package does not claim that the pilot is currently isolated.

## Preparation verification

`node --no-addons --test --test-reporter=tap tests/fresh_render/test_bootstrap.cjs`
tests protocol with inert streams and one ordinary Node READY/EOF child, with
nonexistent inputs to ensure no target preparation before GO. Positive GO is tested
only in the protocol helper; main's fixed post-GO browser path is NOT run. Existing
twenty harness unit/structural checks stay separate. No browser/server/Consul/Job
assignment/physical pilot is run by these tests. Runtime remains NO-GO until Root
and A8 review immutable source plus actual serialized admission evidence.
