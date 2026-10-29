"""Invocation-bound browser evidence. Failure never turns into a zero exit."""
import argparse,base64,hashlib,json,os,re,shutil,subprocess,time,uuid
from datetime import datetime
from pathlib import Path
TITLE='saved history controls identity clusters research and cancellation'
PROJECTS=[f'{b}-dpr{d}' for b in ('chromium','firefox') for d in ('1','1.5','2')]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check_report(raw,source_sha,invocation,projects):
 try:
  if not re.fullmatch('[a-f0-9]{40}',source_sha) or not re.fullmatch('[a-f0-9]{32}',invocation):raise ValueError()
  meta=raw['config']['metadata']
  # Playwright adds CI context automatically. Its merge SHA is not our source SHA.
  if set(meta)-{'invocation','source_sha','actualWorkers','started_ms','ci'} or meta.get('invocation')!=invocation or meta.get('source_sha')!=source_sha or raw['errors']!=[]:raise ValueError()
  if 'ci' in meta and type(meta['ci']) is not dict:raise ValueError()
  started=meta['started_ms'];report_start=int(datetime.fromisoformat(raw['stats']['startTime'].replace('Z','+00:00')).timestamp()*1000)
  if type(started) is not int or not started<=report_start<=started+30000:raise ValueError()
  if 'actualWorkers' in meta and (type(meta['actualWorkers']) is not int or meta['actualWorkers']!=1):raise ValueError()
  if any(type(raw['stats'].get(k)) is not int or raw['stats'][k]!=v for k,v in dict(expected=len(projects),unexpected=0,skipped=0,flaky=0).items()):raise ValueError()
  tests=[]
  def walk(suites):
   for suite in suites:
    for spec in suite.get('specs',[]):
     if spec['title']!=TITLE or spec['file']!='saved.spec.cjs' or spec['ok'] is not True:raise ValueError()
     tests.extend(spec['tests'])
    walk(suite.get('suites',[]))
  walk(raw['suites'])
  if len(tests)!=len(projects) or sorted(t['projectName'] for t in tests)!=sorted(projects):raise ValueError()
  for t in tests:
   if t['projectId']!=t['projectName'] or t['expectedStatus']!='passed' or t['status']!='expected' or len(t['results'])!=1:raise ValueError()
   r=t['results'][0]
   if r['status']!='passed' or type(r['retry']) is not int or r['retry']!=0 or r.get('errors') or r.get('error'):raise ValueError()
  return tests
 except (KeyError,TypeError,AttributeError):raise ValueError() from None

def main():
 p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--sha',required=True);p.add_argument('--invocation',required=True);p.add_argument('--started-ms',required=True,type=int);p.add_argument('--out',required=True);p.add_argument('--scope',choices=['all','chromium'],default='all');args=p.parse_args()
 root=Path(args.out);pending=root.with_name(root.name+'.pending-'+uuid.uuid4().hex)
 if root.exists():return 50
 pending.mkdir(parents=True);ok=False
 try:
  repo=Path(__file__).resolve().parents[1]
  if not 0<=int(time.time()*1000)-args.started_ms<=15*60*1000:raise ValueError()
  if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()!=args.sha or subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip():raise ValueError()
  report=Path(args.report)
  if report.stat().st_size>16*1024*1024:raise ValueError()
  raw=json.loads(report.read_text(encoding='utf-8-sig'));tests=check_report(raw,args.sha,args.invocation,PROJECTS if args.scope=='all' else PROJECTS[:3])
  if raw['config']['metadata']['started_ms']!=args.started_ms or report.stat().st_mtime_ns//1000000<args.started_ms:raise ValueError()
  screenshots=[]
  allowed=(Path.cwd()/'saved-test-results').resolve()
  for t in tests:
   attachments=[a for a in t['results'][0]['attachments'] if a.get('name')=='saved-workspace' and a.get('contentType')=='image/png']
   if len(attachments)!=1:raise ValueError()
   a=attachments[0]
   if 'body' in a:
    if type(a['body']) is not str or len(a['body'])>6*1024*1024:raise ValueError()
    data=base64.b64decode(a['body'],validate=True)
   else:
    path=Path(a['path']).resolve()
    if not path.is_relative_to(allowed) or not path.is_file() or path.stat().st_size>4*1024*1024:raise ValueError()
    data=path.read_bytes()
   if len(data)>4*1024*1024 or data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError()
   name=t['projectName']+'.png';(pending/name).write_bytes(data);screenshots.append(name)
  fixtures=Path(__file__).with_name('fixtures')
  pins={f.name:sha(f) for f in fixtures.glob('saved-*.json')}
  (pending/'pins.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf8')
  (pending/'browser-report.json').write_text(json.dumps(dict(report_sha256=sha(report),projects=[t['projectName'] for t in tests],expected=len(tests),unexpected=0,skipped=0,interrupted=0,retries=0,screenshots=screenshots),indent=2)+'\n',encoding='utf8');ok=True
 except Exception:pass
 summary=dict(version=1,result='AUTOMATED_PASS' if ok else 'FAIL',exit_code=0 if ok else 50,physical='PENDING',candidate_sha=args.sha,invocation=args.invocation,run_id=os.environ.get('GITHUB_RUN_ID','LOCAL'),attempt=os.environ.get('GITHUB_RUN_ATTEMPT','1'),mode='SYNTHETIC',scope=args.scope,error_class=None if ok else 'INCOMPLETE_BROWSER_EVIDENCE')
 (pending/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
 manifest=[dict(path=f.name,sha256=sha(f)) for f in sorted(pending.iterdir())]
 (pending/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8');os.replace(pending,root)
 return summary['exit_code']
if __name__=='__main__':raise SystemExit(main())
