"""The canonical Math predicate owns modeled execution financial domains."""
import unittest
from dataclasses import replace
from decimal import Decimal as D
from datetime import datetime,timezone
from unittest.mock import patch
from report_literal_fixture import fixture
from terminan.research_evaluation import EvaluationDisposition

class ReportExecutionDomainTests(unittest.TestCase):
 def source(self):return fixture(EvaluationDisposition.FILLED)
 def changed(self,source,**changes):
  out=source.evaluation.outcomes[0];execution=out.execution
  if 'quantity' in changes:execution=replace(execution,quantity=changes.pop('quantity'))
  if changes:execution=replace(execution,fill=replace(execution.fill,**changes))
  out=replace(out,execution=execution)
  return replace(source,evaluation=replace(source.evaluation,outcomes=(out,)),outcomes=(replace(source.outcomes[0],outcome=out),))
 def build(self,source,rows=()):
  from terminan.research_reporting import build_research_report
  return build_research_report(source,rows,value_unit='USDT')
 def test_positive_price_quantity_and_zero_fees_use_canonical_predicate(self):
  import market_math as owner
  source=self.changed(self.source(),fees=D(0));original=owner.paper_execution_values_valid;calls=[]
  def predicate(*values):calls.append(values);return original(*values)
  with patch.object(owner,'paper_execution_values_valid',side_effect=predicate):report=self.build(source)
  self.assertEqual(calls,[(D(101),D(100),D(1),D(0))]);self.assertEqual(report.all_filled.fees_total,0.0)
 def test_zero_negative_prices_quantity_and_negative_fees_refuse_before_projection(self):
  for changes in ({'entry':D(0)},{'entry':D(-1)},{'exit':D(0)},{'exit':D(-1)},{'quantity':D(0)},{'quantity':D(-1)},{'fees':D(-1)}):
   source=self.changed(self.source(),**changes)
   with self.subTest(changes=changes),patch('history_statistics.project_decimal_observations',side_effect=AssertionError('PROJECT_CALLED')),patch('history_statistics.numeric_trade_summary',side_effect=AssertionError('SUMMARY_CALLED')),patch('terminan.paper.PaperEngine',side_effect=AssertionError('ENGINE_CALLED')),patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')):
    with self.assertRaises(ValueError):self.build(source)
 def test_predicate_must_return_literal_true(self):
  import market_math as owner
  source=self.source()
  for value in (False,1,'true',None):
   with patch.object(owner,'paper_execution_values_valid',return_value=value),patch('history_statistics.project_decimal_observations',side_effect=AssertionError('PROJECT_CALLED')):
    with self.assertRaises(ValueError):self.build(source)
 def test_all_symbol_clock_and_unit_preflight_precedes_domain_predicate(self):
  from terminan.research_reporting import DeclaredTradeMetadata
  import market_math as owner
  source=self.source();out=source.evaluation.outcomes[0]
  badclock=self.changed(source,exit_time=datetime(1970,1,1,0,2,tzinfo=timezone.utc))
  wrong_symbol=replace(source,evaluation=replace(source.evaluation,dataset=replace(source.evaluation.dataset,symbol='ETHUSDT')))
  row=DeclaredTradeMetadata('BTCUSDT',60000,120000,mae=D(1),mae_unit=None)
  for value,rows in ((badclock,()),(wrong_symbol,()),(source,(row,))):
   with patch.object(owner,'paper_execution_values_valid',side_effect=AssertionError('PREDICATE_CALLED')):
    with self.assertRaises(ValueError):self.build(value,rows)
 def test_first_domain_callback_cannot_mutate_captured_input_graph(self):
  import market_math as owner
  source=self.source();expected=self.build(source);original=owner.paper_execution_values_valid
  def mutate(*values):
   object.__setattr__(source.outcomes[0].outcome.execution,'quantity',D(0));object.__setattr__(source.outcomes[0].outcome.execution.fill,'exit_time',datetime(1970,1,1,0,4,tzinfo=timezone.utc));return original(*values)
  with patch.object(owner,'paper_execution_values_valid',side_effect=mutate):actual=self.build(source)
  self.assertEqual(actual,expected)
 def test_nonfilled_outcomes_never_call_execution_domain_predicate(self):
  import market_math as owner
  source=fixture(EvaluationDisposition.NOT_FILLED)
  with patch.object(owner,'paper_execution_values_valid',side_effect=AssertionError('PREDICATE_CALLED')):report=self.build(source)
  self.assertEqual(report.trades,())
 def test_invalid_last_fill_prevents_all_projection_and_summary_calls(self):
  import test_research_reporting as fixtures
  source=fixtures.ResearchReportingTests().multiple();last=source.evaluation.outcomes[-1];bad=replace(last,execution=replace(last.execution,quantity=D(0)));pairs=source.outcomes[:-1]+(replace(source.outcomes[-1],outcome=bad),);source=replace(source,evaluation=replace(source.evaluation,outcomes=source.evaluation.outcomes[:-1]+(bad,)),outcomes=pairs)
  with patch('history_statistics.project_decimal_observations',side_effect=AssertionError('PROJECT_CALLED')),patch('history_statistics.numeric_trade_summary',side_effect=AssertionError('SUMMARY_CALLED')):
   with self.assertRaises(ValueError):self.build(source)
 def test_domain_validation_preserves_no_origin_or_execution_grant(self):
  report=self.build(self.source());self.assertEqual(report.execution_basis,'CALLER_SUPPLIED_MODELED_EXECUTIONS_NOT_REEXECUTED');self.assertIs(report.execution_authority,False);self.assertEqual(report.source_authentication,'NOT_EVALUATED');self.assertTrue(hasattr(report,'execution_domain_policy'));self.assertEqual(report.execution_domain_policy,'MATH_PAPER_EXECUTION_VALUES_V1_DECLARATIONS_ONLY')
