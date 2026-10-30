# Unified Terminan workspaces — staged consolidation

Base: codex/instrument-research-overlay-20261030, preserving existing history-overlay,
Math scientific lab, source adapters, and saved/cache code. The primary server
already exposes /, /monitor, /math, /history-overlay and associated APIs.
This PR adds a single accessible navigation strip to those four real routes.

## Inventory and actual availability

| Workspace | Primary port | Status |
|---|---|---|
| Terminal | / | Available |
| Fleet monitoring | /monitor | Available; Grid schema/availability not certified |
| Scientific lab | /math | Available; Math engine optional and independently gated |
| Research overlay | /history-overlay | Available; historical packet validation is not source authentication |
| Saved candles/footprint/replay/cache | /saved on separate saved_runner | Implemented but NOT mounted on primary server |

The /saved implementation inherits R4Server/R4Handler and requires its own
session, diagnostics, candidate SHA, and source configuration. Mounting only
its HTML onto the primary server would break its API, assets, session fences
and evidence. Do not create a misleading /saved tab until a supported
adapter or unified lifecycle is implemented and tested.

## Next integration gate

1. Freeze exact HEAD of the scientific branch; compare the saved runner,
   cache audit, overlay, and infrastructure dashboard workstreams.
2. Design a same-origin adapter that preserves R4 session fencing and
   read-only source credentials; no transparent localhost proxy or new
   network listener by default.
3. Add /saved and /api/saved/* only after negative session, stale cache,
   source revision and cancellation tests pass.
4. Reconcile PR55 historical-level validation with the scientific branch's
   level_history_quality before applying any cherry-pick.
5. Run exact-head Python, Node and Playwright suites, then LS-5 physical
   browser acceptance across tabs and 15/600-second soak.
6. Never merge to main or modify PostgreSQL, Grid or Strattester implicitly.

## Windows read-only smoke

From a clean checkout of this branch:
```powershell
py -3.12 -m unittest tests.test_unified_workspace_navigation -v
py -3.12 -m terminan
```
Open /, /monitor, /math and /history-overlay on the printed loopback port.
Source-backed pages may display UNAVAILABLE until their owners are started.
No deployment, services or VM required.
