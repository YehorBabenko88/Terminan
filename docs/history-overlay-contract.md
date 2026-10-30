# Read-only instrument overlay contracts

`/history-overlay` appends up to 8 packets / 16 colored layers. All packets must
have identical dataset id, snapshot fingerprint, market, units and observations.
Different experiments may share one frozen model; their receipts distinguish
policy runs. Identical receipt reimport is a no-op. Multi-file import commits
atomically. Clear/new selection invalidates older asynchronous admission.

## History

Use actual Strattester `scripts/export_history_scientific_handoff.py` output:
`terminan.history.scientific-handoff.v1`. Producer fix is stacked on #65 in #67,
commit `2669c433333b811b0eaedf88ea13b0e955b0836b`.
Receipt validation uses the producer's Python canonical JSON (sort keys, compact
separators, ASCII strings, finite numbers), excluding `handoff_sha256`. The
stateless same-origin POST `/api/history-overlay/validate` does this with Python
stdlib to retain Python float encoding. It neither opens sources nor saves files.
Duplicate keys, nonfinite numbers, excessive nesting and rows are rejected.

Required authority: SYNTHETIC, UNATTESTED, and false execution/training/trading.
Source identity and market identity are separate. Forecast clocks satisfy
`feature_event <= feature_available <= decision < target`, and the feature event
must be in the imported observations with no understated prefix availability.

Model/runtime commit, manifest, units and test split are preserved by #67.
Older v1 packets without a model are labeled UNKNOWN. Legacy missing OOS
publication clocks yield OOS_UNTIMED_NOT_DISPLAYED; an absent market symbol is
rejected, rather than inferred. Even self-consistent rehashed source receipts
are caller claims and cannot grant source trust.

## Scientific v2.1 display envelope

`terminan.scientific-overlay.v1` contains:

- `evidence_class: SYNTHETIC`, `source_authenticity: UNATTESTED`, three false authority flags.
- `history_binding`: original `dataset_id`, `snapshot_fingerprint`, `market`, `units`.
- `engine`: repository `YehorBabenko88/math`, immutable commit
  `1f97e56701c0fce01dc8dd05952111fa8df3f2d1`, `api_revision: 2.1`.
- `request`: original `math.scientific.graph.v2` research request with one source.
- `result`: unmodified `math.scientific.result.v2` from the real engine.
- `packet_sha256`: Python canonical envelope digest, excluding itself.

Only price-unit series can share this chart. Incompatible series or scalars are
rejected explicitly, with no unit conversion. Browser verifies Math's own JS
canonical normalized request digest, node definitions and requested output/port
trace digests. The envelope binds source provenance to the historical snapshot;
compatibility also compares actual observation rows. These checks establish
internal consistency, not that an engine or market source is independently
authenticated. Retain UNATTESTED even when every checksum matches.

Outputs retain exact `timestamps`, `availableAt`, `unit`, and `values`. Historical
scientific outputs require both availability and event timestamp <= display
asOf, including lagged series whose availableAt precedes their timestamp. Math's
historical source convention (`availableAt <= timestamp <= request.asOf`) is
different from delayed market publication. No event-to-availability relabeling
is performed. A delayed market snapshot incompatible with this convention is
rejected; the display must not invent a scientific result to bridge it.

## Temporal display

Observations require `available <= asOf`. Forecasts require `decision <= asOf`:
hollow diamonds at past targets remain PAST_PREDICTION; filled circles at future
targets are FUTURE_HORIZON. Forward mode hides past predictions and keeps only
causally known observations. Scientific dashed lines are historical results,
never forecasts or OOS certifications. Producer OOS metrics appear only when
their explicit publication time is known, after test end and source availability.
Metadata excludes future numerical outcomes. No scoring/fitting/interpolation
or model composition is implemented by the chart.

Wheel/buttons zoom; drag, arrows and buttons pan; timeline click centers the
view, slider moves asOf. Crosshair uses the nearest visible point with separate
event/availability/decision/target fields; keyboard focus exposes the same text.
Range and asOf use safe integer UTC ms. Invalid views clear the plotted values.
Only validated view configuration is saved, keyed by the set of packet receipts.
Evidence must be reimported after reload; localStorage never grants trust.

## Reproduction

Create separate clean checkouts at the four commits in
`scripts/build_history_overlay_evidence.py`. Then:

```text
python scripts/build_history_overlay_evidence.py --grid ../grid-history --math ../math-history --strattester ../producer --scientific ../math-scientific --output reports/history-evidence
npm ci
npx playwright install chromium firefox
npm run test:history
```

The output directory must not already exist. This executes the actual pinned
Grid export fixture, historical Math stdio process, Strattester replay/review
and exporter CLI for two fee policies, followed by a separate pinned Scientific
engine invocation producing mean, formula and lag layers. No mock forecast endpoint
or browser-generated forecast is used. Each history packet has 60 predictions;
the Scientific packet has three series. The initial test split has zero trades,
so its zero OOS PnL is a producer result, not evidence of predictive performance.

The manifest records upstream commits/trees, runtime SHA256 and file/packet
digests. Historical receipts bind the Python runtime, so different executable
builds may yield different receipts while preserving synthetic numerical values.
CI rebuilds everything, runs Python/Node regressions and both real browsers,
and uploads reports with the exact consumer head. Existing saved-source tests
use separate legacy pins via GRID_REPO/STRATTESTER_REPO, preserving old contracts.

No production PostgreSQL, external market requests, ADMINIT changes, orders,
deployment or merge are part of this workflow.
