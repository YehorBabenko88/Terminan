"""Independent report checks and SHA256 receipts, never source attestation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser()
p.add_argument('--expected-sha',required=True)
p.add_argument('--math-repo',required=True)
p.add_argument('--math-sha',required=True)
p.add_argument('--projects',default='chromium,firefox')
p.add_argument('--out',default='reports/math-evidence')
a=p.parse_args()
def git(*args,root='.'):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
if git('rev-parse','HEAD')!=a.expected_sha:raise SystemExit('HEAD_MISMATCH')
if git('rev-parse','HEAD',root=a.math_repo)!=a.math_sha:raise SystemExit('MATH_HEAD_MISMATCH')
if git('status','--porcelain','--untracked-files=no') or git('status','--porcelain','--untracked-files=no',root=a.math_repo):raise SystemExit('DIRTY_TRACKED_SOURCE')
r=json.loads(Path('reports/math-browser.json').read_text(encoding='utf-8-sig'))
meta=r.get('config',{}).get('metadata',{})
if meta.get('source_head')!=a.expected_sha or meta.get('source_tree')!=git('rev-parse','HEAD^{tree}') or meta.get('math_head')!=a.math_sha:raise SystemExit('REPORT_SOURCE_MISMATCH')
cases=[]
def visit(suites):
    for suite in suites:
        for spec in suite.get('specs',[]):
            for test in spec['tests']:
                results=test.get('results',[])
                if len(results)!=1 or results[0]['status']!='passed' or test.get('status')!='expected':raise SystemExit('BROWSER_NOT_PASS')
                cases.append({'name':spec['title'],'project':test['projectName']})
        visit(suite.get('suites',[]))
visit(r['suites'])
projects=a.projects.split(',')
if sorted(set(c['project'] for c in cases))!=sorted(projects):raise SystemExit('BROWSER_PROJECT_MISSING')
if any(sum(c['project']==project for c in cases)<11 for project in projects):raise SystemExit('BROWSER_CASES_MISSING')
if any(not any(c['project']==project and c['name'].startswith('real pinned Math') for c in cases) for project in projects):raise SystemExit('REAL_ENGINE_CASE_MISSING')
if r.get('errors') or r['stats'].get('unexpected') or r['stats'].get('skipped'):raise SystemExit('BROWSER_ERRORS')
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
summary=dict(schema='terminan.math-evidence.v1',head=a.expected_sha,tree=git('rev-parse','HEAD^{tree}'),
             math_head=a.math_sha,math_tree=git('rev-parse','HEAD^{tree}',root=a.math_repo),cases=cases,
             scope='CONTROLLED_UI_PROTOCOL_AND_REAL_OFFLINE_MATH',source_authenticity='UNATTESTED',
             physical_ADMINIT='USER_REPORTED_ORIGINAL_RECEIPT_NOT_AVAILABLE',isolated_reproduction='AUTOMATED_REAL_MATH_BROWSER_TEST',installed_ADMINIT_changes=False,execution_authority=False,trading_authorized=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
paths=[Path('reports/math-browser.json'),out/'summary.json']
paths.extend(x for x in (Path('reports/python-math.txt'),Path('reports/python-all.txt'),Path('reports/graph-unit.txt')) if x.exists())
manifest={str(x).replace('\\','/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
(out/'sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'state':'PASS','cases':len(cases),'scope':summary['scope'],'head':a.expected_sha}))
