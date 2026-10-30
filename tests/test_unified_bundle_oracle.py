"""Test the future evidence oracle, not an engine or hosted qualification.

Inert miniature records below are synthetic test doubles, never accepted as real
pipeline/CI proof. Literal values test preservation, not scientific correctness.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tests.check_unified_e2e_bundle import check

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def signed(v,key):return {**v,key:digest(v)}

def fixture():
    flags=dict(execution_authority=False,training_authorized=False,trading_authorized=False)
    rows=[dict(event_end_ms=60000,watermark_ms=60000,available_at_ms=61000,close=101)]
    model=dict(commit='a'*40,tree='b'*40,manifest={'src/a.mjs':'c'*64,'python/a.py':'d'*64})
    market=dict(venue='bybit',market_type='linear',symbol='BTCUSDT')
    provenance=dict(dataset_id='e'*64,dataset_fingerprint='f'*64,rows=rows,market=market,
        source={'identity':'fixture','source_revision':'c'*40,'epoch':'test'},units={'price':'USDT/BTC','volume':'BTC'},decision_ms=61000)
    q=dict(schema='math.history.scientific.request.v1',history=copy.deepcopy(provenance),graph={})
    out=dict(node='twice',port='value',type='series',unit='USDT/BTC',values=[202],timestamps=[60000],availableAt=[61000])
    scalar=dict(node='comparison',port='mae',type='scalar',values=[0])
    trace=[dict(decision_ms=d,forecast_target_event_end_ms=t,forecast=v) for d,t,v in [(61000,120000,102),(121000,180000,103),(181000,240000,104)]]
    h=dict(feature_event_end_ms=60000,feature_available_at_ms=61000,forecast_target_event_end_ms=120000,forecast=102,prefix_digest=digest(rows),request_digest=digest(q['history']))
    grid=dict(dataset_id='e'*64,dataset_fingerprint='f'*64,rows=rows,source=provenance['source'],request={**market,'units':provenance['units']})
    joint=signed(dict(schema='math.history.scientific.result.v1',api_revision='history-1.1+scientific-2.1',
        request_digest=digest(q),provenance=provenance,history=h,scientific={'outputs':[out,scalar]},math_source=model,**flags),'completion_receipt')
    replay_model={**model,'manifest':{'python/a.py':'d'*64}}
    replay=signed(dict(dataset_id=grid['dataset_id'],market=market,math=replay_model,math_trace=trace,splits={'test':{'end_ms':240000,'metrics':{'net_pnl':7}}},**flags),'completion_receipt')
    handoff=signed(dict(dataset_id=grid['dataset_id'],snapshot_fingerprint=grid['dataset_fingerprint'],market=market,
        forecast_points=[dict(decision_ms=x['decision_ms'],target_event_end_ms=x['forecast_target_event_end_ms'],value=x['forecast'],
            feature_event_end_ms=x['decision_ms']-1000,feature_available_at_ms=x['decision_ms'],request_digest=digest({'decision':x['decision_ms']})) for x in trace],**flags),'handoff_sha256')
    admitted=dict(authenticity='UNATTESTED',layers=[dict(label='twice:value',kind='scientific',unit='USDT/BTC',points=[dict(time=60000,available=61000,value=202)])],
        diagnostics=[dict(node='comparison',port='mae',values=[0],kind='DESCRIPTIVE_NOT_OOS')],oos={'available':240000,'metrics':{'net_pnl':7}})
    admitted['layers'].append({'kind':'forecast','points':[dict(time=p['target_event_end_ms'],available=p['feature_available_at_ms'],
        decision=p['decision_ms'],feature_event=p['feature_event_end_ms'],value=p['value'],request_digest=p['request_digest']) for p in handoff['forecast_points']]})
    report={'errors':[],'suites':[{'specs':[{'tests':[{'projectName':b,'status':'expected','results':[{'status':'passed'}]} for b in ('chromium','firefox')]} for _ in range(9)]}],
        'stats':{'expected':18,'skipped':0,'unexpected':0,'flaky':0}}
    coverage=dict(status='PASS',requiredCells=6,postgresCells=4,windowsCells=2,head=model['commit'],tree=model['tree'],runId='123',attempt='1')
    return {'grid.json':grid,'joint.json':joint,'joint-request.json':q,'replay.json':replay,'handoff.json':handoff,'admitted.json':admitted,'browser.json':report,'qualification/full-ci-coverage.json':coverage}

class BundleOracleTests(unittest.TestCase):
    def run_check(self,files,omit_pin=None):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,v in files.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding='utf-8')
            math={'head':'a'*40,'tree':'b'*40,'run_id':'123','attempt':'1'}
            manifest={'schema':'terminan.unified-e2e.v1','math':math,
                'coverage_report_sha256':hashlib.sha256((root/'qualification/full-ci-coverage.json').read_bytes()).hexdigest(),
                'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files if n!=omit_pin}}
            (root/'manifest.json').write_text(json.dumps(manifest))
            return check(root)

    def test_preserved_capture_is_checked_without_qualifying_its_source(self):
        self.assertEqual(self.run_check(fixture())['state'],'CAPTURED_PIPELINE_ASSERTIONS_PASS_NOT_SOURCE_QUALIFICATION')

    def test_missing_input_hash_is_not_allowed_to_escape_the_manifest(self):
        with self.assertRaises(AssertionError):self.run_check(fixture(),omit_pin='joint.json')

    def test_changed_joint_request_is_rejected_even_with_rehashed_file_manifest(self):
        f=fixture();f['joint-request.json']['graph']={'changed':True}
        with self.assertRaises(AssertionError):self.run_check(f)

    def test_nonmatching_forecasts_and_oos_classification_are_rejected(self):
        for mutate in (lambda f:f['handoff.json']['forecast_points'][1].update(value=999),
                       lambda f:f['admitted.json']['diagnostics'][0].update(kind='OOS')):
            f=fixture();mutate(f)
            with self.subTest(mutate=mutate),self.assertRaises(AssertionError):self.run_check(f)

    def test_admitted_forecasts_cannot_be_missing_duplicated_or_substituted(self):
        for mutate in (lambda p:p.clear(),lambda p:p.append(copy.deepcopy(p[0])),lambda p:p[0].update(value=999)):
            f=fixture();mutate(f['admitted.json']['layers'][1]['points'])
            with self.subTest(mutate=mutate),self.assertRaises(AssertionError):self.run_check(f)

    def test_rehashed_request_cannot_disagree_with_returned_provenance(self):
        f=fixture();q=f['joint-request.json'];q['history']['rows'][0]['close']=999
        j=f['joint.json'];j['request_digest']=digest(q)
        j['history']['request_digest']=digest(q['history'])
        j['completion_receipt']=digest({k:v for k,v in j.items() if k!='completion_receipt'})
        with self.assertRaises(AssertionError):self.run_check(f)
