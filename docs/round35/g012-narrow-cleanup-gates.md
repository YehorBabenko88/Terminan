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

**Current candidate source finding (verified at 9e6c5379):** the symbol
`qualified_timeframe_rows` is ALREADY ABSENT from the current
`terminan/qualified_partial.py` (blob
`f743205fd4deedaca55dff8d7bd822300e209f52`).
It exists in the preserved *historical D129* blob
`27cd754b97a0a8c32b0ec51daac41110dca35292` used by the
test-only differential. Therefore there is **no current D136 production
implementation of that symbol left to delete**; producing a deletion patch
for it would be fictitious. No entire-module removal is authorized.
Current `terminan/data.py` blob
`7c656355a68c27c3ad24ef55c15f80fece4c701c`
still calls `validate_qualified_v2`/`chart_rows` from
`qualified_partial.py` for managed 1m, and calls
`validate_qualified_rollup`/`chart_rollup_rows` from
`qualified_rollup.py` for 5m/15m LIVE and HISTORICAL.
The current rollup consumer blob is
`77c6855c52030d5d9b0e839e0c9245b947db41b5`.
Thus both current modules have live, distinct consumer responsibilities,
not a proved duplicate pair.

The next meaningful narrow cleanup search must occur in any *other still
deployed* owner/runtime copy of the historical G012 aggregator, with an
exact immutable source blob, actual caller graph, and proof of canonical
cutover. Preserve D129 and D167 archived test-only blobs and all their
receipts. Do not remove the whole qualified_partial module, its 1m
adapters, or either 5m/15m LIVE/HISTORICAL adapter. Any future cleanup PR
must demonstrate a concrete still-present production symbol, its callers,
a source-exact replacement and H/G/J/F independent acceptance.

This prospective removal **does not** authorize removing any richer datasets:
raw trades, tick archives, source 1m, footprint/delta/POC, OI, funding,
mark/index/premium, long-short, turnover, SQLite offline history, historical
as-of metadata, provider acquisition windows, epoch/fingerprint/lease
provenance, or unavailable states.

## Blocking acceptance gates

1. **Same-input numerical and temporal parity:** compare old original
   D129's actual limited output **OHLCV + start/closed clocks only**
   against Grid/Math/Terminan canonical 5m and 15m, bounded 1..5 windows.
   D129's original 68-line `qualified_timeframe_rows` does NOT output
   delta, directional buy/sell, trade count, turnover, OI, footprint or
   provider-raw trades: asserting old-vs-new equality for absent fields
   is invalid. Separately require canonical Math exact stored-1m
   buy/sell/volume/delta consistency, source minute fingerprints,
   timestamps and original source retention. Current new historical-as-of
   test is a *candidate*, not yet original CI executed. Missing, duplicate,
   shifted, cross-epoch, stale and malformed source must fail closed.
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

\n**Disposition of current Terminan D136:** the D129-only aggregate function
is already absent in the deployed-source candidate; no deletion diff is
available or warranted in this repository. The cleanup deliverable for D is
the source-exact no-deletion finding and independent data-lineage gate.
Other owners must identify and prove an actual still-present duplicate
before asking MASTER for a symbol-only deletion.\n
**At this stage no candidate is approved for deletion.**
