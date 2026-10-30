"""Exact-head visual matrix orchestration. Only synthetic fixtures and owned processes."""
import argparse,hashlib,json,os,subprocess,sys,uuid,struct,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from terminan.unified_process import run_browser
from terminan.unified_evidence import atomic_json
TITLE='visual matrix semantics and retained workspace state'
PROJECTS=['chromium-dpr1','chromium-dpr1.5','chromium-dpr2']
def validate_report(report,sha,tree,invocation):
 try:
  meta=report['config']['metadata']
  if any(meta.get(k)!=v for k,v in dict(source_sha=sha,tree=tree,invocation=invocation,zoom_method='CHROME_TABS_SETZOOM_GETZOOM').items()):raise ValueError()
  if report.get('errors'):raise ValueError()
  stats=report['stats']
  if any(type(stats.get(k)) is not int or stats[k]!=v for k,v in dict(expected=3,unexpected=0,skipped=0,flaky=0).items()):raise ValueError()
  found=[]
  def walk(suite):
   for spec in suite.get('specs',[]):
    if spec.get('title')!=TITLE:raise ValueError()
    for test in spec['tests']:
     results=test['results']
     if test.get('expectedStatus')!='passed' or test.get('status')!='expected' or len(results)!=1 or results[0].get('status')!='passed' or results[0].get('errors') or results[0].get('error'):raise ValueError()
     found.append(test['projectName'])
   for child in suite.get('suites',[]):walk(child)
  for suite in report['suites']:walk(suite)
  if sorted(found)!=PROJECTS:raise ValueError()
 except (KeyError,TypeError,ValueError,AttributeError,RecursionError):raise ValueError('BROWSER_INCOMPLETE_OR_UNBOUND') from None

def validate_metrics(reports,sha,tree,invocation):
 if len(reports)!=3:raise ValueError('METRICS_INCOMPLETE')
 projects=[];total=0
 for r in reports:
  if any(r.get(k)!=v for k,v in dict(source_sha=sha,tree=tree,invocation=invocation).items()):raise ValueError('METRICS_UNBOUND')
  projects.append(r['project']);rows=r['rows'];expected={(w,h,z,route) for w,h in ((1280,720),(1920,1080)) for z in (1,1.5,2) for route in ('/','/saved','/math','/history-overlay','/monitor','/cache')}
  found=[]
  for row in rows:
   key=(row['size']['width'],row['size']['height'],row['zoom'],row['route']);found.append(key)
   name='terminal' if row['route']=='/' else row['route'][1:]
   if row.get('screenshot')!=str(key[0])+'x'+str(key[1])+'-zoom'+str(key[2])+'-'+name+'.png':raise ValueError('SCREENSHOT_UNBOUND')
   if row['scrollWidth']>row['width']+1 or row['controls'] or row['overlaps'] or row['replacementChars'] or row['actualZoom']!=row['zoom']:raise ValueError('VISUAL_REGRESSION')
   if abs(row['browser']['dpr']-r['dpr']*row['zoom'])>.001 or row['browser']['pinch']!=1:raise ValueError('ZOOM_NOT_VERIFIED')
  if len(found)!=36 or set(found)!=expected:raise ValueError('MATRIX_INCOMPLETE')
  if r['state_retention']!=dict(terminal=True,saved=True,lab=True) or r['page_errors'] or r['console_errors'] or len(r['pixel_parity'])!=3 or any(v.get('equal') is not True for v in r['pixel_parity']):raise ValueError('VISUAL_CHECKS_INCOMPLETE')
  total+=len(rows)
 if sorted(projects)!=PROJECTS:raise ValueError('METRICS_PROJECTS_INVALID')
 return total

def validate_png(file,width,height):
 try:
  raw=Path(file).read_bytes()
  if len(raw)>32*1024*1024 or raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError()
  pos=8;header=False;data=False;end=False
  while pos<len(raw):
   if pos+12>len(raw):raise ValueError()
   n=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];chunk=raw[pos+8:pos+8+n]
   if pos+12+n>len(raw) or zlib.crc32(kind+chunk)&0xffffffff!=struct.unpack('>I',raw[pos+8+n:pos+12+n])[0]:raise ValueError()
   if kind==b'IHDR':
    if header or n!=13 or struct.unpack('>II',chunk[:8])!=(width,height):raise ValueError()
    header=True
   if kind==b'IDAT':data=data or n>0
   if kind==b'IEND':
    if n or pos+12!=len(raw):raise ValueError()
    end=True
   pos+=n+12
  if not header or not data or not end:raise ValueError()
 except (OSError,ValueError,struct.error):raise ValueError('SCREENSHOT_MISSING_OR_INVALID') from None

def validate_screenshots(metric_files):
 count=0
 for file in metric_files:
  r=json.loads(file.read_text(encoding='utf8'));base=file.parent.resolve()
  for row in r['rows']:
   target=(base/row['screenshot']).resolve()
   if not target.is_relative_to(base):raise ValueError('SCREENSHOT_UNBOUND')
   validate_png(target,round(row['size']['width']*r['dpr']),round(row['size']['height']*r['dpr']));count+=1
  for name in ('monitor-unavailable.png','history-error.png'):
   validate_png(base/name,round(1920*r['dpr']),round(1080*r['dpr']));count+=1
 return count

def main():
 p=argparse.ArgumentParser();p.add_argument('--expected-sha',required=True);p.add_argument('--out',required=True);a=p.parse_args();os.chdir(ROOT)
 out=Path(a.out).resolve()
 try:out.mkdir(parents=True,exist_ok=False)
 except OSError:print('EVIDENCE_ROOT_UNAVAILABLE');return 50
 invocation=uuid.uuid4().hex;code=50;stage='source';error='SOURCE_MISMATCH';summary=dict(version=1,invocation=invocation,candidate_sha=a.expected_sha,tree=None,result='FAIL',physical='PENDING',scope='HEADLESS_CHROMIUM_REAL_TAB_ZOOM',exit_code=50,python=sys.version.split()[0],shell=os.environ.get('VISUAL_SHELL','DIRECT'))
 def redact(text):
  for private in (str(ROOT),str(out),str(Path.home())):text=text.replace(private.replace('\\','\\\\'),'<LOCAL>').replace(private,'<LOCAL>').replace(private.replace('\\','/'),'<LOCAL>')
  return text
 try:
  def git(*args):return subprocess.check_output(['git',*args],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
  sha=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');summary['tree']=tree
  if sha!=a.expected_sha or git('status','--porcelain'):raise ValueError()
  stage='browser';error='BROWSER_INCOMPLETE_OR_UNBOUND';code=31
  env={**os.environ,'VISUAL_EVIDENCE_ROOT':str(out),'VISUAL_INVOCATION':invocation,'VISUAL_PYTHON':sys.executable}
  run=run_browser(['node','node_modules/@playwright/test/cli.js','test','-c','playwright.visual.config.cjs'],env,timeout=660)
  (out/'browser-console.txt').write_text(redact((run.stdout+run.stderr).decode('utf8',errors='replace'))[:262144],encoding='utf8')
  file=out/'browser.json'
  if not file.is_file() or file.stat().st_size>16*1024*1024:raise ValueError()
  report=json.loads(file.read_text(encoding='utf8'));file.write_text(redact(json.dumps(report,ensure_ascii=False,indent=2))+'\n',encoding='utf8')
  if run.returncode:raise ValueError()
  validate_report(report,sha,tree,invocation)
  metric_files=[f for f in out.rglob('metrics.json') if f.stat().st_size<2*1024*1024]
  metrics=[json.loads(f.read_text(encoding='utf8')) for f in metric_files]
  total=validate_metrics(metrics,sha,tree,invocation)
  stage='evidence_finalize';error='SCREENSHOT_MISSING_OR_INVALID';code=50
  screenshots=validate_screenshots(metric_files)
  if screenshots!=114:raise ValueError()
  summary.update(screenshots_verified=screenshots)
  summary.update(result='AUTOMATED_VISUAL_PASS',exit_code=0,matrix_cases=total);code=0;stage=None;error=None
 except KeyboardInterrupt:code=130;error='CANCELLED'
 except Exception:pass
 finally:
  summary.update(exit_code=code,failure_stage=stage,error_class=error);atomic_json(out/'summary.json',summary)
  rows=[dict(path=f.relative_to(out).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='manifest.json'];atomic_json(out/'manifest.json',rows)
 print(json.dumps(dict(exit_code=code,result=summary['result'],invocation=invocation)));return code
if __name__=='__main__':raise SystemExit(main())
