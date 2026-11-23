# Declared-time market structure transfer

Term owns state, decision chronology and timeframe context. Existing Math owns
strict swing/gap geometry and numeric-domain predicates; the existing
terminan.price_structure projection binds full dependency availability.

## Design

OHLCObservation declares start, end and availability separately and supplies
all four literal prices. MarketTimeframe is a closed enum; each explicit
end-start duration must match its label and adjacent observations must be
contiguous. Labels validate supplied clocks; they never construct them. Inputs
are detached before the first numeric owner call, including every timeframe in
a multi-timeframe batch. Even observations beyond the cutoff are validated.

The numerical geometry is reused from Math through analyze_price_structure.
State contains confirmed swings, BOS, CHOCH, rejection sweeps and order blocks;
gaps remain in the existing price-pattern API, matching the original state
function's scope. OHLC financial admission is deliberately stricter than
nonnegative calibration range geometry: Math's lossless literal predicate and
positive ordered OHLC predicate both apply. Decimal(str(price)) is only a
presentation into that existing predicate. No Decimal arithmetic or precision
recovery occurs, and event payloads retain their original int/float values.

Eligible candles are processed by (availability,start). A swing must have been
known by the trigger candle's start, even when its decision arrives late. The
latest event-time visible swing is selected on each side; a broken swing is
consumed exactly once. Sweeps do not consume levels. Trend transitions follow
the original high-side-before-low-side rule within one decision. An opposing
order-block candle must be at/after the swing, strictly before the trigger in
event time and actually available by the trigger decision. Among eligible
candidates the latest event-time candle wins.

MarketStructureEvent consistently carries level, low/high, source availability,
a confirmed swing reference and an optional trigger reference, each with
explicit clocks. MarketStructureContext snapshots all declared evidence and
selects bias by maximum (known time,event time,kind), independent of list order.
Its bias and higher-timeframe alignment results remain analytical declarations.
No source authentication or trading/execution authority is granted. The context
returns detached event copies; it does not expose its primitive snapshots.

## Alternatives and scope

Recomputing numeric swings in Term would duplicate Math ownership. Keeping the
old dictionary/fallback API would hide missing OHLC and infer bar-end clocks.
The selected design uses exact typed records, existing Math and explicit clocks,
while preserving unique state decisions and fixing delayed-data leakage.

Seven original state/timeframe golden behaviors are reexpressed in the new
canonical tests. Original source and tests are retained byte-for-byte in raw/,
with Git object IDs and SHA256 in SOURCE.json. No old source or consumer was
deleted. Legacy counts remain 547 declared test functions, 516 remaining; this
transfer deducts zero. Consumer-pipeline retirement and overall release remain
NO_GO pending separate acceptance.

## Validation plan

Run the pure market-state suite on existing Python3.11 and3.12 with the installed
pure Math SDK. Deny database, socket, process, thread, native FFI and write
operations. Cover original goldens, delayed decision chronology, conservative
visibility, broken-state uniqueness, candidate availability/event-time, prefix
invariance, input snapshots, MTF evidence, hostile inputs, Math refusals and
Decimal context preservation. Recheck existing price-pattern and selected pure
canonical PaperEngine regressions without running its HTTP/server tests.
