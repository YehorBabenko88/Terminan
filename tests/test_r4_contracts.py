import copy,unittest
from terminan.r4_contracts import fixtures,validate,seal,BASE_MS
class R4Contracts(unittest.TestCase):
 def check(self,raw,**kw):return validate(raw,symbol=kw.get('symbol',raw['symbol']),timeframe=kw.get('timeframe',raw['timeframe']),as_of_ms=kw.get('now',BASE_MS),previous=kw.get('previous'))
 def test_valid_pinned_sources(self):
  for raw in fixtures():
   r=self.check(raw);self.assertEqual(r['state'],'HISTORICAL_ONLY');self.assertEqual(r['authority'],'SYNTHETIC_ONLY');self.assertEqual(r['runtime_source'],'NONE');self.assertTrue(r['rows'])
 def test_fail_closed_schema_provenance(self):
  for key,value in [('version',True),('version',2),('schema_version','unknown'),('source_id','other'),('mode','LIVE_SOURCE_VERIFIED'),('epoch',True),('observed_at_ms',1.5),('observed_at_ms',None)]:
   raw=copy.deepcopy(fixtures()[0]);raw[key]=value;seal(raw)
   with self.subTest(key=key):self.assertEqual(self.check(raw)['rows'],[])
  raw=fixtures()[0];raw['provenance']['source_sha']='f'*40;seal(raw);self.assertEqual(self.check(raw)['state'],'INVALID_PROVENANCE')
 def test_identity_and_native_timeframe(self):
  raw=fixtures()[0]
  self.assertEqual(self.check(raw,symbol='ETHUSDT')['state'],'IDENTITY_MISMATCH')
  self.assertEqual(self.check(raw,timeframe='5m')['state'],'UNSUPPORTED_TIMEFRAME')
  raw['rows'][0]['symbol']='ETHUSDT';seal(raw);self.assertEqual(self.check(raw)['rows'],[])
 def test_future_nonfinite_null_order(self):
  for fault in ('future','nan','null','duplicate','reverse','coverage'):
   raw=copy.deepcopy(fixtures()[0])
   if fault=='future':raw['rows'][0]['available_at_ms']=BASE_MS+1
   elif fault=='nan':raw['rows'][0]['c']=float('nan')
   elif fault=='null':raw['rows'][0]['v']=None
   elif fault=='duplicate':raw['rows'].append(copy.deepcopy(raw['rows'][-1]))
   elif fault=='reverse':raw['rows'].reverse()
   else:raw['coverage']['to_ms']=raw['coverage']['from_ms']-1
   try:seal(raw)
   except ValueError:pass
   with self.subTest(fault=fault):self.assertEqual(self.check(raw)['rows'],[])
 def test_freshness_partial_unavailable_epoch(self):
  raw=fixtures()[0];self.assertEqual(self.check(raw,now=BASE_MS+120001)['state'],'STALE')
  raw['source_state']='PARTIAL';seal(raw);self.assertEqual(self.check(raw)['state'],'PARTIAL')
  raw['source_state']='UNAVAILABLE';seal(raw);self.assertEqual(self.check(raw)['state'],'UNAVAILABLE');self.assertEqual(self.check(raw)['rows'],[])
  raw=fixtures()[0];self.assertEqual(self.check(raw,previous=(raw['epoch']+1,0))['state'],'OUT_OF_ORDER');self.assertEqual(self.check(raw,previous=(raw['epoch'],raw['sequence']))['state'],'DUPLICATE')
 def test_hash_mismatch_and_unknown_fields(self):
  raw=fixtures()[0];raw['rows'][0]['c']=100.5;self.assertEqual(self.check(raw)['state'],'INVALID_PROVENANCE')
  raw=fixtures()[0];raw['dsn']='PRIVATE_NEVER_EXPORT';seal(raw);r=self.check(raw);self.assertEqual(r['rows'],[]);self.assertNotIn('PRIVATE_NEVER_EXPORT',str(r))

 def test_canonical_pins_and_versioned_negatives(self):
  import json,hashlib,tempfile
  from pathlib import Path
  from unittest.mock import patch
  import terminan.r4_contracts as module
  values=module.fixtures()
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for name in ('r4-contract-v1.json','r4-contract-lock-v1.json'):(root/name).write_bytes((module.ROOT/name).read_bytes().replace(b'\r\n',b'\n'))
   with patch.object(module,'ROOT',root):self.assertEqual(module.fixtures(),values)
   (root/'r4-contract-v1.json').write_bytes((root/'r4-contract-v1.json').read_bytes().replace(b'\n',b'\r\n'))
   with patch.object(module,'ROOT',root):self.assertEqual(module.fixtures(),values)
  spec=json.loads((module.ROOT/'r4-negative-v1.json').read_text());self.assertEqual(spec['pins'],module.LOCK)
  for case in spec['cases']:
   raw=copy.deepcopy(values[0]);raw.update(case['patch']);module.seal(raw)
   with self.subTest(case=case['name']):self.assertEqual(self.check(raw)['state'],case['state'])
 def test_gap_and_nullable_poc(self):
  raw=fixtures()[0];self.assertIsNone(raw['rows'][0]['poc']);raw['rows'].pop(1);seal(raw);self.assertEqual(self.check(raw)['state'],'GAP')
