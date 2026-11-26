# ROUND 16 D — original POC arithmetic → canonical research composition

Historical source Strattester git tree \`37ff7e9d12a4d2dccd788fc493c28557dbe8bcea\`,
\`strattester/research/volume_profile.py\` blob
\`6d74dd706c720c3f801bb88ff886ca9be97235e2\`. The byte-identical
original is included under test fixtures only.

New read-only \`terminan.historical_poc_research.research_historical_poc\`
does not calculate any numeric POC or value area. It combines **existing**
Math-backed \`analyze_trade_profile\` / \`analyze_candle_proxy_profile\` and
the **existing** Terminan \`generate_profile_reclaim_entries\`. POC and proxy
are explicitly distinguished and the closed timed data batch is detached
before Math. The original arithmetic is compared by running the actual
historical profile functions from pinned tests. Math owns floats, 70% area,
binary64 accumulation, POC ties and precise output domain.

Changed historical semantics are intentional: Strattester's known_at cutoff
ignores *delivery* availability and can include late data; canonical Math
requires event_ms AND explicit available_at_ms <= decision_ms. Canonical
returns the latest observed availability instead of claiming old known_at is a
proven observation timestamp. A missing flow is None, not observed zero.
Historical trade POC and candle proxy modes cannot silently convert.

**IMPORTANT:** \`POC_MEAN_REVERSION\`, \`POC_MIGRATION\`,
\`POC_BREAKOUT_RETEST\`, \`POC_VAH_VAL_REJECTION\` remain \`SPEC_ONLY\`.
\`profile_reclaim_v2\` is a separate pre-existing canonical *research*
generator; emitting its non-authorizing entries does not establish dynamic
equivalence with a historical strategy which had no generator. Nor does
this implement any new fills, a second PaperEngine, bid/ask order execution,
spread-aware simulation or an invented backtest.

Mandatory follow-up: validate positive native same-port Root C/E PG18/Grid
cohort before treating any profile as sourced. Current implementation has no
exchange, network, file IO, SQL, production process, or trading pathway.

CODE NO_GO / PRODUCTION NO_GO.
