"""Exact-invocation browser gate and atomic evidence publication."""
import hashlib,json,os
from pathlib import Path
TITLE='six workspaces preserve chart state and fail closed without engines'
def validate_browser(report,sha,tree,invocation):
    try:
        meta=report['metadata']
        if any(meta.get(k)!=v for k,v in dict(source_sha=sha,tree=tree,invocation=invocation).items()):raise ValueError()
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
        if sorted(found)!=['chromium-dpr1','chromium-dpr1.5','chromium-dpr2']:raise ValueError()
        return len(found)
    except (KeyError,TypeError,ValueError,AttributeError,RecursionError):raise ValueError('BROWSER_INCOMPLETE_OR_UNBOUND') from None

def atomic_json(path,value):
    path=Path(path);temp=path.with_name(path.name+'.tmp')
    with temp.open('x',encoding='utf8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
def seal(root):
    files=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(Path(root).iterdir()) if p.is_file() and p.name!='manifest.json']
    atomic_json(Path(root)/'manifest.json',files)
def verify_previous(root,sha,tree):
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text(encoding='utf8'))
    names=set()
    for row in manifest:
        name=row['path']
        if not isinstance(name,str) or Path(name).name!=name or name in names:raise ValueError('PRIOR_EVIDENCE_INVALID')
        names.add(name)
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('PRIOR_EVIDENCE_INVALID')
    if not {'summary.json','browser.json','smoke.json','shutdown.json'}<=names:raise ValueError('PRIOR_EVIDENCE_INCOMPLETE')
    s=json.loads((root/'summary.json').read_text(encoding='utf8'))
    if s['result']!='AUTOMATED_PASS' or s['exit_code']!=0 or s['review_seconds']!=15 or s['candidate_sha']!=sha or s['tree']!=tree:raise ValueError('PRIOR_SMOKE_REQUIRED')
    validate_browser(json.loads((root/'browser.json').read_text(encoding='utf8')),sha,tree,s['invocation'])
