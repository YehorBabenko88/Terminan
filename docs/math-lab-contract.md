# Terminan Scientific Laboratory contract

Base: PR #48, `d10d5a0e2f00fcd68e284d2b6e743f61430997c9`. Workstream: #49.
Design approved by user 2026-10-30. Direct coordination with Codex №1 selected the separate Math v2 interface; all v1 endpoints remain available.

## Documents and boundaries

`terminan.scientific-lab.v1` is an editor document, not an executable engine contract. Required fields: schema, execution_authority:false, trading_authorized:false, asOf, nodes, edges, view. Node fields: id, kind, label, x, y, unit, parameters. Edge fields: id, from, to, port (zero-based numeric input or `knowledge`). View: x, y, zoom (0.25–2.5). Unknown fields, invalid IDs, cycles, occupied ports and authority changes are rejected transactionally. Empty/incomplete documents may be saved; execution requires all numeric inputs connected.

Up to 24 editor nodes, 12 computational nodes, 24 edges, 2000 samples/source, 16384 input values, 256 KiB document/request. Requests and results have an 8-second UI deadline / 5-second upstream deadline and 2 MiB response limit. Engine limits are independently enforced and may reject requests accepted structurally by the UI.

Kinds: source, formula, model (named formula), method, difference, average, multiply, divide, convert, lag, hypothesis, result. Numeric outputs are series; source inputs are explicit values/timestamps/availableAt. `asOf`, timestamps and availability are integer UTC milliseconds; availableAt <= timestamp <= asOf. Source provenance sourceId/version/sha256 is a caller declaration, not verification of content or external identity. Defaults are small manual examples, never live market data.

`terminan.hypothesis.v1` parameters: schema, title, sourceId, page (positive integer), version, attested:false. Hypothesis edges annotate formulas locally and remain in saved snapshots. They do not confer mathematical validity and are not converted into trusted engine knowledge. Math knowledge nodes require server-hosted catalogue references; the default catalogue is empty, so no book source is fabricated.

## HTTP

GET `/api/math/catalog` forwards to fixed `http://127.0.0.1:8788/v2/catalog`; schema `math.scientific.capabilities.v2`, units, unitMetadata and dimensionBasis are rendered as engine declarations. No unit inference algorithm runs in Terminan.

POST `/api/math/scientific` forwards to `/v2/graph/execute`, only with `TERMINAN_MATH_OFFLINE_BRIDGE=1`, exact local Host/Origin, application/json, bounded Content-Length. No proxy environment or redirects are followed. Browser code cannot choose upstream host, credentials, catalogue or database.

Request: `math.scientific.graph.v2`, mode:HISTORICAL_RESEARCH, execution_authority:false, asOf, nodes, edges, outputs. Edges: `{from:{node,port:'value'},to:{node,port:'x'|'a'|'b'}}`. Formula/model maps to `{id,kind:'formula',expression,outputUnit}`; AST parsing, unit semantics and evaluation occur exclusively in Math. Method parameters are finite and bounded to ±1e6, method polynomial/sine/gaussian. Convert declares target unit. Lag declares positive integer steps. Binary operators use a/b. Multiple sinks and explicit result-node selections become outputs.

Response: `math.scientific.result.v2`, RESEARCH_ONLY, requestSHA256, order, outputs, trace, source:CALLER_SUPPLIED_UNATTESTED; execution_authority/trading_authorized/training_authorized/mathematicallyVerified all false. Outputs carry node, port, type, unit, values, timestamps, availableAt. The bridge checks identities, temporal invariants and response limits. The browser also checks the canonical normalized request digest using the engine's documented ordering. SHA256 establishes consistency only.

Engine trace includes definitionSHA256, dependencies and outputSHA256; provenance/knowledge are displayed verbatim as inert text. Engine descriptive metrics are displayed without recalculation; missing metrics are explicitly NOT_PROVIDED_BY_ENGINE. Charts only project returned samples into screen coordinates, using a shared UTC domain and separate unit lanes. No predictions, fit metrics, source authenticity or trading authority are inferred from a plot.

Semantic errors: INVALID_SCIENTIFIC_REQUEST (422), BRIDGE_DISABLED, BODY_LIMIT, RESPONSE_LIMIT, MATH_ENGINE_UNAVAILABLE, UNTRUSTED_GRAPH_RESULT. Private engine exception text is not returned. Legacy `/api/math/formula` now appears in the POST allowlist and delegates through the same bounded loopback transport; existing evaluate/graph/ports paths and read-only GET API are retained.

## Reproduction

Math pin and source-file digests are in `math-engine.lock.json`. Run `npm ci`, `node --test tests/test_lab_graph.cjs`, `python -m unittest discover -s tests`, then set MATH_REPO to the pinned checkout and run `npx playwright test -c playwright.math.config.cjs`. Python full-suite tests also require Grid/Strattester exact checkouts from contracts.lock.json. Dedicated CI checks exact source heads, installs Chromium/Firefox and requires the real offline Math case with no skips.

Acceptance is limited to software/UI/protocol and offline-engine integration. ADMINIT physical acceptance remains NOT_RUN until the separate instructions are performed.

## Interactive laboratory increment (base PR51)

The searchable library contains editor definitions plus methods and knowledge references actually advertised by the pinned Math catalogue. Catalogue methods are bounded/deduplicated; a missing/invalid catalogue is reported explicitly. No book record is fabricated. Catalogue knowledge is an additive `knowledge` editor node with `parameters:{reference:{id,sha256}}`; it maps exactly to the Math knowledge node. Expressions, edition/page, hypothesis and confidence are displayed as inert catalogue metadata, never executable client code or an expression override. The user-facing reference/unit remains bound to the server definition. The old local `hypothesis` node remains non-executable metadata.

Editor usability: transactional creation from templates, bounded40-step undo/redo, duplicate, fit graph, click/keyboard/drag connections, Escape cancellation, explicit source/target/input selection and relinking. Failed creation/import/validation preserves the current graph. History is local and is not sent to Math. Imported v1 documents remain accepted; old code will reject the additive knowledge kind rather than silently treating it as a formula.

Result usability: UTC time ticks, time zoom/pan/reset (buttons, wheel and keyboard), per-output visibility, experiment naming, unit-separated lanes and searchable trace tables. A shared timestamp domain aligns branches; shrinking history clamps the viewport to the current domain. Chart coordinate projection is presentation only; all returned values, scientific metrics and AST operations belong to Math.

`TERMINAN_MATH_PORT` is an optional integer1..65535. It changes only the port of fixed127.0.0.1 for **every** Math call, including health and legacy APIs; default remains8788. No URL/host/proxy may be supplied. Test fixtures obtain a free port from an owned Math listener and use an ephemeral Terminan port, preserving installed listeners.

The user-reported Source→Formula→Formula scenario is reproduced with source[1,2,3], formula x*2, then x^2+1 and literal expected output[5,17,37]. This is an isolated automated Windows/browser observation, not independent attestation of the working ADMINIT installation or the original human acceptance receipt. No original human receipt was found in the accessible PR discussion.
