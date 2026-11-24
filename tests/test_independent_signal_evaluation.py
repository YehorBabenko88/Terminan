"""Closed independent hypothetical accounts; real sole engine/Math, no IO."""
import unittest,json,hashlib,dataclasses,enum,os,random
from decimal import Decimal as D,getcontext
from datetime import datetime
from types import MappingProxyType
from unittest.mock import patch
from terminan import research_evaluation as core,research_entry_evaluation as rich,research_reporting as reports
from terminan.research_signals import ResearchSignal,SignalNotFilled
from terminan.continuation_strategy import CandleBodyObservation,generate_continuation_entries
from terminan.volatility import VolatilityRegime
import history_statistics,market_math
import test_rich_entry_transfer as fixtures

def encoded(value):
 if dataclasses.is_dataclass(value):return {'type':type(value).__name__,'fields':{f.name:encoded(getattr(value,f.name)) for f in dataclasses.fields(value)}}
 if isinstance(value,enum.Enum):return {'enum':type(value).__name__,'value':value.value}
 if type(value) is D:return {'decimal':str(value)}
 if type(value) is datetime:return {'utc':value.isoformat()}
 if type(value) is MappingProxyType or type(value) is dict:return {k:encoded(v) for k,v in value.items()}
 if type(value) in (tuple,list):return [encoded(v) for v in value]
 return value

def fingerprint(value):return hashlib.sha256(json.dumps(encoded(value),sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')).hexdigest()

class IndependentSignalAccountTests(unittest.TestCase):
 def model(self):
  value=getattr(core,'EvaluationAccountModel',None);self.assertIsNotNone(value,'CLOSED_ACCOUNT_MODEL_REQUIRED');return value.INDEPENDENT_PER_SIGNAL_V1
 def bars(self,delayed=False):
  return tuple(core.EvaluationCandle(i*60000,(i+1)*60000,300000 if delayed and i==1 else (i+1)*60000,D(100),D(106 if i==2 else 101),D(99),D(105 if i==2 else 100),D(1)) for i in range(3))
 def offers(self):return (ResearchSignal('BTCUSDT',0,'long','market',None,D(95),D(105)),ResearchSignal('BTCUSDT',60000,'long','market',None,D(95),D(105)))
 def evaluate(self,*,delayed=False,signals=None,candles=None,**kwargs):
  options=dict(dataset=core.EvaluationDataset('a'*64,'BTCUSDT','USDT',0,300000 if delayed else 180000),bar_ms=60000,folds=1,notional=D(100),fee_rate=D(0),slippage_bps=D(0));options.update(kwargs)
  return core.evaluate_research_signals('volatility_continuation_v2',self.offers() if signals is None else signals,self.bars(delayed) if candles is None else candles,**options)
 def rich_evaluate(self,**kwargs):
  f=fixtures.RichEntryTransferTests();entries=generate_continuation_entries('BTCUSDT',tuple(CandleBodyObservation(i*60000,(i+1)*60000,(i+1)*60000,100,101) for i in range(2)),tuple(f.vol(event_start_ms=i*60000,available_at_ms=(i+1)*60000) for i in range(2)),as_of_ms=120000)
  entries=tuple(dataclasses.replace(e,signal=dataclasses.replace(e.signal,stop=D(95),target=D(105))) for e in entries)
  rows=tuple(core.EvaluationCandle(i*60000,(i+1)*60000,(i+1)*60000,D(100),D(106 if i==3 else 101),D(99),D(105 if i==3 else 100),D(1)) for i in range(4))
  return rich.evaluate_research_entries('volatility_continuation_v2',entries,rows,dataset=core.EvaluationDataset('a'*64,'BTCUSDT','USDT',0,240000),bar_ms=60000,folds=1,notional=D(100),fee_rate=D(0),slippage_bps=D(0),**kwargs)
 def report(self,source):
  filled=tuple(p for p in source.outcomes if p.outcome.disposition is core.EvaluationDisposition.FILLED)
  rows=tuple(reports.DeclaredTradeMetadata(p.entry.signal.symbol,p.entry.decision_ms,p.outcome.known_at_ms,coverage=reports.CoverageDeclaration.COMPLETE_HISTORY if i==0 else reports.CoverageDeclaration.PARTIAL_HISTORY) for i,p in enumerate(filled))
  return reports.build_research_report(source,rows,value_unit='USDT')
 def default_snapshots(self):
  a=self.evaluate();b=self.rich_evaluate();c=self.report(b)
  return {name:fingerprint(value) for name,value in (('core',a),('rich',b),('report',c))}
 def test_default_core_rich_report_bytes_match_public83f_goldens(self):
  import pathlib
  expected=json.loads((pathlib.Path(__file__).parent/'fixtures/independent_accounts/default83f.json').read_text(encoding='utf-8'))
  self.assertEqual(self.default_snapshots(),expected['sha256'])
 def test_overlap_independent_two_net10_default_one_net5(self):
  mode=self.model();old=self.evaluate();new=self.evaluate(account_model=mode)
  self.assertEqual([o.disposition.value for o in old.outcomes],['FILLED','POSITION_OCCUPIED']);self.assertEqual(old.numeric.numeric.total,5.)
  self.assertEqual([o.disposition.value for o in new.outcomes],['FILLED','FILLED']);self.assertEqual(tuple(o.execution.fill.net for o in new.outcomes),(D(5),D(5)));self.assertEqual(new.numeric.numeric.total,10.)
  self.assertEqual([o.known_at_ms for o in new.outcomes],[180000,180000]);self.assertEqual([o.execution.exit_ms for o in new.outcomes],[120000,120000]);self.assertIsNot(new.outcomes[0].execution,new.outcomes[1].execution)
 def test_nofill_pending_is_local_to_independent_signal(self):
  mode=self.model();first=dataclasses.replace(self.offers()[0],entry_kind='limit',entry_price=D(50),stop=D(49),target=D(51));offers=(first,self.offers()[1])
  old=self.evaluate(signals=offers);new=self.evaluate(signals=offers,account_model=mode)
  self.assertEqual([o.disposition.value for o in old.outcomes],['NOT_FILLED','POSITION_OCCUPIED']);self.assertEqual([o.disposition.value for o in new.outcomes],['NOT_FILLED','FILLED']);self.assertEqual([o.known_at_ms for o in new.outcomes],[180000,180000]);self.assertEqual(new.numeric.numeric.total,5.)
 def test_delayed_middle_dependency_max_is_per_signal(self):
  mode=self.model();new=self.evaluate(delayed=True,account_model=mode)
  self.assertEqual([o.known_at_ms for o in new.outcomes],[300000,300000]);self.assertEqual(new.numeric.numeric.total,10.)
  first=dataclasses.replace(self.offers()[0],entry_kind='limit',entry_price=D(50),stop=D(49),target=D(51));new=self.evaluate(delayed=True,signals=(first,self.offers()[1]),account_model=mode)
  self.assertEqual([o.known_at_ms for o in new.outcomes],[300000,300000])
 def test_invalid_model_refuses_before_math_or_factory_without_callbacks(self):
  self.model();calls=[]
  class Meta(type):
   def __eq__(self,other):calls.append('meta');return False
  class Foreign(metaclass=Meta):pass
  class Text(str):
   def __str__(self):calls.append('str');return 'INDEPENDENT_PER_SIGNAL_V1'
  for invalid in (None,True,'INDEPENDENT_PER_SIGNAL_V1',Text('x'),Foreign()):
   with patch.object(market_math,'candle_ohlcv_valid',side_effect=AssertionError('MATH')),patch.object(core,'PaperEngine',side_effect=AssertionError('ENGINE')):
    with self.assertRaises(ValueError):self.evaluate(account_model=invalid)
    with self.assertRaises(ValueError):self.rich_evaluate(account_model=invalid)
  self.assertEqual(calls,[])
 def test_default_explicit_member_keeps_old_hashes(self):
  self.model();mode=core.EvaluationAccountModel.FOLD_OCCUPANCY_V1
  self.assertEqual(self.evaluate(),self.evaluate(account_model=mode));self.assertEqual(self.rich_evaluate(),self.rich_evaluate(account_model=mode))
 def test_empty_mode_hash_chain_distinct_and_reports_explicit_versions(self):
  mode=self.model();old=self.evaluate(signals=());new=self.evaluate(signals=(),account_model=mode)
  self.assertEqual(old.numeric,new.numeric);self.assertNotEqual(old.input_sha256,new.input_sha256);self.assertEqual(new.policy,'CANDLE_INDEX_INDEPENDENT_SIGNAL_ACCOUNTS_V2')
  a=self.rich_evaluate();b=self.rich_evaluate(account_model=mode);ra=self.report(a);rb=self.report(b)
  self.assertEqual(b.version,'research_entry_evaluation.v3');self.assertNotEqual(a.input_sha256,b.input_sha256);self.assertNotEqual(ra.input_sha256,rb.input_sha256);self.assertEqual(rb.schema,'terminan.research-performance-report.independent-signals.v2')
  self.assertEqual((rb.all_filled.net.numeric.count,rb.all_filled.net.numeric.total),(2,10.));self.assertEqual([p.numeric.net.numeric.count for p in rb.by_coverage],[1,1,0])
  for record in (new,b,rb):self.assertIs(record.execution_authority,False);self.assertIs(record.trading_authorized,False);self.assertEqual(record.source_authentication,'NOT_EVALUATED')
  self.assertIs(rb.point_in_time_qualified,False);self.assertIs(rb.completeness_qualified,False)
 def test_report_rejects_unknown_mismatched_models_and_independent_occupied(self):
  mode=self.model();value=self.rich_evaluate(account_model=mode)
  invalid=(dataclasses.replace(value,version='research_entry_evaluation.v2'),dataclasses.replace(value,evaluation=dataclasses.replace(value.evaluation,policy='UNKNOWN')))
  for bad in invalid:
   with patch.object(market_math,'paper_execution_values_valid',side_effect=AssertionError('DOMAIN')),patch.object(history_statistics,'project_decimal_observations',side_effect=AssertionError('PROJECTION')):
    with self.assertRaises(ValueError):self.report(bad)
  pair=value.outcomes[1];badout=dataclasses.replace(pair.outcome,disposition=core.EvaluationDisposition.POSITION_OCCUPIED,execution=None);bad=dataclasses.replace(value,outcomes=(value.outcomes[0],dataclasses.replace(pair,outcome=badout)),evaluation=dataclasses.replace(value.evaluation,outcomes=(value.evaluation.outcomes[0],badout)))
  with self.assertRaises(ValueError):self.report(bad)
 def test_future_bad_inputs_preflight_before_any_engine(self):
  mode=self.model();rows=self.bars();bad=rows[:-1]+(dataclasses.replace(rows[-1],open=D(-1)),)
  with patch.object(core,'PaperEngine',side_effect=AssertionError('ENGINE')):
   with self.assertRaises(ValueError):self.evaluate(candles=bad,account_model=mode)
   with self.assertRaises(ValueError):self.evaluate(signals=(self.offers()[0],dataclasses.replace(self.offers()[1],target=D(-1))),account_model=mode)
  with patch.object(market_math,'candle_ohlcv_valid',side_effect=AssertionError('MATH')),patch.object(core,'PaperEngine',side_effect=AssertionError('ENGINE')):
   with self.assertRaises(ValueError):self.evaluate(candles=rows[:-1]+(dataclasses.replace(rows[-1],available_at_ms=True),),account_model=mode)
 def test_snapshot_and_model_tag_derive_before_math_callbacks(self):
  mode=self.model();expected=self.evaluate(account_model=mode);offers=self.offers();rows=self.bars();original=market_math.candle_ohlcv_valid;oldvalue=mode.value;first=True
  def change(*args):
   nonlocal first
   if first:
    first=False;object.__setattr__(offers[1],'target',D(999));object.__setattr__(rows[1],'available_at_ms',999999);object.__setattr__(mode,'_value_','FOREIGN_CHANGED')
   return original(*args)
  try:
   with patch.object(market_math,'candle_ohlcv_valid',side_effect=change):actual=self.evaluate(signals=offers,candles=rows,account_model=mode)
  finally:object.__setattr__(mode,'_value_',oldvalue)
  self.assertEqual(actual,expected)
 def test_fresh_accounts_never_inherit_ledger_environment_or_mutable_state(self):
  mode=self.model();real=core.PaperEngine;engines=[]
  class Capture(real):
   def __init__(self,**kwargs):super().__init__(**kwargs);engines.append(self)
  from terminan.paper_ledger import PaperReplayLedger
  with patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':'FORBIDDEN_USER_LEDGER'}),patch.object(PaperReplayLedger,'__init__',side_effect=AssertionError('LEDGER')),patch.object(PaperReplayLedger,'lookup_existing',side_effect=AssertionError('LEDGER')),patch.object(core,'PaperEngine',Capture):result=self.evaluate(account_model=mode)
  self.assertEqual(result.numeric.numeric.total,10.);self.assertEqual(len(engines),2)
  for name in ('reference','positions','fills','last_trade_time'):self.assertEqual(len({id(getattr(e,name)) for e in engines}),2)
  self.assertEqual([len(e.fills) for e in engines],[1,1]);self.assertEqual([e.positions for e in engines],[{},{}])
 def test_exact_resource_caps_and_no_factory_for_outside_offer(self):
  mode=self.model();real=core.PaperEngine;engines=[]
  def make(**kwargs):e=real(**kwargs);engines.append(e);return e
  with patch.object(core,'PaperEngine',side_effect=make):out=self.evaluate(account_model=mode,embargo_ms=60000)
  self.assertEqual(len(engines),1);self.assertEqual([x.disposition.value for x in out.outcomes],['OUTSIDE_TEST_WINDOW','FILLED'])
  offers=tuple(ResearchSignal('BTCUSDT',i,'long','market',None,D(95),D(105)) for i in range(512));row=core.EvaluationCandle(0,60000,60000,D(100),D(101),D(99),D(100),D(1));engines.clear()
  with patch.object(core,'PaperEngine',side_effect=make):out=self.evaluate(account_model=mode,signals=offers,candles=(row,))
  self.assertEqual(len(out.outcomes),512);self.assertEqual(len(engines),512)
  with patch.object(core,'PaperEngine',side_effect=AssertionError('ENGINE')),patch.object(market_math,'candle_ohlcv_valid',side_effect=AssertionError('MATH')):
   with self.assertRaises(ValueError):self.evaluate(account_model=mode,signals=offers+(dataclasses.replace(offers[-1],decision_ms=512),),candles=(row,))
   with self.assertRaises(ValueError):self.evaluate(account_model=mode,candles=self.bars()*2000)
   with self.assertRaisesRegex(ValueError,'ROW_VISIT_BUDGET'):self.evaluate(account_model=mode,signals=offers[:61],candles=(row,)*4096)
 def test_financial_policy_refuses_even_without_eligible_accounts(self):
  mode=self.model()
  with patch.object(core,'PaperEngine',side_effect=AssertionError('ENGINE')):
   with self.assertRaises(ValueError):self.evaluate(account_model=mode,signals=(),notional=D(-1))
   with self.assertRaises(ValueError):self.evaluate(account_model=mode,signals=(),fee_rate=D(-1))
 def test_other_owner_errors_abort_instead_of_becoming_nofill(self):
  mode=self.model()
  with patch.object(core.PaperEngine,'execute_signal',side_effect=ValueError('OWNER_REFUSED')):
   with self.assertRaisesRegex(ValueError,'OWNER_REFUSED'):self.evaluate(account_model=mode)
  class ForeignNoFill(SignalNotFilled):pass
  with patch.object(core.PaperEngine,'execute_signal',side_effect=ForeignNoFill('FOREIGN')):
   with self.assertRaises(ForeignNoFill):self.evaluate(account_model=mode)
 def test_decimal_context_rng_and_caller_objects_unchanged(self):
  mode=self.model();context=getcontext();old=context.copy();state=random.getstate();offers=self.offers();rows=self.bars();before=(repr(offers),repr(rows))
  try:
   context.prec=7;context.clear_flags();flags=dict(context.flags);self.evaluate(account_model=mode,signals=offers,candles=rows);self.assertEqual(context.prec,7);self.assertEqual(dict(context.flags),flags)
  finally:context.prec=old.prec;context.rounding=old.rounding;context.flags=old.flags;context.traps=old.traps
  self.assertEqual(random.getstate(),state);self.assertEqual((repr(offers),repr(rows)),before)
 def test_original28_fivefold_and_empty_both_models(self):
  mode=self.model();rows=tuple(core.EvaluationCandle(i*60000,(i+1)*60000,(i+1)*60000,D(100),D(101),D(99),D(100),D(1)) for i in range(150));offers=tuple(ResearchSignal('BTCUSDT',i*60000,'long','market',None,D(99),D(101)) for i in range(5,145,5))
  for account in (core.EvaluationAccountModel.FOLD_OCCUPANCY_V1,mode):
   out=self.evaluate(account_model=account,signals=offers,candles=rows,dataset=core.EvaluationDataset('a'*64,'BTCUSDT','USDT',0,9000000),folds=5)
   self.assertEqual(len(out.folds),5);self.assertEqual(out.numeric.numeric.count,28);self.assertTrue(all(o.disposition is core.EvaluationDisposition.FILLED for o in out.outcomes));self.assertEqual(out.numeric.numeric.total,-28.)
   empty=self.evaluate(account_model=account,signals=());self.assertEqual(empty.outcomes,());self.assertIsNone(empty.bootstrap)
 def test_original_reporting_two_roles_both_account_models(self):
  self.model()
  from test_research_reporting import ResearchReportingTests
  from unittest.mock import patch as replacing
  original=rich.evaluate_research_entries
  for mode in (core.EvaluationAccountModel.FOLD_OCCUPANCY_V1,core.EvaluationAccountModel.INDEPENDENT_PER_SIGNAL_V1):
   def selected(*args,**kwargs):return original(*args,**kwargs,account_model=mode)
   with replacing.object(rich,'evaluate_research_entries',side_effect=selected):
    for nets,regimes in (((D(2),D(100)),(VolatilityRegime.HIGH,)*2),((D(2),D(-1),D(3)),(VolatilityRegime.HIGH,VolatilityRegime.LOW,VolatilityRegime.HIGH))):
     owner=ResearchReportingTests().original_partition_vector(nets,regimes)
     declarations=tuple(reports.DeclaredTradeMetadata(p.entry.signal.symbol,p.entry.decision_ms,p.outcome.known_at_ms,coverage=reports.CoverageDeclaration.PARTIAL_HISTORY if i==len(nets)-1 else reports.CoverageDeclaration.COMPLETE_HISTORY) for i,p in enumerate(owner.outcomes))
     report=reports.build_research_report(owner,declarations,value_unit='USDT')
     self.assertEqual(report.all_filled.net.numeric.count,len(nets));self.assertEqual(report.all_filled.net.numeric.total,float(sum(nets)));self.assertEqual([p.numeric.net.numeric.count for p in report.by_coverage],[len(nets)-1,1,0])
     self.assertEqual(report.by_coverage[0].numeric.net.numeric.total,2. if len(nets)==2 else 1.);self.assertEqual(report.by_coverage[1].numeric.net.numeric.total,100. if len(nets)==2 else 3.)
     self.assertIs(report.execution_authority,False);self.assertIs(report.trading_authorized,False);self.assertIs(report.completeness_qualified,False)
