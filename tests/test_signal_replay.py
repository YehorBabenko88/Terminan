import copy,importlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal as D,localcontext,Inexact,Rounded
from terminan.paper import STRATEGIES
from terminan.paper_ledger import ReplayConflict

def request():
 return {'schema':'terminan.paper.signal-replay.v1','run_id':'signal-run','strategy':{'id':'ohlc_signal','version':'1'},'source':{'snapshot_sha256':'a'*64,'as_of_ms':120000,'available_from_ms':0,'units':{'price':'quote/base','volume':'base'}},'parameters':{'notional':'100','fee_rate':'0','slippage_bps':'0','bar_ms':60000,'ambiguity_policy':'SL_FIRST'},'signal':{'symbol':'BTCUSDT','decision_ms':60000,'side':'long','entry_kind':'market','entry_price':None,'stop':'99','target':'102'},'bars':[{'start_ms':60000,'open':'100','high':'101','low':'98','close':'100'}]}
class SignalReplayTests(unittest.TestCase):
 def replay(self,value):
  self.assertIsNotNone(importlib.util.find_spec('terminan.research_replay'),'runnable canonical signal replay required')
  return importlib.import_module('terminan.research_replay').run_signal_replay(value)
 def test_actual_engine_result_is_read_only_unattested_and_deterministic(self):
  value=request();before=copy.deepcopy(value);first=self.replay(value);second=self.replay(value)
  self.assertEqual(first,second);self.assertEqual(value,before);self.assertEqual(first['strategy']['id'],'ohlc_signal');self.assertEqual(D(first['fill']['net']),D('-1'));self.assertEqual(first['tick_ordering'],'UNKNOWN');self.assertFalse(first['execution_authority']);self.assertFalse(first['trading_authorized'])
 def test_receipt_survives_restart_disabled_strategy_and_unavailable_math(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':str(Path(tmp)/'paper.sqlite')}):
   first=self.replay(request());before=(Path(tmp)/'paper.sqlite').read_bytes();STRATEGIES.set_enabled('ohlc_signal','1',False)
   try:
    with patch.dict('sys.modules',{'market_math':None}):self.assertEqual(self.replay(request()),first)
   finally:STRATEGIES.set_enabled('ohlc_signal','1',True)
   self.assertEqual((Path(tmp)/'paper.sqlite').read_bytes(),before)
   changed=request();changed['bars'][0]['close']='100.5'
   with self.assertRaises(ReplayConflict):self.replay(changed)
   self.assertEqual((Path(tmp)/'paper.sqlite').read_bytes(),before)
 def test_invalid_complete_batch_or_unqualified_new_run_creates_nothing(self):
  bad=[]
  for change in ('nan','future','extra','clock','old-id'):
   value=request()
   if change=='nan':value['bars'][-1]['close']='NaN'
   elif change=='future':value['source']['as_of_ms']=119999
   elif change=='extra':value['parameters']['token']='UNSUPPORTED'
   elif change=='clock':value['signal']['decision_ms']=True
   else:value['strategy']['id']='meta.poc.next_minute'
   bad.append(value)
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':str(Path(tmp)/'absent.sqlite')}):
   for value in bad:
    with self.subTest(value=value),self.assertRaises(ValueError):self.replay(value)
    self.assertEqual(list(Path(tmp).iterdir()),[])
 def test_hostile_decimal_context_cannot_change_new_signal_result(self):
  expected=self.replay(request())
  with localcontext() as context:
   context.prec=2;context.traps[Inexact]=True;context.traps[Rounded]=True
   self.assertEqual(self.replay(request()),expected)
 def test_offline_cli_uses_same_function_without_any_process_or_listener(self):
  self.assertIsNotNone(importlib.util.find_spec('terminan.research_replay'))
  import io
  module=importlib.import_module('terminan.research_replay');output=io.StringIO()
  self.assertEqual(module.main([],stdin=io.StringIO(json.dumps(request())),stdout=output),0)
  self.assertEqual(json.loads(output.getvalue())['strategy']['id'],'ohlc_signal')

 def test_declared_source_availability_rejects_prior_decision_or_bars(self):
  valid=request();valid['source']['available_from_ms']=60000
  self.assertEqual(self.replay(valid)['entry_ms'],60000)
  bad=copy.deepcopy(valid);bad['signal']['decision_ms']=0
  with self.assertRaises(ValueError):self.replay(bad)
  bad=copy.deepcopy(valid);bad['source']['available_from_ms']=60001
  with self.assertRaises(ValueError):self.replay(bad)
