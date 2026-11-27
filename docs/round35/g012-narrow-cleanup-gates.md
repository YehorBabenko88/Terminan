# Agent D — ROUND 35 — G012 narrowly scoped duplicate retirement gate

**STATUS: BLOCKED — CODE NO_GO / PRODUCTION NO_GO.** This is a
test-and-evidence plan, not permission to remove historical code, route
records, change provenance, trade, or merge.

## Exact independently reproducible evidence to date

At candidate `fe4316d7c1580b9799903b57d8471034b5281996`, the original
four-cell hosted matrix on Windows and Ubuntu, Python 3.11/3.12, passed:
72 existing B-D HTTP tests, 12 original D129-vs-Grid/Math/D G012 differential
tests (3 per cell). The two real Chromium and three historical-vector tests
also passed on that exact commit, with raw jobs under workflow runs 46026544862
and 46026544857. The current expanded differential is a *new* SHA, and inherits
**no PASS** until its own original execution.

The original historical 68-line D129 aggregator comes from Terminan commit
`6e4a39c185d51eeab37f004964655da3b8dd938b`, immutable
`terminan/qualified_partial.py` blob
`27cd754b97a0a8c32b0ec51daac41110dca35292`.
The original historical Math D167 is
`14d9ca92803b3ede19c7292e85c3627554d5c1d9`,
blob `aebe6f799ffe2c20c9b68daad10b96764c245246`.
The tested production candidates are Grid B310
`e5864a933dc407b2ccc10a91cb2520e21ebfc447`,
Math `9e6acbd9e12a91189f57234828e31640983af553`,
and D consumer `terminan/qualified_rollup.py` blob
`77c6855c52030d5d9b0e839e0c9245b947db41b5`.

## Exact prospective narrow cleanup target

Only after independent H/G review of **all** required invariants, identify
the exact legacy implementation symbol `qualified_timeframe_rows` in
`terminan/qualified_partial.py` and its reachable consumers. Do not remove
the entire module or `qualified_partial.py`: it also contains the separately
used managed v2 qualification logic. Do not delete the historical D129 source,
Math D167 source or test-only pinned read fixtures. A future deletion PR must
show symbol-level call graph and the absence of a runtime caller, with an
explicit positive canonical Grid/Math replacement per consumer.

This prospective removal **does not** authorize removing any richer datasets:
raw trades, tick archives, source 1m, footprint/delta/POC, OI, funding,
mark/index/premium, long-short, turnover, SQLite offline history, historical
as-of metadata, provider acquisition windows, epoch/fingerprint/lease
provenance, or unavailable states.

## Blocking acceptance gates

1. **Same-input numerical and temporal parity:** old 68-line original versus
   Grid/Math/Terminan canonical 5m and 15m, 1..5 windows,
   Decimal exact stored source presentation, buy/sell/volume/delta,
   OHLC, open/close clocks, trade-count presentation, closed bars,
   contiguous minutes, deterministic fingerprints. Fail-closed for
   missing, duplicated, shifted, cross-epoch, stale and malformed source.
2. **History preservation:** independently test original G's
   SQLite closed/reopened, read-only eight-dataset preservation and
   current Grid historical as-of cutoff; no lookahead, old/new
   retention/precision/provenance and explicit NOT_ATTESTED flags.
3. **No authority promotion:** verify bearer/current lease pre/post read,
   `read_only=true`, `execution_authority=false`,
   `paper_admitted=false`, `trading_authorized=false`,
   `exchange_completeness=NOT_ATTESTED`, no hidden legacy fallback.
   B observational roster is INFORMATIONAL, never authoritative/delist.
4. **Original running CI / independent acceptance:** exact final SHA
   Windows and Linux, native isolated PG18/Consul when those dependencies
   govern installed operation, real Chromium and absent/negative UI
   persistence. H, G, J and F independently review exact blobs and logs;
   a green synthetic test alone cannot prove provider completeness.
5. **One narrow cleanup PR, later:** manifest source/ref/consumer inventory,
   before/after test proof, negative branch coverage, rollback support,
   no removed unique fields, no main merge until MASTER authorization.
   Report PASS/FAIL/ERROR/SKIP/NOT_RUN separately with exact job IDs.

**At this stage no candidate is approved for deletion.**
