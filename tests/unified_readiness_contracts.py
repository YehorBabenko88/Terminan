"""Contract probes only: reuse qualified #59 evidence; never execute Math.

These passing tests document integration blockers, not a successful Unified E2E.
STRATTESTER_UNIFIED_REPO must be #66 c951b3f; CONTROL_EVIDENCE is the downloaded
exact-head #59 CI artifact directory. No input is promoted to source authenticity.
"""
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from terminan.history_overlay import admit, canonical
from terminan import math_bridge

ROOT=Path(__file__).resolve().parents[1]
STRAT=Path(os.environ.get('STRATTESTER_UNIFIED_REPO',ROOT.parent/'readiness-strattester'))
EVIDENCE=Path(os.environ.get('CONTROL_EVIDENCE',ROOT.parent/'readiness-evidence/terminan59'))
CONTROL='eafdc320a9bdb218d4bbadc3c590f98906932689'
PRODUCER='c951b3f711780affc8e6936f75fe3796d8ef99eb'

def seal(p):
    p['handoff_sha256']=hashlib.sha256(canonical({k:v for k,v in p.items() if k!='handoff_sha256'})).hexdigest()
    return p

class UnifiedReadinessContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if subprocess.check_output(['git','-C',str(STRAT),'rev-parse','HEAD'],text=True).strip()!=PRODUCER:
            raise RuntimeError('EXACT_PRODUCER_REQUIRED')
        if (EVIDENCE/'consumer-head.txt').read_text().strip()!=CONTROL:
            raise RuntimeError('EXACT_CONTROL_EVIDENCE_REQUIRED')
        report=json.loads((EVIDENCE/'history-browser.json').read_bytes())
        if report['stats']['expected']!=18 or any(report['stats'][k] for k in ('skipped','unexpected','flaky')):
            raise RuntimeError('QUALIFIED_CONTROL_REPORT_REQUIRED')
        sys.path.insert(0,str(STRAT))
        cls.review=importlib.import_module('strattester.research.history_terminan').review_packet
        cls.export=importlib.import_module('strattester.research.history_scientific_handoff').handoff_packet
        cls.result=json.loads((EVIDENCE/'history-evidence/result-0.json').read_bytes())
        cls.packet=cls.export(cls.review(cls.result,cls.result['completion_receipt']))

    def test_real_66_export_is_rejected_for_lost_market_identity(self):
        self.assertEqual(self.packet['market']['identity'],'fixture')
        self.assertNotIn('symbol',self.packet['market'])
        with self.assertRaisesRegex(ValueError,'MARKET_IDENTITY_REQUIRED'):
            admit(canonical(self.packet))

    def test_market_only_diagnostic_correction_still_loses_model_and_timed_oos(self):
        p=copy.deepcopy(self.packet)
        p['market']=self.result['market']  # test-only isolation of the second blocker
        r=admit(canonical(seal(p)))
        self.assertEqual(len(r['layers'][0]['points']),60)
        self.assertEqual(r['metadata']['model_version'],'UNKNOWN')
        self.assertIsNone(r['oos'])
        for k in ('model','model_version','split_receipts','oos_available_at_ms'):
            self.assertNotIn(k,self.packet)

    def test_joint_result_has_no_existing_review_or_display_adapter(self):
        # Schema probe, not a fabricated numerical engine response.
        p={'schema':'math.history.scientific.result.v1','evidence_class':'SYNTHETIC',
            'source_authenticity':'UNATTESTED','execution_authority':False,
            'training_authorized':False,'trading_authorized':False}
        with self.assertRaisesRegex(ValueError,'REVIEW_SCHEMA'):
            type(self).review(p,'0'*64)
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_SCHEMA'):
            admit(canonical(p))

    def test_legacy_http_bridge_rejects_unified_delayed_publication(self):
        q={'schema':'math.scientific.graph.v2','mode':'HISTORICAL_RESEARCH',
           'execution_authority':False,'asOf':61000,'nodes':[{'id':'history'}],
           'edges':[],'outputs':[{'node':'history','port':'value'}]}
        # Wire-contract fixture, not source or engine qualification evidence.
        response={'schema':'math.scientific.result.v2','status':'RESEARCH_ONLY',
            'source':'CALLER_SUPPLIED_UNATTESTED','requestSHA256':'a'*64,
            'execution_authority':False,'training_authorized':False,'trading_authorized':False,
            'mathematicallyVerified':False,'order':['history'],'trace':[{'node':'history'}],
            'outputs':[{'node':'history','port':'value','type':'series','unit':'USDT/BTC',
                'values':[101.0],'timestamps':[60000],'availableAt':[61000]}]}
        with patch.dict(os.environ,{'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}), \
             patch.object(math_bridge,'scientific_urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
            with self.assertRaisesRegex(ValueError,'UNTRUSTED_GRAPH_RESULT'):
                math_bridge.execute_scientific(json.dumps(q).encode())

    def test_new_engine_pin_is_correctly_denied_before_qualification(self):
        p={'schema':'terminan.scientific-overlay.v1','evidence_class':'SYNTHETIC',
           'source_authenticity':'UNATTESTED','execution_authority':False,
           'training_authorized':False,'trading_authorized':False,
           'history_binding':{k:self.packet.get(k,self.packet['source'].get(k)) for k in
               ('dataset_id','snapshot_fingerprint','market','units')},
           'engine':{'repository':'YehorBabenko88/math','commit':'03d31f55dc38c43b044666d712524219eb47a51e','api_revision':'2.1'}}
        p['history_binding']['market']=self.result['market']
        p['packet_sha256']=hashlib.sha256(canonical(p)).hexdigest()
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ENGINE_PIN'):
            admit(canonical(p))
