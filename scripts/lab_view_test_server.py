"""Disposable SYNTHETIC_TEST_INPUT lab fixture. No engines or market calls."""
import json,os,sys,tempfile,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminan.unified_server import UnifiedServer,UnifiedHandler

def fixture(stale=False):
 now=int(time.time()*1000)-(16000 if stale else 0)
 return dict(schema='unified.lab.market-paper.v1',mode='LAB_SIMULATION',trading_authorized=False,release_id='SYNTHETIC_TEST_INPUT',run_id='SYNTHETIC_TEST_INPUT',sequence=1,generated_at_ms=now,quotes=[dict(symbol=f'COIN{i}USDT',last_price=10,bid=9,ask=11,event_ts_ms=now,source='BYBIT_PUBLIC') for i in range(10)],trades=[],strategies=[dict(id='SYNTHETIC_TEST_INPUT',status='READY',trades=0,error_code=None)],nodes=[dict(node_id=n,role='CONTROL' if n=='LS5' else 'WORKER',state='READY',last_heartbeat_ms=now,error_code=None) for n in ('LS5','PC1','PC2','PC3','PC4','LS7')],errors=[])

with tempfile.TemporaryDirectory(prefix='terminan-lab-synthetic-') as folder:
 snapshot=Path(folder)/'snapshot.json'
 def write(stale=False):
  temporary=snapshot.with_suffix('.tmp');temporary.write_text(json.dumps(fixture(stale)),encoding='utf-8');os.replace(temporary,snapshot)
 write();os.environ['TERMINAN_LAB_SNAPSHOT']=str(snapshot)
 server=UnifiedServer(('127.0.0.1',0),UnifiedHandler);server.candidate_sha='a'*40
 thread=threading.Thread(target=server.serve_forever);thread.start()
 print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','fixture':'SYNTHETIC_TEST_INPUT'}),flush=True)
 try:
  for command in sys.stdin:
   if command.strip()=='stop':break
   if command.strip() in ('fresh','stale'):write(command.strip()=='stale')
 finally:server.session.end();server.shutdown();server.server_close();thread.join(5)
