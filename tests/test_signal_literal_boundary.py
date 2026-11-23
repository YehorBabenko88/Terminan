import unittest
from decimal import Decimal
class SignalLiteralBoundaryTests(unittest.TestCase):
 def check(self,bars):
  from terminan.research_signals import ResearchSignal,validate_signal_batch
  signal=ResearchSignal('BTCUSDT',60000,'long','market',None,Decimal(99),Decimal(101))
  return validate_signal_batch(signal,bars,bar_ms=60000,as_of_ms=120000,ambiguity_policy='SL_FIRST')
 def test_foreign_metaclass_batch_refuses_without_equality(self):
  class Meta(type):
   def __eq__(cls,other):raise AssertionError('foreign metaclass eq')
  class Foreign(metaclass=Meta):pass
  with self.assertRaises(ValueError):self.check(Foreign())
 def test_container_subclasses_refuse_without_iteration_or_length(self):
  class ForeignList(list):
   def __len__(self):raise AssertionError('foreign len')
   def __iter__(self):raise AssertionError('foreign iter')
  class ForeignTuple(tuple):
   def __len__(self):raise AssertionError('foreign len')
   def __iter__(self):raise AssertionError('foreign iter')
  for value in (ForeignList(),ForeignTuple()):
   with self.assertRaises(ValueError):self.check(value)
