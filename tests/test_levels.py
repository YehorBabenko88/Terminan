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
    def test_nonfinite_prices_rejected(self):
        h = 3600000
        for bad in (float('nan'), float('inf'), -float('inf')):
            for field in ('h', 'l'):
                with self.subTest(bad=bad, field=field):
                    candle = dict(t=0, h=5, l=1)
                    candle[field] = bad
                    with self.assertRaisesRegex(ValueError, 'invalid candle'):
                        untouched_levels([candle], '1h', h)

    def test_nonfinite_tick_size_rejected(self):
        for bad in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(tick_size=bad):
                with self.assertRaisesRegex(ValueError, 'invalid parameters'):
                    untouched_levels([], '1h', 0, tick_size=bad)

    def test_invalid_observation_timestamp(self):
        for bad in (-1, 1.5, None, True):
            with self.subTest(observation=bad):
                with self.assertRaisesRegex(ValueError, 'invalid observation timestamp'):
                    untouched_levels([], '1h', bad)

    def test_negative_candle_timestamp(self):
        with self.assertRaisesRegex(ValueError, 'invalid candle timestamp'):
            untouched_levels([dict(t=-1, h=5, l=1)], '1h', 3600000)

    def test_weekly_exchange_alignment_is_allowed(self):
        w=604800000
        self.assertEqual(len(untouched_levels([dict(t=4*86400000, h=5, l=1)], '1w', w+4*86400000)), 2)

    def test_identical_closed_candles_are_deduplicated(self):
        h=3600000
        candle=dict(t=0,h=100,l=90)
        self.assertEqual(untouched_levels([candle,candle], '1h', h),
                         untouched_levels([candle], '1h', h))

    def test_conflicting_closed_candles_are_rejected(self):
        h=3600000
        with self.assertRaisesRegex(ValueError, 'conflicting duplicate candle'):
            untouched_levels([dict(t=0,h=100,l=90),dict(t=0,h=101,l=90)],'1h',h)

    def test_incomplete_duplicate_does_not_replace_closed(self):
        h=3600000
        rows=[dict(t=0,h=101,l=90,complete=False),dict(t=0,h=100,l=90,complete=True)]
        self.assertEqual(len(untouched_levels(rows,'1h',h)),2)

    def test_invalid(self):
        with self.assertRaises(ValueError): untouched_levels([], '1m', 0)
if __name__=='__main__':unittest.main()
