"""Bounded, offline cache audit on NEW temporary SQLite databases only."""
from __future__ import annotations
import argparse, hashlib, json, math, platform, re, sqlite3, subprocess, sys, tempfile, time, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from terminan.saved_cache import ALGORITHM, EXACT_INDEX, canonical, key_for, open_cache, prepare, transaction, materialize_preview
from terminan.cache_queue import init_queue, submit, run_once
from terminan.cache_monitor import LOOKUP_SQL, lookup_exact_cache

def fixture():
    t=1767225600000
    identity=dict(source='grid',source_revision='a'*64,dataset='candles_1m',symbol='BTCUSDT',timeframe='5m',from_ms=t,to_ms=t+240000,algorithm=ALGORITHM,parameters_hash='b'*64)
    candles=[dict(symbol='BTCUSDT',ts=t+i*60000,open=100,high=102,low=99,close=101,buy_volume=2,sell_volume=1) for i in range(5)]
    source=dict(source_revision='a'*64,candles=candles,footprint=[dict(symbol='BTCUSDT',ts=c['ts'],price=100,buy_volume=2,sell_volume=1) for c in candles])
    return identity,source

def measure(fn,samples):
    elapsed=[];cpu=time.process_time()
    for _ in range(samples):
        before=time.perf_counter();fn();elapsed.append((time.perf_counter()-before)*1000)
    cpu=(time.process_time()-cpu)*1000;ordered=sorted(elapsed)
    return dict(samples=samples,p50_ms=ordered[math.ceil(samples*.5)-1],p95_ms=ordered[math.ceil(samples*.95)-1],p99_ms=max(ordered),cpu_mean_ms=cpu/samples,quantiles='NEAREST_RANK_P99_IS_MAX_AT_THIS_SAMPLE_SIZE')

def benchmark(samples=20):
    if type(samples) is not int or not 5<=samples<=100:raise ValueError('INVALID_SAMPLES')
    results=[]
    with tempfile.TemporaryDirectory(prefix='terminan-cache-audit-') as folder:
        path=Path(folder)/'synthetic.sqlite';con=init_queue(open_cache(path))
        try:
            identity,source=fixture();submit(con,identity,source);run_once(con)
            full=json.loads(con.execute('SELECT payload FROM cache_entries').fetchone()[0]);inserted=1
            for total in (1000,10000,100000):
                while inserted<total:
                    jobs=[];entries=[];views=[]
                    for i in range(inserted,min(total,inserted+500)):
                        other=dict(identity,symbol='SYN'+str(i));key,raw,h,view,vh=prepare(other,full);ident=canonical(other).decode();now=int(time.time())
                        jobs.append((f'{i:032x}',key,ident,'{}','READY',now,now))
                        view,vh=materialize_preview((key,raw,h,view,vh),now+86400)
                        entries.append((key,ident,other['source_revision'],h,raw,now,now+86400,now));views.append((key,h,key,vh,view))
                    # Archival stress corpus intentionally bypasses normal queue128/cache256 retention.
                    # It is not a claim that normal enqueue policy accepts100k jobs.
                    with transaction(con):
                        con.executemany('INSERT INTO cache_entries VALUES(?,?,?,?,?,?,?,?)',entries)
                        con.executemany('INSERT INTO cache_jobs(job_id,cache_key,identity_json,source_json,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',jobs)
                        con.executemany('INSERT INTO cache_previews VALUES(?,?,?,?,?)',views)
                    inserted+=len(jobs)
                args=(identity['source_revision'],'BTCUSDT','5m',identity['from_ms'],identity['to_ms'],ALGORITHM)
                con.execute('DROP INDEX '+EXACT_INDEX)
                baseline_sql=LOOKUP_SQL.replace(' INDEXED BY '+EXACT_INDEX,'')
                before_plan=[r[3] for r in con.execute('EXPLAIN QUERY PLAN '+baseline_sql,args)]
                baseline=measure(lambda:con.execute(baseline_sql,args).fetchall(),5)
                start=time.perf_counter();init_queue(con);index_build_ms=(time.perf_counter()-start)*1000
                plan=[r[3] for r in con.execute('EXPLAIN QUERY PLAN '+LOOKUP_SQL,args)]
                if not any('SEARCH j USING INDEX '+EXACT_INDEX in x for x in plan) or any('SCAN ' in x or 'TEMP B-TREE' in x for x in plan):raise ValueError('INDEX_REQUIRED')
                def hit():
                    r=lookup_exact_cache(path,identity['source_revision'],'BTCUSDT','5m',identity['from_ms'],identity['to_ms'])
                    if r['state']!='READY':raise ValueError('EXPECTED_HIT')
                def miss():
                    if lookup_exact_cache(path,'c'*64,'BTCUSDT','5m',identity['from_ms'],identity['to_ms'])['state']!='MISS':raise ValueError('EXPECTED_MISS')
                results.append(dict(records=total,cache_entries=con.execute('SELECT count(*) FROM cache_entries').fetchone()[0],baseline_sql=baseline,baseline_plan=before_plan,index_build_ms=index_build_ms,hit=measure(hit,samples),miss=measure(miss,samples),plan=plan))
        finally:con.close()
    return results

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def source_ok(expected):
    return re.fullmatch('[0-9a-f]{40}',expected) and subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()==expected and not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()

def prepare_preview(folder):
    """Create a fresh, consistent SYNTHETIC provider and cache for manual UI checks."""
    from terminan.saved_sources import demo_config
    folder=Path(folder)
    if folder.exists():raise ValueError('NEW_DIRECTORY_REQUIRED')
    folder.mkdir(parents=True)
    config=demo_config();spec=config['sources'][0];original=json.loads(Path(spec['path']).read_text(encoding='utf8'))
    identity,source=fixture();candles=[];footprint=[]
    for row in source['candles']:candles.append(dict(original['datasets']['candles_1m'][0],**row,delta=1,trade_count=3,poc_price=100))
    for row in source['footprint']:footprint.append(dict(original['datasets']['footprint_1m'][0],**row,volume=3,delta=1,buy_count=2,sell_count=1))
    original.update(as_of_ms=identity['to_ms']+60000,datasets=dict(candles_1m=candles,footprint_1m=footprint))
    snapshot=folder/'snapshot.json';snapshot.write_bytes(canonical(original));revision=sha(snapshot)
    identity['source_revision']=source['source_revision']=revision
    spec.update(id='audit-fixture',path=str(snapshot.resolve()))
    (folder/'sources.json').write_bytes(canonical(dict(version=1,sources=[spec])))
    (folder/'identity.json').write_bytes(canonical(identity));(folder/'input.json').write_bytes(canonical(source))
    con=init_queue(open_cache(folder/'cache.sqlite'))
    try:
        job=submit(con,identity,source)
        if run_once(con)['state']!='FINISHED':raise ValueError('PREVIEW_PREPARE_FAILED')
        if lookup_exact_cache(folder/'cache.sqlite',revision,'BTCUSDT','5m',identity['from_ms'],identity['to_ms'])['state']!='READY':raise ValueError('PREVIEW_PREPARE_FAILED')
    finally:con.close()
    return dict(state='READY_OFFLINE_SYNTHETIC',source_revision=revision,job_id=job['job_id'],algorithm=ALGORITHM)

def main():
    p=argparse.ArgumentParser();p.add_argument('--sha',required=True);choice=p.add_mutually_exclusive_group(required=True);choice.add_argument('--out');choice.add_argument('--prepare-preview');p.add_argument('--shell-version',default='NOT_SUPPLIED');p.add_argument('--samples',type=int,default=20);a=p.parse_args()
    if a.prepare_preview:
        try:
            if not source_ok(a.sha):raise ValueError()
            print(json.dumps(prepare_preview(a.prepare_preview)));return 0
        except Exception:print('PREVIEW_PREPARE_FAILED');return 50
    out=Path(a.out)
    if out.exists():print('EVIDENCE_ALREADY_EXISTS');return 50
    out.mkdir(parents=True);summary=dict(version=1,candidate_sha=a.sha,invocation=uuid.uuid4().hex,created_at_utc=datetime.now(timezone.utc).isoformat(),result='FAIL',exit_code=50,physical='PENDING',mode='OFFLINE_SYNTHETIC_TEMP_SQLITE',python=platform.python_version(),sqlite=sqlite3.sqlite_version,os=platform.system(),powershell=a.shell_version,run_id=__import__('os').environ.get('GITHUB_RUN_ID','LOCAL'),attempt=__import__('os').environ.get('GITHUB_RUN_ATTEMPT','1'),failure_stage='source',error_class='SOURCE_MISMATCH')
    try:
        if not source_ok(a.sha):raise ValueError()
        summary['failure_stage']='regressions';summary['error_class']='REGRESSION_FAILED';checks=[]
        for name,cmd in [('python-cache',[sys.executable,'-m','unittest','discover','-s','tests','-p','test*cache*.py','-v']),('node-cache',['node','tests/check_cache_race.cjs'])]:
            r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
            text=r.stdout.replace(str(ROOT),'<REPO>').replace(str(Path.home()),'<USER>')
            (out/(name+'.txt')).write_text(text,encoding='utf8')
            n=re.search(r'Ran (\d+) tests',text);tests=int(n[1]) if n else None
            checks.append(dict(name=name,exit_code=r.returncode,tests=tests))
            if r.returncode or name=='python-cache' and (tests is None or tests<43 or re.search(r'\bskipped\b',text)):raise ValueError()
        summary['checks']=checks;summary['failure_stage']='benchmark';summary['error_class']='PERFORMANCE_FAILED'
        results=benchmark(a.samples);(out/'benchmark.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n',encoding='utf8')
        # Local audit target, not an exchange/display SLA. Report every measured result.
        summary['lookup_p95_budget_ms']=50
        if any(r['hit']['p95_ms']>=50 or r['miss']['p95_ms']>=50 for r in results):raise ValueError()
        summary.update(result='AUTOMATED_AUDIT_PASS',exit_code=0,failure_stage=None,error_class=None)
    except KeyboardInterrupt:summary.update(error_class='CANCELLED')
    except Exception:pass
    finally:
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
        files=[dict(path=f.name,sha256=sha(f)) for f in sorted(out.iterdir()) if f.is_file()]
        temporary=out/'manifest.pending';temporary.write_text(json.dumps(files,indent=2)+'\n',encoding='utf8');temporary.replace(out/'manifest.json')
    print(json.dumps(summary));return summary['exit_code']
if __name__=='__main__':raise SystemExit(main())
