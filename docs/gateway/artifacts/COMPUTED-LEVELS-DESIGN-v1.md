# Computed levels chart consumer — local proposal v1

Status: PROPOSED_LOCAL_CHART_NOT_ENDPOINT_OR_JOB_ADMISSION.
Metadata module remains unchanged until this design ACK. Owned paths unchanged.

## Exact source admission reviewed by A6

A7 publication f3d2877ac5e7af6f89586fcdb184974b494e46ac,
tree9904546a5445c91bf275dd69f39e281e8905f516.
Actual producer execution revision6360a75a428c0cb1538085820381324bc4dd9d6f
is distinct from artifact publication; reported coroutine-close P1 fix requires
new source/replay receipt before callable/job ACK. Historical bytes are immutable.

Exact local schema candidates ACKed for offline consumer with semantic validation:
request7338a91675611c8f5ead41f334f657e0fe682ab6c5567b5a16387d90dbc928ac;
Meta result8a831f84129eb3ba06034ca88e081703d2c07db4da96281d555021f4961a156e;
descriptor a14286cdf1fdeb3cb0b826575f231346a517706a8cf39f7b5727b78811e4eef4.
No async codec/transport contract is inferred from Python descriptor+bytes return.

A6 verified three metaschemas, three packet instances, four packet hashes,
descriptor/bytes/request/dataset/units/clocks bindings, and independently executed
only the three pinned pure Meta files twice: canonical result BYTE_IDENTICAL.
No A7 wrapper/job/lease/storage/auth code was executed for that consumer review.

## Proposed local API and verification

Add async renderComputedLevels(rootElement, descriptorRawText, artifactRawText)
to owned gateway_artifacts.js. Input is bounded canonical ASCII UTF8 text from
owner-supplied bytes, never URLs, decoded object graphs or price arguments.
This is a new LOCAL consumer signature, not the existing Python or transport ABI.
Copy/validate immutable string inputs before await; reset previous chart immediately.
Validate closed descriptor<=64KiB and artifact<=1MiB, decoded duplicate keys,
depth12/nodes32768/members64, strings per exact schema and fixed arrays<=256rows/512levels.
Hash raw ASCII UTF8 artifact bytes with local WebCrypto SHA256; byte_count and digest
must equal descriptor. Digest agreement is BYTE_MATCH_ONLY, never provenance trust.
Use a fixed admitted test fixture manifest for integration evidence, not a runtime
registry or authorizing provider. No fetch, storage, callbacks, timers or remote URLs.
If crypto unavailable, malformed input, hash mismatch or unsupported numeric/time
conversion: clear chart and show UNAVAILABLE with bounded error code.

## Mandatory semantic validation beyond schema

Preserve original labels including uppercase E notation. Decimal grammar/length
from owner schema; exact finite decimal >0 and <=1e15; reject plotting underflow,
overflow, collapsed nonidentical prices or nonfinite coordinates. No financial
precision/tick/currency claim. A plotting approximation is explicitly labelled.
Match symbol and price/volume units; descriptor units/dataset/requestdigest/clocks
must match embedded artifact. Dataset revision remains unavailable.
Minute-aligned closed contiguous rows, exact window bounds and row count;
positive OHLC consistency, volume>=0; source.retrieved_at matches data_available;
window_end <= retrieval <= decision <= snapshot_as_of <= calculated.
Each level source_start must refer to a matching row boundary in the same window,
kind high/low price must match that source row high/low; no duplicate level identity.
No rows or calculated prices supplied by renderer/model. No recomputation replaces
owner result; schema/digest checks do not attest arbitrary result provenance.

## Presentation

Scatter chart of actual levels: X = source candle locator (UTC minute),
Y = observed price unit. High/low marker shapes + text labels; no connecting path,
historical timeline playback, order arrows or level extension pretending it was
known at source_start. Accessible data table preserves exact decimal labels and
source locator. Empty levels yields explicit empty computed result, never zero.
Show input replay as separate table, clearly INPUT_REPLAY_NOT_DERIVED.
Persistent TEST_ONLY_SYNTHETIC / UNATTESTED / NOT_EVALUATED source authenticity /
UNKNOWN quality / DECLARED_COMPLETE_UNVERIFIED coverage /
SYNTHETIC_ENGINEERING_ONLY_NOT_MEASURED fidelity /
NO_ORDERS_NO_LEDGER_NO_EXECUTION_SIGNALS / finance unavailable.
Show window/retrieval/decision/asof/calculation separately plus experiment revision,
dataset digest, unavailable dataset revision and source pins in native details.
Never LIVE, PIT, verified provenance, authenticated retrieval or operational PASS.
SVG elements generated from validated finite numeric geometry and textContent only;
no imported SVG/HTML/foreignObject/links/styles/scripts from artifacts. This inert
SVG DOM is the only new rendering capability; current metadata renderer stays inert.

## Executable evidence after chart design ACK

Use exact A7 request1126B SHA c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648,
Meta result2070B SHA f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940,
descriptor2122B SHA664d34f06721b3d62404ea2f05b6b929a59b9e3eeecc281a71d2ca927c802cda.
Expected markers: low8@0,low9@60000,high12@120000,low10@120000, all whole-window.
Tests: real owner fixture rendering; tampered digest; schema unknown/duplicate;
unit/time/source mismatch; zero/E999/underflow; unavailable reset; exact labels;
qualifiers and source/input distinction; SVG safety; keyboard/table/mobile and
no network. Fixture-only browser qualification is not runtime integration PASS.

## Independent gates

Exact local schema ACK does not admit A7 wrapper callable while coroutine P1 open,
A5 submission/fencing, A4 publication/registry/retrieval, A2 authenticated readcap or
ROOT runtime composition. Current endpoints/readcap remain NONE. Windows/physical/
production/real orders BLOCKED. Chart design awaiting ROOT review.
