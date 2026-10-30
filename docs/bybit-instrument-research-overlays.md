# Instrument research overlays

The isolated read-only `/history-overlay` supports multiple Strattester experiments
and Scientific Laboratory Math v2.1 outputs on the same instrument chart.

See [the current contract and reproduction guide](history-overlay-contract.md)
for accepted schemas, immutable pins, integrity checks, causal time semantics,
OOS publication rules, view controls and the real producer-to-browser workflow.

No numerical fitting, prediction, composition or scoring runs in the viewer.
Historical Math #100 and Scientific #102 remain separate APIs/commits.
All imported evidence remains SYNTHETIC / UNATTESTED / NO_TRADING even when its
SHA256 matches. Independent market or engine authentication is not claimed.

Browser acceptance: `npm run test:history`. The dedicated
`.github/workflows/history-overlay.yml` rebuilds the real producer exports and
runs Chromium and Firefox with exact consumer/upstream heads in the evidence.
No ADMINIT, production PostgreSQL, orders, deployment or merge is included.
