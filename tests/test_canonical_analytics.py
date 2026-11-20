import unittest
from decimal import Decimal

class CanonicalAnalyticsTests(unittest.TestCase):
    def test_canonical_stream_and_presentation_without_retired_package(self):
        from terminan.analytics.orderflow_adapters import from_records
        from terminan.analytics.orderflow_aggregation import aggregate_by_price
        rows=from_records([dict(timestamp_ms=1,price='1.009',volume='100.00001',side='buy'),dict(timestamp_ms=2,price='1.009',volume='0.00002',side='buy')])
        result=aggregate_by_price(rows,Decimal('0.001'))
        self.assertEqual(result[0][0],Decimal('1.009'))
        self.assertEqual(result[0][1].buy_volume,Decimal('100.00003'))

    def test_only_canonical_paper_engine_is_exported_by_analytics(self):
        from terminan.analytics import core
        self.assertFalse(hasattr(core,'PaperEngine'))
        self.assertFalse(hasattr(core,'Position'))

    def test_active_level_annotations_reject_retired_owner(self):
        from terminan.metascalp_levels import owned_id
        self.assertIsNone(owned_id(dict(id=1,note='meta_analyse:old')))
        self.assertEqual(owned_id(dict(id=2,note='terminan:current')),2)

class RefusedAnalyticsStateTests(unittest.TestCase):
    def test_refused_minute_trade_never_changes_ohlc_or_volume_state(self):
        from datetime import datetime,timezone
        from copy import deepcopy
        from terminan.analytics.core import Minute,Trade
        stamp=datetime(2026,11,20,tzinfo=timezone.utc)
        bad=[dict(size=Decimal('NaN')),dict(size=Decimal('1E999999')),
             dict(side='invalid'),dict(high=Decimal('NaN')),dict(low=Decimal('2000'))]
        for change in bad:
            minute=Minute(stamp,Decimal('0.01'),Decimal('100'),Decimal('100'),Decimal('100'),Decimal('100'))
            before=deepcopy(minute)
            args=dict(symbol='BTCUSDT',time=stamp,price=Decimal('999'),size=Decimal('1'),side='buy')
            args.update(change)
            with self.assertRaises((ValueError,ArithmeticError)):minute.add(Trade(**args))
            self.assertEqual(minute,before)
