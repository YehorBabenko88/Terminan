import unittest
from decimal import Decimal as D
from copy import deepcopy
from types import SimpleNamespace
from terminan.analytics.footprint import Footprint
from terminan.analytics.book_summary import summarize_book
from terminan.analytics.tape_velocity import TapeVelocity

class AnalyticsQualityTests(unittest.TestCase):
    def test_invalid_footprint_trade_does_not_create_cell_or_advance_trust_clock(self):
        for quantity,side in ((D('NaN'),'Buy'),(D('1'),'other')):
            fp=Footprint('BTCUSDT',0,60000,D('.01'));before=deepcopy(fp)
            event=SimpleNamespace(symbol='BTCUSDT',timestamp_ms=1,price=D('100'),quantity=quantity,taker_side=side)
            with self.assertRaises(ValueError):fp.add(event,contiguous=False)
            self.assertEqual(fp,before)
    def test_crossed_book_returns_unverified_view_without_math_or_signal(self):
        book=SimpleNamespace(symbol='BTCUSDT',valid=True,bids={D('102'):D('1')},asks={D('100'):D('1')})
        self.assertFalse(summarize_book(book,D('.01')).valid)
    def test_tape_boundary_uses_exact_math_predicate_not_display_rounding(self):
        tape=TapeVelocity(D('.001'),proximity_ticks=9)
        event=SimpleNamespace(symbol='BTCUSDT',timestamp_ms=1000,price=D('1.009000000000000000000000000000001'),quantity=D('1'),taker_side='Buy')
        view=tape.add(event,D('1'),contiguous=True)
        self.assertFalse(view.trusted)
