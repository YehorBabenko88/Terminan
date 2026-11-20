import copy,json,unittest,hashlib
from pathlib import Path
from terminan.paper_ledger import canonical_json
FIXTURE=Path(__file__).parent/'fixtures/causal-paper-inputs-v2.json'
def packet():return json.loads(FIXTURE.read_bytes())
def next_packet(value,*,connection=None,sequence=11,update=21):
 p=copy.deepcopy(value);p['request']['after_id']=p['cursor'];p['cursor']+=1;row=p['rows'][0];row['id']=p['cursor'];row['event_us']=str(int(row['event_us'])+200000);row['ingest_us']=str(int(row['ingest_us'])+200000);row['payload']['sequence']=sequence;row['payload']['update_id']=update
 if connection is not None:row['payload']['_producer_connection']['connection_id']=connection
 row['payload_sha256']=hashlib.sha256(canonical_json(row['payload'])).hexdigest();row['row_sha256']=hashlib.sha256(canonical_json({k:v for k,v in row.items() if k!='row_sha256'})).hexdigest();return p
class CausalInputsTests(unittest.TestCase):
 def cursor(self):
  from terminan.causal_inputs import CausalInputCursor
  return CausalInputCursor('BTCUSDT')
 def test_actual_data_validator_preserves_packet_qualifiers_and_wire_micros(self):
  p=packet();before=copy.deepcopy(p);cursor=self.cursor();batch=cursor.accept(p,expected_request=p['request'])
  self.assertEqual(p,before);self.assertEqual(batch.packet,p);self.assertEqual(cursor.snapshot()['cursor'],2);self.assertEqual(batch.row_clocks[0].event_us,1999600000);self.assertIs(type(batch.packet['rows'][0]['event_us']),str);self.assertEqual(batch.packet['point_in_time_availability'],'UNKNOWN');self.assertEqual(batch.packet['availability_basis'],'CALLER_DECLARED_ROW_CLOCK_CUT_NOT_COMMIT_OR_PIT')
  batch.packet['cursor']=999;self.assertEqual(cursor.snapshot()['cursor'],2)
 def test_malformed_late_row_or_wrong_expected_query_does_not_advance(self):
  cursor=self.cursor();p=packet();before=cursor.snapshot();bad=copy.deepcopy(p);bad['rows'].append(copy.deepcopy(bad['rows'][0]));bad['rows'][-1]['id']=3
  for value,expected in ((bad,p['request']),(p,{**p['request'],'after_id':True}),(p,{**p['request'],'symbol':'ETHUSDT'})):
   with self.assertRaises(ValueError):cursor.accept(value,expected_request=expected)
   self.assertEqual(cursor.snapshot(),before)
 def test_cross_packet_book_regression_is_atomic_and_new_epoch_is_explicit(self):
  cursor=self.cursor();p=packet();cursor.accept(p,expected_request=p['request']);before=cursor.snapshot()
  bad=next_packet(p,sequence=9,update=19)
  with self.assertRaises(ValueError):cursor.accept(bad,expected_request=bad['request'])
  self.assertEqual(cursor.snapshot(),before)
  new=next_packet(p,connection='b'*32,sequence=1,update=1);batch=cursor.accept(new,expected_request=new['request']);self.assertEqual(batch.changed_channels,('book',));self.assertEqual(cursor.snapshot()['cursor'],3)
 def test_expected_cursor_and_duplicate_packet_cannot_replay_state(self):
  cursor=self.cursor();p=packet();cursor.accept(p,expected_request=p['request']);before=cursor.snapshot()
  with self.assertRaises(ValueError):cursor.accept(p,expected_request=p['request'])
  self.assertEqual(cursor.snapshot(),before)
 def test_microsecond_values_above_binary64_safe_integer_remain_exact(self):
  from datetime import datetime,timezone,timedelta
  from market_data.paper_inputs import export_paper_inputs
  event=datetime(9999,1,1,tzinfo=timezone.utc,microsecond=123);ingest=event+timedelta(microseconds=200);epoch=datetime(1970,1,1,tzinfo=timezone.utc);delta=event-epoch;us=delta.days*86400000000+delta.seconds*1000000+delta.microseconds;ms=us//1000
  payload=copy.deepcopy(packet()['rows'][0]['payload']);payload['cts']=ms
  q=dict(symbol='BTCUSDT',after_id=0,start_ms=ms-10000,end_ms=ms+1,as_of_ms=ms+1,max_age_ms=10000)
  p=export_paper_inputs([dict(id=2,symbol='BTCUSDT',source='bybit',event_type='orderbook_snapshot',event_ts=event,ingest_ts=ingest,payload=payload)],q)
  batch=self.cursor().accept(p,expected_request=q);self.assertGreater(us,2**53);self.assertEqual(batch.row_clocks[0].event_us,us);self.assertEqual(batch.packet['rows'][0]['event_us'],str(us))
