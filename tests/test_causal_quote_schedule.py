import copy,hashlib,json,unittest
from terminan.paper_ledger import canonical_json

def seal(v):return dict(v,sha256=hashlib.sha256(canonical_json(v)).hexdigest())
def receipt(ident,**kw):return seal(dict(receipt_id=ident,source_id='synthetic_source',raw_sha256='a'*64,symbol='BTCUSDT',**kw))
def fixture():
 return dict(open_decision=receipt('open',decision_ms=100,observed_ms=99,expires_ms=200,side='long'),close_decision=receipt('close',decision_ms=300,observed_ms=300,expires_ms=400),quotes=[receipt('entry',epoch='e',sequence=1,event_ms=110,observed_ms=111,bid='99',ask='100'),receipt('exit',epoch='e',sequence=2,event_ms=310,observed_ms=311,bid='101',ask='102')],funding=receipt('funding',kind='COMPLETE_INTERVAL',observed_ms=90,previous_ms=0,next_ms=1000,interval_ms=1000,events=[]),latency_ms=10,max_quote_age_ms=100,max_hold_ms=1000,now_ms=320)
class CausalScheduleTests(unittest.TestCase):
 def validate(self,v):
  from terminan.causal_quotes import validate_causal_schedule
  return validate_causal_schedule(**v)
 def test_valid_schedule_retains_declared_receipts_and_has_no_financial_authority(self):
  v=fixture();before=copy.deepcopy(v);r=self.validate(v);self.assertEqual(v,before);self.assertEqual(r,());self.assertEqual(len(v['quotes']),2)
 def test_reference_or_pre_latency_or_out_of_epoch_quote_refuses(self):
  for changes in ({'event_ms':109},{'event_ms':100},{'epoch':'other'},{'sequence':1}):
   v=fixture();index=1 if 'epoch' in changes or 'sequence' in changes else 0
   q=dict(v['quotes'][index]);q.pop('sha256');q.update(changes);v['quotes'][index]=seal(q)
   with self.subTest(changes=changes),self.assertRaises(ValueError):self.validate(v)
 def test_tampered_last_receipt_duplicate_identity_and_boolean_clock_refuse(self):
  for mode in ('hash','duplicate','bool','unknown'):
   v=fixture()
   if mode=='hash':v['quotes'][-1]['ask']='999'
   elif mode=='duplicate':q=dict(v['quotes'][-1]);q.pop('sha256');q['receipt_id']='entry';v['quotes'][-1]=seal(q)
   elif mode=='bool':v['now_ms']=True
   else:v['quotes'][-1]['extra']=1
   before=copy.deepcopy(v)
   with self.subTest(mode=mode),self.assertRaises(ValueError):self.validate(v)
   self.assertEqual(v,before)
 def test_ambiguous_funding_boundary_and_missing_schedule_event_refuse(self):
  for mode in ('boundary','missing'):
   v=fixture();f=dict(v['funding']);f.pop('sha256');f.update(kind='COMPLETE_EVENTS',previous_ms=10 if mode=='boundary' else 0,next_ms=510 if mode=='boundary' else 600,interval_ms=100 if mode=='boundary' else 200,observed_ms=312,events=[]);v['funding']=seal(f)
   with self.assertRaises(ValueError):self.validate(v)
 def test_complete_funding_events_are_selected_only_inside_fill_interval(self):
  v=fixture();events=[receipt('f'+str(t),event_ms=t,observed_ms=t,rate='0.01',mark_price='100') for t in (50,250,450)]
  f=dict(v['funding']);f.pop('sha256');f.update(kind='COMPLETE_EVENTS',previous_ms=0,next_ms=500,interval_ms=200,observed_ms=451,events=events);v['funding']=seal(f)
  # Correct complete schedule has events200/400; only200 lies within entry110..exit310.
  f=dict(v['funding']);f.pop('sha256');f['events']=[receipt('f'+str(t),event_ms=t,observed_ms=t,rate='0.01',mark_price='100') for t in (200,400)];f['next_ms']=600;v['funding']=seal(f);v['now_ms']=451;v['max_quote_age_ms']=200
  self.assertEqual(self.validate(v),(('100','0.01'),))
