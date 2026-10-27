"""R4 strict browser benchmark evidence; never grants physical authority."""
import argparse,hashlib,json,math,os,re,shutil,subprocess,uuid
from pathlib import Path
PROJECTS=[f'{b}-dpr{d}' for b in ('chromium','firefox') for d in ('1','1.5','2')]
def read(p):
    if p.stat().st_size>16*1024*1024:raise ValueError()
    return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def numeric(value,minimum=None):
    if type(value) not in (int,float) or not math.isfinite(value) or minimum is not None and value<minimum:raise ValueError()
    return value
from .r3_evidence import check as check_r3

def check(data,sha):
    check_r3(data,sha) # Original measured renderer/CPU/RSS budgets retained verbatim.
    extra=data['r4']
    if extra.get('version')!=1 or extra['contractStates']!=['UNSUPPORTED_TIMEFRAME','UNSUPPORTED_TIMEFRAME','HISTORICAL_ONLY','HISTORICAL_ONLY']:raise ValueError()
    if extra['startupClose']!=dict(state='VIEW_CLOSED',sessionRequests=0) or data['disposed']['startupPending']!=0:raise ValueError()
    f=extra['fetch']
    if f['clock']!='PERFORMANCE_NOW_REQUEST_TO_SETTLED' or type(f['samples']) is not int or not 4<=f['samples']<=240:raise ValueError()
    q=f['quantiles']
    if set(q)!={'p50','p95','p99'}:raise ValueError()
    for v in q.values():numeric(v,0)
    if not q['p50']<=q['p95']<=q['p99'] or q['p95']>=2000 or q['p99']>=5000:raise ValueError()
    if extra['normalStop']!=dict(state='SESSION_ENDED',closed=True,requestsStable=True,childExit=0,consoleErrorsAfterEnd=0):raise ValueError()
    u=extra['unexpectedStop']
    if set(u)!={'state','bounded','requests','retries','noRevival'} or u['state']!='DISCONNECTED' or u['bounded'] is not True or u['noRevival'] is not True or type(u['requests']) is not int or not 1<=u['requests']<=8 or type(u['retries']) is not int or not 1<=u['retries']<=5:raise ValueError()
    if extra['limitations']!=['RENDER_CADENCE_NOT_PRESENTATION_FPS','MAIN_THREAD_CPU_NOT_HOST_TOTAL','RSS_SUM_MAY_COUNT_SHARED_PAGES','OFFLINE_FIXTURES_NO_RUNTIME_AUTHORITY']:raise ValueError()
    session=data['disposed']['session']
    if session['state']!='SESSION_ENDED' or session['closed'] is not True or session['pending']!=0 or session['active']!=0 or data['disposed']['retryPending']!=0:raise ValueError()

def report_invocation(raw):
    if not isinstance(raw,dict):raise ValueError()
    return raw.get('config',{}).get('metadata',{}).get('r4_invocation')

def report_tests(raw,sha,invocation,projects):
    if not isinstance(raw,dict) or report_invocation(raw)!=invocation:raise ValueError()
    if raw['config']['metadata'].get('r4_source_sha')!=sha or raw.get('errors')!=[]:raise ValueError()
    stats=raw.get('stats')
    if not isinstance(stats,dict):raise ValueError()
    if any(type(stats.get(k)) is not int or stats[k]!=v for k,v in dict(expected=len(projects),skipped=0,unexpected=0,flaky=0).items()):raise ValueError()
    tests=[]
    def walk(suites):
        if not isinstance(suites,list):raise ValueError()
        for suite in suites:
            for spec in suite.get('specs',[]):
                if spec.get('title')!='R4 bounded workloads contracts and session lifecycle' or spec.get('file')!='r4.spec.cjs' or spec.get('ok') is not True:raise ValueError()
                tests.extend(spec['tests'])
            walk(suite.get('suites',[]))
    walk(raw['suites'])
    if len(tests)!=len(projects) or sorted(t['projectName'] for t in tests)!=sorted(projects):raise ValueError()
    for t in tests:
        if t.get('expectedStatus')!='passed' or t.get('status')!='expected' or len(t['results'])!=1:raise ValueError()
        result=t['results'][0]
        if result.get('status')!='passed' or type(result.get('retry')) is not int or result['retry']!=0 or result.get('errors')!=[]:raise ValueError()
        if t.get('projectId')!=t['projectName']:raise ValueError()
    return tests

def work_root():return Path(os.environ.get('R4_WORK_ROOT','.'))
def bundle(report,out,sha,scope):
    invocation=os.getenv('R4_INVOCATION','')
    if not re.fullmatch('[0-9a-f]{32}',invocation):raise ValueError()
    if out.exists():raise ValueError()
    final=out;out=out.with_name('.pending-'+out.name+'-'+uuid.uuid4().hex)
    out.mkdir(parents=True,exist_ok=False);projects=PROJECTS if scope=='all' else [p for p in PROJECTS if p.startswith('chromium')]
    summary=dict(version=2,invocation=invocation,candidate_sha=sha,result='FAIL',physical='PENDING',scope=scope,run_id=os.getenv('GITHUB_RUN_ID','LOCAL'),attempt=os.getenv('GITHUB_RUN_ATTEMPT','1'))
    try:
        raw=read(report)
        tests=report_tests(raw,sha,invocation,projects)
        # Keep only typed, privacy-safe report facts. Never copy raw exceptions/paths.
        write(out/'browser-report.json',dict(version=1,candidate_sha=sha,invocation=invocation,stats={k:raw['stats'][k] for k in ('expected','skipped','unexpected','flaky')},projects=projects,report_sha256=hashlib.sha256(report.read_bytes()).hexdigest()))
        for project in projects:
            files=list((work_root()/'r4-test-results').glob('**/r4-performance.json'))
            found=[p for p in files if read(p)['project']==project]
            if len(found)!=1:raise ValueError()
            record=read(found[0])
            if any(record.get(k)!=summary[k] for k in ('invocation','run_id','attempt')):raise ValueError()
            check(record,sha)
            shutil.copyfile(found[0],out/(project+'.json'))
            shutil.copyfile(found[0].with_name('r4-preview.png'),out/(project+'.png'))
        shutil.copyfile('contracts.lock.json',out/'contract-pins.json')
        shutil.copyfile('terminan/fixtures/r4-negative-v1.json',out/'negative-fixtures.json')
        for name in ('r4-contract-v1.json','r4-contract-lock-v1.json'):
            shutil.copyfile(Path(__file__).with_name('fixtures')/name,out/name)
        write(out/'tests.json',[dict(project=t['projectName'],status=t['results'][0]['status'],attempts=len(t['results'])) for t in tests])
        summary['result']='AUTOMATED_SYNTHETIC_BENCHMARK_PASS'
    finally:
        write(out/'summary.json',summary)
        write(out/'manifest.json',[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'])
        # Only complete verified bundles are published under the requested name.
        if summary['result']=='FAIL':os.replace(out,final)
    try:verify(out,sha)
    except (ValueError,KeyError,TypeError,OSError,AttributeError,OverflowError,RecursionError):
        summary['result']='FAIL'
        write(out/'summary.json',summary)
        write(out/'manifest.json',[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'])
        os.replace(out,final)
        raise
    os.replace(out,final)
    return 0

def verify(root,sha):
    if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError()
    entries=read(root/'manifest.json')
    if not isinstance(entries,list) or not entries:raise ValueError()
    names=[]
    for entry in entries:
        name=entry['path']
        if not isinstance(name,str) or Path(name).name!=name or '/' in name or '\\' in name or name in ('.','..','manifest.json') or name in names:raise ValueError()
        names.append(name);p=root/name
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError()
    if set(names)!={p.name for p in root.iterdir() if p.name!='manifest.json'}:raise ValueError()
    summary=read(root/'summary.json')
    if summary.get('version')!=2 or not re.fullmatch('[0-9a-f]{32}',summary.get('invocation','')) or summary['candidate_sha']!=sha or summary['result']!='AUTOMATED_SYNTHETIC_BENCHMARK_PASS' or summary['physical']!='PENDING':raise ValueError()
    if summary['scope'] not in ('all','chromium'):raise ValueError()
    projects=PROJECTS if summary['scope']=='all' else PROJECTS[:3]
    required={'summary.json','tests.json','browser-report.json','contract-pins.json','negative-fixtures.json','r4-contract-v1.json','r4-contract-lock-v1.json'}|{p+ext for p in projects for ext in ('.json','.png')}
    if set(names)!=required:raise ValueError()
    report=read(root/'browser-report.json')
    if report.get('version')!=1 or report.get('candidate_sha')!=sha or report.get('invocation')!=summary['invocation'] or report.get('projects')!=projects or not re.fullmatch('[0-9a-f]{64}',report.get('report_sha256','')):raise ValueError()
    stats=report['stats']
    if set(stats)!={'expected','skipped','unexpected','flaky'} or any(type(stats[k]) is not int or stats[k]!=v for k,v in dict(expected=len(projects),skipped=0,unexpected=0,flaky=0).items()):raise ValueError()
    if read(root/'negative-fixtures.json')!=read(Path(__file__).with_name('fixtures')/'r4-negative-v1.json'):raise ValueError()
    if read(root/'contract-pins.json')!=read(Path(__file__).resolve().parents[1]/'contracts.lock.json'):raise ValueError()
    for name in ('r4-contract-v1.json','r4-contract-lock-v1.json'):
        if read(root/name)!=read(Path(__file__).with_name('fixtures')/name):raise ValueError()
    tests=read(root/'tests.json')
    if sorted(t['project'] for t in tests)!=sorted(projects) or any(t['status']!='passed' or t['attempts']!=1 for t in tests):raise ValueError()
    for project in projects:
        record=read(root/(project+'.json'))
        if any(record.get(k)!=summary[k] for k in ('invocation','run_id','attempt')):raise ValueError()
        check(record,sha)
        if (root/(project+'.png')).read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError()
    return 0
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');parser.add_argument('--report',type=Path,default=Path('reports/r4-browser.json'));parser.add_argument('--out',type=Path,required=True);parser.add_argument('--sha',required=True);parser.add_argument('--scope',choices=['all','chromium'],default='all');args=parser.parse_args()
    try:raise SystemExit(verify(args.out,args.sha) if args.verify else bundle(args.report,args.out,args.sha,args.scope))
    except (ValueError,KeyError,TypeError,OSError,AttributeError,OverflowError,RecursionError):print('R4 evidence FAIL error_class=EVIDENCE_INVALID');raise SystemExit(50)
