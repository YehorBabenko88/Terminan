# Visual Scientific Laboratory

User approved existing JavaScript + SVG, no new frontend framework, and continuous implementation on 2026-10-30.

The /math tab becomes a freeform research graph editor. SVG nodes expose typed input/output ports; pointer and keyboard actions share structural validation. An inspector edits parameters, formulas, unit declarations, caller-supplied market series and versioned scientific hypotheses. SVG is preferable to a graph framework because Terminan currently serves static HTML with no frontend build. Canvas would require a second accessibility tree and manual hit testing.

A bounded versioned document stores graph, positions, view, units and unattested provenance. Imports validate transactionally, preserving the current graph on failure. Local checks are usability checks only: Math must independently validate every execution. No formula parser, numerical transformation or model runs in Terminan. Formula text becomes AST only inside Math's restricted parser.

The existing loopback opt-in, same-origin HTTP bridge remains the sole execution path. Existing pages and read-only endpoints remain intact. /api/math/formula must be repaired first. A new graph contract will be pinned after coordination with Codex 1; legacy contracts remain available.

Results show engine-returned series, scalars, metrics, diagnostics and provenance. Up to five immutable experiment snapshots support overlays without recomputing metrics locally. Edits invalidate the current execution state; an in-flight response cannot overwrite a changed graph.

Limits: 12 computational nodes, 24 edges, 2000 values per source, 262144 request bytes; bounded import and responses, finite parameters, no trading/training authority, no production DB access. Knowledge citations remain hypotheses and cannot confer trust.

Acceptance: real HTTP regression tests, browser pointer/keyboard workflows, invalid type/cycle/import recovery, unavailable engine, real pinned Math integration, exact-head CI, SHA256 evidence. ADMINIT physical acceptance is documented and NOT_RUN here.
