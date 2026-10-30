# Instrument research overlay

Approved direction: extend `/history-overlay` (user approval, 2026-10-30).
Keep the existing read-only Python/static SVG stack. No new screen, ADMINIT,
production database, live order access, merge or local scientific calculations.

Use a same-origin, bounded, stateless Python admission endpoint so SHA256 is
computed with the producer's exact canonical number encoding, rather than
JavaScript's different float representation. This endpoint performs no I/O.
Import bounded Strattester history handoffs as independent model layers. Retain
original values and receipts, require compatible market/dataset/price units,
and show model/source versions, time bounds and integrity separately from source
authenticity. A valid digest is never market authentication. Legacy handoffs
missing model identity remain explicitly unknown; never invent model versions.

The chart gates observations by availability and predictions by decision time.
Targets before/after asOf have distinct marker styles. OOS values are displayed
only from producer exports with an explicit publication clock; unavailable OOS
clocks do not grant visibility. Scientific v2.1 results use explicit original
timestamp/availability axes, without reinterpreting them as forecast targets.

Use independent colors, legend switches, UTC interval/asOf inputs, a timeline,
wheel/button zoom, drag/keyboard pan, crosshair and point tooltips. Persist only
view configuration keyed by imported receipts; do not persist evidence or trust.
Reject malformed, oversized, incompatible, tampered and authority-promoting
imports; prevent stale async imports from committing after newer selections.

Alternatives: a new chart screen would duplicate contract validation; replacing
the app-wide chart would unnecessarily affect other routes. Extend the existing
isolated overlay as approved. Rendering projections are allowed, numerical model
fitting, interpolation, composition and OOS scoring remain producer-owned.

Acceptance: reproduce Grid -> pinned historical Math -> Strattester replay ->
review -> real handoff exporter -> browser with multiple predictions, plus
separate real Scientific v2.1 engine result import. Chromium and Firefox tests
must cover causal boundaries, corrupt imports, hashes, units, interaction,
persistence, source claims and recovery. Record exact commits and fixture hashes.
