"""Real offline producer chain. Refuse mismatched/dirty upstream code; never use DBs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

PINS={'grid':'28d4ae46c8ddbc0238b351e8d6b2bd29c6602ef2',
      'math':'3a9c542841e160f8b1924f155aaa2d1a676dfd04',
      'strattester':'2669c433333b811b0eaedf88ea13b0e955b0836b',
      'scientific':'1f97e56701c0fce01dc8dd05952111fa8df3f2d1'}

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def main():
    parser=argparse.ArgumentParser()
    for name in PINS:parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    a=parser.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    roots={k:getattr(a,k).resolve() for k in PINS}
    for k,root in roots.items():
        if git(root,'rev-parse','HEAD')!=PINS[k] or git(root,'status','--porcelain','--untracked-files=no'):
            raise ValueError('UPSTREAM_PIN_OR_DIRTY:'+k)
    os.environ['GRID_REFERENCE']=str(roots['grid']);os.environ['MATH_REFERENCE']=str(roots['math'])
    os.environ['HISTORY_REQUIRE_CROSSREPO']='1'
    sys.path.insert(0,str(roots['strattester']))
    spec=importlib.util.spec_from_file_location('overlay_fixture',roots['strattester']/'tests/research/test_grid_math_history_v11.py')
    f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
    from strattester.research.grid_math_history import replay
    evidence=[];packets=[]
    for i,fee in enumerate((5.,10.)):
        d=f.dataset();policy=f.policy();policy['fee_bps']=fee
        with f.client() as client:r=replay(d,d['dataset_fingerprint'],client,policy)
        result=out/f'result-{i}.json';result.write_bytes(canonical(r))
        target=out/f'history-{i}.json'
        env={**os.environ,'PYTHONPATH':str(roots['strattester'])}
        subprocess.run([sys.executable,str(roots['strattester']/'scripts/export_history_scientific_handoff.py'),
            '--input',str(result),'--receipt-pin',r['completion_receipt'],'--output',str(target)],env=env,check=True)
        packet=json.loads(target.read_bytes());packets.append(packet)
        if len(packet['forecast_points'])<3:raise ValueError('INSUFFICIENT_REAL_FORECASTS')
        evidence.append({'file':target.name,'file_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'handoff_sha256':packet['handoff_sha256'],'forecast_count':len(packet['forecast_points']),
            'fee_bps':fee,'result_receipt':r['completion_receipt']})
    p=packets[0];rows=p['observed_prices']
    # Preserve event and availability axes exactly. The pinned synthetic dataset has a==event.
    request={'schema':'math.scientific.graph.v2','mode':'HISTORICAL_RESEARCH','execution_authority':False,
        'asOf':max(r['available_at_ms'] for r in rows),
        'nodes':[{'id':'source','kind':'source','type':'series','unit':p['units']['price'],
            'values':[r['value'] for r in rows],'timestamps':[r['event_end_ms'] for r in rows],
            'availableAt':[r['available_at_ms'] for r in rows],
            'provenance':{'sourceId':p['dataset_id'],'version':p['snapshot_fingerprint'],'sha256':p['snapshot_fingerprint']}},
            {'id':'mean','kind':'rolling-mean','window':3},
            {'id':'affine','kind':'formula','expression':'x*1.01','outputUnit':p['units']['price']}],
        'edges':[{'from':{'node':'source','port':'value'},'to':{'node':n,'port':'x'}} for n in ('mean','affine')],
        'outputs':[{'node':n,'port':'value'} for n in ('mean','affine')]}
    req=out/'scientific-request.json';req.write_bytes(canonical(request))
    # Execute the actual pinned engine, no browser or Python reimplementation of mathematics.
    engine=(roots['scientific']/'src/scientific-engine.mjs').as_uri()
    code="import fs from 'node:fs';import {executeScientificGraph} from "+json.dumps(engine)+";process.stdout.write(JSON.stringify(executeScientificGraph(JSON.parse(fs.readFileSync(process.argv[1],'utf8')))));"
    result=json.loads(subprocess.check_output(['node','--input-type=module','-e',code,str(req)]))
    wrapper={'schema':'terminan.scientific-overlay.v1','evidence_class':'SYNTHETIC','source_authenticity':'UNATTESTED',
        'execution_authority':False,'trading_authorized':False,'training_authorized':False,
        'history_binding':{k:p[k] for k in ('dataset_id','snapshot_fingerprint','market','units')},
        'engine':{'repository':'YehorBabenko88/math','commit':PINS['scientific'],'api_revision':'2.1'},
        'request':request,'result':result}
    wrapper['packet_sha256']=digest(wrapper)
    scientific=out/'scientific.json';scientific.write_bytes(canonical(wrapper))
    manifest={'schema':'terminan.overlay-evidence.v1','pins':PINS,'trees':{k:git(v,'rev-parse','HEAD^{tree}') for k,v in roots.items()},
        'python_sha256':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        'history':evidence,'scientific_file_sha256':hashlib.sha256(scientific.read_bytes()).hexdigest(),
        'scientific_request_sha256':result['requestSHA256'],'scientific_packet_sha256':wrapper['packet_sha256'],
        'source_authenticity':'UNATTESTED','execution_authority':False}
    (out/'manifest.json').write_bytes(canonical(manifest))
    print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
