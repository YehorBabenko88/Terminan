import unittest
from terminan.contracts import TradeEvent, align_trades, aggregate_footprint, poc_close_events

class ContractTests(unittest.TestCase):
    def test_trade_validation(self):
        base=dict(run_id='r',strategy_id='s',symbol='BTCUSDT',trade_id='t',entry_ms=100,exit_ms=200,entry_price=10,exit_price=12,side='long',quantity=2,pnl=4)
        t=TradeEvent.parse(base)
        self.assertEqual(align_trades([t],150,160),[t])
        with self.assertRaises(ValueError):TradeEvent.parse({**base,'exit_ms':99})
        with self.assertRaises(ValueError):TradeEvent.parse({**base,'side':'other'})
    def test_poc_tie_and_close(self):
        rows=[dict(t=100,price=11,volume=5),dict(t=100,price=10,volume=5),dict(t=200,price=9,volume=8)]
        buckets=aggregate_footprint(rows)
        self.assertEqual(buckets[0]['poc'],10)
        events=poc_close_events(buckets,[dict(t=100,c=11),dict(t=200,c=9)])
        self.assertEqual([e['relation'] for e in events],['above','at'])
    def test_no_negative_volume(self):
        with self.assertRaises(ValueError):aggregate_footprint([dict(t=1,price=2,volume=-1)])
if __name__=='__main__':unittest.main()
