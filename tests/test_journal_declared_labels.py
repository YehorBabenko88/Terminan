"""Posthoc journal labels: collected in report rows, never execution evidence."""
import unittest
from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch
from contextlib import ExitStack
import test_research_reporting as fixtures
import test_independent_signal_evaluation as accounts
from terminan import research_reporting as api
from terminan import research_evaluation as core
from terminan.volatility import VolatilityRegime

class JournalDeclaredLabelTests(unittest.TestCase):
 def source(self):return fixtures.ResearchReportingTests().evaluation()
 def row(self,e,**kwargs):return fixtures.ResearchReportingTests().declaration(e,**kwargs)
 def build(self,e,rows=()):return api.build_research_report(e,rows,value_unit='USDT')
 def blocked(self):
  stack=ExitStack()
  for name in ('market_math.paper_execution_values_valid','history_statistics.project_decimal_observations','history_statistics.numeric_trade_summary','terminan.paper.PaperEngine.execute_signal','terminan.research_entry_evaluation.evaluate_research_entries'):
   stack.enter_context(patch(name,side_effect=AssertionError('CALLBACK_BEFORE_PREFLIGHT')))
  return stack
 def test_original_journal_three_labels_survive_actual_modeled_fill(self):
  e=self.source();row=self.row(e,coverage=api.CoverageDeclaration.COMPLETE_HISTORY,declared_volatility='HIGH',declared_poc_mode='TRADE_POC')
  with patch('terminan.paper.PaperEngine.execute_signal',side_effect=AssertionError('REEXECUTION')),patch('terminan.research_entry_evaluation.evaluate_research_entries',side_effect=AssertionError('REEVALUATION')):r=self.build(e,(row,))
  trade=r.trades[0];self.assertEqual((trade.declaration.coverage.value,trade.declaration.declared_volatility,trade.declaration.declared_poc_mode),('COMPLETE_HISTORY','HIGH','TRADE_POC'))
  self.assertEqual(trade.outcome,e.outcomes[0]);self.assertEqual(trade.gross_pnl,e.outcomes[0].outcome.execution.fill.gross)
  self.assertEqual(r.schema,'terminan.research-performance-report.declared-labels.v1');self.assertEqual(r.source_authentication,'NOT_EVALUATED');self.assertIs(r.execution_authority,False);self.assertIs(r.completeness_qualified,False);self.assertIs(r.trading_authorized,False)
 def test_missing_none_and_keyword_only_labels_keep_existing_encoding(self):
  e=self.source();plain=self.row(e);explicit=self.row(e,declared_volatility=None,declared_poc_mode=None)
  self.assertEqual(self.build(e,(plain,)),self.build(e,(explicit,)));self.assertEqual(self.build(e,(plain,)).schema,'terminan.research-performance-report.v1')
  self.assertNotIn('declared_volatility',api._encoded(plain)['fields']);self.assertNotIn('declared_poc_mode',api._encoded(plain)['fields'])
  with self.assertRaises(TypeError):api.DeclaredTradeMetadata('BTCUSDT',60000,120000,None,None,None,None,None,None,None,'HIGH')
 def test_declared_high_does_not_replace_observed_low_group(self):
  e=fixtures.ResearchReportingTests().multiple();pair=e.outcomes[1];row=self.row(replace(e,outcomes=(pair,)),declared_volatility='HIGH')
  r=self.build(e,(row,));trade=next(t for t in r.trades if t.identity==(row.symbol,row.decision_ms));low=next(p for p in r.by_volatility if p.label=='LOW');self.assertIn(trade.identity,low.trade_ids);self.assertEqual(trade.declaration.declared_volatility,'HIGH');self.assertIsNone(trade.declaration.declared_poc_mode)
 def test_duplicate_unused_future_and_nonfilled_labels_preflight(self):
  e=self.source();row=self.row(e,declared_volatility='HIGH')
  for rows in ((row,row),(replace(row,symbol='ETHUSDT'),),(replace(row,decision_ms=0),),(replace(row,available_at_ms=180001),),(replace(row,available_at_ms=row.available_at_ms-1),)):
   with self.subTest(rows=rows),self.blocked(),self.assertRaises(ValueError):self.build(e,rows)
  pair=e.outcomes[0];o=replace(pair.outcome,disposition=core.EvaluationDisposition.NOT_FILLED,execution=None);no=replace(e,outcomes=(replace(pair,outcome=o),),evaluation=replace(e.evaluation,outcomes=(o,)))
  with self.blocked(),self.assertRaises(ValueError):self.build(no,(row,))
 def test_foreign_and_invalid_label_leaves_refuse_without_callbacks(self):
  e=self.source();calls=[]
  class Text(str):
   def __str__(self):calls.append('str');return 'HIGH'
   def __eq__(self,other):calls.append('eq');return False
  class Meta(type):
   def __eq__(self,other):calls.append('meta');return False
  class Foreign(metaclass=Meta):pass
  for name in ('declared_volatility','declared_poc_mode'):
   for value in (True,1,'','high','A-B','A'*65,'HIGH\n',Text('HIGH'),Foreign(),MappingProxyType({'label':'HIGH'})):
    with self.subTest(name=name,value=type(value).__name__),self.blocked(),self.assertRaises(ValueError):self.build(e,(self.row(e,**{name:value}),))
  self.assertEqual(calls,[])
 def test_labels_snapshot_before_first_math_and_bind_full_hash(self):
  import market_math
  e=self.source();row=self.row(e,declared_volatility='HIGH',declared_poc_mode='TRADE_POC');expected=self.build(e,(row,));original=market_math.paper_execution_values_valid
  def mutate(*args):object.__setattr__(row,'declared_volatility','LOW');object.__setattr__(row,'declared_poc_mode',None);return original(*args)
  with patch.object(market_math,'paper_execution_values_valid',side_effect=mutate):actual=self.build(e,(row,))
  self.assertEqual(actual,expected);self.assertNotEqual(self.build(e,(row,)).input_sha256,expected.input_sha256)
  self.assertEqual(set(api._encoded(expected.trades[0].declaration)['fields'])&{'declared_volatility','declared_poc_mode'},{'declared_volatility','declared_poc_mode'})
 def test_independent_hypotheses_labels_keep_association_and_closed_schema(self):
  f=accounts.IndependentSignalAccountTests();e=f.rich_evaluate(account_model=f.model());rows=tuple(self.row(replace(e,outcomes=(pair,)),declared_volatility=label) for pair,label in zip(e.outcomes,('HIGH','LOW')))
  r=self.build(e,rows);self.assertEqual(r.schema,'terminan.research-performance-report.independent-signals.declared-labels.v1');self.assertEqual(tuple(t.identity for t in r.trades),tuple((p.entry.signal.symbol,p.entry.decision_ms) for p in e.outcomes));self.assertEqual(tuple(t.declaration.declared_volatility for t in r.trades),('HIGH','LOW'))
  self.assertEqual(r.execution_basis,'CALLER_DECLARED_INDEPENDENT_HYPOTHESES_SIGNAL_ORDER_NOT_PORTFOLIO_NOT_REEXECUTED')
 def test_label_present_none_and_both_fields_have_distinct_hashes(self):
  e=self.source();rows=(self.row(e),self.row(e,declared_volatility='HIGH'),self.row(e,declared_poc_mode='TRADE_POC'),self.row(e,declared_volatility='HIGH',declared_poc_mode='TRADE_POC'))
  reports=tuple(self.build(e,(row,)) for row in rows);self.assertEqual(len({r.input_sha256 for r in reports}),4);self.assertTrue(all(r.all_filled==reports[0].all_filled for r in reports));self.assertIsNone(reports[1].trades[0].declaration.declared_poc_mode)
 def test_label_batch_order_is_canonical_and_original_objects_detached(self):
  e=fixtures.ResearchReportingTests().multiple();rows=tuple(self.row(replace(e,outcomes=(p,)),declared_poc_mode='TRADE_POC') for p in e.outcomes)
  a=self.build(e,rows);b=self.build(e,tuple(reversed(rows)));self.assertEqual(a.input_sha256,b.input_sha256);self.assertEqual(a.trades,b.trades)
  self.assertIsNot(a.trades[0].declaration,rows[0]);self.assertEqual(len({t.identity for t in a.trades}),3)
