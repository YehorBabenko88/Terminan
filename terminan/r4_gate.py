"""Aggregate R4 gate. Lifecycle-only and unfinished invocations always fail closed."""
import argparse,hashlib,json,os,re,subprocess,uuid
from pathlib import Path
from .r4_harness import inspect as inspect_run
from .r4_evidence import read,verify as browser_verify
ERRORS=('NONE','INCOMPLETE','LIFECYCLE_FAILED','BROWSER_FAILED','EVIDENCE_INVALID','LAUNCHER_ERROR')
REPO=Path(__file__).resolve().parents[1]
def atomic(path,value):
    temp=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(temp,path)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(sha):
    if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError()
    def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,stderr=subprocess.DEVNULL,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=sha or git('status','--porcelain','--untracked-files=normal'):raise ValueError()
def begin(root,sha,invocation):
    if not re.fullmatch('[0-9a-f]{32}',invocation):raise ValueError()
    root.mkdir(parents=True,exist_ok=False)
    atomic(root/'summary.json',dict(version=1,candidate_sha=sha,invocation=invocation,result='FAIL',exit_code=50,error_class='INCOMPLETE',failure_stage='preflight',physical='PENDING',mode='SYNTHETIC',authority='SYNTHETIC_ONLY',sources='DISABLED',run_id=os.getenv('GITHUB_RUN_ID','LOCAL'),attempt=os.getenv('GITHUB_RUN_ATTEMPT','1')))
    source(sha)
def bindings(root,sha,invocation):
    summary=read(root/'summary.json')
    if type(summary.get('version')) is not int or summary.get('version')!=1 or summary.get('mode')!='SYNTHETIC' or summary.get('authority')!='SYNTHETIC_ONLY' or summary.get('sources')!='DISABLED' or summary.get('candidate_sha')!=sha or summary.get('invocation')!=invocation or not re.fullmatch('[0-9a-f]{32}',invocation) or summary.get('physical')!='PENDING':raise ValueError()
    life=list((root/'lifecycle').iterdir())
    if len(life)!=1 or not life[0].is_dir() or inspect_run(life[0],sha)!=0:raise ValueError()
    browser_verify(root/'browser',sha)
    browser=read(root/'browser/summary.json')
    if browser['scope']!='chromium' or any(browser[k]!=summary[k] for k in ('invocation','candidate_sha','run_id','attempt')):raise ValueError()
    return summary
def entries(root):
    result=[]
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError()
        if p.is_file() and p!=root/'manifest.json':result.append(dict(path=p.relative_to(root).as_posix(),sha256=digest(p)))
    return result
def complete(root,sha,invocation):
    source(sha);summary=bindings(root,sha,invocation)
    summary.update(result='AUTOMATED_R4_PASS',exit_code=0,error_class='NONE',failure_stage='NONE')
    atomic(root/'summary.json',summary);atomic(root/'manifest.json',entries(root))
    verify(root,sha,invocation)
def fail(root,kind):
    if kind not in ERRORS[1:]:raise ValueError()
    summary=read(root/'summary.json');summary.update(result='FAIL',exit_code=50,error_class=kind)
    atomic(root/'summary.json',summary);atomic(root/'manifest.json',entries(root))
def verify(root,sha,invocation):
    summary=bindings(root,sha,invocation)
    if type(summary.get('exit_code')) is not int or summary.get('result')!='AUTOMATED_R4_PASS' or summary.get('exit_code')!=0 or summary.get('error_class')!='NONE' or summary.get('failure_stage')!='NONE':raise ValueError()
    manifest=read(root/'manifest.json')
    if manifest!=entries(root):raise ValueError()
    # Only these three aggregate children are permitted; no workspace/raw reports.
    if {p.name for p in root.iterdir()}!={'summary.json','manifest.json','lifecycle','browser'}:raise ValueError()
    return 0
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['begin','complete','verify','fail','stage']);p.add_argument('--out',type=Path,required=True);p.add_argument('--sha',required=True);p.add_argument('--invocation',required=True);p.add_argument('--error-class',choices=ERRORS[1:],default='EVIDENCE_INVALID');p.add_argument('--stage',choices=['lifecycle','browser_run','browser_evidence','evidence_finalize']);a=p.parse_args()
    try:
        if a.action=='begin':begin(a.out,a.sha,a.invocation)
        elif a.action=='complete':complete(a.out,a.sha,a.invocation)
        elif a.action=='verify':verify(a.out,a.sha,a.invocation)
        elif a.action=='stage':
            if not a.stage:raise ValueError()
            summary=read(a.out/'summary.json')
            if summary['candidate_sha']!=a.sha or summary['invocation']!=a.invocation or summary['exit_code']!=50:raise ValueError()
            summary['failure_stage']=a.stage;atomic(a.out/'summary.json',summary)
        else:fail(a.out,a.error_class)
        return 0
    except (Exception,KeyboardInterrupt):
        if a.action=='complete':
            try:fail(a.out,'EVIDENCE_INVALID')
            except Exception:pass
        print('R4 gate FAIL error_class=EVIDENCE_INVALID exit_code=50');return 50
if __name__=='__main__':raise SystemExit(main())
