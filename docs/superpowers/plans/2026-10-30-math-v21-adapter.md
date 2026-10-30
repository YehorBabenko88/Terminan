# Math v2.1 adapter — approved incremental design and execution plan

Base PR52 exact0d0bb679a279fd251d3d2cc8a5ad763b0cc24910. Math PR102 exact1f97e56701c0fce01dc8dd05952111fa8df3f2d1/tree45f7b0fc99efac7d611bb7717c8ee23703b3bace. User authorizes continuous implementation without further design gates.

Architecture: preserve legacy documents and formula-model alias; add named fromPort (default value) and engine-model distinct editor kind. New operations are enabled only by revision/features/exact advertised ports. Compound unit strings remain inert declarations, parsed only by Math /v2/units/describe. A separate protocol module compiles requests and verifies canonical digests/definitions/output payloads/dependency port hashes. Request every used output as an audit output to permit independent digest recomputation; visual identity always(node,port). No scientific algorithm or units algebra in Terminan.

- [ ] RED/GREEN capability and document tests: new operations/models, exact named ports, duplicates/cycles/types, downgrade blocking, legacy imports.
- [ ] RED/GREEN protocol tests against pinned real engine: control example, all actual dependency port digests, definition/request/result receipts, time/availability/scalar-final-time/authority corruption.
- [ ] Bounded bridge /units route and multi-port response checks, UI inputs/output selection, server unit descriptions, scalar final-time markers.
- [ ] Browser real2.1 control experiment, downgrade2.0, wrong units/time/ports/server refusal, legacy workflows. Full applicable local suites and independent review.
- [ ] Own stacked Draft PR, exact-head workflows, source/tree/SHA256 evidence, compatibility table and isolated ADMINIT instructions. No installed ADMINIT/PG/Norton/Grid/trading/merge/deployment changes.

Resource choices:12compute nodes/24edges/64requested output/audit refs,2000samples/source,256KiBrequest/2MiBresponse,40history snapshots retained. Engine has independent stricter total-work/value bounds. V2.0 continues value-only; new operations never fall back to local evaluation.
