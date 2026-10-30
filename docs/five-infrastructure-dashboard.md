# D infrastructure dashboard migration

Exact owner sources: Terminan PR48 `d10d5a0e2f00fcd68e284d2b6e743f61430997c9`; Math PR97 `b92cd96ab5a8cab048524b311f565f4fe1937b1f`; Unified integration starting base `b8facc028e00493d8423d15280f87c2047c2b63b`. Source branches remain unchanged. These pins identify source revisions, not source observation authenticity.

`/infrastructure` is an additive read-only dashboard. `/api/infrastructure` reads only `TERMINAN_LIFECYCLE_SNAPSHOT`, a local export of Unified `unified.lifecycle.v1` (max 256KiB). An absent, oversized or invalid export is explicitly UNAVAILABLE. No default network request, module launch, discovery, installation or DB access occurs. Existing monitor/Math tabs remain available. Fleet nodes accept A's id, epoch, sequence, state, zone, last_heartbeat_ms, cpu, memory, disk, available_resources, db_sizes, modules and identity_verified fields. Null utilization and sizes remain UNAVAILABLE. Capacity units never become utilization ratios. Six initial empty slots are labeled UNAVAILABLE; observed topology renders 0/1/5/6/7+ nodes. No topology edges render: caller verified flags are ignored until independent owner-link receipt admission exists. Snapshots require exact integer API1.0 and all seven lifecycle stages in canonical order. Inputs must be bounded local regular files; UNC/device paths, reparse points and malformed recursive JSON fail closed.

Lifecycle uses epoch/sequence and bounded stage counters. The view explicitly operates as a manual snapshot monitor. Latest refresh generation wins and aborts stale fetches; a stalled refresh becomes UNAVAILABLE after an absolute three-second deadline. Canonical fleet filters include ACTIVE, APPROVED, SUSPECT, OFFLINE, QUARANTINED and RETIRED. Selected details always update from the newest snapshot. Search, state and heartbeat-window filters operate on the observed snapshot. Details are text-only. Math status stays independent and paper remains NOT_AUTHORIZED.

| Source functionality | Migration | Remaining |
|---|---|---|
| Terminan PR48 Grid monitor | Preserved; separate Unified infrastructure view | P1 authenticated live snapshot transport |
| Unified A fleet | Source snapshot fields; no synthetic physical nodes | P0 owner-approved physical identity and provisioning |
| Unified B lifecycle | Explicit ordered stage/counters export | P1 durable snapshot export deployment |
| Math PR97 engine | Independent bounded API in Math PR99 | P1 optional dashboard experiment history |
| Research/Grid health | Display explicit provider status; absence UNAVAILABLE | P0 source-qualified deployment receipts |

SOFTWARE: unit and real Chromium controls tested against labeled synthetic fixtures. SOURCE_PROVENANCE: UNVERIFIED for snapshot observations. PHYSICAL: NOT_RUN. PRODUCTION: NO_GO. P2 richer visual charts await real telemetry. CI PASS does not attest source authenticity, network links, physical hosts or trading authority.

## Independent nested consumer validation (2026-10-30)
The local export is untrusted. The consumer independently accepts the exact Unified v1 PLAN_ONLY fleet shape, empty links/databases/alerts and false identity/execution authority. Current producer utilization and database sizes must be null. Available resource capacity is bounded finite numeric data labeled UNATTESTED; it never becomes CPU/RAM/disk utilization. Future authenticated telemetry needs a separately reviewed versioned contract.

Compatibility is limited to historical exports with fleet nodes containing only id and optional cpu:null; their missing fields project UNAVAILABLE and identity remains false. Historical links remain discarded. Extra fleet/node/stage/module/top-level fields, authority upgrades and invalid bounds fail closed. Core API remains exact integer 1.0. No unknown dictionaries are copied into the display. Existing controls and dynamic fleets remain available.

Negative regressions reproduced the original acceptance of forged identity_verified, execution_authorized and db_sizes. Added exact-producer positive/negative tests and Chromium coverage that runs the actual Python consumer on a forged source before rendering its unavailable result. All browser controls, timeout and stale response tests remain intact. Physical NOT_RUN; production NO_GO.
