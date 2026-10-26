import hashlib
import json
import unittest
from terminan.synthetic import frame, BASE_MS, MAX_STEP
from terminan.dom import BookEngine, Snapshot, Delta, Level, viewport

class Replay(unittest.TestCase):
    def test_determinism_seed_identity_and_bounds(self):
        a=frame(seed=17,step=90,symbol='BTCUSDT',timeframe='5m')
        self.assertEqual(a,frame(seed=17,step=90,symbol='BTCUSDT',timeframe='5m'))
        self.assertNotEqual(a['candles'],frame(seed=18,step=90,symbol='BTCUSDT',timeframe='5m')['candles'])
        self.assertEqual(a['mode'],'SYNTHETIC')
        self.assertLessEqual(len(a['candles']),240)
        self.assertLessEqual(len(a['events']),20)
        self.assertLessEqual(len(a['dom']['bids'])+len(a['dom']['asks']),40)
        for bad in (-1,MAX_STEP+1,True,1.5):
            with self.assertRaises(ValueError):frame(step=bad)

    def test_faults_and_snapshot_recovery(self):
        for scenario,step,state in [('gap',24,'GAP'),('gap',32,'COHERENT'),
                                    ('stale',48,'STALE'),('stale',56,'COHERENT'),
                                    ('reconnect',72,'DISCONNECTED'),('reconnect',80,'COHERENT')]:
            with self.subTest(scenario=scenario):
                value=frame(step=step,scenario=scenario)
                self.assertEqual(value['dom']['status'],state)
                self.assertFalse(value['dom']['crossed'])
        for scenario in ('duplicates','out-of-order'):
            a=frame(step=23,scenario=scenario);b=frame(step=23)
            self.assertEqual(a['dom'],b['dom'])
            self.assertGreater(a['counters']['rejected'],0)

    def test_no_future_candle_information(self):
        for tf in ('1m','5m','15m','1h'):
            value=frame(step=15,timeframe=tf)
            for row in value['candles']:
                self.assertLessEqual(row['available_at_ms'],value['as_of_ms'])
                if row['complete']:self.assertLessEqual(row['t']+value['period_ms'],value['as_of_ms'])
            older=frame(step=0,timeframe=tf)
            complete=[c for c in older['candles'] if c['complete']]
            by_time={c['t']:c for c in value['candles']}
            self.assertTrue(all(by_time[c['t']]==c for c in complete))

    def test_footprint_consistency_and_minute_identity(self):
        value=frame(step=60)
        rows=value['footprint']['rows']
        self.assertEqual(len({(r['t'],r['price']) for r in rows}),len(rows))
        self.assertTrue(all(r['volume']==r['buy']+r['sell'] and r['delta']==r['buy']-r['sell'] for r in rows))
        candle=next(c for c in value['candles'] if c['t']==rows[0]['t'])
        self.assertEqual(sum(r['volume'] for r in rows),candle['v'])
        self.assertTrue(value['footprint']['complete_price_levels'])
        expected=min(rows,key=lambda r:(-r['volume'],r['price']))['price']
        self.assertEqual(value['footprint']['poc'],expected)

    def test_retired_delta_and_aligned_viewport(self):
        book=BookEngine();book.snapshot(Snapshot('old',10,()))
        book.snapshot(Snapshot('new',1,(Level('bid',101,2),)))
        before=book.view
        self.assertFalse(book.delta(Delta('old',11,10,())))
        self.assertEqual(book.view,before)
        rows=viewport(book.view,105,2,10)
        self.assertEqual(rows[0]['price_ticks'],100)
        self.assertEqual(rows[0]['bid_lots'],2)

    def test_unknown_source_inputs_rejected(self):
        for kwargs in ({'symbol':'bad'},{'timeframe':'7m'},{'scenario':'live'},{'seed':2**40}):
            with self.assertRaises(ValueError):frame(**kwargs)
