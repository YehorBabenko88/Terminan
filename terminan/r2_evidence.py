"""Integrity plus mandatory assertion checks, separate from physical acceptance."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil

BASE='0ad0f36edce2ac7717c753d35ebe113dc6334fd0'
PROJECTS=[engine+'-dpr'+str(dpr) for engine in ('chromium','firefox') for dpr in (1,1.5,2)]
BROWSER_CONTRACT_VERSION=2
BROWSER_ASSERTIONS={
    'zoom pan resize DPR and complete synthetic identity',
    'fault recovery contracts and bounded replay',
    'superseded requests cannot keep another symbol visible',
    'stress frame pipeline memory CPU and lifecycle evidence',
    'partial HTTP failure and in-flight disposal abort all requests',
    'dynamic fleet, every control, unavailable data and selection',
    'aborted stale response cannot overwrite new snapshot',
    'actual A states filter and selected detail follows latest metrics',
    'stalled local refresh becomes explicitly unavailable at deadline',
    'actual Python consumer rejects forged nested observation before Chromium renders',
    'delayed facts, frozen forecasts and joint publication remain distinct',
    'OOS is displayed only after its declared publication, outside diagnostics',
    'rehashed envelope cannot bypass scientific output trace integrity',
    'asOf slider reaches publication later than every event and forecast target',
}
REPO=Path(__file__).resolve().parents[1]

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_report(report):
    if report.get('errors'):raise ValueError('browser runner errors')

def check_performance(perf):
    metrics=perf['metrics']
    for key in ('avgRenderMs','p95RenderMs','playRateHz','idleExtraRenders'):
        if type(metrics[key]) not in (int,float) or not math.isfinite(metrics[key]):raise ValueError('invalid performance measurement')
    if not 0<=metrics['avgRenderMs']<20 or not 0<=metrics['p95RenderMs']<50 or not 1.2<=metrics['playRateHz']<=5.5 or metrics['idleExtraRenders']!=0:
        raise ValueError('render/cadence/idle budget exceeded')
    engine=perf['enginePerformance']
    if engine['available']:
        cpu=engine['mainThreadCpuMs'];wall=perf['wallMs']
        if not math.isfinite(cpu) or not math.isfinite(wall) or wall<=0 or not 0<=cpu/wall<.75:raise ValueError('CPU duty budget exceeded')

def manifest(root):
    root=Path(root)
    entries=[dict(file=p.relative_to(root).as_posix(),sha256=digest(p),bytes=p.stat().st_size)
             for p in sorted(root.rglob('*')) if p.is_file() and p.name!='manifest.json']
    write(root/'manifest.json',entries)

def verify(root,sha):
    root=Path(root);entries=read(root/'manifest.json');names=set()
    if not isinstance(entries,list) or not entries:raise ValueError('empty evidence manifest')
    for e in entries:
        name=e['file'];parts=PurePosixPath(name)
        if not isinstance(name,str) or parts.is_absolute() or any(p in ('.','..') for p in parts.parts) or ':' in name or '\\' in name or name in names or name=='manifest.json':raise ValueError('unsafe manifest path')
        path=root/name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():raise ValueError('unsafe evidence')
        if path.stat().st_size!=e['bytes'] or digest(path)!=e['sha256']:raise ValueError('evidence tampered')
        names.add(name)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if names!=actual:raise ValueError('unmanifested evidence')
    summary=read(root/'summary.json')
    if summary.get('candidate_sha')!=sha or summary.get('physical')!='PENDING' or summary.get('mode')!='SYNTHETIC':raise ValueError('wrong evidence identity')
    if summary.get('kind')=='browser':
        # Current evidence must account for the full additive browser contract.
        # No implicit legacy inventory can qualify this source's collected suite.
        if type(summary.get('browser_contract_version')) is not int or summary['browser_contract_version']!=BROWSER_CONTRACT_VERSION:raise ValueError('unsupported browser contract')
        if summary.get('scope') not in ('all','chromium'):raise ValueError('unsupported browser scope')
        expected=[p for p in PROJECTS if p.startswith('chromium')] if summary['scope']=='chromium' else PROJECTS
        required={'summary.json','tests.json','contract-pins.json','fixture-v1.json'}
        for project in expected:required.update({project+'/performance.json',project+'/preview.png'})
        if not required.issubset(names) or summary['result']!='PASS':raise ValueError('incomplete browser evidence')
        tests=read(root/'tests.json')
        if any(t['status']!='passed' or t['attempts']!=1 for t in tests):raise ValueError('browser failures/skips')
        inventory={(project,title) for project in expected for title in BROWSER_ASSERTIONS}
        observed=[(t['project'],t['title']) for t in tests]
        if len(observed)!=len(inventory) or set(observed)!=inventory:raise ValueError('missing, duplicate or unexpected browser assertions')
        for project in expected:
            perf=read(root/project/'performance.json')
            if perf['candidate_sha']!=sha or not perf['source_clean'] or perf['mode']!='SYNTHETIC':raise ValueError('wrong browser source')
            check_performance(perf)
            if project.startswith('chromium') and not perf['enginePerformance']['available']:raise ValueError('Chromium CPU evidence missing')
            if perf['disposed']['listeners'] or perf['disposed']['rafPending'] or perf['disposed']['timerPending'] or perf['disposed']['activeRequests']:raise ValueError('retained lifecycle resource')
            if perf['metrics']['retainedCandles']>240 or perf['metrics']['retainedEvents']>20 or perf['metrics']['peakRequests']>4:raise ValueError('resource bounds violated')
            if (root/project/'preview.png').read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('invalid screenshot')
    else:
        if 'harness_contract_version' in summary and (type(summary['harness_contract_version']) is not int or summary['harness_contract_version']!=2):raise ValueError('unsupported harness contract')
        required={'summary.json','ready.json','smoke.json','browser-checklist.txt'}
        if not required.issubset(names) or summary.get('result')!='AUTOMATED_SYNTHETIC_SMOKE_PASS' or summary.get('exit_code')!=0:raise ValueError('incomplete harness evidence')
        ready=read(root/'ready.json')
        if ready.get('candidate_sha')!=sha or not ready.get('source_clean') or ready.get('sources')!='DISABLED' or ready.get('host')!='127.0.0.1':raise ValueError('wrong listener/source')
        smoke=read(root/'smoke.json')
        if len(smoke)!=9 or any(r['status']!=200 for r in smoke):raise ValueError('missing smoke assertions')
        routes={r['route'] for r in smoke}
        if not {'/api/status','/api/synthetic/frame?step=24&scenario=gap','/api/synthetic/contracts?scenario=future','/'}.issubset(routes):raise ValueError('missing required routes')
        if summary.get('harness_contract_version')==2:
            from .r2_harness import _integrity
            _integrity(root)
            stages=summary.get('stages',{})
            if any(stages.get(s)!='PASS' for s in ('preflight','startup','smoke','child_health','graceful_shutdown','evidence_finalize')):raise ValueError('incomplete harness stages')
            if stages.get('browser_launch')!=('DISPATCHED' if summary['browser_requested'] else 'NOT_REQUESTED'):raise ValueError('browser stage mismatch')
            requested=summary['review_seconds_requested']
            if stages.get('review_wait')!=('PASS' if requested else 'NOT_REQUESTED') or not summary['review_completed'] or summary['review_elapsed_seconds']<requested:raise ValueError('review stage incomplete')
            if any(r.get('assertions_passed') is not True for r in smoke):raise ValueError('smoke assertions incomplete')

def bundle(report,results,out,sha,scope='all'):
    report=read(report);check_report(report);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    tests=[]
    def visit(suite):
        for spec in suite.get('specs',[]):
            for test in spec['tests']:
                attempts=test.get('results',[])
                tests.append(dict(title=spec['title'],project=test['projectName'],
                                  status=attempts[-1]['status'] if attempts else 'missing',
                                  attempts=len(attempts),duration_ms=sum(a.get('duration',0) for a in attempts)))
        for child in suite.get('suites',[]):visit(child)
    for suite in report.get('suites',[]):visit(suite)
    write(out/'tests.json',tests)
    shutil.copyfile(REPO/'contracts.lock.json',out/'contract-pins.json')
    shutil.copyfile(REPO/'terminan/fixtures/r2-contract-v1.json',out/'fixture-v1.json')
    expected=[p for p in PROJECTS if p.startswith('chromium')] if scope=='chromium' else PROJECTS
    for path in Path(results).rglob('performance.json'):
        perf=read(path);project=perf.get('project')
        if project not in expected:continue
        folder=out/project;folder.mkdir(exist_ok=True)
        write(folder/'performance.json',perf)
        screenshot=path.with_name('stress-preview.png')
        if screenshot.exists():shutil.copyfile(screenshot,folder/'preview.png')
    summary=dict(kind='browser',browser_contract_version=BROWSER_CONTRACT_VERSION,candidate_sha=sha,mode='SYNTHETIC',physical='PENDING',
                 result='PASS',scope=scope,base_g0_sha=BASE,fixture_sha256=digest(out/'fixture-v1.json'),
                 run_id=os.environ.get('GITHUB_RUN_ID'),run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                 tests=len(tests),failures=sum(t['status']!='passed' for t in tests))
    write(out/'summary.json',summary);manifest(out)
    try:verify(out,sha)
    except (ValueError,KeyError,OSError):
        summary['result']='FAIL';write(out/'summary.json',summary);manifest(out)
        raise ValueError('browser evidence incomplete or failing; details retained') from None

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    make=sub.add_parser('bundle');make.add_argument('--report',required=True);make.add_argument('--results',default='test-results');make.add_argument('--out',required=True);make.add_argument('--sha',required=True);make.add_argument('--scope',choices=['all','chromium'],default='all')
    check=sub.add_parser('verify');check.add_argument('root');check.add_argument('--sha',required=True)
    args=parser.parse_args()
    if args.action=='bundle':bundle(args.report,args.results,args.out,args.sha,args.scope)
    else:
        manifests=list(Path(args.root).rglob('manifest.json'))
        if not manifests:raise ValueError('no evidence manifest')
        for path in manifests:verify(path.parent,args.sha)
    print('R2 synthetic evidence verified; PHYSICAL PENDING')

if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt):
        print('R2 evidence FAIL error_class=EVIDENCE_INVALID')
        raise SystemExit(50)
