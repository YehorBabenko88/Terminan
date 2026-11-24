import math
from terminan.volatility import VolatilityAnalyzer,VolatilityRegime

def _bar(t,o,h,l,c,v=100,turnover=10000):
    return {'event_start_ms':t,'available_at_ms':t+60,'open':o,'high':h,'low':l,'close':c,'volume':v,'turnover':turnover}

import unittest
class VolatilityTransferTests(unittest.TestCase):
    def test_observatory_computes_causal_metrics_and_regime(self):
        bars=[
          _bar(0,100,101,99,100),
          _bar(60,100,102,99,101),
          _bar(120,101,103,100,102),
          _bar(180,102,106,101,105,200,21000),
          _bar(240,105,110,104,109,300,32700),
        ]
        obs=VolatilityAnalyzer(window=3,percentile_lookback=10,version='vol-v1')
        xs=obs.analyze(bars,bar_duration_ms=60)
        x=xs[-1]
        assert x.available_at_ms==300
        assert x.atr_fraction>0
        assert x.realized_volatility>=0
        assert x.parkinson_volatility>=0
        assert x.range_fraction>0
        assert x.volume_ratio>1
        assert x.turnover_ratio>1
        assert x.regime in set(VolatilityRegime)
    
    def test_future_rows_cannot_reclassify_old_snapshot(self):
        base=[
          _bar(0,100,101,99,100),
          _bar(60,100,102,99,101),
          _bar(120,101,103,100,102),
          _bar(180,102,104,101,103),
        ]
        future=_bar(240,103,150,50,140,10000,1400000)
        obs=VolatilityAnalyzer(window=2,percentile_lookback=10)
        a=obs.analyze(base,bar_duration_ms=60)[-1]
        b=[x for x in obs.analyze(base+[future],bar_duration_ms=60) if x.event_start_ms==a.event_start_ms][0]
        assert a==b
    
    def test_percentile_uses_only_prior_history(self):
        bars=[
          _bar(0,100,101,99,100),
          _bar(60,100,101,99,100),
          _bar(120,100,102,98,101),
          _bar(180,101,106,95,104),
        ]
        xs=VolatilityAnalyzer(window=2,percentile_lookback=10).analyze(bars,bar_duration_ms=60)
        assert xs[-1].atr_percentile>=xs[-2].atr_percentile
    
class CanonicalVolatilityBoundaryTests(unittest.TestCase):
    def test_adapter_calls_actual_math_once_and_does_not_grant_authority(self):
        from unittest.mock import patch
        import market_compute_api as api
        rows=[_bar(0,100,101,99,100),_bar(60,100,102,99,101)]
        with patch.object(api,'causal_volatility_metrics',wraps=api.causal_volatility_metrics) as compute:
            result=VolatilityAnalyzer(window=2).analyze(rows,bar_duration_ms=60)
        compute.assert_called_once_with(rows,window=2,percentile_lookback=252,bar_duration_ms=60)
        self.assertFalse(result[0].execution_authority);self.assertFalse(result[0].trading_authorized)
        self.assertEqual(result[0].source_authentication,'NOT_EVALUATED')
    def test_unknown_math_abi_refused(self):
        from unittest.mock import patch
        with patch('market_compute_api.VOLATILITY_ABI','unsupported'):
            with self.assertRaises(RuntimeError):VolatilityAnalyzer().analyze([],bar_duration_ms=60)
    def test_result_and_configuration_are_frozen(self):
        from dataclasses import FrozenInstanceError
        analyzer=VolatilityAnalyzer(window=2)
        result=analyzer.analyze([_bar(0,100,101,99,100),_bar(60,100,101,99,100)],bar_duration_ms=60)
        with self.assertRaises(FrozenInstanceError):analyzer.window=3
        with self.assertRaises(FrozenInstanceError):result[0].execution_authority=True
    def test_invalid_configuration_is_not_silently_coerced(self):
        with self.assertRaises(ValueError):VolatilityAnalyzer(version=True)
        with self.assertRaises(ValueError):VolatilityAnalyzer(window=True).analyze([],bar_duration_ms=60)
    def test_delayed_declared_clock_is_not_replaced_by_bar_end(self):
        rows=[dict(_bar(0,100,101,99,100),available_at_ms=1000),_bar(60,100,102,99,101),_bar(120,101,103,100,102)]
        values=VolatilityAnalyzer(window=2).analyze(rows,bar_duration_ms=60)
        self.assertEqual([value.available_at_ms for value in values],[1000,1000])
        self.assertTrue(all(value.availability_basis=='CALLER_DECLARED_PREFIX_MAX' for value in values))
        self.assertTrue(all(value.source_authentication=='NOT_EVALUATED' and not value.execution_authority for value in values))
    def test_missing_availability_is_not_inferred_by_adapter(self):
        row=_bar(0,100,101,99,100);del row['available_at_ms']
        with self.assertRaises(ValueError):VolatilityAnalyzer(window=2).analyze([row,_bar(60,100,101,99,100)],bar_duration_ms=60)
