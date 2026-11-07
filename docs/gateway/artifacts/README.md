# Local Gateway artifact rendering

Metadata and computed-level chart consumers are local isolated components. No route,
provider, registry, authenticated retrieval, job dispatch or Sync mapping is added.
ROOT full local chart design ACK applies to COMPUTED-LEVELS-DESIGN-v1.md original
SHA256 f6b2bb4ed304ad062b7e990fbe03a3b0fc9bfa0995c39c1151017ca37c4aaf42.
The ACKed design bytes are preserved; proposal wording records its original status.

UMD global TerminanGatewayArtifacts / CommonJS exports:
- parseArtifactMetadata(rawText=null): frozen local metadata result.
- renderArtifactMetadata(root,rawText=null): inert metadata text display and reset.
- async renderComputedLevels(root,descriptorRawText=null,artifactRawText=null):
  bounded ASCII UTF8 input, exact artifact digest/length, closed pinned schemas,
  semantic units/clocks/row/level/decimal validation; inert SVG scatter + exact
  accessible table + separate input replay. Status UNATTESTED or UNAVAILABLE.
  SUPERSEDED returns without changing DOM after a newer render/reset. A per-root
  Symbol in a WeakMap is bounded UI bookkeeping, never authority/generation.

Geometry is an approximation. Nonfinite, underflow, mismatched source prices and
collapsed distinct prices refuse chart display. Exact decimal strings, including
uppercase E, remain in labels. Native keyboard-scroll regions retain chart/table
readability on narrow screens. No imported markup, event handlers, URLs or IO.
Byte hash agreement is not source authenticity/publication/financial precision.

## Immutable owner computation

Fixture directory tests/gateway_artifacts/a7-f3d2877 contains original A7 schemas,
request, result, descriptor and computation receipt, byte-for-byte from publication
f3d2877ac5e7af6f89586fcdb184974b494e46ac/tree9904546a5445c91bf275dd69f39e281e8905f516.
Actual execution source6360a75a428c0cb1538085820381324bc4dd9d6f is distinct.
Actual result2070B SHA f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940
was independently reproduced twice through the three pinned pure Meta source files.
The renderer does not run Meta or fabricate/calculate input prices.
Four original levels: low8@0,low9@60000,high12@120000,low10@120000.
These are whole-window results; source locators are not historical knowledge times.

The historical producer source has a known coroutine cancellation caveat. A7 reports
fix f11f393ddc1ce1d45e5ec66839fa98e15ee98496; corrected replay receipt is independent.
No old packet or source claim is rewritten, and chart ACK admits no callable/job.

## Engineering checks

node --test tests/gateway_artifacts/test_metadata.cjs tests/gateway_artifacts/test_chart.cjs
27 mandatory Node scenarios (15 metadata +12 chart), no skips. Chart scenario0 pins
all seven original owner fixture/schema hashes and exact embedded schemas. Adversarial
numeric mutations are negative tests only; never computation/production evidence.
Source-bound runner qualification.cjs requires --no-addons, expected exact HEAD,
raw Git equality before/after, no ambient Node injection/links/untracked files and
only allocated additive paths againstc752dff. Use a raw LF checkout; a normalized
CRLF checkout must refuse rather than weaken source equality. Evidence outside source.
Workflow runs Node22.14.0 on Windows/Ubuntu with pinned actions and no dependencies.
Browser stand command: node tests/gateway_artifacts/browser_chart.cjs <raw-repo>
<external-output> <existing-playwright-module>. It serves isolated loopback TEST_ONLY
fixtures with CSP connect-src none; actual WebCrypto completion is delayed for a
stale/reset test without forging digest bytes. No backend, lease or signature mock.

Hosted CI, Windows runtime, authenticated retrieval, publication/registry and physical
acceptance are independent. Local chart tests do not satisfy vertical runtime E2E.
Production/real orders remain BLOCKED; overall NO-GO.
