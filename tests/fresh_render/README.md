# Prepared fresh-file render package

This test-only package extends immutable Terminan PR73 source22e6e72. It does not
change renderer, PR73/74, Root composition, authorization or API contracts. Root
selects all fresh inputs from its exclusive disposable directory. Nothing reads
the committed result fixture in run/preflight. No fallback, exchange access,
production credential, new endpoint or market-data verification is provided.

`preflight` performs bounded ordinary-file reads, Windows ReparsePoint checks on
all ancestors, single-link checks, raw expected SHA256, same-open/read identity,
pinned renderer parse and exact canonical artifact agreement. Raw request/envelope
must satisfy the existing fixed synthetic f499 profile. Unique request IDs are
accepted when both original request and envelope binding agree. It cannot prove
freshness/producer execution: Root must separately join its fresh producer receipt.
Local bytes always remain LOCAL_UNATTESTED, with synthetic datasets, unknown source
authenticity, no chart and no authenticated gateway/physical acceptance.

## Root usage (PowerShell)

Use an exact raw Git checkout (core.autocrlf=false at clone time), not a CRLF
renderer checkout. Select native canonical absolute paths using Resolve-Path;
do not include junctions, symlinks, hardlinks, ADS or UNC paths. All three inputs
must be different existing files below `$testRoot`. Do not place real secrets
there: the UI deliberately displays the complete raw request/envelope.

```powershell
$node = 'C:\Program Files\nodejs\node.exe'
$repo = (Resolve-Path '<EXACT-RAW-PACKAGE-CHECKOUT>').Path
$testRoot = (Resolve-Path '<ROOT-EXCLUSIVE-DISPOSABLE-TEST-DIR>').Path
$request = (Resolve-Path '<FRESH-PREPARED-REQUEST-BELOW-TESTROOT>').Path
$envelope = (Resolve-Path '<FRESH-DIRECT-RESULT-BELOW-TESTROOT>').Path
$artifact = (Resolve-Path '<FRESH-META-ARTIFACT-BELOW-TESTROOT>').Path
$requestSha = (Get-FileHash -LiteralPath $request -Algorithm SHA256).Hash.ToLowerInvariant()
$envelopeSha = (Get-FileHash -LiteralPath $envelope -Algorithm SHA256).Hash.ToLowerInvariant()
$artifactSha = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
$harness = Join-Path $repo 'tests/fresh_render/harness.cjs'
& $node --no-addons $harness preflight $testRoot $request $envelope $artifact $requestSha $envelopeSha $artifactSha NO_BROWSER
# Only AFTER Root/A8 isolation admission and assignment of the serialized lane:
$playwright = (Resolve-Path 'C:\Users\LS-5\Documents\Codex\2026-11-06\codex-agent-6-distributed-terminan-control\work\terminan-sync-v1-manual\node_modules\@playwright\test').Path
$chromium = 'C:\Users\LS-5\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\ms-playwright\chromium_headless_shell-1194\chrome-win\headless_shell.exe'
& $node --no-addons $harness run $testRoot $request $envelope $artifact $requestSha $envelopeSha $artifactSha ROOT_SERIAL_LANE $playwright $chromium
```

`ROOT_SERIAL_LANE` is an explicit CLI mode marker, NOT an authorization credential
or proof that admission occurred. Root controls OS identity, admission and launch.
Run refuses ambient NODE/PW/PLAYWRIGHT/SELENIUM/DEBUG configuration. Launch from a normal
nonadmin process with no sensitive environment/credentials. Harness passes only
Windows system paths and its own temp/home directories to the browser. No npm,
browser download or services. No Node22.14 claim: Node24.22.1 is intentional here.

The usual AppData/Local/ms-playwright path is a Codex app virtualization alias on
this host and deliberately refuses PATH_REALPATH. The full Packages path above
is the observed canonical native path; do not weaken path checks for that alias.

Pins in `harness.cjs`: existing Node executable SHA d702daa8..., Playwright1.56.1
lock SHA ee92d25c..., all521 installed package files tree SHA3a122fd6...,
browsers.json SHA1387ec66..., headless Chromium141.0.7390.37/rev1194 binary
SHAed19d88b..., renderer SHA574dbf08.... Full hashes are executable constants.
Dependency file links and unexpected package tree contents refuse. This validates
the selected installed tooling; it is not a signed software supply-chain claim.

## Network, temp and process ownership

HTTP listens only127.0.0.1:ephemeral. GET `/`, `/renderer.js`, `/packet.js` are the
only routes; other methods/queries/traversals do not serve files. CSP connect-src
none; context routes block every page request outside these exact three URLs.
No artifact file route, browser fetch, logs endpoint or arbitrary static directory.
BrowserServer's SDK WebSocket also binds127.0.0.1:ephemeral and is never logged.
WebSocket access is a local browser-control capability: Root must provide exclusive
test-user custody. Page routing does not qualify all browser-native OS traffic;
the disposable sandbox/isolation admission belongs to Root/A8, not this harness.

New exclusive `$testRoot/fresh-render-<random>/temp` holds TEMP/TMP/TMPDIR, SDK
artifact directory, generated browser profile and explicit disk cache. SDK temp
selection is set BEFORE importing Playwright. No real user profile is opened.
`chromiumSandbox:true` is mandatory; no no-sandbox, certificate bypass or web
security disable. SDK default security-disabling feature/phishing/IPC/popup/self-XSS
switches are filtered; actual issued spawn arguments are checked after launch.
No user-supplied launch flags. A refused launch never retries with weaker security.

`BrowserServer.process()` gives the actual launched browser PID. An immediate
`owned-browser.json` retains PID/parent/run-root, not WS token or raw environment.
Cleanup calls the SAME SDK BrowserServer.close(), bounded5s; fallback is ONLY that
issued handle's BrowserServer.kill(), bounded5s. No process enumeration, arbitrary
PID, taskkill or process.kill. Receipt PASS requires observed exitCode/signalCode.
SDK removes its own generated temp profile/artifacts on owned process exit;
the harness never recursively deletes test inputs, evidence or foreign directories.
Root's watchdog must own only this harness process and the recorded SDK-issued
child if catastrophic parent death prevents SDK cleanup. An observed PID number
alone is not a durable post-exit kill grant; PID reuse requires fresh OS identity
checks in Root's watchdog. No such watchdog or foreign-process killer is shipped.

45s cooperative budget with bounded SDK operations; cleanup has separate bounds.
No detached global timer races a still-running launch continuation. This is NOT
hard scheduler CPU/RAM/disk containment. Root supplies external watchdog/resource
observations and exclusive writable-directory custody. Reparse checks do not prove
hostile concurrent filesystem race/ACL isolation. Stop if those prerequisites fail.

## Evidence and limits

Three inputs each1..16384B; renderer<=65536B. Header cap4096B, max4HTTPconnections,
page request cap32. Screenshot fixed1280x900 viewport (not unbounded full page),
max4MiB; JSON outputs each<=64KiB. Only three fixed evidence names use exclusive
create: `owned-browser.json`, `fresh-render.png`, `render-receipt.json`; combined
evidence is below8.125MiB. SDK profile/cache space is not a hard disk quota.

Browser result must equal the independently parsed fresh Node model, retain the
LOCAL_UNATTESTED banner, exact four levels and three replay rows including every
displayed cell, with no link/image/control/chart. Structured receipt includes all
three fresh raw input hashes, renderer/model/screenshot hashes, request counts,
PID cleanup and explicit false authentication/verified-market-data/production.
No claim that local identity roles/hashes are authority. A4/A2 positive APIs remain
NONE; PR74 stays quarantined independently of this disposable rendering package.

## Preparation checks only

```powershell
$env:FRESH_UNIT_ROOT = '<ABSOLUTE-EXTERNAL-UNIT-EVIDENCE-DIR>'
& $node --no-addons --test --test-reporter=tap "$repo/tests/fresh_render/test_harness.cjs"
```

Tests use deterministic copied fixture bytes with a rebound independent request
ID only inside unit cases; no browser, server, Consul or production request is
started. Cleanup tests exercise handle call/exit bookkeeping with inert doubles,
not real process containment. Real browser/physical pilot remains NOT_RUN until
Root/A8 separately admit and run this exact committed package. Overall NO-GO.
