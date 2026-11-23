# Three declared strategy-entry generators

The canonical module terminan.strategy_entries owns research sweep reclaim,
breakout retest and profile reclaim decisions. It returns frozen ResearchEntry
records containing a typed pattern/side, literal reference, the existing
ResearchSignal, typed EntryEvidence and recursively read-only entry context.
It does not register a strategy, import a provider, store data or execute a trade.
The existing continuation generator and canonical PaperEngine are unchanged.

## Boundaries and clocks

OHLCObservation declares start, end and availability separately. Its timeframe
must be an exact MarketTimeframe and the explicit intervals must satisfy the
existing contiguous timeframe policy. No availability/end is start+bar duration.
All OHLC, structure, volatility, profile and signed-flow records are detached
before any numeric owner call. Exact records and bounded literal containers are
required. Canonical MarketStructureContext validates all supplied structure,
including future records and conflicts, and its duplicates remain harmless.
Canonical build_entry_context validates every volatility/profile observation,
including future evidence, and selects latest availability rather than list order.
SignedFlowObservation explicitly declares event start, availability and a signed
literal delta; Math validates its finite/lossless domain. Conflicting flow
identities refuse, and absence remains None rather than a synthetic zero.

Sweep decisions wait for both declared structure and actual matching candle
availability. Retests require a body event strictly after the break event, body
availability strictly after break availability, Math's retest predicate and an
actually available volume ratio meeting policy. Candidates are evaluated by
(actual availability,event start); the first qualifying body wins. max_wait_bars
is a bounded interval policy over the explicitly validated timeframe cadence,
not a source of clocks. An earlier-arriving out-of-window event cannot terminate
the search for a late but eligible candle.

Profile reclaim compares event-adjacent closes through the latest available POC.
Decision time includes BOTH previous and current candle availability. A direction
is filtered by signed flow only when an actual flow observation exists; an
observed zero rejects the crossing. Profile kind remains trade-distribution or
candle-proxy as declared. No L2/OI, volume or missing observation is invented.

## Numerical ownership and evidence

Math owns literal numerical domains, positive ordered OHLC, the original retest
multiplication/comparisons and every risk-price formula. Signals use only
research_bracket_prices(...).as_decimal(); Term performs no price arithmetic.
When volatility is missing, .002 is a labeled POLICY_DEFAULT risk fraction,
never reported as observed ATR. Otherwise the actual declared ATR and regime
are retained. Original pattern/reference/level/sweep/break/volume/profile/flow
metadata semantics have typed canonical locations listed in SOURCE.json.

The signal remains an offline research DTO. Entry, evidence, signed flow and
context carry false execution/trading authority and NOT_EVALUATED source
authentication. The canonical disabled PaperEngine independently rejects the
signal; generating entries does not enable it or mutate its state.

## Provenance and validation

raw/ contains whole exact Git blobs for the original generator, five-function
test file and still-retained registry consumer. SOURCE.json records object IDs,
byte counts, SHA256 and the three role mappings. The continuation and registry
obligations are retained, not silently counted as transferred here. Original
sources/callers are not deleted; counts remain547 declared test functions and
516 remaining, with zero deduction. Overall consumer retirement/release stays
NO_GO. Math e3 is an immutable prerequisite whose publication is handled by the
parent before consumer publication; no workflow/checker was modified here.

Pure tests cover the three original entry goldens, long/short symmetry, delayed
structure/candles, first retest chronology and wait bounds, full future preflight,
identities, input snapshots, missing signed flow, latest-clock context, explicit
fallback policy, Math refusals, Decimal context, prefix stability, immutable
metadata and disabled canonical execution. Review receipts retain the TDD RED,
exact source SHA, installed pure Math origin and both Python3.11/3.12 audit-denied
runs; no database, socket, thread, process, native FFI or write operation is
permitted inside the reviewed test runtime.
