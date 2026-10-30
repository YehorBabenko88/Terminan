"""Offline physical harness; fail closed, one owned child, no raw stderr evidence."""
import argparse,json,os,queue,socket,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
from urllib.request import urlopen
from .unified_runner import provenance
from .unified_process import run_browser
from .unified_evidence import atomic_json,seal,validate_browser,verify_previous

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sha',required=True);parser.add_argument('--out',required=True);parser.add_argument('--seconds',type=int,choices=(15,600),default=15);parser.add_argument('--previous');args=parser.parse_args()
    root=Path(args.out).resolve();root.mkdir(parents=True,exist_ok=False)
    invocation=uuid.uuid4().hex;summary=dict(invocation=invocation,candidate_sha=args.sha,tree=None,review_seconds=args.seconds,result='FAIL',physical='PENDING',exit_code=50,failure_stage='source',error_class='SOURCE_MISMATCH',python=sys.version.split()[0],shell=os.environ.get('UNIFIED_SHELL','DIRECT'))
    child=None;err=[0];read_threads=[];code=50;stage='source';error='SOURCE_MISMATCH';shutdown={};smoke=[]
    try:
        source=provenance();summary['tree']=source['tree']
        if source['candidate_sha']!=args.sha or not source['source_clean']:raise ValueError()
        if args.seconds==600:
            stage='prior_smoke';error='PRIOR_SMOKE_REQUIRED'
            if not args.previous:raise ValueError()
            verify_previous(args.previous,args.sha,source['tree'])
        stage='startup';error='STARTUP_FAILED';code=20
        child=subprocess.Popen([sys.executable,'-m','terminan.unified_runner','--demo','--port','0','--expected-sha',args.sha],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        ready=queue.Queue(maxsize=1)
        def stdout():
            line=child.stdout.readline(16385)
            try:ready.put_nowait(line)
            except queue.Full:pass
            while child.stdout.read(4096):pass
        def stderr():
            while True:
                b=child.stderr.read(4096)
                if not b:return
                err[0]=min(2**31-1,err[0]+len(b))
        for fn in (stdout,stderr):
            t=threading.Thread(target=fn,daemon=True);t.start();read_threads.append(t)
        receipt=json.loads(ready.get(timeout=15));url=receipt['url']
        if receipt['candidate_sha']!=args.sha or receipt['tree']!=source['tree'] or receipt['source_clean'] is not True or not url.startswith('http://127.0.0.1:') or receipt['sources']!='SYNTHETIC_FIXTURES':raise ValueError()
        atomic_json(root/'ready.json',receipt)
        def get(path):
            with urlopen(url+path,timeout=5) as response:
                if response.status!=200:raise ValueError()
                return response.read(2097153)
        stage='smoke';error='SMOKE_FAILED';code=30
        for path in ('/','/saved','/math','/history-overlay','/monitor','/cache','/api/status','/api/synthetic/status','/api/session','/api/saved/catalog','/api/infrastructure','/api/cache/status'):
            body=get(path);smoke.append(dict(route=path,status=200,bytes=len(body)))
        if json.loads(get('/api/synthetic/status'))['sources']!='DISABLED' or json.loads(get('/api/infrastructure'))['state']!='UNAVAILABLE':raise ValueError()
        atomic_json(root/'smoke.json',smoke)
        stage='browser';error='BROWSER_INCOMPLETE_OR_UNBOUND';code=31
        with tempfile.TemporaryDirectory(prefix='terminan-unified-browser-') as tmp:
            raw=Path(tmp)/'report.json';env={**os.environ,'UNIFIED_URL':url,'UNIFIED_REPORT':str(raw),'UNIFIED_RESULTS':str(Path(tmp)/'screenshots'),'UNIFIED_INVOCATION':invocation,'R2_PYTHON':sys.executable}
            browser=run_browser(['node','node_modules/@playwright/test/cli.js','test','-c','playwright.unified.config.cjs'],env=env,timeout=300)
            if not raw.is_file() or raw.stat().st_size>8*1024*1024:raise ValueError()
            report=json.loads(raw.read_text(encoding='utf8'))
            # Public report retains assertions/status/identities; local paths are redacted.
            text=json.dumps(report,ensure_ascii=False)
            for private in (str(Path.cwd()),str(Path.home()),tmp):
                text=text.replace(private.replace('\\','\\\\'),'<LOCAL>').replace(private,'<LOCAL>').replace(private.replace('\\','/'),'<LOCAL>')
            atomic_json(root/'browser.json',json.loads(text))
            if browser.returncode!=0:raise ValueError()
            validate_browser(report,args.sha,source['tree'],invocation)
            for i,image in enumerate(sorted((Path(tmp)/'screenshots').rglob('unified.png'))):
                (root/('browser-'+str(i+1)+'.png')).write_bytes(image.read_bytes())
        stage='child_health';error='CHILD_FAILURE';code=33
        started=time.monotonic();polls=0
        while time.monotonic()-started<args.seconds:
            if child.poll() is not None or err[0]:raise ValueError()
            if json.loads(get('/api/session'))['state']!='ACTIVE':raise ValueError()
            polls+=1;time.sleep(1)
        atomic_json(root/'review.json',dict(seconds=args.seconds,polls=polls,elapsed_seconds=round(time.monotonic()-started,3),stderr_bytes=err[0]))
        stage='graceful_shutdown';error='SHUTDOWN_FAILED';code=40
        child.stdin.write(b'\n');child.stdin.flush();ended=False;deadline=time.monotonic()+2.5
        while time.monotonic()<deadline:
            if json.loads(get('/api/session'))['state']=='SESSION_ENDED':ended=True;break
            time.sleep(.1)
        native=child.wait(timeout=12)
        for t in read_threads:t.join(2)
        port=receipt['port'];listener=socket.socket();listener.settimeout(.5)
        try:closed=listener.connect_ex(('127.0.0.1',port))!=0
        finally:listener.close()
        shutdown=dict(native_exit=native,session_ended_observed=ended,listener_closed=closed,owned_pid_exited=child.poll() is not None,stderr_bytes=err[0])
        atomic_json(root/'shutdown.json',shutdown)
        if native!=0 or not ended or not closed or err[0]:raise ValueError()
        stage='evidence_finalize';error='EVIDENCE_INCOMPLETE';code=50
        for name in ('ready.json','smoke.json','browser.json','review.json','shutdown.json'):
            if not (root/name).is_file():raise ValueError()
        summary.update(result='AUTOMATED_PASS',exit_code=0,failure_stage=None,error_class=None);code=0
    except KeyboardInterrupt:code=130;error='CANCELLED'
    except Exception:pass
    finally:
        if child and child.poll() is None:
            try:child.stdin.write(b'\n');child.stdin.flush();child.wait(timeout=12)
            except Exception:child.kill();child.wait(timeout=5)
        if code:summary.update(exit_code=code,failure_stage=stage,error_class=error)
        summary['stderr_bytes']=err[0]
        try:atomic_json(root/'summary.json',summary);seal(root)
        except Exception:code=50
    print(json.dumps(dict(exit_code=code,result=summary['result'],invocation=invocation)),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
