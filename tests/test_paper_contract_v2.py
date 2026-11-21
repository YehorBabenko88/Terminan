import base64,copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from terminan import paper
from terminan.paper_ledger import PaperReplayLedger
FIXTURE=json.loads((Path(__file__).parent/'fixtures/historical_paper_v1_f20.json').read_text())
def request():
 return {'schema':'terminan.paper.replay.v2','run_id':'v2-request','strategy':{'id':'poc_next_minute','version':'2'},'source':{'snapshot_sha256':'a'*64,'as_of_ms':62000,'units':{'price':'quote/base','volume':'base'}},'parameters':{},'events':[{'kind':'closed_minute','event_ms':60000,'symbol':'BTCUSDT','profile':[{'price':'100','volume':'1'}],'close':'100'},{'kind':'trade','event_ms':61000,'symbol':'BTCUSDT','price':'102'},{'kind':'trade','event_ms':62000,'symbol':'BTCUSDT','price':'100'}]}
def compute(req):return dict(schema='math.market.result.v1',execution_authority=False,trading_authorized=False,provenance='CALLER_SUPPLIED_UNATTESTED',source=req['source'],results=[{'operation':'volume_profile_poc','value':'100'}])
class ActiveContractTests(unittest.TestCase):
 def test_old_active_schema_or_strategy_is_not_an_alias(self):
  with self.assertRaises(ValueError):paper.replay_paper(FIXTURE['request'],compute=compute)
  self.assertEqual(paper.REPLAY_SCHEMA,'terminan.paper.replay.v2')
  changed=request();changed['strategy']={'id':'meta.poc.next_minute','version':'1'}
  with self.assertRaises(ValueError):paper.replay_paper(changed,compute=compute)
 def test_v2_uses_canonical_identity_and_one_engine_registry(self):
  self.assertEqual(paper.REPLAY_SCHEMA,'terminan.paper.replay.v2')
  value=paper.replay_paper(request(),compute=compute)
  self.assertEqual(value['schema'],'terminan.paper.result.v2');self.assertEqual(value['strategy']['id'],'poc_next_minute')
  self.assertFalse(value['execution_authority']);self.assertFalse(value['trading_authorized'])
  definitions=paper.STRATEGIES.discover();self.assertEqual({d.id for d in definitions},{'poc_next_minute','ohlc_signal'})
  self.assertTrue(all(d.implementation is paper.PaperEngine for d in definitions))
 def test_invalid_final_event_future_source_and_disabled_new_run_create_nothing(self):
  self.assertEqual(paper.REPLAY_SCHEMA,'terminan.paper.replay.v2')
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'absent.sqlite'
   invalid=[]
   for price in ('NaN','1e5000'):
    value=request();value['events'][-1]['price']=price;invalid.append(value)
   value=request();value['source']['as_of_ms']=61000;invalid.append(value)
   for value in invalid:
    with self.subTest(value=value),patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':str(path)}),self.assertRaises(ValueError):paper.replay_paper(value,compute=compute)
    self.assertEqual(list(Path(tmp).iterdir()),[])
   paper.STRATEGIES.set_enabled('poc_next_minute','2',False)
   try:
    with patch.dict(os.environ,{'TERMINAN_PAPER_LEDGER':str(path)}),self.assertRaises(ValueError):paper.replay_paper(request(),compute=compute)
    self.assertEqual(list(Path(tmp).iterdir()),[])
   finally:paper.STRATEGIES.set_enabled('poc_next_minute','2',True)
 def test_legacy_stream_key_refuses_before_any_ddl_or_mutation(self):
  from terminan.paper_journal import PaperJournal
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'v1.sqlite';path.write_bytes(base64.b64decode(FIXTURE['database_base64']));before=path.read_bytes();ledger=PaperReplayLedger(path)
   with patch.object(ledger,'_paper_event_transaction',side_effect=AssertionError('NO_DDL_OR_WRITE_TRANSACTION')),self.assertRaises(RuntimeError):PaperJournal(ledger,'preserved-v1-source','paper-v1-run','BTCUSDT')
   self.assertEqual(path.read_bytes(),before);self.assertEqual({p.name for p in Path(tmp).iterdir()},{'v1.sqlite'})
