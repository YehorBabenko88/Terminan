"""R4 lifecycle atop proven R2 ownership/stderr guards; explicit owner end receipt."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from .r2_harness import Runtime,OwnedChild,Harness,Fault,PrivateParser,inspect_run as inspect_r2
from .r4_session import validate_receipt
from urllib.request import build_opener,ProxyHandler

def fetch_receipt(url,timeout):
 with build_opener(ProxyHandler({})).open(url,timeout=timeout) as response:
  body=response.read(8193)
  if len(body)>8192:raise ValueError()
  return response.status,body
class R4Child(OwnedChild):
 def quit(self,timeout):
  deadline=time.monotonic()+timeout
  self.process.stdin.write(b'quit\n');self.process.stdin.flush();self.process.stdin.close()
  self.end_seen=False
  while time.monotonic()<deadline and self.poll() is None:
   try:
    status,body=fetch_receipt(self.url+'/api/session?session_id='+self.receipt['session_id'],min(.5,max(.001,deadline-time.monotonic())));value=validate_receipt(json.loads(body),self.receipt['candidate_sha'],self.receipt)
    if status==200 and value['state']=='SESSION_ENDED':self.end_seen=True;break
   except Exception:pass # Still require receipt and native exit below; no waiver.
   time.sleep(.05)
  remaining=deadline-time.monotonic()
  if remaining<=0:raise Fault('SHUTDOWN_TIMEOUT')
  try:code=self.process.wait(timeout=remaining)
  except subprocess.TimeoutExpired:raise Fault('SHUTDOWN_TIMEOUT') from None
  if not self.end_seen:raise Fault('SHUTDOWN_FAILED')
  return code
class R4Runtime(Runtime):
 def spawn(self,repo,ready):
  env={k:v for k,v in os.environ.items() if not k.startswith('TERMINAN_')}
  return R4Child(subprocess.Popen([sys.executable,'-m','terminan.r4_runner','--ready',str(ready),'--diagnostics',str(ready.with_name('child-diagnostics.json'))],cwd=repo,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
class R4Harness(Harness):
 def __init__(self,**kw):super().__init__(runtime=R4Runtime(),**kw);self.receipt=None;self.contract_probe=None
 def _startup(self):
  super()._startup();status,body=self.ops.fetch(self.url+'/api/session');self.receipt=validate_receipt(json.loads(body),self.expected)
  if status!=200 or self.receipt['state']!='ACTIVE':raise Fault('READY_INVALID')
  self.child.url=self.url;self.child.receipt=self.receipt
 def _smoke(self):
  super()._smoke();status,body=self.ops.fetch(self.url+'/api/synthetic/contracts?symbol=ETHUSDT&timeframe=5m');data=json.loads(body)
  validate_receipt(data['session'],self.expected,self.receipt)
  values=data['sources'];states=[v['state'] for v in values]
  if status!=200 or data['symbol']!='ETHUSDT' or data['timeframe']!='5m' or states!=['UNSUPPORTED_TIMEFRAME','UNSUPPORTED_TIMEFRAME','HISTORICAL_ONLY','HISTORICAL_ONLY'] or any(v['symbol']!='ETHUSDT' or v['runtime_source']!='NONE' or v['authority'] not in ('SYNTHETIC_ONLY','UNVERIFIED') for v in values):raise Fault('SMOKE_ASSERTION_FAILED')
  self.contract_probe=dict(symbol='ETHUSDT',timeframe='5m',states=states,sha256=hashlib.sha256(body).hexdigest())
 def _health(self):
  super()._health();status,body=self.ops.fetch(self.url+'/api/session?session_id='+self.receipt['session_id']);value=validate_receipt(json.loads(body),self.expected,self.receipt)
  if status!=200 or value['state']!='ACTIVE':raise Fault('CHILD_HEALTH_FAILED')
 def _summary(self):
  value=super()._summary();value['r4']=dict(version=1,session_sha256=hashlib.sha256(self.receipt['session_id'].encode()).hexdigest() if self.receipt else None,end_receipt_seen=bool(self.child and getattr(self.child,'end_seen',False)),contract_probe=self.contract_probe)
  return value

def inspect(root,sha):
 code=inspect_r2(root,sha)
 if code:return code
 try:
  root=Path(root);s=json.loads((root/'summary.json').read_text());d=json.loads((root/'child-diagnostics.json').read_text())['r4_session'];r=s['r4']
  if r['version']!=1 or r['end_receipt_seen'] is not True or d['state']!='SESSION_ENDED' or d['end_receipts']<1 or d['session_sha256']!=r['session_sha256'] or r['contract_probe']['states']!=['UNSUPPORTED_TIMEFRAME','UNSUPPORTED_TIMEFRAME','HISTORICAL_ONLY','HISTORICAL_ONLY']:raise ValueError()
  return 0
 except Exception:return 50

def main():
 p=PrivateParser();p.add_argument('--expected-sha',required=True);p.add_argument('--evidence-root',required=True);p.add_argument('--review-seconds',default='15');p.add_argument('--run-id');p.add_argument('--shell-version');p.add_argument('--open-browser',action='store_true');p.add_argument('--inspect-run',action='store_true');a=p.parse_args()
 if a.inspect_run:code=inspect(Path(a.evidence_root)/a.run_id,a.expected_sha)
 else:
  h=R4Harness(expected_sha=a.expected_sha,evidence_root=a.evidence_root,review_seconds=a.review_seconds,open_browser=a.open_browser,run_id=a.run_id,shell_version=a.shell_version);code=h.run()
  if inspect(h.final_dir,a.expected_sha)!=code:code=50
 print('R4 lifecycle exit_code='+str(code));return code
if __name__=='__main__':
 try:raise SystemExit(main())
 except (Exception,KeyboardInterrupt):print('R4 lifecycle FAIL error_class=LIFECYCLE_FAILED');raise SystemExit(50)
