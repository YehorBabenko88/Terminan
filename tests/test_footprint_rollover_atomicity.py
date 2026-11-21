import unittest
from copy import deepcopy
from decimal import Decimal as D
from types import SimpleNamespace
from terminan.analytics.footprint_engine import FootprintEngine

def trade(ts=1,quantity=D('1'),side='Buy',price=D('100')):
    return SimpleNamespace(symbol='BTCUSDT',timestamp_ms=ts,price=price,quantity=quantity,taker_side=side)

class FootprintRolloverAtomicityTests(unittest.TestCase):
    def test_refused_future_trade_never_closes_or_replaces_current_footprint(self):
        for time in (60001,180001):
            for qty,side,price in ((D('NaN'),'Buy',D('999')),(D('1'),'other',D('100')),(D('1'),'Buy',D('0'))):
                with self.subTest(time=time,side=side):
                    engine=FootprintEngine({'BTCUSDT':D('.01')})
                    original=engine.execution(trade(),contiguous=True);before=deepcopy(engine.__dict__)
                    with self.assertRaises(ValueError):engine.execution(trade(time,qty,side,price),contiguous=True)
                    self.assertIs(engine.current['BTCUSDT'],original)
                    self.assertEqual(engine.__dict__,before)
    def test_refused_late_trade_never_changes_current_trust(self):
        engine=FootprintEngine({'BTCUSDT':D('.01')})
        current=engine.execution(trade(60001),contiguous=True);before=deepcopy(engine.__dict__)
        with self.assertRaises(ValueError):engine.execution(trade(1,D('NaN')),contiguous=True)
        self.assertIs(engine.current['BTCUSDT'],current);self.assertEqual(engine.__dict__,before)
    def test_valid_rollover_and_late_gap_policy_are_preserved(self):
        engine=FootprintEngine({'BTCUSDT':D('.01')})
        first=engine.execution(trade(),contiguous=True)
        next=engine.execution(trade(60001),contiguous=True)
        self.assertIs(engine.closed[0],first);self.assertTrue(first.trusted)
        self.assertIs(engine.current['BTCUSDT'],next)
        self.assertIsNone(engine.execution(trade(2),contiguous=True));self.assertFalse(next.trusted)
