# Exact numeric loopback resolver exemption — 2026-11-10

Source-only successor from47530d8/PR79. Root f originals show PAGE_NAVIGATE
11963→12007ms failed ERR_NAME_NOT_RESOLVED, page_requests1/blocked0, no DOM or
screenshot. Node returned1 with natural idle, independently confirmed owned
cleanup and no watchdog. Full f is FAIL; these facts do not diagnose e or office DNS.

Primary Chromium source at exact tag141.0.7390.37 was read, not executed:

- [host_mapping_rules.cc](https://github.com/chromium/chromium/blob/141.0.7390.37/net/base/host_mapping_rules.cc),
  Git blob fec058db4f7c10062355f1f2f9ef5093eb0eeb54, lines41–66 matches host
  strings to MAP patterns before checking exclusion patterns, without a numeric
  IP bypass. EXCLUDE localhost does not match127.0.0.1. Lines98–120 parse separate
  map/exclusion lists. This is an established source mismatch, not a DNS probe.
- [mapped_host_resolver.cc](https://github.com/chromium/chromium/blob/141.0.7390.37/net/dns/mapped_host_resolver.cc),
  Git blob588fac6bc4f797e2ddf5dcf9d1782b66093b19a8, lines31–70 rewrites before
  delegation and maps an invalid URL rewrite to ERR_NAME_NOT_RESOLVED. The special
  HostPortPair sentinel is ^NOTFOUND, not ~NOTFOUND. Root's later direction
  supersedes its initial preserve-tilde caution: use canonical ^NOTFOUND so both
  reviewed paths explicitly fail closed. Equivalence of tilde/caret is not assumed.
  Linking this mismatch to the actual f error remains inference
  until Root's new immutable package retest, not an e/office causal RCA.

One runtime line changes (canonical deny sentinel plus exact loopback exemption):

`--host-resolver-rules=MAP * ^NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1`

The wildcard deny and existing localhost exception remain; exactly one
literal127.0.0.1 exemption is added and the canonical caret sentinel closes both
primary overload paths. No127.* /LAN/domain/subnet/IPv6 wildcard.
HostMappingRules exclusions are host-based, not this one ephemeral port. Separate
existing page allowRequest still pins numeric host+exact ephemeral port+three GET
routes, and CSP connect-src none remains. The resolver flag/page gate does NOT
prove all browser-native OS traffic denied; Root's isolation scope is unchanged.
No proxy/TLS/certificate/sandbox/security-policy/network-setting changes are made.

Pure regressions inspect actual launchOptions and route helpers, including external
host/LAN/link-local/distinct127 addresses/IPv6/localhost endpoint rejection, wrong
ports/methods/queries and unchanged CSP. They DO NOT implement a fake Chromium
resolver or qualify actual DNS, browser URL canonicalization, connection behavior,
OS egress or a successful render. Noncanonical aliases of the same IPv4 address
may be canonicalized by Chromium before interception; no contrary runtime claim
is inferred from raw string helper checks. Initial RED is1missing-exemption failure
plus4existing-boundary controls. The superseding canonical-sentinel regression has
its own RED. CHROMIUM-141-SOURCE.json pins reviewed primary blob/SHA identities and
both overload facts; unit assertions bind that manifest and actual launchOptions,
not a fake resolver implementation or a rerun of Chromium's C++ tests. Only source
fetch/hash verification authenticated primary bytes; units do not fetch networks.

Bootstrap/OWN cleanup deadline/guard/renderer/digests/per-read checks, Root20s/USER10s/
1GiB and PS-batching DESIGN_PENDING are preserved. SDK/browser/PS/Job/native fixtures
and diagnostic reruns by A6 remain NOT_RUN. Only Root may prepare/review a NEW
source/package/state and perform any separately admitted retest. Overall NO-GO.
