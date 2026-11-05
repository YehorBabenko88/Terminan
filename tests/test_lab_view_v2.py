"""SYNTHETIC v2 contract controls; no producer/source authentication claims."""
import copy,hashlib,json,os,tempfile,time,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from terminan import lab_view


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def market(now=1500):
 request=dict(symbol='ETHUSDT',start_ms=now-500,end_ms=now+500,as_of_ms=now,max_age_ms=1000)
 stamp=(datetime.fromtimestamp(now//1000,timezone.utc)+timedelta(milliseconds=now%1000)).isoformat(timespec='microseconds')
 row=dict(id=1,symbol='ETHUSDT',event_type='derivatives_ticker',source='bybit',event_ts=stamp,ingest_ts=stamp,payload={'last_price':'123.4500','bid1_price':None},event_age_ms=0.0,observation_status='observed',field_freshness='unknown')
 return dict(schema='grid.lab_observations.v1',request=request,evidence_class='persisted_observation_unverified',execution_authority=False,trading_authorized=False,rows=[row],row_count=1,output_truncated=False,source_completeness='NOT_EVALUATED',selection_scope=dict(symbol='ETHUSDT',event_types=['derivatives_ticker','orderbook_snapshot'],start_ms=now-500,end_ms=now+500,range='start_ms <= event_ts < end_ms',ordering=['event_ts','id']))
def paper():
 result=dict(schema='stratt.paper.quote.result.v1',mode='PUBLIC_QUOTE_PAPER_RESEARCH',trade_id='r1',strategy='SYNTHETIC_TEST_INPUT',strategy_revision='b'*40,evidence_class='SYNTHETIC',request_sha256='a'*64,symbol='ETHUSDT',units={'price':'USDT/ETH','qty':'ETH'},side='BUY',status='CLOSED',entry_ts_ms=1010,exit_ts_ms=1210,entry_price=101,exit_price=108.9,raw_entry_price=100,raw_exit_price=110,qty=1,signed_qty=1,gross_raw=10,gross_fill=7.9,fees=.2099,slippage=2.1,funding=0,pnl=7.6901,receipt_bindings=[{'receipt_id':n,'sha256':'c'*64} for n in ['s1','s2','q1','q2','f1']],source_authenticity='NOT_EVALUATED',receipt_provenance='CALLER_DECLARED',fill_selection='CALLER_SUPPLIED_CAUSAL_QUOTES_NOT_COMPLETE_MARKET_STREAM',missing_capabilities=['MARKET_DEPTH_LIQUIDITY','ACTUAL_EXCHANGE_FILLS','STREAM_COMPLETENESS_ATTESTATION'],execution_authority=False,trading_authorized=False,training_authorized=False,grid_normal='NOT_QUALIFIED',paper_eligible='NOT_QUALIFIED',h_b='NOT_QUALIFIED',durability='NODE_LOCAL_NOT_DISTRIBUTED_CONSENSUS_OR_FAILOVER')
 row=dict(request_id='r1',signal_receipt_id='s1',request_sha256='a'*64,result_sha256=digest(result),admitted_ms=1300,result=result)
 return dict(schema='stratt.paper.quote.snapshot.v1',mode='PUBLIC_QUOTE_PAPER_RESEARCH',source_authenticity='NOT_EVALUATED',receipt_provenance='CALLER_DECLARED',durability='NODE_LOCAL_NOT_DISTRIBUTED_CONSENSUS_OR_FAILOVER',execution_authority=False,trading_authorized=False,ledger_scope='CHECKPOINTED_ROLLBACK_JOURNAL_ONLY',live_wal_supported=False,missing_state=['OPEN_POSITIONS','ACCOUNT_EQUITY','BALANCE','UNREALIZED_PNL'],selection_order=['admitted_ms DESC','request_id DESC'],validated_count=1,returned_count=1,has_more=False,rows=[row])
def fleet():
 node=dict(id='LS-5',epoch=1,sequence=0,state='APPROVED',zone='SYNTHETIC_TEST_INPUT',modules=[],last_heartbeat_ms=None,cpu=None,memory=None,disk=None,available_resources=None,db_sizes=None,identity_verified=False)
 return dict(mode='PLAN_ONLY',status='PLAN_ONLY',execution_authorized=False,nodes=[node],links=[],databases=[],alerts=[],source_provenance='NOT_EVALUATED',physical='NOT_RUN',production='NO_GO')
def sample(now):
 section=lambda payload:dict(state='AVAILABLE',error_code=None,payload=payload)
 return dict(schema='unified.lab.market-paper.v2',mode='LAB_SIMULATION',trading_authorized=False,authority='REPORTED_UNATTESTED',release_id='SYNTHETIC_TEST_INPUT',run_id='SYNTHETIC_TEST_INPUT',sequence=1,generated_at_ms=now,sections=dict(market=section([market(now)]),paper=section(paper()),fleet=section(fleet())))


class LabV2Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'snapshot.json';self.now=int(time.time()*1000)
 def read(self,value):
  self.path.write_text(json.dumps(value),encoding='utf8');os.utime(self.path,(self.now/1000,)*2)
  return lab_view.overview(str(self.path),now_ms=self.now)
 def test_exact_source_payloads_preserved_and_unknown_is_not_readiness(self):
  value=sample(self.now);result=self.read(value)
  self.assertEqual(result['schema'],value['schema']);self.assertEqual(result['state'],'AVAILABLE')
  self.assertEqual(result['sections'],value['sections']);self.assertIsNone(result['sections']['fleet']['payload']['nodes'][0]['last_heartbeat_ms'])
  self.assertEqual(result['sections']['market']['payload'][0]['rows'][0]['payload']['last_price'],'123.4500')
  self.assertEqual(result['sections']['paper']['payload']['rows'][0]['result']['paper_eligible'],'NOT_QUALIFIED')
 def test_partial_zero_market_and_nodes_and_missing_paper(self):
  value=sample(self.now);value['sections']['market']['payload']=[];value['sections']['fleet']['payload']['nodes']=[]
  value['sections']['paper']=dict(state='UNAVAILABLE',error_code='SOURCE_NOT_CONFIGURED',payload=None)
  result=self.read(value);self.assertEqual(result['state'],'PARTIAL');self.assertEqual(result['sections'],value['sections'])
 def test_declared_stale_and_snapshot_age_preserve_raw_source(self):
  value=sample(self.now);value['sections']['market']['state']='STALE';value['sections']['market']['error_code']='STALE_SOURCE'
  self.assertEqual(self.read(value)['section_states']['market'],'STALE')
  value=sample(self.now-16000);result=self.read(value);self.assertEqual(result['state'],'STALE');self.assertEqual(result['sections'],value['sections'])
 def test_invalid_source_flags_ids_and_limits_fail_closed(self):
  changes=[lambda v:v.update(trading_authorized=True),lambda v:v['sections']['market']['payload'][0].update(output_truncated=True),lambda v:v['sections']['market']['payload'][0].update(source_completeness='AUTHENTICATED'),lambda v:v['sections']['market']['payload'][0]['rows'][0].update(field_freshness='fresh'),lambda v:v['sections']['market']['payload'][0]['rows'][0].update(id=2**53),lambda v:v['sections']['market']['payload'].append(copy.deepcopy(v['sections']['market']['payload'][0])),lambda v:v['sections']['paper']['payload']['rows'][0]['result'].update(paper_eligible='QUALIFIED'),lambda v:v['sections']['paper']['payload'].update(missing_state=[]),lambda v:v['sections']['fleet']['payload']['nodes'][0].update(identity_verified=True),lambda v:v['sections']['fleet']['payload']['nodes'].extend([copy.deepcopy(v['sections']['fleet']['payload']['nodes'][0])]*6),lambda v:v['sections']['market'].update(error_code='PRIVATE_PATH'),lambda v:v.update(extra='private')]
  for change in changes:
   value=sample(self.now);change(value);result=self.read(value)
   self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(result['error'],'VALIDATION_FAILED')
 def test_paper_hash_and_request_receipt_binding_rejected_without_recalculation(self):
  for field,bad in [('result_sha256','f'*64),('request_id','another'),('signal_receipt_id','missing')]:
   value=sample(self.now);value['sections']['paper']['payload']['rows'][0][field]=bad
   self.assertEqual(self.read(value)['error'],'VALIDATION_FAILED')
 def test_all_unavailable_has_no_invented_rows(self):
  value=sample(self.now)
  value['sections']={k:dict(state='UNAVAILABLE',error_code='SOURCE_UNAVAILABLE',payload=None) for k in value['sections']}
  result=self.read(value);self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(result['sections'],value['sections'])
 def test_two_megabyte_limit_rejects_instead_of_truncating(self):
  self.path.write_bytes(b' '*2097153)
  result=lab_view.overview(str(self.path),now_ms=self.now);self.assertEqual(result['state'],'UNAVAILABLE')
 def test_v1_oversize_limit_remains_one_megabyte(self):
  from tests.test_lab_view import sample as v1
  self.path.write_text(json.dumps(v1(self.now))+' '*1048576)
  self.assertEqual(lab_view.overview(str(self.path),now_ms=self.now)['state'],'UNAVAILABLE')

 def test_valid_v2_over_one_megabyte_is_preserved_without_truncation(self):
  value=sample(self.now);value['sections']['market']['payload']=[]
  for symbol in ('ETHUSDT','BTCUSDT','SOLUSDT'):
   packet=market(self.now);packet['request']['symbol']=symbol;packet['selection_scope']['symbol']=symbol
   original=packet['rows'][0];packet['rows']=[]
   for ident in range(1,1001):
    row=copy.deepcopy(original);row.update(id=ident,symbol=symbol);row['payload']['last_price']='1'*128;packet['rows'].append(row)
   packet['row_count']=1000;value['sections']['market']['payload'].append(packet)
  size=len(json.dumps(value).encode());self.assertGreater(size,1048576);self.assertLessEqual(size,2097152)
  result=self.read(value);self.assertEqual(result['state'],'AVAILABLE');self.assertEqual(result['sections'],value['sections'])
 def test_depth_and_container_budgets_fail_closed(self):
  value=sample(self.now);nested=0
  for _ in range(20):nested=[nested]
  value['sections']['market']['payload'][0]['rows'][0]['payload']['last_price']=nested
  self.assertEqual(self.read(value)['error'],'VALIDATION_FAILED')
  value=sample(self.now);value['sections']['market']['payload'][0]['rows']*=1001
  self.assertEqual(self.read(value)['error'],'VALIDATION_FAILED')
 def test_receipt_labels_and_source_unknowns_survive_without_relabeling(self):
  value=sample(self.now);value['sections']['market']['payload'][0]['rows'][0]['payload']['_quality']={'symbol':'ETHUSDT','feeds':{'ticker':{'status':'degraded'}},'missing_counts':{'funding':2},'last_update':{'ticker':1.5}}
  value['sections']['fleet']['payload']['nodes'][0]['last_heartbeat_ms']=self.now+1000
  result=self.read(value);self.assertEqual(result['sections'],value['sections']);self.assertEqual(result['state'],'AVAILABLE')

 def test_authority_cannot_be_promoted_even_with_a_repaired_result_hash(self):
  value=sample(self.now);row=value['sections']['paper']['payload']['rows'][0]
  row['result']['execution_authority']=True;row['result_sha256']=digest(row['result'])
  self.assertEqual(self.read(value)['error'],'VALIDATION_FAILED')
  value=sample(self.now);value['sections']['market']['payload'][0]['rows'][0]['payload']['last_price']=2**53
  self.assertEqual(self.read(value)['error'],'VALIDATION_FAILED')
 def test_actual_loopback_route_uses_v2_reader_and_existing_session_gate(self):
  import threading
  from urllib.request import urlopen
  from urllib.error import HTTPError
  from unittest.mock import patch
  from terminan.unified_server import UnifiedServer,UnifiedHandler
  value=sample(self.now);self.read(value)
  server=UnifiedServer(('127.0.0.1',0),UnifiedHandler);server.candidate_sha='a'*40
  thread=threading.Thread(target=server.serve_forever);thread.start()
  try:
   with patch.dict(os.environ,TERMINAN_LAB_SNAPSHOT=str(self.path)):
    url='http://127.0.0.1:'+str(server.server_port)+'/api/lab/overview'
    with urlopen(url,timeout=3) as response:result=json.load(response)
    self.assertEqual(result['sections'],value['sections']);self.assertEqual(result['state'],'AVAILABLE')
    server.session.end()
    with self.assertRaises(HTTPError) as failure:urlopen(url,timeout=3)
    self.assertEqual(failure.exception.code,410)
  finally:server.shutdown();server.server_close();thread.join(5)

 def test_lab_asset_is_strict_utf8_without_replacement_characters(self):
  raw=Path(lab_view.__file__).with_name('lab_view.html').read_bytes()
  text=raw.decode('utf8')
  self.assertNotIn(chr(65533),text)

 def test_old_market_declaration_is_stale_without_rewriting_raw_quality_or_paper(self):
  value=sample(self.now);value['sections']['market']['payload']=[market(self.now-16000)]
  result=self.read(value)
  self.assertEqual(result['state'],'STALE');self.assertEqual(result['section_states']['market'],'STALE')
  self.assertEqual(result['section_states']['paper'],'AVAILABLE')
  self.assertEqual(result['sections'],value['sections'])
  self.assertEqual(result['sections']['market']['payload'][0]['rows'][0]['field_freshness'],'unknown')
  self.assertEqual(result['sections']['market']['payload'][0]['rows'][0]['observation_status'],'observed')
