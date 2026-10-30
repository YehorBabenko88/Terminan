# Terminan ↔ Math Scientific Engine v2.1

Base: Terminan PR52 `0d0bb679a279fd251d3d2cc8a5ad763b0cc24910`; it and its pin remain unchanged. Primary Math PR102 exact `1f97e56701c0fce01dc8dd05952111fa8df3f2d1`, tree `45f7b0fc99efac7d611bb7717c8ee23703b3bace`. Legacy compatibility pin: Math PR101 `321c4cd94d9ee0aba7a5d709042612f5ad4c5a05`. Both lock files contain canonical source-object digests; hashes prove integrity/consistency only.

## Compatibility

| Capability | Real Math v2.0 | Pinned Math v2.1 |
|---|---|---|
| Legacy source/formula/method/knowledge/conversion/lag/binary nodes | Preserved | Preserved |
| Existing editor `model` formula alias | Compiles to formula | Compiles to formula |
| `engine-model` affine/landau-map/logistic-map | Hidden/blocked | Exact advertised models, fixed parameters |
| sum/rolling-mean/derivative/integral | Hidden/blocked | Revision + features + matching named ports required |
| overlay / compare | Hidden/blocked | Named output ports, `(node,port)` identity |
| Compound units | Blocked when unsupported | Only Math `/v2/units/describe` parses and describes them |
| Request/definition/output/dependency digest checks | Required | Required per actual output port |
| Imported old documents | Default `value` preserved | Default `value` preserved |
| Imported v2.1 graph after downgrade | Retained for editing, execution blocked | Negotiated execution |
| Book/source/trading authority | UNATTESTED / NOT_VERIFIED / false | Same; no promotion |

Unknown API revisions do not implicitly enable v2.1. Revision alone is insufficient: required features and exact known input/advertised output ports must also match. A subset of recognized output ports may be presented; unknown port semantics are blocked. No fallback calculation is performed locally.

## Graph and UI

The existing bounded document schema gains optional `edges[].fromPort` (omission means `value`) and optional explicit `outputs:[{node,port}]`. Strict named identities are node-local; repeated `value` or `mae` on different nodes are distinct. Old clients fail closed on unsupported fields/kinds. New documents retain limits12computational nodes/24edges/2000samples/source/256KiB. Execution/audit output refs are bounded to64 and responses to2MiB; Math independently enforces total values/work. Audit requests can reach engine resource bounds earlier than an unaudited request.

The library advertises only negotiated sum, rolling-mean, derivative, integral, overlay, compare and fixed models. Output circles, pointer/keyboard connection controls and edge relinking select actual named ports. The legacy user-formula model is distinct from a fixed engine model. Source and formula unit strings are inert declarations, max96characters; no unit syntax/algebra is implemented in Terminan. The units endpoint is bounded, exact-schema, same-origin, fixed-loopback, opt-in and rejects mismatched/nonfinite/authority-bearing descriptions.

Results and visibility use `(node,port)` throughout, including descriptive metrics. Comparison `rmse/mae/bias` are single scalar observations at the last input timestamp, drawn as points at that time rather than a line extended into the past. Downstream scalar results retain their final timestamp. Scientific sample values and metrics are exclusively produced by Math.

## Digest and temporal verification

`lab_protocol.js` compiles inert requests and computes cryptographic consistency checks. It does not parse/evaluate formulas or calculate numerical models/statistics. Canonical request hashing matches pinned Math sorting of nodes, edge digests and object keys. There is no server root `resultSHA256` field: the client records its own canonical result/trace digest as a receipt, not a signature or independent attestation.

Every actual dependency port and every default value port is requested as audit data, in addition to visual outputs. Before rendering, the verifier checks:

- exact requested `(node,port)` identity/order and uniqueness;
- definitionSHA256 for the exact submitted node;
- each returned port's data digest against default outputSHA256 / portOutputs;
- dependency node/input/output identity, topological order and the actual selected port's digest (MAE never borrows the difference-series digest);
- explicit declared unit strings, port types and source/provenance/reference binding;
- finite values, integer monotonic timestamps, availability<=timestamp<=asOf;
- structural timestamp/availability propagation for pointwise/binary/lag/window/calculus metadata, with no sample-value calculation;
- compare scalar final-time semantics, false authority/proof flags and NOT_VERIFIED knowledge.

Self-consistent malicious metadata with recomputed hashes is still rejected when it contradicts declared units, port types or causal metadata. These checks do NOT prove mathematical accuracy, source authenticity, scientific applicability, book licensing, real availability time or host integrity. Caller time/provenance remains UNATTESTED.

Audit data is retained in experiment snapshots; only selected visual outputs are plotted. Verification receipts and server unit descriptions are available in experiment details. Editing aborts/invalidate requests; downgrade preserves documents/history and blocks incompatible execution.

## Control experiment and tests

Copied control fixture `terminan/math-example.json` is the pinned `examples/scientific-composition.v21.json`. Engine docs/source specify: square[5,17,37], trailing mean[11,27], prior[5,17], signed differences[6,10], MAE8, RMSE≈8.24621125123532. The button imports this document; it does not calculate expected values. Tests assert literal expected values and timestamps from pinned sources/docs.

Primary Node tests include self-consistent digest corruption, false authority, missing/duplicate ports, cycles, mixed types, declared units, causal availability, scalar final-time and actual MAE dependency hashes. Browser tests cover real control execution, independently visible ports, downgrade, server errors, compound units, stale replies, imports/history and legacy workflows. A separate real v2.0 suite uses the retained lock and applicable browser cases without v2.1 scenarios. Hosted workflows require Chromium/Firefox; local Firefox failure is separately reported if the host cannot launch it.

## Limitations and admission

Only the pinned known model/port contracts are supported, not arbitrary catalogue plugins. Source entry is manual historical/synthetic data; no Grid/PG/live market source is added. Book catalogue remains host-configured and empty by default. Compound dimensional conversion, numerical algorithms and domain assumptions remain Math-owned. This is software/protocol integration, not mathematical proof or trading authority.

The user-reported original physical ADMINIT scenario has no independently supplied receipt here. New local isolated browser observations do not attest the installed ADMINIT system. No merge/deployment, installed ADMINIT, PostgreSQL, Norton, Grid or trading changes are made. Exact-head hosted success may only be stated after actual job completion and artifacts.
