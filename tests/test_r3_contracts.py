import copy, unittest
from terminan.synthetic_contracts import fixtures, validate_fixture
class R3Contracts(unittest.TestCase):
    def test_reject_row_identity(self):
        for field,value in [('symbol','ETHUSDT'),('timeframe','1h')]:
            raw=copy.deepcopy(fixtures()[0]);raw['rows'][0][field]=value
            self.assertEqual(validate_fixture(raw,1767226200000)['state'],'INVALID_DATA')
    def test_reject_reverse(self):
        raw=copy.deepcopy(fixtures()[0]);raw['rows']=list(reversed(raw['rows']))
        self.assertEqual(validate_fixture(raw,1767226200000)['state'],'INVALID_DATA')
    def test_reject_early_availability(self):
        raw=copy.deepcopy(fixtures()[0]);row=raw['rows'][0];row['complete']=False;row['available_at_ms']=row['t']-1
        self.assertEqual(validate_fixture(raw,1767226200000)['state'],'INVALID_DATA')
    def test_versioned_negative_fixtures(self):
        import json
        from pathlib import Path
        from terminan.synthetic_contracts import LOCK
        spec=json.loads(Path('terminan/fixtures/r3-negative-v1.json').read_text())
        self.assertEqual(spec['pins'],LOCK)
        for case in spec['cases']:
            raw=copy.deepcopy(fixtures()[0]);raw.update(case['patch'])
            result=validate_fixture(raw,spec['as_of_ms'])
            self.assertEqual(result['state'],case['expected'],case['name'])
            self.assertEqual(result['authority'],'SYNTHETIC_ONLY')
    def test_process_memory(self):
        import os
        from terminan.process_metrics import sample
        result=sample([os.getpid()]);self.assertEqual(result['state'],'AVAILABLE');self.assertGreater(result['rss_bytes'],0)
    def test_duplicate_and_nonfinite(self):
        for mutate in ('duplicate','nan','future','cross-symbol'):
            raw=copy.deepcopy(fixtures()[0])
            if mutate=='duplicate':raw['rows'].append(copy.deepcopy(raw['rows'][-1]))
            elif mutate=='nan':raw['rows'][0]['c']=float('nan')
            elif mutate=='future':raw['rows'][0]['available_at_ms']=1767226200001
            else:raw['dataset_id']='synthetic-v1:17:ETHUSDT'
            result=validate_fixture(raw,1767226200000)
            self.assertEqual(result['rows'],[],mutate)
            self.assertIn(result['state'],('INVALID_DATA','FUTURE_LEAKAGE'))
    def test_100k_linked_deltas(self):
        from terminan.dom import BookEngine,Snapshot,Delta,Level
        engine=BookEngine(max_levels=40)
        engine.snapshot(Snapshot('r3',0,(Level('bid',99,1),Level('ask',101,1))))
        for i in range(1,100001):
            self.assertTrue(engine.delta(Delta('r3',i,i-1,(Level('bid',99,i%100+1),))))
        self.assertEqual(engine.view.sequence,100000)
        self.assertEqual(len(engine.view.bids)+len(engine.view.asks),2)
