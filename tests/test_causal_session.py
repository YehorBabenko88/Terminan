import copy,unittest
from unittest.mock import patch
import test_causal_account as account_helpers
from test_book_tape_research import packet
class SessionTests(unittest.TestCase):
 setUp=account_helpers.CausalAccountOwnershipTests.setUp
 create=account_helpers.CausalAccountOwnershipTests.create
 def session(self,account=None,**kwargs):
  from terminan.causal_session import CausalPaperSession
  self.clock=[4000]
  return CausalPaperSession(self.create() if account is None else account,run_id='offline_1',strategy_revision='1'*40,planned_duration_ms=4000,source_max_age_ms=10000,clock_ms=lambda:self.clock[0],min_history=4,**kwargs)
 def test_exact_duplicate_packet_is_idempotent_and_descriptors_are_immutable(self):
  s=self.session();p=packet(['100','100.01','100.02','100.03'],as_of=4000);a=s.accept_packet(p,expected_request=p['request']);before=s.status();self.clock[0]=4001;self.assertEqual(s.accept_packet(p,expected_request=p['request']),a);self.assertEqual(s.status(),before)
  for item in a:
   value=item.decode();self.assertFalse(value['execution_authority']);self.assertFalse(value['trading_authorized']);self.assertEqual(value['source_authenticity'],'NOT_EVALUATED');value['execution_authority']=True;self.assertFalse(item.decode()['execution_authority'])
 def test_revoked_freshness_refuses_before_strategy_factories_or_files(self):
  a=self.create();before={p.name:p.read_bytes() for p in self.root.iterdir()};a.require_current=lambda:1
  with patch('terminan.analytics.book_tape_research.BookTapeResearch',side_effect=AssertionError('NO_FACTORY')),self.assertRaises(ValueError):self.session(a)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_capacity_forecast_refuses_before_strategy_factories(self):
  from terminan.causal_session import CausalPaperSession
  a=self.create();before={p.name:p.read_bytes() for p in self.root.iterdir()}
  with patch('terminan.analytics.book_tape_research.BookTapeResearch',side_effect=AssertionError('NO_FACTORY')),self.assertRaises(ValueError):CausalPaperSession(a,run_id='offline_1',strategy_revision='1'*40,planned_duration_ms=600000,source_max_age_ms=10000,clock_ms=lambda:4000)
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
 def test_elapsed_window_ends_without_consuming_another_packet(self):
  s=self.session();self.clock[0]=8000;events=s.advance();self.assertEqual(s.status()['state'],'WINDOW_ENDED');before=s.status();self.assertEqual(s.accept_packet({'unread':'x'*5000000},expected_request={}),());self.assertEqual(s.status(),before);self.assertTrue(any(e.decode()['kind']=='WINDOW_ENDED' for e in events))

def source_packet(rows,after,as_of):
 from market_data.paper_inputs import export_paper_inputs
 return export_paper_inputs(rows,dict(symbol='BTCUSDT',after_id=after,start_ms=0,end_ms=as_of+1,as_of_ms=as_of,max_age_ms=10000))
def stored_row(ident,kind,payload,event,ingest,connection='a'*32):
 from datetime import datetime,timezone,timedelta
 p=copy.deepcopy(payload);p['_producer_connection']=dict(schema='market_data.public-market-connection.v1',venue='bybit',category='linear',endpoint='wss://stream.bybit.com/v5/public/linear',connection_id=connection,scope='PRODUCER_DECLARED_LOCAL_CONNECTION_NOT_REMOTE_AUTHENTICATION')
 epoch=datetime(1970,1,1,tzinfo=timezone.utc)
 return dict(id=ident,symbol='BTCUSDT',source='bybit',event_type=kind,payload=p,event_ts=epoch+timedelta(milliseconds=event),ingest_ts=epoch+timedelta(milliseconds=ingest))
def book_row(ident,event,bid='100',ask='100.1',connection='a'*32):
 return stored_row(ident,'orderbook_snapshot',dict(best_bid=bid,best_ask=ask,sequence=ident,update_id=ident,cts=event,_quality={'symbol':'BTCUSDT','feeds':{'orderbook':{'status':'available'}}}),event,event+1,connection)
def funding_row(ident=6,next_ms='28800000',interval='8',known=True,event=4095):
 from terminan.causal_replay import digest
 p=dict(funding_rate='0.0001',funding_interval_hour=interval,next_funding_time=next_ms)
 if known:p['_field_observations']=dict(schema='market_data.ticker-field-observations.v1',clock_basis='EXCHANGE_FRAME_TS_AND_PROCESS_WALL_CLOCK',fields={k:dict(event_ms=4090,observed_ms=4091,value_sha256=digest(v)) for k,v in p.items()})
 return stored_row(ident,'derivatives_ticker',p,event,event+1)

class SessionFlowTests(unittest.TestCase):
 setUp=SessionTests.setUp
 create=SessionTests.create
 session=SessionTests.session
 def accept(self,s,p,now):self.clock[0]=now;return s.accept_packet(p,expected_request=p['request'])
 def opened(self,known=True,delay=0):
  s=self.session();self.accept(s,packet(['100','100.01','100.02','100.03'],as_of=4000),4000);self.accept(s,source_packet([book_row(5,4090),funding_row(known=known)],4,4100),4100);original=s.account.reserve
  def delayed(*args,**kwargs):
   result=original(*args,**kwargs);self.clock[0]+=delay;return result
  with patch.object(s.account,'reserve',side_effect=delayed):events=self.accept(s,packet(['101'],after=6,start=4000,as_of=4300,buy=40),4300)
  return s,events
 def test_actual_strategy_risk_new_quotes_close_and_immutable_publication_descriptor(self):
  s,events=self.opened();self.assertTrue(any(e.decode()['kind']=='ENTRY_DECISION' for e in events));self.accept(s,source_packet([book_row(8,4305)],7,4310),4310);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'DECIDED');self.accept(s,source_packet([book_row(9,4310)],8,4320),4320);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'ENTRY_SELECTED');self.accept(s,source_packet([book_row(10,4410)],9,4420),4420);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'EXIT_DECIDED');p=source_packet([book_row(11,4430,'102','102.1')],10,4440);r=self.accept(s,p,4440);self.assertTrue(any(e.decode()['kind']=='LEDGER_COMMITTED' for e in r));self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'SETTLED');self.assertEqual(s.account.snapshot()['reserved_usdt'],'0');self.assertEqual(self.accept(s,p,4441),r);self.assertFalse(s.publication_descriptor().decode()['execution_authority'])
 def test_reconnect_retains_uncertain_collateral_and_never_reuses_old_quote(self):
  s,_=self.opened();self.accept(s,source_packet([book_row(8,4310,connection='c'*32)],7,4320),4320);r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['uncertainty'],'SOURCE_GAP');self.assertNotEqual(s.account.snapshot()['reserved_usdt'],'0')
 def test_changed_funding_schedule_retains_collateral_instead_of_old_interval(self):
  s,_=self.opened();self.accept(s,source_packet([funding_row(8,next_ms='57600000',event=4200)],7,4320),4320);r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['uncertainty'],'FUNDING_CHANGED')

 def test_unknown_funding_never_creates_a_fill_or_reserved_cash(self):
  s,events=self.opened(known=False);r=s.account.snapshot();self.assertEqual(r['reserved_usdt'],'0');self.assertTrue(all(x['status']=='DENIED' for x in r['reservations']));self.assertTrue(any(e.decode()['detail'].get('risk',{}).get('reason')=='FUNDING_UNPROVEN' for e in events))
 def test_processing_delay_does_not_relabel_source_request_or_funding_observation(self):
  s,_=self.opened();saved=copy.deepcopy(s._state['BTCUSDT']['funding'][0]);fund=s._funding('BTCUSDT',4400);self.assertEqual(fund['observed_ms'],4096);self.assertEqual(saved,s._state['BTCUSDT']['funding'][0]);self.assertEqual(saved['request']['as_of_ms'],4100)
 def test_risk_processing_delay_does_not_refresh_expired_proposal_window(self):
  s,_=self.opened(delay=501);r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['uncertainty'],'QUOTE_TIMEOUT');self.assertEqual(r['candidate']['signal']['expires_ms'],4800);self.assertNotEqual(s.account.snapshot()['reserved_usdt'],'0')
 def test_revocation_precedes_another_packet_validation_and_keeps_reserved_bytes(self):
  s,_=self.opened();before={p.name:p.read_bytes() for p in self.root.iterdir()};s.account.require_current=lambda:False
  with patch('market_data.paper_inputs.validate_paper_inputs',side_effect=AssertionError('NO_SOURCE_WORK')),self.assertRaises(ValueError):s.accept_packet({},expected_request={})
  self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before);self.assertEqual(s.status()['state'],'BLOCKED')
 def test_no_packet_arrival_holds_cursor_then_later_packet_has_own_asof(self):
  s=self.session();first=packet(['100','100.01','100.02','100.03'],as_of=4000);self.accept(s,first,4000);self.clock[0]=4050;s.advance();self.assertEqual(s.status()['instruments']['BTCUSDT']['cursor'],4);second=source_packet([book_row(5,4090),funding_row()],4,4100);self.accept(s,second,4100);self.assertEqual(s.status()['instruments']['BTCUSDT']['cursor'],6);self.assertEqual(first['request']['as_of_ms'],4000);self.assertEqual(second['request']['as_of_ms'],4100)
 def test_fractional_funding_units_are_exact_and_nonintegral_clock_is_unavailable(self):
  s=self.session();self.assertEqual(s._funding_values({'funding_interval_hour':'0.125','next_funding_time':'450000.0'}),(450000,450000));self.assertEqual(s._funding_values({'funding_interval_hour':0.125,'next_funding_time':450000.0}),(450000,450000));self.assertIsNone(s._funding_values({'funding_interval_hour':'.125','next_funding_time':'450000.1'}));self.assertIsNone(s._funding_values({'funding_interval_hour':'0.0000000001','next_funding_time':'450000'}))
 def test_foreign_completed_result_blocks_before_a_publication_descriptor(self):
  from terminan.causal_replay import calculate_causal_receipt
  from test_causal_receipt import request
  from test_causal_quote_schedule import fixture
  s,_=self.opened();s.account._results.record(calculate_causal_receipt(request(),now_ms=fixture()['now_ms']))
  with patch.object(s,'_emit',side_effect=AssertionError('NO_FINANCIAL_PUBLICATION')),self.assertRaises(ValueError):s.publication_artifact()
  self.assertEqual(s.status()['state'],'BLOCKED')
 def test_closing_window_abstains_before_a_new_risk_reservation(self):
  s=self.session();self.accept(s,packet(['100','100.01','100.02','100.03'],as_of=4000),4000);self.accept(s,packet(['101'],after=4,start=7000,as_of=7300,buy=40),7300);self.assertEqual(s.status()['instruments']['BTCUSDT']['issue'],'RUN_WINDOW_CLOSING');self.assertEqual(s.account.snapshot()['reservations'],[])

 def test_ten_symbols_actual_data_math_engine_and_verified_artifact(self):
  from terminan.causal_replay import SYMBOLS
  import hashlib,json
  s=self.session();symbols=sorted(SYMBOLS)
  def feed(p,now):
   for symbol in symbols:self.accept(s,resymbol(p,symbol),now)
  feed(packet(['100','100.01','100.02','100.03'],as_of=4000),4000);feed(source_packet([book_row(5,4090),funding_row()],4,4100),4100);feed(packet(['101'],after=6,start=4000,as_of=4300,buy=40),4300)
  self.assertEqual(len(s.account.snapshot()['reservations']),10);self.assertTrue(all(r['status']=='DECIDED' for r in s.account.snapshot()['reservations']))
  feed(source_packet([book_row(8,4305)],7,4310),4310);self.assertTrue(all(r['status']=='DECIDED' for r in s.account.snapshot()['reservations']))
  feed(source_packet([book_row(9,4310)],8,4320),4320);feed(source_packet([book_row(10,4410)],9,4420),4420);feed(source_packet([book_row(11,4430,'102','102.1')],10,4440),4440)
  self.assertTrue(all(r['status']=='SETTLED' for r in s.account.snapshot()['reservations']));self.assertEqual(s.account.snapshot()['reserved_usdt'],'0');artifact=s.publication_artifact();body=json.loads(artifact.artifact_json);self.assertEqual(body['row_count'],10);self.assertEqual({r['symbol'] for r in body['rows']},set(symbols));self.assertEqual(hashlib.sha256(artifact.artifact_json).hexdigest(),artifact.sha256);self.assertEqual(artifact.descriptor.decode()['detail']['paper_sha256'],artifact.sha256);self.assertFalse(body['execution_authority']);self.assertEqual(body['point_in_time_availability'],'UNKNOWN');from terminan.causal_artifacts import validate_causal_ledger_artifact;self.assertEqual(validate_causal_ledger_artifact(artifact.artifact_json,expected_sha256=artifact.sha256),body)
 def test_finish_is_idempotent_and_retains_unresolved_collateral(self):
  from terminan.causal_session import CausalPaperSession
  s,_=self.opened();self.clock[0]=4350;events=s.finish();self.assertEqual(s.status()['state'],'FINISHED');r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['uncertainty'],'RESTART');self.assertNotEqual(s.account.snapshot()['reserved_usdt'],'0');self.assertEqual(s.finish(),());self.assertTrue(any(e.decode()['kind']=='SESSION_FINISHED' for e in events))
  with patch('terminan.analytics.book_tape_research.BookTapeResearch',side_effect=AssertionError('NO_RESTART_FACTORY')),self.assertRaises(ValueError):CausalPaperSession(s.account,run_id='another',strategy_revision='1'*40,planned_duration_ms=4000,source_max_age_ms=10000,clock_ms=lambda:4400)

def resymbol(p,symbol):
 from market_data.paper_inputs import export_paper_inputs
 from datetime import datetime,timezone,timedelta
 q=dict(p['request'],symbol=symbol);epoch=datetime(1970,1,1,tzinfo=timezone.utc);rows=[]
 for row in p['rows']:
  payload=copy.deepcopy(row['payload'])
  if '_quality' in payload:payload['_quality']['symbol']=symbol
  rows.append(dict(id=row['id'],symbol=symbol,source=row['source'],event_type=row['event_type'],payload=payload,event_ts=epoch+timedelta(microseconds=int(row['event_us'])),ingest_ts=epoch+timedelta(microseconds=int(row['ingest_us']))))
 return export_paper_inputs(rows,q)
