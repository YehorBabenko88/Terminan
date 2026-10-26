"""Fail-closed synthetic harness lifecycle. No source DB or exchange operations."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time
from urllib.request import build_opener,ProxyHandler
import uuid

REPO=Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
STAGES={'preflight':10,'startup':20,'smoke':30,'browser_launch':31,'review_wait':32,
        'child_health':33,'graceful_shutdown':40,'evidence_finalize':50}
CLASSES={'NONE','UNEXPECTED_EXCEPTION','INVALID_SHA','SHA_MISMATCH','INVALID_ARGUMENT','DIRTY_SOURCE',
 'PYTHON_UNSUPPORTED','SOURCE_IDENTITY_UNAVAILABLE','STARTUP_FAILED','READY_TIMEOUT',
 'READY_INVALID','SYNTHETIC_IDENTITY_MISMATCH','SMOKE_HTTP_FAILED','SMOKE_ASSERTION_FAILED',
 'BROWSER_LAUNCH_FAILED','REVIEW_WAIT_FAILED','CHILD_EARLY_EXIT','CHILD_HEALTH_FAILED',
 'CHILD_STDERR','CHILD_OUTPUT_LIMIT','SHUTDOWN_TIMEOUT','SHUTDOWN_FAILED',
 'CHILD_EXIT_FAILED','OUTPUT_DRAIN_TIMEOUT','EVIDENCE_FINALIZE_FAILED',
 'EVIDENCE_DIRECTORY_UNAVAILABLE','EVIDENCE_PATH_REDIRECTED'}
FILES={'ready.json','smoke.json','browser-checklist.txt','summary.json'}
ROUTES=('/api/status','/api/synthetic/frame?step=24&scenario=gap',
 '/api/synthetic/frame?step=48&scenario=stale','/api/synthetic/frame?step=72&scenario=reconnect',
 '/api/synthetic/frame?step=80&scenario=reconnect','/api/synthetic/contracts?scenario=future',
 '/r2_preview.js','/r2_preview.css','/')
RUN_ID=re.compile(r'^[0-9]{8}T[0-9]{9}Z-[a-f0-9]{8}$')
SHA=re.compile(r'^[a-f0-9]{40}$')

class Fault(Exception):
    def __init__(self,error_class):
        self.error_class=error_class if error_class in CLASSES else 'UNEXPECTED_EXCEPTION'

class OwnedChild:
    def __init__(self,process):
        self.process=process;self.counts=[0,0];self.threads=[]
        for index,stream in enumerate((process.stdout,process.stderr)):
            def drain(index=index,stream=stream):
                try:
                    while True:
                        data=stream.read1(4096)
                        if not data:break
                        self.counts[index]=min(2**31-1,self.counts[index]+len(data))
                except (OSError,ValueError):self.counts[index]=65537
            thread=threading.Thread(target=drain,daemon=True);thread.start();self.threads.append(thread)
    @property
    def stdout_bytes(self):return self.counts[0]
    @property
    def stderr_bytes(self):return self.counts[1]
    @property
    def output_limit(self):return max(self.counts)>65536
    def poll(self):return self.process.poll()
    def quit(self,timeout):
        try:
            self.process.stdin.write(b'quit\n');self.process.stdin.flush();self.process.stdin.close()
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:raise Fault('SHUTDOWN_TIMEOUT') from None
    def kill(self):
        if self.process.poll() is None:self.process.kill()
        self.process.wait(timeout=3)
    def close(self):
        complete=True
        for thread,stream in zip(self.threads,(self.process.stdout,self.process.stderr)):
            thread.join(2)
            if thread.is_alive():complete=False
            else:stream.close()
        if self.process.stdin and not self.process.stdin.closed:self.process.stdin.close()
        return complete

class Runtime:
    def clock(self):return time.monotonic()
    def sleep(self,seconds):time.sleep(seconds)
    def identity(self,repo):
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,stderr=subprocess.DEVNULL,timeout=5).decode().strip()
        dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=repo,stderr=subprocess.DEVNULL,timeout=5)
        if not SHA.fullmatch(sha):raise Fault('SOURCE_IDENTITY_UNAVAILABLE')
        return sha,not bool(dirty.strip())
    def spawn(self,repo,ready):
        env={k:v for k,v in os.environ.items() if not k.startswith('TERMINAN_')}
        return OwnedChild(subprocess.Popen([sys.executable,'-m','terminan.r2_runner','--ready',str(ready)],
            cwd=repo,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
    def fetch(self,url):
        with build_opener(ProxyHandler({})).open(url,timeout=3) as response:
            body=response.read(1048577)
            if len(body)>1048576:raise Fault('SMOKE_HTTP_FAILED')
            return response.status,body
    def browser(self,url):
        if os.name=='nt':os.startfile(url)
        else:
            import webbrowser
            if not webbrowser.open(url,new=2):raise Fault('BROWSER_LAUNCH_FAILED')
    def write_json(self,path,value):
        temporary=path.with_name(path.name+'.tmp')
        with temporary.open('x',encoding='utf-8',newline='\n') as out:
            json.dump(value,out,allow_nan=False,sort_keys=True,indent=2);out.write('\n')
        os.replace(temporary,path)
    def publish(self,pending,final):
        if final.exists():raise Fault('EVIDENCE_FINALIZE_FAILED')
        os.rename(pending,final)

def _integrity(root):
    for path in (root,root/'manifest.json'):
        info=os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ValueError()
    entries=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if not isinstance(entries,list) or not entries:raise ValueError()
    names=set()
    for entry in entries:
        name=entry['file']
        if name not in FILES or name in names:raise ValueError()
        path=root/name
        if path.is_symlink() or not path.is_file():raise ValueError()
        body=path.read_bytes()
        if len(body)!=entry['bytes'] or hashlib.sha256(body).hexdigest()!=entry['sha256']:raise ValueError()
        names.add(name)
    if names!={p.name for p in root.iterdir() if p.is_file() and p.name!='manifest.json'}:raise ValueError()
    summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    if summary.get('harness_contract_version')!=2 or summary.get('mode')!='SYNTHETIC' or summary.get('physical')!='PENDING':raise ValueError()
    code=summary['exit_code'];stage=summary['failure_stage'];error=summary['error_class']
    if type(code) is not int or code not in (0,*STAGES.values()) or error not in CLASSES:raise ValueError()
    if code==0:
        if stage!='NONE' or error!='NONE' or summary['result']!='AUTOMATED_SYNTHETIC_SMOKE_PASS':raise ValueError()
    elif STAGES.get(stage)!=code or error=='NONE' or summary['result']!='FAIL':raise ValueError()
    return summary

def inspect_run(root,expected_sha):
    try:
        root=Path(root);summary=_integrity(root)
        expected=expected_sha if SHA.fullmatch(expected_sha) else 'INVALID'
        if summary['candidate_sha']!=expected:raise ValueError()
        if summary['exit_code']==0:
            from terminan.r2_evidence import verify
            verify(root,expected_sha)
        return summary['exit_code']
    except Exception:return 50

class Harness:
    def __init__(self,*,expected_sha,evidence_root,review_seconds='0',open_browser=False,runtime=None,run_id=None,shutdown_timeout=10,shell_version=None):
        self.ops=runtime or Runtime();self.expected=expected_sha;self.requested_seconds=review_seconds;self.seconds=0
        self.open_browser=bool(open_browser);self.shutdown_timeout=shutdown_timeout
        self.run_id=run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')[:-3]+'Z-'+uuid.uuid4().hex[:8]
        if not RUN_ID.fullmatch(self.run_id):raise ValueError('invalid run identifier')
        root=Path(evidence_root)
        if not root.is_absolute():root=REPO/root
        self.final_dir=root/self.run_id;self.pending=root/('.pending-'+self.run_id)
        self.stage='preflight';self.states={name:'NOT_RUN' for name in STAGES}
        self.code=0;self.failure_stage='NONE';self.error_class='NONE';self.os_error_code=None;self.secondary=[]
        self.child=None;self.shutdown_attempted=False;self.smoke=[];self.checklist=None
        self.actual_sha='UNVERIFIED';self.clean=False;self.review_elapsed=0;self.review_completed=False;self.health_probes=0
        self.owned_pending=False
        self.shell_version=shell_version if isinstance(shell_version,str) and re.fullmatch(r'[0-9]{1,3}(\.[0-9]{1,10}){1,3}',shell_version) else None
    def _set(self,stage,state='RUNNING'):self.stage=stage;self.states[stage]=state
    def _fail(self,stage,exc):
        fallback={'preflight':'SOURCE_IDENTITY_UNAVAILABLE','startup':'STARTUP_FAILED','smoke':'SMOKE_HTTP_FAILED',
          'browser_launch':'BROWSER_LAUNCH_FAILED','review_wait':'REVIEW_WAIT_FAILED','child_health':'CHILD_HEALTH_FAILED',
          'graceful_shutdown':'SHUTDOWN_FAILED','evidence_finalize':'EVIDENCE_FINALIZE_FAILED'}
        error=exc.error_class if isinstance(exc,Fault) else 'SHUTDOWN_TIMEOUT' if stage=='graceful_shutdown' and isinstance(exc,TimeoutError) else fallback[stage]
        native=getattr(exc,'winerror',None) or getattr(exc,'errno',None)
        native=native if type(native) is int and abs(native)<=2**31-1 else None
        failure=dict(exit_code=STAGES[stage],failure_stage=stage,error_class=error)
        self.states[stage]='FAIL'
        if self.code and stage!='evidence_finalize':self.secondary.append(failure)
        else:
            if self.code:self.secondary.append(dict(exit_code=self.code,failure_stage=self.failure_stage,error_class=self.error_class))
            self.code=STAGES[stage];self.failure_stage=stage;self.error_class=error;self.os_error_code=native
    def _identity(self,value):
        if not isinstance(value,dict) or value.get('mode')!='SYNTHETIC' or value.get('sources')!='DISABLED' or value.get('candidate_sha')!=self.expected or value.get('source_clean') is not True:
            raise Fault('SYNTHETIC_IDENTITY_MISMATCH')
    def _preflight(self):
        if sys.version_info<(3,11):raise Fault('PYTHON_UNSUPPORTED')
        if not isinstance(self.expected,str) or not SHA.fullmatch(self.expected):raise Fault('INVALID_SHA')
        seconds=str(self.requested_seconds)
        if not seconds.isascii() or not seconds.isdecimal() or len(seconds)>4 or not 0<=int(seconds)<=3600:raise Fault('INVALID_ARGUMENT')
        self.seconds=int(seconds);self.actual_sha,self.clean=self.ops.identity(REPO)
        if self.actual_sha!=self.expected:raise Fault('SHA_MISMATCH')
        if not self.clean:raise Fault('DIRTY_SOURCE')
    def _acquire(self):
        for path in (self.pending,*self.pending.parents,self.final_dir):
            try:info=os.lstat(path)
            except FileNotFoundError:continue
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise Fault('EVIDENCE_PATH_REDIRECTED')
            if path in (self.pending,self.final_dir):raise Fault('EVIDENCE_DIRECTORY_UNAVAILABLE')
        self.pending.mkdir(parents=True,exist_ok=False)
        self.owned_pending=True
    def _startup(self):
        self.child=self.ops.spawn(REPO,self.pending/'ready.json');deadline=self.ops.clock()+15
        while True:
            if self.child.poll() is not None:raise Fault('CHILD_EARLY_EXIT')
            if (self.pending/'ready.json').exists():break
            if self.ops.clock()>=deadline:raise Fault('READY_TIMEOUT')
            self.ops.sleep(.1)
        ready=json.loads((self.pending/'ready.json').read_text(encoding='utf-8'))
        self._identity(ready)
        if ready.get('host')!='127.0.0.1' or type(ready.get('port')) is not int or not 1<=ready['port']<=65535:raise Fault('READY_INVALID')
        self.url='http://127.0.0.1:'+str(ready['port'])
    def _smoke(self):
        expected_states=('GAP','STALE','DISCONNECTED','COHERENT')
        for index,route in enumerate(ROUTES):
            record=dict(route=route,status=None,assertions_passed=False)
            self.smoke.append(record)
            status,body=self.ops.fetch(self.url+route);record['status']=status
            if status!=200:raise Fault('SMOKE_HTTP_FAILED')
            record['response_sha256']=hashlib.sha256(body).hexdigest()
            if index==0:
                data=json.loads(body);self._identity(data)
                if data.get('execution')!='DISABLED':raise Fault('SMOKE_ASSERTION_FAILED')
            elif 1<=index<=4:
                data=json.loads(body)
                if data.get('mode')!='SYNTHETIC' or data.get('candidate_sha')!=self.expected or data.get('execution')!='DISABLED' or data.get('dom',{}).get('status')!=expected_states[index-1]:raise Fault('SMOKE_ASSERTION_FAILED')
                record['observed_state']=data['dom']['status']
            elif index==5:
                data=json.loads(body);sources=data.get('sources')
                if data.get('mode')!='SYNTHETIC' or data.get('candidate_sha')!=self.expected or not isinstance(sources,list) or len(sources)!=4 or any(v.get('state')!='FUTURE_LEAKAGE' or v.get('mode')!='SYNTHETIC' or v.get('runtime_source')!='NONE' or v.get('rows')!=[] for v in sources):raise Fault('SMOKE_ASSERTION_FAILED')
                record['observed_states']=[v['state'] for v in sources]
            elif not body:raise Fault('SMOKE_ASSERTION_FAILED')
            record['assertions_passed']=True
        self.checklist='PHYSICAL PENDING. SYNTHETIC ONLY.\nCandidate: '+self.expected+'\nReview browser/DPR/zoom/pan/resize/switch/cancellation/console/performance.\nPreserve redacted screenshots separately; no real sources or orders.\n'
    def _health(self):
        self._set('child_health');self.health_probes+=1
        if self.child.poll() is not None:raise Fault('CHILD_EARLY_EXIT')
        if self.child.output_limit:raise Fault('CHILD_OUTPUT_LIMIT')
        if self.child.stderr_bytes:raise Fault('CHILD_STDERR')
        status,body=self.ops.fetch(self.url+'/api/status')
        if status!=200:raise Fault('CHILD_HEALTH_FAILED')
        data=json.loads(body);self._identity(data)
        if data.get('execution')!='DISABLED':raise Fault('SYNTHETIC_IDENTITY_MISMATCH')
        self._set('child_health','PASS')
    def _review(self):
        self._health();self._set('review_wait')
        start=self.ops.clock();deadline=start+self.seconds;next_probe=start+1
        try:
            while self.ops.clock()<deadline:
                self._set('review_wait');self.ops.sleep(min(.25,deadline-self.ops.clock()))
                if self.ops.clock()>=next_probe:self._health();next_probe=self.ops.clock()+1
            self.review_completed=True
        finally:self.review_elapsed=round(max(0,self.ops.clock()-start),3)
        self._set('review_wait','PASS' if self.seconds else 'NOT_REQUESTED');self._health()
    def _shutdown(self):
        self._set('graceful_shutdown');self.shutdown_attempted=True
        code=self.child.quit(self.shutdown_timeout)
        if code!=0:raise Fault('CHILD_EXIT_FAILED')
        self._set('graceful_shutdown','PASS')
    def _cleanup(self):
        if not self.child:
            self.states['graceful_shutdown']='NOT_REQUESTED';return
        previous=None
        if threading.current_thread() is threading.main_thread():
            try:previous=signal.signal(signal.SIGINT,signal.SIG_IGN)
            except (ValueError,OSError):pass
        try:
            try:
                if self.child.poll() is None and not self.shutdown_attempted:
                    try:self._shutdown()
                    except (Exception,KeyboardInterrupt) as exc:self._fail('graceful_shutdown',exc)
            finally:
                try:
                    if self.child.poll() is None:self.child.kill()
                except (Exception,KeyboardInterrupt) as exc:self._fail('graceful_shutdown',exc)
                finally:
                    try:
                        if self.child.close() is False:raise Fault('OUTPUT_DRAIN_TIMEOUT')
                        if self.child.output_limit:raise Fault('CHILD_OUTPUT_LIMIT')
                        if self.child.stderr_bytes:raise Fault('CHILD_STDERR')
                    except (Exception,KeyboardInterrupt) as exc:self._fail('graceful_shutdown',exc)
        finally:
            if previous is not None:signal.signal(signal.SIGINT,previous)
    def _summary(self):
        return dict(harness_contract_version=2,kind='harness',run_id=self.run_id,
          candidate_sha=self.expected if isinstance(self.expected,str) and SHA.fullmatch(self.expected) else 'INVALID',
          actual_sha=self.actual_sha,source_clean=self.clean,utc=datetime.now(timezone.utc).isoformat(),
          python_version='.'.join(map(str,sys.version_info[:3])),powershell_version=self.shell_version,
          mode='SYNTHETIC',sources='DISABLED',physical='PENDING',exit_code=self.code,
          result='FAIL' if self.code else 'AUTOMATED_SYNTHETIC_SMOKE_PASS',
          failure_stage=self.failure_stage,error_class=self.error_class,os_error_code=self.os_error_code,
          stages=self.states,secondary_failures=self.secondary,health_probes=self.health_probes,
          browser_requested=self.open_browser,review_seconds_requested=self.seconds,
          review_elapsed_seconds=self.review_elapsed,review_completed=self.review_completed,
          child_exit_code=self.child.poll() if self.child else None,
          child_stdout_bytes=self.child.stdout_bytes if self.child else 0,
          child_stderr_bytes=self.child.stderr_bytes if self.child else 0)
    def _write(self):
        if not self.owned_pending:raise Fault('EVIDENCE_DIRECTORY_UNAVAILABLE')
        info=os.lstat(self.pending)
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise Fault('EVIDENCE_PATH_REDIRECTED')
        if self.smoke:self.ops.write_json(self.pending/'smoke.json',self.smoke)
        if self.checklist:
            with (self.pending/'browser-checklist.txt').open('w',encoding='utf-8',newline='\n') as out:out.write(self.checklist)
        self.ops.write_json(self.pending/'summary.json',self._summary())
        entries=[]
        for path in sorted(self.pending.iterdir()):
            if path.name=='manifest.json':continue
            if path.name not in FILES or not path.is_file() or path.is_symlink():raise Fault('EVIDENCE_FINALIZE_FAILED')
            body=path.read_bytes();entries.append(dict(file=path.name,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body)))
        self.ops.write_json(self.pending/'manifest.json',entries)
        _integrity(self.pending)
        if self.code==0:
            from terminan.r2_evidence import verify
            verify(self.pending,self.expected)
        self.ops.publish(self.pending,self.final_dir)
    def run(self):
        try:
            self._set('evidence_finalize');self._acquire()
            self._set('preflight');self._preflight();self._set('preflight','PASS')
            self._set('startup');self._startup();self._set('startup','PASS')
            self._set('smoke');self._smoke();self._set('smoke','PASS')
            self._set('browser_launch')
            if self.open_browser:self.ops.browser(self.url);self._set('browser_launch','DISPATCHED')
            else:self._set('browser_launch','NOT_REQUESTED')
            self._review();self._shutdown()
        except (Exception,KeyboardInterrupt) as exc:self._fail(self.stage,exc)
        finally:
            try:self._cleanup()
            except (Exception,KeyboardInterrupt) as exc:self._fail('graceful_shutdown',exc)
        if not self.owned_pending:return self.code or 50
        self._set('evidence_finalize','PASS')
        try:self._write()
        except (Exception,KeyboardInterrupt) as exc:
            self._fail('evidence_finalize',exc)
            try:self._write()
            except Exception:pass
        return self.code

class PrivateParser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('invalid arguments')

def main(argv=None):
    try:
        parser=PrivateParser();parser.add_argument('--expected-sha',required=True);parser.add_argument('--evidence-root',default='.r2-evidence')
        parser.add_argument('--review-seconds',default='0');parser.add_argument('--open-browser',action='store_true')
        parser.add_argument('--run-id');parser.add_argument('--inspect-run',action='store_true')
        parser.add_argument('--shell-version')
        args=parser.parse_args(argv)
        harness=Harness(expected_sha=args.expected_sha,evidence_root=args.evidence_root,review_seconds=args.review_seconds,open_browser=args.open_browser,run_id=args.run_id,shell_version=args.shell_version)
        if args.inspect_run:
            code=inspect_run(harness.final_dir,args.expected_sha)
            print('R2 evidence inspection exit_code='+str(code))
        else:
            code=harness.run()
            print('R2 evidence run_id='+harness.run_id)
            print('R2 result exit_code='+str(code)+' failure_stage='+harness.failure_stage+' error_class='+harness.error_class)
        return code
    except (Exception,KeyboardInterrupt):
        print('R2 failure_stage=evidence_finalize error_class=EVIDENCE_FINALIZE_FAILED exit_code=50')
        return 50

if __name__=='__main__':raise SystemExit(main())
