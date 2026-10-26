import os
import unittest
from unittest.mock import patch
from terminan import g0_sources
from terminan.contracts import aggregate_footprint, poc_close_events

class AuditRegressions(unittest.TestCase):
    def test_completed_grid_bar_cannot_close_in_future(self):
        rows=[dict(t=60000,o=10,h=12,l=9,c=11,buy=3,sell=2,delta=1,trades=4,poc=None)]
        with patch.dict(os.environ,{'TERMINAN_GRID_DSN':'synthetic'}),patch.object(g0_sources,'grid_rows',return_value=(rows,'pg18-structural-v1')):
            self.assertEqual(g0_sources.snapshot('grid','BTCUSDT',now_ms=60001)['state'],'INVALID_DATA')
            view=g0_sources.snapshot('grid','BTCUSDT',now_ms=120000,timeframe='1h')
            self.assertEqual(view['coverage']['to_ms'],120000)

    def test_footprint_duplicate_and_arithmetic_are_rejected(self):
        row=dict(t=60000,price=10,buy=3,sell=2,delta=1,volume=5)
        for rows in ([row,row],[dict(row,delta=999)]):
            with patch.dict(os.environ,{'TERMINAN_GRID_DSN':'synthetic'}),patch.object(g0_sources,'grid_rows',return_value=(rows,'pg18-structural-v1')):
                self.assertEqual(g0_sources.snapshot('footprint','BTCUSDT',now_ms=120000)['state'],'INVALID_DATA')
        for row in (dict(t=0,price=float('nan'),volume=1),dict(t=True,price=10,volume=1)):
            with self.assertRaises(ValueError):aggregate_footprint([row])

    def test_partial_poc_observation_is_not_a_close(self):
        minutes=[dict(t=0,poc=10)]
        self.assertEqual(poc_close_events(minutes,[dict(t=0,c=11,complete=False)]),[])
        self.assertEqual(poc_close_events(minutes,[dict(t=0,c=11,complete=True)],as_of_ms=59999),[])
        self.assertEqual(poc_close_events(minutes,[dict(t=0,c=11,complete=True)],as_of_ms=60000)[0]['available_at_ms'],60000)
