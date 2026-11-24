# Original producer fixture counterparts

Four existing canonical tests now carry original-ID subtests; two catalog roles map to existing catalog tests in tests/original_producer_counterparts_v1.json. The original five scalp tests and separate catalog test remain Data-owned and unretired.

Sweep, breakout and profile use an explicit synthetic M1 clock mapping: original0/60/120/180 milliseconds become0/60000/120000/180000 milliseconds. Prices and declared volatility/profile numeric fields remain exact. This is an intentionally changed fixture cadence, not literal clock equivalence, an adapter, or a rewrite of historical market data. Each counterpart also demonstrates raw60ms OHLC refusal at canonical M1 generator admission. Existing ordinary execution fixtures keep raw60ms unchanged.

Continuation accepts explicit arbitrary body durations, so its original60/120 clocks remain unchanged. Original OHLC100/104/99/103 projects to CandleBodyObservation open100 close103; high104 and low99 are deliberately omitted by the body-only API. Original default bar volume100 is also absent from canonical OHLC/body input records; no flow observation is fabricated.

Original VolumeProfileSnapshot fields are poc, vah, val, known_at, mode, value_area_width. Canonical ProfileSummary renames them to poc, value_area_high, value_area_low, available_at_ms, kind, value_area_width. Original100/101/99/120/TRADE_POC/2 maps to100/101/99/120000/TRADE_DISTRIBUTION/2. Sixth2 is width, never a trade count. This corrects the earlier read-only report outputs/readonly-producer-exact-vectors-1795524483856/report.json. Missing flow remains None; legacy synthetic delta0 is not retained as an observation.

Catalog set/callable/output/refusal tests already distinguish exactly four canonical v2 generators and reject legacy IDs/URIs. Their two original-ID mappings are provenance only; no duplicate runtime tests or compatibility aliases are added. RESEARCH_GENERATOR confers no execution authority.

The installed checker binds the closed contract bytes, archived source bytes and counterpart test bytes, and requires all four labeled subtests to execute successfully. The374 ordered roster is unchanged. No runtime, wheel, Data deletion, publication or retirement deduction is part of this change. Full374 qualification belongs to the later combined cohort.
