# Fixed-profile disposable Target Adapter result UI

Standalone TerminanTargetResult UMD/CommonJS module. No dependency on or edits to
existing gateway_artifacts.js, Sync, target execution, provider or authenticated API.

- async parseTargetResult(requestRawText=null,envelopeRawText=null)
- async renderTargetResult(root,requestRawText=null,envelopeRawText=null)

Both RAW strings are mandatory, ASCII <=16384 bytes and exact sorted compact JSON
without LF/whitespace padding. Decoder refuses duplicate decoded keys, fractions,
exponents, -0, unsafe integers and all unsupported numeric lexemes BEFORE Number
conversion; it does not turn an attacker11.0 into the golden11. Exact schema profile
supports closed objects/fixed positional arrays. Hash/length checks bind the entire
raw prepared request ID/SHA to the envelope, then recanonicalize actual embedded
Meta result and descriptor under the declared fixed integral ASCII subset:
artifact2070B/f4997d7d against BOTH refs + golden, descriptor664d34f0 golden.
This is local byte agreement only, never producer authenticity or publication.

Success returns LOCAL_UNATTESTED with a detached frozen model. Invalid, missing,
unsupported or any non-success/refusal clears prior rendering to UNAVAILABLE.
No retry/refund/rekey/submit action or custom event handler exists. Async per-root
UI token prevents older hash success/failure overwriting new view/reset. It has no
authority/cluster generation meaning. Missing WebCrypto withholds the view.

Displays experiment, capability/version, local manifest identity versus separate
Meta content digest/unavailable A4 revision, params/request hashes, observations'
units, exact derived-level/input-replay tables, provenance, budget and limitations.
Source6360 is labelled historical fixture metadata; A7aed8/MetaF3 declarations do
not prove current execution. DIRECT_TARGET_PASS is a reported producer status under
LOCAL_UNATTESTED, not whole-integration acceptance. All native/auth/physical flags
stay false, scheduler BLOCKED, finance null/unavailable; cooperative budget is not
native CPU/RSS/time containment. TextContent/native details and keyboard-scroll
tables only, no links/imported markup/SVG/fetch/storage/logging/target invocation.

## Exact owner fixtures and evidence attribution

owner-cf7d files are original schema/contract and actual payload bytes from ROOT
publicationcf7dad91bf0d3a24073c91e0d3e326e6d9e7d2db /
tree892891afb6aad2ca9af595473536ccb0fb71d5a6; actual packet execution source
 a84eabb533865f6a422a03bf096222ee51052e8f/tree0b064c8291cb4030e0a4a97ca3296b69883576a6.
SOURCE-PINS.json is test evidence, not a registry or authority. These payload bytes
are identical to earlier4e96/source8dc, but qualification does not transfer. Earlier
8dc qualification snapshots are archived outside source; Root/A8 observer P2 and
current correction/full direct qualification retain their separate owners/scopes.
No Root code is executed by this UI. No model-generated prices/results are used.

## Checks and source boundaries

node --test tests/target_adapter_result/test_target_result.cjs
16 target-only mandatory scenarios, RED then GREEN. These are not added to Root's
21 direct tests or16 schema vectors as a fictitious unique total. Oldb70741/browser
evidence is historical and unchanged; this slice qualifies its own exact HEAD.
New qualification.cjs requires --no-addons/expectedHEAD/baseb707, only NEW allocated
paths, all raw primary blobs before/after, no links/untracked files/Node injections.
Run it from an exact raw Git checkout with external evidence directory. New workflow
pins Node22.14.0/Windows+Ubuntu/actions/no dependencies. runner.temp appears only
inside step env/step artifact input, never job-level env (Root CI defect prevention).
PowerShell pre-interpreter env guard is distinct from runtime guard-model probes.
Browser command: node tests/target_adapter_result/browser_stand.cjs <raw-repo>
<external-output> <existing-playwright-module>. Actual loopback Chromium/WebCrypto,
CSP connect-src none, exact owner result, reset/stale/keyboard/mobile checks only.
HostedCI/Windows runtime/native/physical qualification are separate, NOT_RUN until
actual evidence. Public submit remains denied; no A2/A5/A4 runtime admission.

GO_NO_GO: NO-GO (isolated local UI engineering evidence only).
