import copy,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from market_data.paper_inputs import export_paper_inputs

def packet(prices,*,after=0,start=1000,as_of=10000,epoch='b'*32,buy=10,sell=1):
 context=dict(schema='market_data.public-market-connection.v1',venue='bybit',category='linear',endpoint='wss://stream.bybit.com/v5/public/linear',connection_id=epoch,scope='PRODUCER_DECLARED_LOCAL_CONNECTION_NOT_REMOTE_AUTHENTICATION')
 rows=[]
 for i,price in enumerate(prices):
  stamp=start+i*250;large=(buy==40);payload=dict(start_ms=stamp,open=str(price),high=str(price),low=str(price),close=str(price),buy_volume=buy,sell_volume=sell,buy_count=buy,sell_count=sell,trade_count=41 if large else 11,delta=39 if large else 9,cvd=39 if large else 9,range=0,aggressor_imbalance='0.9512195121951219' if large else '0.8181818181818182',_producer_connection=context)
  if epoch is None:payload.pop('_producer_connection')
  rows.append(dict(id=after+i+1,symbol='BTCUSDT',source='bybit',event_type='trade_tape_250ms',payload=payload,event_ts=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=stamp),ingest_ts=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=stamp+251)))
 q=dict(symbol='BTCUSDT',after_id=after,start_ms=0,end_ms=as_of+1,as_of_ms=as_of,max_age_ms=10000)
 return export_paper_inputs(rows,q)
class BookTapeTests(unittest.TestCase):
 def method(self,**kw):
  from terminan.analytics.book_tape_research import BookTapeResearch
  return BookTapeResearch('BTCUSDT',**kw)
 def observe(self,m,p):return m.observe_packet(p,expected_request=p['request'])
 def test_original_warmup_breakout_role_uses_canonical_math_and_declared_cut(self):
  m=self.method(window=16,min_history=8);first=packet(['100','100.01','100.02','100.03','100.04','100.05','100.06','100.07'],as_of=4000);a=self.observe(m,first);self.assertTrue(all(x['eligible'] is False for x in a.observations));last=packet(['101'],after=8,start=3000,as_of=4000,buy=40);r=self.observe(m,last).observations[0];self.assertTrue(r['eligible']);self.assertEqual(r['direction'],1);self.assertTrue(r['patterns']['jbe_proxy']);self.assertEqual(r['available_from_ms'],4000);self.assertEqual(r['source_authenticity'],'NOT_EVALUATED');self.assertEqual(r['point_in_time_availability'],'UNKNOWN');self.assertFalse(r['execution_authority']);self.assertEqual(r['row_sha256'],last['rows'][0]['row_sha256'])
 def test_duplicate_or_invalid_last_row_never_advances_history_or_cursor(self):
  m=self.method(min_history=4);p=packet(['100','100.01','100.02','100.03']);self.observe(m,p);before=m.snapshot()
  with self.assertRaises(ValueError):self.observe(m,p)
  self.assertEqual(m.snapshot(),before)
  p=packet(['101','102'],after=4,start=3000);p['rows'][-1]['payload']['buy_volume']='NaN'
  with self.assertRaises(ValueError):self.observe(m,p)
  self.assertEqual(m.snapshot(),before)
 def test_math_refusal_after_earlier_staged_row_is_atomic(self):
  import market_math
  m=self.method(min_history=4);self.observe(m,packet(['100','100.01','100.02','100.03']));before=m.snapshot();real=market_math.book_tape_research_metrics;calls=[]
  def reject_last(*args):
   calls.append(1)
   if len(calls)==2:raise ValueError('DOMAIN_REFUSAL')
   return real(*args)
  with patch('market_math.book_tape_research_metrics',side_effect=reject_last),self.assertRaises(ValueError):self.observe(m,packet(['101','102'],after=4,start=3000))
  self.assertEqual(m.snapshot(),before)
 def test_new_declared_tape_connection_resets_warmup_without_auth_upgrade(self):
  m=self.method(min_history=4);self.observe(m,packet(['100','100','100','100']));r=self.observe(m,packet(['101'],after=4,start=3000,epoch='c'*32));self.assertEqual(r.observations[0]['reason'],'warmup');self.assertFalse(r.observations[0]['eligible']);self.assertEqual(len(m.snapshot()['history']),1);self.assertEqual(r.packet['source_authenticity'],'NOT_EVALUATED')

 def test_original_flat_abstention_and_wrong_symbol_do_not_mix_history(self):
  m=self.method(min_history=4);self.observe(m,packet(['100','100','100','100']));r=self.observe(m,packet(['100'],after=4,start=3000)).observations[0];self.assertEqual(r['direction'],0);self.assertEqual(r['decision'],'ABSTAIN');before=m.snapshot()
  from terminan.analytics.book_tape_research import BookTapeResearch
  other=BookTapeResearch('ETHUSDT',min_history=4)
  with self.assertRaises(ValueError):self.observe(other,packet(['100']))
  self.assertEqual(other.snapshot()['history'],());self.assertEqual(m.snapshot(),before)
 def test_missing_producer_context_clears_history_without_a_candidate(self):
  m=self.method(min_history=4);self.observe(m,packet(['100','100','100','100']));r=self.observe(m,packet(['101'],after=4,start=3000,epoch=None)).observations[0];self.assertEqual(r['reason'],'SOURCE_CONTEXT_UNAVAILABLE');self.assertFalse(r['eligible']);self.assertEqual(m.snapshot()['history'],())
 def test_hostile_context_cannot_change_math_features_or_flags(self):
  from decimal import localcontext
  m=self.method(min_history=4)
  with localcontext() as c:
   c.prec=1;c.Emax=2;c.Emin=-2
   for signal in c.traps:c.traps[signal]=True
   c.clear_flags();self.observe(m,packet(['100','100.01','100.02','100.03']));r=self.observe(m,packet(['101'],after=4,start=3000,buy=40));self.assertEqual(r.observations[0]['direction'],1);self.assertFalse(any(c.flags.values()))
