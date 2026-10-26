"""R3 strict browser benchmark evidence; never grants physical authority."""
import argparse,hashlib,json,math,os,re,shutil,subprocess
from pathlib import Path
PROJECTS=[f'{b}-dpr{d}' for b in ('chromium','firefox') for d in ('1','1.5','2')]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def numeric(value,minimum=None):
    if type(value) not in (int,float) or not math.isfinite(value) or minimum is not None and value<minimum:raise ValueError()
    return value
def check(data,sha):
    if data['version']!=1 or data['candidate_sha']!=sha or data['source_clean'] is not True:raise ValueError()
    if data['project'] not in PROJECTS or len(data['results'])!=2:raise ValueError()
    for r,count in zip(data['results'],(10000,100000)):
        checksum=17
        for _ in range(count):checksum=(checksum*1664525+1013904223)&0xffffffff
        if (r['updates'],r['seed'],r['batch'],r['frames'],r['samples'],r['checksum'])!=(count,17,100,count//100,count//100,checksum):raise ValueError()
        if r['mode']!='SYNTHETIC' or r['authority']!='SYNTHETIC_ONLY':raise ValueError()
        values=[r['elapsedMs'],r['renderCadenceFps'],r['updatesPerSecond']]+[q for key in ('latencyMs','drawMs','frameIntervalMs') for q in r[key].values()]
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):raise ValueError()
        if r['latencyMs']['p99']>=100 or r['drawMs']['p95']>=50 or r['renderCadenceFps']<=10:raise ValueError()
        m=r['metrics']
        if m['retainedCandles']>240 or m['retainedEvents']>20 or m['bookRows']>40 or m['activeRequests']!=0:raise ValueError()
    resources=data['resources']
    if data['project'].startswith('chromium'):
        for key in ('heapBefore','heapAfter'):numeric(resources[key],0)
        numeric(resources['heapGrowthBytes']);numeric(resources['cpuDuty'],0)
        if resources['state']!='AVAILABLE' or not 0<=resources['cpuDuty']<.75 or resources['heapGrowthBytes']>=12*1024**2:raise ValueError()
        memory=resources['processMemory']
        for k in ('before','after'):
            numeric(memory[k]['rss_bytes'],1)
            if type(memory[k]['process_count']) is not int or not 1<=memory[k]['process_count']<=64:raise ValueError()
        if any(memory[k]['state']!='AVAILABLE' for k in ('before','after')) or memory['after']['rss_bytes']>=2*1024**3 or memory['after']['rss_bytes']-memory['before']['rss_bytes']>=256*1024**2:raise ValueError()
    elif resources['state']!='UNAVAILABLE' or resources['reason']!='FIREFOX_CDP_UNSUPPORTED':raise ValueError()
    if any(data['disposed'][key]!=0 for key in ('listeners','rafPending','activeRequests','timerPending','retainedCandles')):raise ValueError()
def bundle(report,out,sha,scope):
    invocation=os.getenv('R3_INVOCATION','')
    if not re.fullmatch('[0-9a-f]{32}',invocation):raise ValueError()
    out.mkdir(parents=True,exist_ok=False);projects=PROJECTS if scope=='all' else [p for p in PROJECTS if p.startswith('chromium')]
    summary=dict(version=1,invocation=invocation,candidate_sha=sha,result='FAIL',physical='PENDING',scope=scope,run_id=os.getenv('GITHUB_RUN_ID','LOCAL'),attempt=os.getenv('GITHUB_RUN_ATTEMPT','1'))
    try:
        raw=read(report)
        if raw.get('metadata',{}).get('r3_invocation')!=invocation:raise ValueError()
        if raw.get('errors'):raise ValueError()
        tests=[]
        def walk(suites):
            for suite in suites:
                for spec in suite.get('specs',[]):tests.extend(spec['tests'])
                walk(suite.get('suites',[]))
        walk(raw['suites'])
        if len(tests)!=len(projects) or sorted(t['projectName'] for t in tests)!=sorted(projects):raise ValueError()
        if any(t['status']!='expected' or len(t['results'])!=1 or t['results'][0]['status']!='passed' for t in tests):raise ValueError()
        for project in projects:
            files=list(Path('r3-test-results').glob('**/r3-performance.json'))
            found=[p for p in files if read(p)['project']==project]
            if len(found)!=1:raise ValueError()
            record=read(found[0])
            if any(record.get(k)!=summary[k] for k in ('invocation','run_id','attempt')):raise ValueError()
            check(record,sha)
            shutil.copyfile(found[0],out/(project+'.json'))
            shutil.copyfile(found[0].with_name('r3-preview.png'),out/(project+'.png'))
        shutil.copyfile('contracts.lock.json',out/'contract-pins.json')
        shutil.copyfile('terminan/fixtures/r3-negative-v1.json',out/'negative-fixtures.json')
        write(out/'tests.json',[dict(project=t['projectName'],status=t['results'][0]['status'],attempts=len(t['results'])) for t in tests])
        summary['result']='AUTOMATED_SYNTHETIC_BENCHMARK_PASS'
    finally:
        write(out/'summary.json',summary)
        write(out/'manifest.json',[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'])
    verify(out,sha)
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
    if summary['candidate_sha']!=sha or summary['result']!='AUTOMATED_SYNTHETIC_BENCHMARK_PASS' or summary['physical']!='PENDING':raise ValueError()
    if summary['scope'] not in ('all','chromium'):raise ValueError()
    projects=PROJECTS if summary['scope']=='all' else PROJECTS[:3]
    required={'summary.json','tests.json','contract-pins.json','negative-fixtures.json'}|{p+ext for p in projects for ext in ('.json','.png')}
    if set(names)!=required:raise ValueError()
    if read(root/'contract-pins.json')!=read(Path(__file__).resolve().parents[1]/'contracts.lock.json'):raise ValueError()
    tests=read(root/'tests.json')
    if sorted(t['project'] for t in tests)!=sorted(projects) or any(t['status']!='passed' or t['attempts']!=1 for t in tests):raise ValueError()
    for project in projects:
        record=read(root/(project+'.json'))
        if any(record.get(k)!=summary[k] for k in ('invocation','run_id','attempt')):raise ValueError()
        check(record,sha)
        if (root/(project+'.png')).read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError()
    return 0
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');parser.add_argument('--report',type=Path,default=Path('reports/r3-browser.json'));parser.add_argument('--out',type=Path,required=True);parser.add_argument('--sha',required=True);parser.add_argument('--scope',choices=['all','chromium'],default='all');args=parser.parse_args()
    try:raise SystemExit(verify(args.out,args.sha) if args.verify else bundle(args.report,args.out,args.sha,args.scope))
    except (ValueError,KeyError,TypeError,OSError):print('R3 evidence FAIL error_class=EVIDENCE_INVALID');raise SystemExit(50)
