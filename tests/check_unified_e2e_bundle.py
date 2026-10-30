"""Prepared post-qualification oracle; never launches Math, DBs or browsers.

Invoke only AFTER independent hosted exact-head artifact verification. This
checks a captured real pipeline bundle, and cannot itself qualify the source.
No mathematical forecasts, transformations or OOS metrics are recalculated.
"""
import argparse
import hashlib
import json
from pathlib import Path

if not __debug__:
    raise RuntimeError('ASSERTIONS_REQUIRED: do not run this evidence oracle with python -O')

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def check(root):
    def read(name):return json.loads((root/name).read_bytes())
    m=read('manifest.json')
    assert m['schema']=='terminan.unified-e2e.v1'
    required={'grid.json','joint.json','joint-request.json','replay.json','handoff.json','admitted.json','browser.json','qualification/full-ci-coverage.json'}
    assert required<=set(m['files']),'mandatory captured file missing from hash manifest'
    # This path names separately verified hosted proof. A caller boolean is not evidence.
    coverage_raw=(root/'qualification/full-ci-coverage.json').read_bytes()
    assert hashlib.sha256(coverage_raw).hexdigest()==m['coverage_report_sha256']
    coverage=json.loads(coverage_raw)
    assert coverage['status']=='PASS' and coverage['requiredCells']==6
    assert (coverage['postgresCells'],coverage['windowsCells'])==(4,2)
    assert (coverage['head'],coverage['tree'])==(m['math']['head'],m['math']['tree'])
    assert (coverage['runId'],coverage['attempt'])==(m['math']['run_id'],m['math']['attempt'])
    for name,pin in m['files'].items():
        p=(root/name).resolve();assert p.is_relative_to(root.resolve()) and p.is_file()
        assert hashlib.sha256(p.read_bytes()).hexdigest()==pin,name
    grid,joint,replay,handoff,admitted=(read(n) for n in ('grid.json','joint.json','replay.json','handoff.json','admitted.json'))
    request=read('joint-request.json');qh=request['history']
    assert joint['request_digest']==digest(request)
    for k in ('dataset_id','dataset_fingerprint','source','market','units','decision_ms','rows'):
        assert qh[k]==joint['provenance'][k],k
    assert qh['source']==grid['source'] and qh['units']==grid['request']['units']
    assert qh['market']=={k:grid['request'][k] for k in ('venue','market_type','symbol')}
    assert joint['history']['request_digest']==digest(qh)
    for packet,key in ((joint,'completion_receipt'),(replay,'completion_receipt'),(handoff,'handoff_sha256')):
        assert packet[key]==digest({k:v for k,v in packet.items() if k!=key})
    assert joint['schema']=='math.history.scientific.result.v1'
    assert joint['api_revision']=='history-1.1+scientific-2.1'
    assert joint['provenance']['dataset_id']==grid['dataset_id']==replay['dataset_id']==handoff['dataset_id']
    assert joint['provenance']['dataset_fingerprint']==grid['dataset_fingerprint']==handoff['snapshot_fingerprint']
    for source in (joint['math_source'],replay['math']):
        assert (source['commit'],source['tree'])==(m['math']['head'],m['math']['tree'])
        assert any(k.startswith('python/') for k in source['manifest'])
    assert any(k.startswith('src/') for k in joint['math_source']['manifest'])
    assert all(k.startswith('python/') and joint['math_source']['manifest'].get(k)==v for k,v in replay['math']['manifest'].items())
    assert joint['provenance']['market']==replay['market']==handoff['market']
    d=joint['provenance']['decision_ms'];rows=joint['provenance']['rows']
    assert rows and rows==grid['rows'][:len(rows)]
    assert all(r['event_end_ms']<=r['watermark_ms']<=r['available_at_ms']<=d for r in rows)
    h=joint['history'];assert h['feature_event_end_ms']<=h['feature_available_at_ms']<=d<h['forecast_target_event_end_ms']
    assert h['prefix_digest']==digest(rows)
    frozen={(r['decision_ms'],r['target_event_end_ms']):r['value'] for r in handoff['forecast_points']}
    assert len(frozen)>=3
    assert frozen=={(r['decision_ms'],r['forecast_target_event_end_ms']):r['forecast'] for r in replay['math_trace']}
    assert frozen[(d,h['forecast_target_event_end_ms'])]==h['forecast']
    expected=[(r['feature_event_end_ms'],r['feature_available_at_ms'],r['decision_ms'],r['target_event_end_ms'],r['value'],r['request_digest']) for r in handoff['forecast_points']]
    actual=[(p['feature_event'],p['available'],p['decision'],p['time'],p['value'],p['request_digest']) for l in admitted['layers'] if l['kind']=='forecast' for p in l['points']]
    assert len(actual)==len(set(actual)),'duplicate admitted forecast'
    assert sorted(actual)==sorted(expected),'missing, substituted or unexpected admitted forecast'
    # Proposed normalized adapter contract: render series verbatim; scalars are diagnostics.
    for out in joint['scientific']['outputs']:
        if out['type']=='scalar':
            metric=next(x for x in admitted['diagnostics'] if (x['node'],x['port'])==(out['node'],out['port']))
            assert metric['values']==out['values'] and metric['kind']=='DESCRIPTIVE_NOT_OOS'
        else:
            layer=next(x for x in admitted['layers'] if x['label']==out['node']+':'+out['port'])
            assert layer['kind']=='scientific' and layer['unit']==out['unit']
            assert [p['time'] for p in layer['points']]==out['timestamps']
            assert [p['available'] for p in layer['points']]==out['availableAt']
            assert [p['value'] for p in layer['points']]==out['values']
    assert admitted['oos']['metrics']==replay['splits']['test']['metrics']
    assert admitted['oos']['available']>=max(replay['splits']['test']['end_ms'],max(r['available_at_ms'] for r in grid['rows']))
    for p in (joint,replay,handoff):
        assert all(p[k] is False for k in ('execution_authority','training_authorized','trading_authorized'))
    assert admitted['authenticity']=='UNATTESTED'
    report=read('browser.json');assert not report['errors']
    counts={}
    def visit(suite):
        for spec in suite.get('specs',[]):
            for test in spec['tests']:
                assert test['status']=='expected' and test['results']
                assert all(r['status']=='passed' for r in test['results'])
                counts[test['projectName']]=counts.get(test['projectName'],0)+1
        for child in suite.get('suites',[]):visit(child)
    for suite in report['suites']:visit(suite)
    assert counts.get('chromium',0)>=9 and counts.get('firefox',0)>=9
    assert report['stats']['expected']==sum(counts.values())
    assert all(report['stats'][k]==0 for k in ('skipped','unexpected','flaky'))
    return {'state':'CAPTURED_PIPELINE_ASSERTIONS_PASS_NOT_SOURCE_QUALIFICATION','browsers':counts}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',required=True,type=Path)
    args=p.parse_args();print(json.dumps(check(args.bundle)))
