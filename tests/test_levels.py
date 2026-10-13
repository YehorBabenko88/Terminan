import unittest
import io
import json
from unittest.mock import patch
from terminan.levels import untouched_levels,merge_levels,missing_candle_intervals,level_history_quality

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

    def test_missing_closed_intervals_reported(self):
        h=3600000
        candles=[dict(t=0,h=10,l=9),dict(t=3*h,h=11,l=10)]
        self.assertEqual(missing_candle_intervals(candles,'1h',4*h),
                         [dict(after_ms=0,before_ms=3*h,missing_intervals=2)])

    def test_gap_detector_ignores_open_and_future_candles(self):
        h=3600000
        candles=[dict(t=0,h=10,l=9),dict(t=h,h=10,l=9,complete=False),
                 dict(t=3*h,h=11,l=10),dict(t=4*h,h=12,l=11)]
        self.assertEqual(missing_candle_intervals(candles,'1h',4*h),
                         [dict(after_ms=0,before_ms=3*h,missing_intervals=2)])

    def test_duplicate_timestamps_do_not_create_gaps(self):
        h=3600000
        candles=[dict(t=0),dict(t=0),dict(t=h)]
        self.assertEqual(missing_candle_intervals(candles,'1h',2*h),[])

    def test_levels_api_opt_in_diagnostics_preserves_default_list(self):
        from terminan.server import Handler
        h=3600000
        rows=[dict(t=0,h=10,l=9,complete=True),
              dict(t=3*h,h=11,l=10,complete=True)]
        def candles(symbol,tf,limit=1000):
            return rows if tf=='1h' else []
        def call(path):
            handler=object.__new__(Handler)
            handler.path=path
            handler.wfile=io.BytesIO()
            handler.send_response=lambda code:None
            handler.send_header=lambda *args:None
            handler.end_headers=lambda:None
            handler.do_GET()
            return json.loads(handler.wfile.getvalue())
        with patch('terminan.server.data.validate'), patch('terminan.server.data.candles',side_effect=candles):
            legacy=call('/api/levels?symbol=BTCUSDT')
            detailed=call('/api/levels?symbol=BTCUSDT&diagnostics=1')
        self.assertIsInstance(legacy,list)
        self.assertEqual(detailed['levels'],legacy)
        self.assertEqual(detailed['history']['state'],'GAPS_DETECTED')
        self.assertEqual(detailed['history']['coverage'],'BOUNDED_WINDOW_ONLY')
        self.assertEqual(detailed['history']['level_validation'],'UNVERIFIED_DUE_TO_GAPS')
        self.assertEqual(detailed['history']['trading_authority'],'NONE')
        self.assertEqual(detailed['history']['data_state'],'CLOSED_CANDLES_PRESENT')
        self.assertEqual(detailed['history']['gaps']['1h'][0]['missing_intervals'],2)

    def test_gap_free_bounded_history_remains_unverified(self):
        from terminan.server import Handler
        h=3600000
        handler=object.__new__(Handler)
        handler.path='/api/levels?diagnostics=1'
        handler.wfile=io.BytesIO()
        handler.send_response=lambda code:None
        handler.send_header=lambda *args:None
        handler.end_headers=lambda:None
        with patch('terminan.server.data.validate'), patch('terminan.server.data.candles',return_value=[dict(t=0,h=10,l=9,complete=True)]):
            handler.do_GET()
        result=json.loads(handler.wfile.getvalue())
        self.assertEqual(result['history']['state'],'NO_INTERNAL_GAPS_DETECTED')
        self.assertEqual(result['history']['level_validation'],'UNVERIFIED_STALE_TIMEFRAMES')
        self.assertEqual(result['history']['stale_timeframes'],['1h','4h','1d'])
        self.assertEqual(result['history']['trading_authority'],'NONE')

    def test_empty_history_is_not_misreported_as_verified(self):
        from terminan.server import Handler
        handler=object.__new__(Handler)
        handler.path='/api/levels?diagnostics=1'
        handler.wfile=io.BytesIO()
        handler.send_response=lambda code:None
        handler.send_header=lambda *args:None
        handler.end_headers=lambda:None
        with patch('terminan.server.data.validate'), patch('terminan.server.data.candles',return_value=[]):
            handler.do_GET()
        result=json.loads(handler.wfile.getvalue())
        self.assertEqual(result['levels'],[])
        self.assertEqual(result['history']['data_state'],'NO_CLOSED_CANDLES')
        self.assertEqual(result['history']['state'],'NO_CLOSED_CANDLES')
        self.assertEqual(result['history']['missing_timeframes'],['1h','4h','1d'])
        self.assertEqual(result['history']['level_validation'],'UNVERIFIED_MISSING_TIMEFRAMES')

    def test_shared_quality_contract(self):
        h=3600000
        series={'1h':[dict(t=0,h=5,l=1),dict(t=3*h,h=6,l=2)],
                '4h':[]}
        quality=level_history_quality(series,4*h)
        self.assertEqual(quality['state'],'GAPS_DETECTED')
        self.assertEqual(quality['data_state'],'CLOSED_CANDLES_PRESENT')
        self.assertEqual(quality['gaps']['1h'][0]['missing_intervals'],2)
        self.assertEqual(quality['gaps']['4h'],[])
        self.assertEqual(quality['timeframe_states']['1h'],'GAPS_DETECTED')
        self.assertEqual(quality['timeframe_states']['4h'],'NO_CLOSED_CANDLES')
        self.assertEqual(quality['missing_timeframes'],['4h'])
        self.assertEqual(quality['level_validation'],'UNVERIFIED_DUE_TO_GAPS')
        self.assertEqual(quality['trading_authority'],'NONE')

    def test_partial_timeframe_coverage_without_gaps(self):
        h=3600000
        quality=level_history_quality(
            {'1h':[dict(t=0,h=5,l=1)], '4h':[]}, h)
        self.assertEqual(quality['state'],'NO_INTERNAL_GAPS_DETECTED')
        self.assertEqual(quality['missing_timeframes'],['4h'])
        self.assertEqual(quality['level_validation'],'UNVERIFIED_MISSING_TIMEFRAMES')

    def test_stale_tail_is_not_an_internal_gap(self):
        h=3600000
        quality=level_history_quality({'1h':[dict(t=0,h=10,l=9),
                                               dict(t=h,h=11,l=10)]},10*h)
        self.assertEqual(quality['state'],'NO_INTERNAL_GAPS_DETECTED')
        self.assertEqual(quality['latest_closed_ms']['1h'],2*h)
        self.assertEqual(quality['stale_timeframes'],['1h'])
        self.assertEqual(quality['level_validation'],'UNVERIFIED_STALE_TIMEFRAMES')

    def test_fresh_closed_candle_is_not_stale(self):
        h=3600000
        quality=level_history_quality({'1h':[dict(t=8*h,h=10,l=9)]},10*h)
        self.assertEqual(quality['stale_timeframes'],[])
        self.assertEqual(quality['level_validation'],'UNVERIFIED_BOUNDED_HISTORY')

    def test_levels_api_rejects_invalid_raw_timestamp_without_coercion(self):
        from terminan.server import Handler
        for bad in ('0', True, 1.5):
            with self.subTest(bad=bad):
                handler=object.__new__(Handler)
                handler.path='/api/levels?symbol=BTCUSDT&diagnostics=1'
                handler.wfile=io.BytesIO()
                statuses=[]
                handler.send_response=lambda code:statuses.append(code)
                handler.send_header=lambda *args:None
                handler.end_headers=lambda:None
                with patch('terminan.server.data.validate'), patch('terminan.server.data.candles',return_value=[dict(t=bad,h=10,l=9,complete=True)]):
                    handler.do_GET()
                self.assertEqual(statuses,[400])
                self.assertIn('invalid candle timestamp',handler.wfile.getvalue().decode())

    def test_levels_api_exposes_irregular_spacing_as_unverified(self):
        from terminan.server import Handler
        h=3600000
        rows=[dict(t=0,h=10,l=9,complete=True),
              dict(t=h//2,h=11,l=10,complete=True)]
        def candles(symbol,tf,limit=1000):
            return rows if tf=='1h' else []
        handler=object.__new__(Handler)
        handler.path='/api/levels?symbol=BTCUSDT&diagnostics=1'
        handler.wfile=io.BytesIO()
        handler.send_response=lambda code:None
        handler.send_header=lambda *args:None
        handler.end_headers=lambda:None
        with patch('terminan.server.data.validate'), patch('terminan.server.data.candles',side_effect=candles):
            handler.do_GET()
        result=json.loads(handler.wfile.getvalue())
        self.assertEqual(result['history']['state'],'GAPS_DETECTED')
        self.assertEqual(result['history']['level_validation'],'UNVERIFIED_DUE_TO_GAPS')
        self.assertTrue(result['history']['gaps']['1h'][0]['irregular_spacing'])
        self.assertIsNone(result['history']['gaps']['1h'][0]['missing_intervals'])
        self.assertEqual(result['history']['trading_authority'],'NONE')

    def test_overlapping_closed_candles_are_reported_as_irregular(self):
        h=3600000
        gaps=missing_candle_intervals([dict(t=0),dict(t=h//2)],'1h',3*h)
        self.assertEqual(len(gaps),1)
        self.assertTrue(gaps[0]['irregular_spacing'])
        self.assertIsNone(gaps[0]['missing_intervals'])
        self.assertEqual(missing_candle_intervals([dict(t=0),dict(t=h)],'1h',3*h),[])

    def test_irregular_candle_spacing_does_not_invent_missing_count(self):
        h=3600000
        gaps=missing_candle_intervals([dict(t=0),dict(t=2*h+1)],'1h',4*h)
        self.assertEqual(len(gaps),1)
        self.assertTrue(gaps[0]['irregular_spacing'])
        self.assertIsNone(gaps[0]['missing_intervals'])
        regular=missing_candle_intervals([dict(t=0),dict(t=3*h)],'1h',4*h)
        self.assertEqual(regular[0]['missing_intervals'],2)
        self.assertNotIn('irregular_spacing',regular[0])

    def test_open_and_future_candles_do_not_require_price_fields(self):
        h=3600000
        rows=[dict(t=0,h=10,l=9,complete=True),
              dict(t=h,complete=False),
              dict(t=2*h,h='unavailable',l=None,complete=True)]
        levels=untouched_levels(rows,'1h',2*h)
        self.assertEqual(len(levels),2)
        self.assertTrue(all(level['origin_ms']==0 for level in levels))

    def test_levels_api_rejects_invalid_closed_prices_without_partial_payload(self):
        from terminan.server import Handler
        h=3600000
        for bad in ('unavailable',None,float('nan')):
            with self.subTest(bad=bad):
                handler=object.__new__(Handler)
                handler.path='/api/levels?symbol=BTCUSDT&diagnostics=1'
                handler.wfile=io.BytesIO()
                statuses=[]
                handler.send_response=lambda code:statuses.append(code)
                handler.send_header=lambda *args:None
                handler.end_headers=lambda:None
                rows=[dict(t=0,h=10,l=9,complete=True),
                      dict(t=h,h=bad,l=9,complete=True)]
                with patch('terminan.server.data.validate'), patch('terminan.server.data.candles',return_value=rows):
                    handler.do_GET()
                self.assertEqual(statuses,[400])
                payload=json.loads(handler.wfile.getvalue())
                self.assertEqual(payload,{'error':'invalid candle'})

    def test_invalid_closed_candle_prices_raise_value_error(self):
        h=3600000
        for bad in ('unavailable',None):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError,'invalid candle'):
                    untouched_levels([dict(t=0,h=bad,l=9,complete=True)],'1h',h)

    def test_level_builder_rejects_boolean_and_fractional_limits(self):
        for bad in (True, 1.5, '20'):
            with self.subTest(max_levels=bad):
                with self.assertRaisesRegex(ValueError, 'invalid parameters'):
                    untouched_levels([], '1h', 3600000, max_levels=bad)
        for bad in (True, '0.1'):
            with self.subTest(tick_size=bad):
                with self.assertRaisesRegex(ValueError, 'invalid parameters'):
                    untouched_levels([], '1h', 3600000, tick_size=bad)

    def test_level_builder_rejects_invalid_timestamp_types(self):
        for bad in (True, 1.5, '0', -1, 2**63):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, 'invalid candle timestamp'):
                    untouched_levels([dict(t=bad,h=10,l=9)], '1h', 3600000)

    def test_gap_diagnostics_rejects_invalid_timestamp_types(self):
        for bad in (True, 1.5, '0', -1, 2**63):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, 'invalid candle timestamp'):
                    missing_candle_intervals([dict(t=bad)], '1h', 3600000)

    def test_invalid(self):
        with self.assertRaises(ValueError): untouched_levels([], '1m', 0)
if __name__=='__main__':unittest.main()
