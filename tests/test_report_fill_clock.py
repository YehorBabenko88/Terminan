"""Exact declared UTC execution-clock consistency, without reexecution."""
import unittest
from dataclasses import replace
from datetime import datetime,timezone,timedelta,tzinfo
from decimal import Decimal
from unittest.mock import patch
from report_literal_fixture import fixture
from terminan.research_evaluation import EvaluationDisposition

class ReportFillClockTests(unittest.TestCase):
 def source(self):return fixture(EvaluationDisposition.FILLED)
 def changed(self,source,*,exit_ms=None,exit_time=None,pair_only=False):
  out=source.evaluation.outcomes[0];execution=out.execution
  if exit_ms is not None:execution=replace(execution,exit_ms=exit_ms)
  if exit_time is not None:execution=replace(execution,fill=replace(execution.fill,exit_time=exit_time))
  out=replace(out,execution=execution);pair=replace(source.outcomes[0],outcome=out)
  return replace(source,outcomes=(pair,),evaluation=source.evaluation if pair_only else replace(source.evaluation,outcomes=(out,)))
 def build(self,source):
  from terminan.research_reporting import build_research_report
  return build_research_report(source,value_unit='USDT')
 def refuse_without_project_or_engine(self,source):
  with patch('history_statistics.project_decimal_observations',side_effect=AssertionError('PROJECT_CALLED')),patch('history_statistics.numeric_trade_summary',side_effect=AssertionError('SUMMARY_CALLED')),patch('terminan.research_evaluation.evaluate_research_signals',side_effect=AssertionError('EVAL_CALLED')),patch('terminan.paper.PaperEngine',side_effect=AssertionError('ENGINE_CALLED')):
   with self.assertRaises(ValueError):self.build(source)
 def test_exact_utc_clock_matches_integer_epoch_milliseconds(self):
  report=self.build(self.source());execution=report.trades[0].outcome.outcome.execution
  self.assertEqual(execution.fill.exit_time,datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=execution.exit_ms));self.assertEqual(execution.exit_ms,60000)
 def test_future_and_under_cutoff_fill_times_refuse_before_math(self):
  for value in (datetime(1970,1,1,0,4,tzinfo=timezone.utc),datetime(1970,1,1,0,2,tzinfo=timezone.utc),datetime(1970,1,1,0,1,0,1000,tzinfo=timezone.utc)):
   with self.subTest(value=value):self.refuse_without_project_or_engine(self.changed(self.source(),exit_time=value))
 def test_nonliteral_signed_or_out_of_range_exit_clock_refuses(self):
  for value in (True,-1,60000.0,Decimal(60000),4102444800001):
   with self.subTest(value=value):self.refuse_without_project_or_engine(self.changed(self.source(),exit_ms=value))
 def test_foreign_datetime_subclass_refuses_without_callbacks(self):
  calls=[]
  class Foreign(datetime):
   def __eq__(self,value):calls.append('eq');return True
   def isoformat(self,*a,**k):calls.append('iso');return 'wrong'
  self.refuse_without_project_or_engine(self.changed(self.source(),exit_time=Foreign(1970,1,1,0,1,tzinfo=timezone.utc)));self.assertEqual(calls,[])
 def test_non_utc_naive_and_hostile_timezone_refuse_without_conversion(self):
  calls=[]
  class ForeignTZ(tzinfo):
   def utcoffset(self,dt):calls.append('offset');raise AssertionError('TZ_CALLBACK')
   def dst(self,dt):calls.append('dst');raise AssertionError('TZ_CALLBACK')
  for value in (datetime(1970,1,1,0,1),datetime(1970,1,1,1,1,tzinfo=timezone(timedelta(hours=1))),datetime(1970,1,1,0,1,tzinfo=ForeignTZ())):self.refuse_without_project_or_engine(self.changed(self.source(),exit_time=value))
  self.assertEqual(calls,[])
 def test_original_fill_clock_mutation_at_first_projection_cannot_change_report(self):
  import history_statistics as owner
  source=self.source();expected=self.build(source);original=owner.project_decimal_observations
  def mutate(values):
   object.__setattr__(source.outcomes[0].outcome.execution.fill,'exit_time',datetime(1970,1,1,0,4,tzinfo=timezone.utc));object.__setattr__(source.outcomes[0].outcome.execution,'exit_ms',120000);return original(values)
  with patch.object(owner,'project_decimal_observations',side_effect=mutate):actual=self.build(source)
  self.assertEqual(actual,expected);self.assertEqual(actual.trades[0].exit_ms,60000)
 def test_clock_mismatch_does_not_construct_or_reexecute_engine(self):
  source=self.changed(self.source(),exit_time=datetime(1970,1,1,0,2,tzinfo=timezone.utc))
  self.refuse_without_project_or_engine(source)
 def test_pair_only_fill_time_contradiction_is_not_ignored(self):
  self.refuse_without_project_or_engine(self.changed(self.source(),exit_time=datetime(1970,1,1,0,2,tzinfo=timezone.utc),pair_only=True))
