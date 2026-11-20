import copy,unittest
from decimal import Decimal as D,localcontext
from unittest.mock import patch
from terminan.paper import PaperEngine
from test_causal_quote_schedule import fixture,seal
class CausalEngineTests(unittest.TestCase):
 def engine(self):
  engine=PaperEngine(notional='100.1',slippage_bps='10');engine.enabled=True;return engine
 def execute(self,engine,args=None,fee=D(10)):
  method=getattr(engine,'execute_quote',None);self.assertIsNotNone(method,'extend the only canonical engine')
  return method(**(fixture() if args is None else args),fee_bps=fee)
 def profitable(self):
  value=fixture();row=dict(value['quotes'][1]);row.pop('sha256');row.update(bid='110',ask='111');value['quotes'][1]=seal(row);return value
 def test_actual_math_quote_metrics_append_one_canonical_fill(self):
  value=self.profitable();before=copy.deepcopy(value);engine=self.engine();result=self.execute(engine,value)
  self.assertEqual(result.metrics.qty,D(1));self.assertEqual(result.metrics.net,D('9.58001'));self.assertEqual(result.fill.net,result.metrics.net);self.assertEqual(result.fill.gross,result.metrics.gross_fill);self.assertEqual(engine.fills,[result.fill]);self.assertEqual(value,before)
 def test_malformed_late_quote_and_math_refusal_leave_all_engine_state_unchanged(self):
  engine=self.engine();before=copy.deepcopy(engine.__dict__);value=self.profitable();row=dict(value['quotes'][1]);row.pop('sha256');row['bid']='NaN';value['quotes'][1]=seal(row)
  with self.assertRaises(ValueError):self.execute(engine,value)
  self.assertEqual(engine.__dict__,before)
  with patch('market_math.paper_quote_metrics',side_effect=ValueError('REFUSED')),self.assertRaises(ValueError):self.execute(engine,self.profitable())
  self.assertEqual(engine.__dict__,before)
 def test_disabled_or_unavailable_quote_kernel_never_commits(self):
  engine=self.engine();engine.enabled=False
  with self.assertRaises(ValueError):self.execute(engine)
  engine.enabled=True;before=copy.deepcopy(engine.__dict__)
  with patch('market_math.paper_quote_metrics',None),self.assertRaises(ValueError):self.execute(engine)
  self.assertEqual(engine.__dict__,before)
 def test_quote_policy_ignores_hostile_context_and_rejects_replayed_decisions(self):
  engine=self.engine()
  with localcontext() as ctx:
   ctx.prec=2;ctx.Emin=-2;ctx.Emax=2;ctx.clear_flags()
   for trap in ctx.traps:ctx.traps[trap]=True
   result=self.execute(engine,self.profitable());self.assertEqual(result.metrics.net,D('9.58001'));self.assertFalse(any(ctx.flags.values()))
  before=copy.deepcopy(engine.__dict__)
  with self.assertRaises(ValueError):self.execute(engine,self.profitable())
  self.assertEqual(engine.__dict__,before)

 def test_unselected_bad_books_refuse_and_locked_book_remains_explicitly_allowed(self):
  for index,changes in ((0,{'bid':'-1'}),(1,{'ask':'1e13'}),(0,{'bid':'101'})):
   value=self.profitable();row=dict(value['quotes'][index]);row.pop('sha256');row.update(changes);value['quotes'][index]=seal(row);engine=self.engine();before=copy.deepcopy(engine.__dict__)
   with self.subTest(changes=changes),self.assertRaises(ValueError):self.execute(engine,value)
   self.assertEqual(engine.__dict__,before)
  value=self.profitable();row=dict(value['quotes'][0]);row.pop('sha256');row['bid']='100';value['quotes'][0]=seal(row);self.assertEqual(self.execute(self.engine(),value).metrics.qty,D(1))
 def test_selected_chronological_funding_is_charged_by_math_only(self):
  from test_causal_quote_schedule import receipt
  value=self.profitable();f=dict(value['funding']);f.pop('sha256');f.update(kind='COMPLETE_EVENTS',previous_ms=0,next_ms=600,interval_ms=200,observed_ms=400,events=[receipt('f200',event_ms=200,observed_ms=200,rate='0.001',mark_price='100'),receipt('f400',event_ms=400,observed_ms=400,rate='0.001',mark_price='100')]);value['funding']=seal(f);value['now_ms']=451;value['max_quote_age_ms']=200
  result=self.execute(self.engine(),value);self.assertEqual(result.metrics.funding,D('.1'));self.assertEqual(result.fill.net,D('9.48001'))

 def test_unselected_funding_event_domain_is_validated_before_any_fill(self):
  from test_causal_quote_schedule import receipt
  for field,value in (('rate','2'),('mark_price','-1'),('mark_price','1e13')):
   data=self.profitable();events=[receipt('f200',event_ms=200,observed_ms=200,rate='0.001',mark_price='100'),receipt('f400',event_ms=400,observed_ms=400,rate='0.001',mark_price='100')];changed=dict(events[-1]);changed.pop('sha256');changed[field]=value;events[-1]=seal(changed);f=dict(data['funding']);f.pop('sha256');f.update(kind='COMPLETE_EVENTS',previous_ms=0,next_ms=600,interval_ms=200,observed_ms=400,events=events);data['funding']=seal(f);data['now_ms']=451;data['max_quote_age_ms']=200;engine=self.engine();before=copy.deepcopy(engine.__dict__)
   with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.execute(engine,data)
   self.assertEqual(engine.__dict__,before)
