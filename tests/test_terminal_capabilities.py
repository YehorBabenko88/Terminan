from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
import asyncio
import unittest
from terminan.analytics.core import Candle,Level
from terminan.analytics.level_quality import LevelReport,verified_levels
from terminan.analytics.level_sync import LevelSync
from terminan.external_terminal import TerminalClient,TerminalTransportError

START=datetime(2026,1,1,tzinfo=timezone.utc)
def candle(n,high='10',low='1'):return Candle(START+timedelta(minutes=n),D(high),D(low),D(low),D(high))
def report():return LevelReport((Level(D(10),'high',START,'M1'),),True,0,'verified requested range')

class QualityTests(unittest.TestCase):
 def test_complete_requested_closed_range_delegates_to_math(self):
  result=verified_levels([candle(1,'9','2'),candle(0)],'M1',START,START+timedelta(minutes=2),as_of=START+timedelta(minutes=2))
  self.assertTrue(result.verified);self.assertEqual(result.missing,0)
  self.assertEqual([(x.kind,x.price) for x in result.levels],[('high',D(10)),('low',D(1)),('high',D(9)),('low',D(2))])
 def test_gaps_unknown_calendar_and_future_do_not_publish(self):
  end=START+timedelta(minutes=2)
  gap=verified_levels([candle(0)],'M1',START,end,as_of=end)
  self.assertEqual((gap.verified,gap.missing,gap.levels),(False,1,()))
  self.assertFalse(verified_levels([candle(0)],'MO1',START,end,as_of=end).verified)
  with self.assertRaises(ValueError):verified_levels([candle(0),candle(1)],'M1',START,end,as_of=START)
 def test_duplicate_unaligned_naive_and_oversize_ranges_refuse(self):
  end=START+timedelta(minutes=1)
  for rows,start,finish in [([candle(0),candle(0)],START,end),([candle(0)],START,end+timedelta(seconds=1)),([candle(0)],START.replace(tzinfo=None),end),([],START,START+timedelta(minutes=20001))]:
   with self.subTest(rows=rows,start=start,finish=finish),self.assertRaises(ValueError):verified_levels(rows,'M1',start,finish,as_of=finish)

class FakeTerminal:
 def __init__(self,rows=()):self.rows=list(rows);self.calls=[];self.fail=False
 async def levels(self,connection,symbol):self.calls.append(('read',));return list(self.rows)
 async def remove_level(self,connection,ident):self.calls.append(('remove',ident))
 async def add_level(self,*args):
  self.calls.append(('add',args[-1]))
  if self.fail:raise TimeoutError('uncertain')

class SyncTests(unittest.IsolatedAsyncioTestCase):
 async def test_replace_only_owned_and_idempotent_after_reread(self):
  from terminan.metascalp_levels import PREFIX,signature
  note=PREFIX+signature('BTCUSDT',report().levels[0])
  terminal=FakeTerminal([{'id':1,'note':'user','price':'2'},{'id':2,'note':PREFIX+'a'*24,'price':'3'}]);sync=LevelSync(terminal)
  self.assertEqual(await sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True),1)
  self.assertEqual(terminal.calls,[('read',),('remove',2),('add',note)])
  terminal.rows=[{'id':3,'note':note,'price':'10'}];terminal.calls=[]
  await sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True)
  self.assertEqual(terminal.calls,[('read',)])
 async def test_truthy_trust_or_invalid_later_owned_row_precedes_any_write(self):
  from terminan.metascalp_levels import PREFIX
  terminal=FakeTerminal([{'id':2,'note':PREFIX+'a'*24,'price':'3'},{'id':True,'note':PREFIX+'b'*24,'price':'5'}]);sync=LevelSync(terminal)
  for options in [dict(connection_verified=1,instrument_verified=True),dict(connection_verified=True,instrument_verified=True)]:
   with self.assertRaises(ValueError):await sync.replace(1,'BTCUSDT',report(),**options)
  self.assertFalse(any(call[0]!='read' for call in terminal.calls))
 async def test_uncertain_post_never_retries_and_next_attempt_rereads(self):
  terminal=FakeTerminal();terminal.fail=True;sync=LevelSync(terminal)
  for _ in range(2):
   with self.assertRaises(TimeoutError):await sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True)
  self.assertEqual([x[0] for x in terminal.calls],['read','add','read','add'])
 async def test_crossing_stages_all_rows_and_requires_literal_continuity(self):
  from terminan.metascalp_levels import PREFIX
  terminal=FakeTerminal([{'id':2,'note':PREFIX+'a'*24,'price':'3'},{'id':3,'note':PREFIX+'b'*24,'price':'NaN'}]);sync=LevelSync(terminal)
  with self.assertRaises(ValueError):await sync.crossed(1,'BTCUSDT',D(1),D(4),contiguous=True,source='exchange_execution')
  self.assertEqual(terminal.calls,[('read',)])
  terminal.calls=[]
  with self.assertRaises(ValueError):await sync.crossed(1,'BTCUSDT',D(1),D(4),contiguous=1,source='exchange_execution')
  self.assertEqual(terminal.calls,[])

class Response:
 def __init__(self,value,status=200):self.status_code=status;self.value=value;self.content=b'{}'
 def json(self):return self.value
class FakeClient:
 def __init__(self,responses):self.responses=list(responses);self.calls=[];self.closed=False
 async def request(self,*args,**kwargs):
  self.calls.append((args,kwargs));value=self.responses.pop(0)
  if isinstance(value,BaseException):raise value
  return value
 async def aclose(self):self.closed=True
class TransportTests(unittest.IsolatedAsyncioTestCase):
 async def test_explicit_localhost_discovery_and_typed_routes(self):
  client=FakeClient([Response({'name':'MetaScalp'}),Response([]),Response(None),Response(None)])
  transport=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  self.assertEqual(await transport.discover(),'http://127.0.0.1:17845')
  await transport.levels(1,'BTCUSDT');await transport.add_level(1,'BTCUSDT','1.2','GreaterThanEqual','terminan:'+'a'*24);await transport.remove_level(1,2)
  self.assertTrue(all(call[0][1].startswith('http://127.0.0.1:17845/') for call in client.calls))
  self.assertTrue(all(call[1]['follow_redirects'] is False for call in client.calls))
  self.assertEqual(client.calls[2][1]['json']['name'],'Terminan')
  await transport.close();self.assertTrue(client.closed)
 async def test_read_retries_bounded_but_uncertain_write_not_replayed(self):
  client=FakeClient([Response({'name':'MetaScalp'}),TimeoutError(),Response([]),TimeoutError()]);transport=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  await transport.levels(1,'BTCUSDT')
  with self.assertRaises(TimeoutError):await transport.remove_level(1,2)
  self.assertEqual([c[0][0] for c in client.calls],['GET','GET','GET','DELETE'])
 async def test_invalid_typed_inputs_or_unrecognized_ping_refuse(self):
  client=FakeClient([Response({'name':'unrelated'})]*11);transport=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  for args in [(True,'BTCUSDT'),(1,'../bad')]:
   with self.assertRaises(ValueError):await transport.levels(*args)
  self.assertEqual(client.calls,[])
  with self.assertRaises(ConnectionError):await transport.discover()
  self.assertEqual(len(client.calls),11)
 async def test_cancellation_propagates_without_retry(self):
  client=FakeClient([Response({'name':'MetaScalp'}),asyncio.CancelledError()]);transport=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  with self.assertRaises(asyncio.CancelledError):await transport.levels(1,'BTCUSDT')
  self.assertEqual(len(client.calls),2)

class PublicationGateTests(unittest.TestCase):
 def test_single_publication_gate_refuses_truthy_and_nonfinite_values(self):
  from terminan.metascalp_levels import publication_decision
  from types import SimpleNamespace as S
  valid=report()
  for marker in (1,'yes',[],None):
   self.assertFalse(publication_decision(valid,connection_verified=marker,instrument_verified=True).allowed)
   self.assertFalse(publication_decision(valid,connection_verified=True,instrument_verified=marker).allowed)
   self.assertFalse(publication_decision(replace(valid,verified=marker),connection_verified=True,instrument_verified=True).allowed)
  for value in (D('NaN'),D('Infinity'),D('-Infinity'),D(0),D(-1),True,1.2):
   invalid=replace(valid,levels=(replace(valid.levels[0],price=value),))
   self.assertFalse(publication_decision(invalid,connection_verified=True,instrument_verified=True).allowed)
  for limit in (True,-1,501,'1'):
   self.assertFalse(publication_decision(valid,connection_verified=True,instrument_verified=True,max_levels=limit).allowed)

class ReconciliationBoundaryTests(unittest.IsolatedAsyncioTestCase):
 async def test_duplicate_note_id_and_conflicting_case_fields_refuse_before_writes(self):
  from terminan.metascalp_levels import PREFIX
  a={'id':2,'note':PREFIX+'a'*24,'price':3.0}
  for bad in ({**a,'id':3},{**a,'note':PREFIX+'b'*24},{**a,'note':'manual'},{**a,'Id':4},{**a,'Price':'4'}):
   terminal=FakeTerminal([a,bad]);sync=LevelSync(terminal)
   with self.assertRaises(ValueError):await sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True)
   self.assertEqual(terminal.calls,[('read',)])
 async def test_valid_float_vendor_price_and_contiguous_crossing(self):
  from terminan.metascalp_levels import PREFIX
  terminal=FakeTerminal([{'id':2,'note':PREFIX+'a'*24,'price':3.0},{'id':4,'note':'manual','price':'3'}]);sync=LevelSync(terminal)
  self.assertEqual(await sync.crossed(1,'BTCUSDT',D(1),D(4),contiguous=True,source='exchange_execution'),1)
  self.assertEqual(terminal.calls,[('read',),('remove',2)])
 async def test_same_instrument_serializes_and_cancellation_releases_lock(self):
  from terminan.metascalp_levels import PREFIX
  entered=asyncio.Event();release=asyncio.Event()
  class Blocking(FakeTerminal):
   async def levels(self,*args):
    self.calls.append(('read',));entered.set();await release.wait();return []
  terminal=Blocking();sync=LevelSync(terminal)
  first=asyncio.create_task(sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True))
  await entered.wait()
  second=asyncio.create_task(sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True))
  await asyncio.sleep(0);self.assertEqual(terminal.calls,[('read',)])
  first.cancel()
  with self.assertRaises(asyncio.CancelledError):await first
  release.set();await second
  self.assertEqual([x[0] for x in terminal.calls],['read','read','add'])
 async def test_bounded_instrument_locks_and_invalid_report_no_io(self):
  terminal=FakeTerminal();sync=LevelSync(terminal)
  for i in range(128):sync._lock(i+1,'BTCUSDT')
  with self.assertRaises(ValueError):sync._lock(129,'BTCUSDT')
  for bad in (replace(report().levels[0],kind='guess'),replace(report().levels[0],price=D('1.'+'1'*300))):
   invalid=replace(report(),levels=(bad,))
   with self.assertRaises(ValueError):await sync.replace(1,'BTCUSDT',invalid,connection_verified=True,instrument_verified=True)
  self.assertEqual(terminal.calls,[])

class TransportBudgetTests(unittest.IsolatedAsyncioTestCase):
 async def test_read_failure_is_exactly_three_attempts_and_write_status_not_retried(self):
  client=FakeClient([Response({'name':'MetaScalp'}),Response({},500),Response({},500),Response({},500)])
  terminal=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  with self.assertRaises(TerminalTransportError):await terminal.connections()
  self.assertEqual(len(client.calls),4);self.assertIsNone(terminal.base)
  client=FakeClient([Response({'name':'MetaScalp'}),Response({},500)])
  terminal=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  with self.assertRaises(TerminalTransportError):await terminal.open_combos(['BTCUSDT'])
  self.assertEqual(len(client.calls),2)
 async def test_oversized_response_and_invalid_mutation_never_retry(self):
  large=Response([]);large.content=b'x'*1048577
  client=FakeClient([Response({'name':'MetaScalp'}),large]);terminal=TerminalClient(client,sleep=lambda _:asyncio.sleep(0))
  with self.assertRaises(ValueError):await terminal.levels(1,'BTCUSDT')
  self.assertEqual(len(client.calls),2)
  for price in ('NaN','Infinity','0','-1'):
   with self.assertRaises(ValueError):await terminal.add_level(1,'BTCUSDT',price,'GreaterThanEqual','terminan:'+'a'*24)
  with self.assertRaises(ValueError):await terminal.open_combos(['BTCUSDT','BTCUSDT'])
  self.assertEqual(len(client.calls),2)

class AmbiguousResponseTests(unittest.IsolatedAsyncioTestCase):
 async def test_competing_known_wrappers_never_create_duplicate_annotation(self):
  from terminan.metascalp_levels import PREFIX,signature,parse_rows
  owned={'id':1,'price':'10','note':PREFIX+signature('BTCUSDT',report().levels[0])}
  for response in ({'items':[],'levels':[owned]},{'items':None,'levels':[owned]}):
   class Raw(FakeTerminal):
    async def levels(self,*args):self.calls.append(('read',));return response
   terminal=Raw();sync=LevelSync(terminal)
   with self.assertRaises(ValueError):await sync.replace(1,'BTCUSDT',report(),connection_verified=True,instrument_verified=True)
   self.assertEqual(terminal.calls,[('read',)])
   with self.assertRaises(ValueError):parse_rows(response)
