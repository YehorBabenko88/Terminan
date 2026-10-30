# D infrastructure dashboard migration

Exact owner sources: Terminan PR48 `d10d5a0e2f00fcd68e284d2b6e743f61430997c9`; Math PR97 `b92cd96ab5a8cab048524b311f565f4fe1937b1f`; Unified integration starting base `b8facc028e00493d8423d15280f87c2047c2b63b`. Source branches remain unchanged. These pins identify source revisions, not source observation authenticity.

`/infrastructure` is an additive read-only dashboard. `/api/infrastructure` reads only `TERMINAN_LIFECYCLE_SNAPSHOT`, a local export of Unified `unified.lifecycle.v1` (max 256KiB). An absent, oversized or invalid export is explicitly UNAVAILABLE. No default network request, module launch, discovery, installation or DB access occurs. Existing monitor/Math tabs remain available. Fleet nodes accept A's id, epoch, sequence, state, zone, last_heartbeat_ms, cpu, memory, disk, available_resources, db_sizes, modules and identity_verified fields. Null utilization and sizes remain UNAVAILABLE. Capacity units never become utilization ratios. Six initial empty slots are labeled UNAVAILABLE; observed topology renders 0/1/5/6/7+ nodes. No links are inferred; explicit verified endpoint links are still caller assertions, not independent host evidence.

Lifecycle uses epoch/sequence and bounded stage counters. Latest refresh generation wins and aborts stale fetches. Search, state and heartbeat-window filters operate on the observed snapshot. Details are text-only. Math status stays independent and paper remains NOT_AUTHORIZED.

| Source functionality | Migration | Remaining |
|---|---|---|
| Terminan PR48 Grid monitor | Preserved; separate Unified infrastructure view | P1 authenticated live snapshot transport |
| Unified A fleet | Source snapshot fields; no synthetic physical nodes | P0 owner-approved physical identity and provisioning |
| Unified B lifecycle | Explicit ordered stage/counters export | P1 durable snapshot export deployment |
| Math PR97 engine | Independent bounded API in Math PR99 | P1 optional dashboard experiment history |
| Research/Grid health | Display explicit provider status; absence UNAVAILABLE | P0 source-qualified deployment receipts |

SOFTWARE: unit and real Chromium controls tested against labeled synthetic fixtures. SOURCE_PROVENANCE: UNVERIFIED for snapshot observations. PHYSICAL: NOT_RUN. PRODUCTION: NO_GO. P2 richer visual charts await real telemetry. CI PASS does not attest source authenticity, network links, physical hosts or trading authority.
