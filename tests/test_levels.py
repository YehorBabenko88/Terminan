import unittest
from terminan.levels import untouched_levels,merge_levels

class LevelTests(unittest.TestCase):
    def test_high_low_touch_invalidation(self):
        h=3600000
        rows=[dict(t=0,h=100,l=90),dict(t=h,h=99,l=91),dict(t=2*h,h=101,l=92)]
        v=untouched_levels(rows,'1h',3*h)
        self.assertFalse(any(x['origin_ms']==0 and x['side']=='high' for x in v))
        self.assertTrue(any(x['origin_ms']==0 and x['side']=='low' for x in v))
    def test_no_future_candles(self):
        h=3600000
        self.assertEqual(untouched_levels([dict(t=0,h=5,l=1)],'1h',h-1),[])
    def test_incomplete_ignored(self):
        h=3600000
        self.assertEqual(untouched_levels([dict(t=0,h=5,l=1,complete=False)],'1h',h),[])
    def test_merge(self):
        h=3600000
        self.assertEqual(len(merge_levels({'1h':[dict(t=0,h=2,l=1)]},h)),2)
    def test_duplicate_timestamps_rejected(self):
        h=3600000
        with self.assertRaises(ValueError):
            untouched_levels([dict(t=0,h=2,l=1),dict(t=0,h=3,l=1)],'1h',h)
    def test_nonfinite_prices_rejected(self):
        h=3600000
        for price in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                untouched_levels([dict(t=0,h=price,l=1)],'1h',h)
    def test_unaligned_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            untouched_levels([dict(t=1,h=2,l=1)],'1h',3600000)
    def test_invalid_tick_size_rejected(self):
        for tick in (float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):
                untouched_levels([], '1h', 3600000,tick_size=tick)
    def test_resource_bound(self):
        with self.assertRaises(ValueError):
            untouched_levels([dict(t=i*3600000,h=2,l=1) for i in range(10001)],'1h',3600000)
    def test_invalid(self):
        with self.assertRaises(ValueError): untouched_levels([], '1m', 0)
if __name__=='__main__':unittest.main()
