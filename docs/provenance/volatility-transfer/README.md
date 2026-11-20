# Volatility owner handoff — source candidate only

Old→new: Strattester VolatilityObservatory.snapshots→Terminan VolatilityAnalyzer.analyze; numerical formulas→Math causal_volatility_metrics. VolatilitySnapshot→VolatilityMetrics, event_time→event_start_ms, known_at→available_at_ms, atr_pct→atr_fraction, realized_vol→realized_volatility, parkinson_vol→parkinson_volatility, range_pct→range_fraction, volume_expansion→volume_ratio, turnover_expansion→turnover_ratio, percentile→atr_percentile. No legacy aliases.

Raw original implementation/test inputs from Data b5ca6363be1f530fbbb4c44fdc1e8f747aaef87d are retained solely as provenance. Three original tests preserve every assertion through declared field/name changes. Four added adapter tests prove actualMath delegation, closedABI, frozenDTO/configuration and noauthority.

Legacy scalp_bootstrap/scientific_bootstrap and trade_context/scalp_entries consumers are not yet migrated; originalData implementation remainsHELD until consumers and independent QA are accepted. No original547 count deduction. No data/provider/strategy execution is introduced.

ABI v2 requires an explicit caller-declared available_at_ms on every candle; there is no bar-close default. Math computes the maximum clock of the entire consumed prefix. VolatilityMetrics labels this CALLER_DECLARED_PREFIX_MAX and NOT_EVALUATED source authentication; it is not historical availability/PIT evidence. Synthetic test fixtures explicitly supply t+60 clocks solely to preserve original numerical assertions.
