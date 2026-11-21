import hashlib,json,tracemalloc,unittest
from unittest.mock import patch
from terminan.causal_artifacts import validate_causal_ledger_artifact
from terminan.causal_session import SessionDescriptor
class CausalJSONBoundsTests(unittest.TestCase):
 def test_structural_overflow_refuses_before_json_object_allocation(self):
  values=[b'{"rows":['+b'{},'*700000+b'{}]}',b'['*17+b'0'+b']'*17,b'{'+b','.join(('"k'+str(i)+'":0').encode() for i in range(33))+b'}',b'{"x":"'+b'a'*1537+b'"}',b'{"events":['+b','.join([b'{}']*129)+b']}']
  for raw in values:
   with self.subTest(size=len(raw)),patch('json.loads',side_effect=AssertionError('NO_PROPORTIONAL_JSON_ALLOCATION')),self.assertRaises(ValueError):validate_causal_ledger_artifact(raw,expected_sha256=hashlib.sha256(raw).hexdigest())
 def test_many_rows_probe_has_small_additional_allocation(self):
  raw=b'{"rows":['+b'{},'*700000+b'{}]}';tracemalloc.start()
  try:
   with self.assertRaises(ValueError):validate_causal_ledger_artifact(raw,expected_sha256=hashlib.sha256(raw).hexdigest())
   _,peak=tracemalloc.get_traced_memory()
  finally:tracemalloc.stop()
  self.assertLess(peak,65536)
 def test_public_descriptor_rejects_oversize_mutable_wrong_family_or_authority(self):
  values=[b'{"x":"'+b'a'*700000+b'"}',bytearray(b'{"schema":"not-a-session-event"}'),b'{"schema":"not-a-session-event"}']
  for raw in values:
   with self.subTest(kind=type(raw),size=len(raw)),self.assertRaises(ValueError):SessionDescriptor(raw,hashlib.sha256(raw).hexdigest())
 def test_structurally_valid_200_by_128_graph_has_no_arbitrary_global_node_cap(self):
  from terminan.bounded_json import preflight_json
  row=b'['+b','.join([b'{}']*128)+b']';raw=b'['+b','.join([row]*200)+b']';preflight_json(raw,max_bytes=4*1024*1024)
  preflight_json(json.dumps('0'*256).encode(),max_bytes=4*1024*1024)

 def test_preflight_preserves_valid_escaped_strings_and_boundary_counts(self):
  from terminan.bounded_json import preflight_json,load_bounded_json
  values=[{'text':'quote\" slash\\ brackets[]{} colon: comma, newline\n'},['unicode \u00e9',None,True,False,0,-1],{str(i):[] for i in range(32)},[0]*200]
  for value in values:
   raw=json.dumps(value,ensure_ascii=True,separators=(',',':')).encode();preflight_json(raw,max_bytes=4*1024*1024);self.assertEqual(load_bounded_json(raw,max_bytes=4*1024*1024),value)

 def test_descriptor_false_flags_are_typed_at_both_envelope_and_detail(self):
  from terminan.paper_ledger import canonical_json
  base=dict(schema='terminan.paper.session-event.v2',sequence=1,kind='UNCERTAIN',run_id='offline_1',symbol='BTCUSDT',reservation_id='p1',at_ms=1,detail={'reason':'SOURCE_GAP'},source_packet_sha256=None,evidence_class='SYNTHETIC',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',execution_authority=False,trading_authorized=False)
  raw=canonical_json(base);self.assertEqual(SessionDescriptor(raw,hashlib.sha256(raw).hexdigest()).decode(),base)
  for field,value in (('execution_authority',True),('execution_authority',0),('schema','wrong'),('detail',{'reason':[]})):
   bad=dict(base);bad[field]=value;raw=canonical_json(bad)
   with self.subTest(field=field,value=value),self.assertRaises(ValueError):SessionDescriptor(raw,hashlib.sha256(raw).hexdigest())
