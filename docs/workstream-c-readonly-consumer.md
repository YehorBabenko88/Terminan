# Workstream C: bounded read-only consumer

Frozen unified-system contract: `50e6e63cb183f6dcf1dee3c753f966717ee3b110`.
PR9 head `0ad0f36edce2ac7717c753d35ebe113dc6334fd0` is an ancestor of
PR20 head `3ed51d908b80a0fa9fee5d72999ca2184f309bec`. The latter is the
frozen independent branch base, retaining transport cleanup fixes. No source
branch is modified. No AGENTS.md was present in this checkout.

Source-owned v1 contract pins: Strattester PR42
`ef1c53861998188bdd03b9f037dc45573b3c2acb`; Grid PR248
`4ad202996ac06116e336b66851beb6e97beffa26`. These are reviewed contract
identities, not attestations of a running service. Runtime identity stays
UNVERIFIED.

`GET /api/consumer/v1/status` exposes presentation labels from the existing
versioned read-only adapter: UNAVAILABLE, STALE, GAP (partial window), HISTORICAL,
and explicit historical aggregate/synthetic provenance. Runtime identity remains
UNVERIFIED and coverage is never promoted to verified by a label.

Optional `TERMINAN_STRATTESTER_CONTRACT_PORT` and
`TERMINAN_GRID_CONTRACT_PORT` enable GET-only capabilities/health consumption
on numeric `127.0.0.1` ports. No URLs, redirects, proxy, credentials or exchange
connections are accepted. Responses are bounded to 64 KiB and socket timeout
250 milliseconds per socket operation and a five second socket shutdown watchdog
covering request, response headers and body across both endpoints per source.
These source-owned v1 APIs currently advertise no
qualified data: status stays UNAVAILABLE. A reachable API is not provenance
qualification. No results/candles/footprint API is requested. This is a bounded
failure presentation integration, not a completed historical-data integration.

Blockers: source A results lack immutable dataset identity/provenance; source B
lacks market type/epoch/freshness/release qualification. Pinned unified-system
supervisor snapshot has no API version, timestamp or independently authenticated
identity and its adapters explicitly accept only synthetic data. Supervisor
therefore stays UNAVAILABLE with VERSIONED_SUPERVISOR_CONTRACT_NOT_PUBLISHED;
no new upstream supervisor schema is invented. Historical/synthetic labels do
not establish real physical acceptance or trading authority.

SYNTHETIC: Python contract tests, Windows loopback HTTP and Playwright Chromium
DOM tests. HOSTED: exact-head workflow records SHA/run/attempt, separate from
local checks. PHYSICAL: NOT_RUN. G1 Execute/Cleanup/live trading NOT_AUTHORIZED.
