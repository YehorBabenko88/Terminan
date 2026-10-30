import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError
from terminan import math_bridge


def payload():
    return dict(schema='math.scientific.graph.v2', mode='HISTORICAL_RESEARCH',
                execution_authority=False, asOf=120000, nodes=[
                    dict(id='s', kind='source', type='series', unit='dimensionless',
                         values=[1, 2, 3], timestamps=[0, 60000, 120000], availableAt=[0, 60000, 120000],
                         provenance=dict(sourceId='manual', version='1', sha256='0'*64)),
                    dict(id='f', kind='formula', expression='x+1', outputUnit='dimensionless')],
                edges=[{'from':dict(node='s',port='value'),'to':dict(node='f',port='x')}], outputs=[dict(node='f', port='value')])


def result():
    return dict(schema='math.scientific.result.v2', status='RESEARCH_ONLY',
                requestSHA256='a'*64, source='CALLER_SUPPLIED_UNATTESTED',
                execution_authority=False, trading_authorized=False, training_authorized=False,
                mathematicallyVerified=False, order=['s', 'f'], trace=[dict(node='s'),dict(node='f')], outputs=[
                    dict(node='f', port='value', type='series', unit='dimensionless',
                         values=[2, 3, 4], timestamps=[0, 60000, 120000], availableAt=[0, 60000, 120000])])


class ScientificBridgeTests(unittest.TestCase):
    def call(self, d=None):
        return math_bridge.execute_scientific(json.dumps(d or payload()).encode())

    def test_forwards_only_to_fixed_loopback(self):
        def upstream(req, **kwargs):
            self.assertEqual(req.full_url, 'http://127.0.0.1:8788/v2/graph/execute')
            return io.BytesIO(json.dumps(result()).encode())
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}), patch('terminan.math_bridge.scientific_urlopen', side_effect=upstream):
            self.assertEqual(self.call()['outputs'][0]['values'], [2, 3, 4])

    def test_disabled_and_bad_authority_do_not_connect(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'BRIDGE_DISABLED'): self.call()
        d=payload();d['execution_authority']=True
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}):
            with self.assertRaises(ValueError): self.call(d)

    def test_nonobject_escalation_and_nonfinite_upstream_fail_closed(self):
        for r in [[], None, {**result(), 'trading_authorized':True}, {**result(), 'training_authorized':True},
                  {**result(), 'mathematicallyVerified':True}, {**result(), 'outputs':[dict(node='f',values=[float('nan')])]}]:
            with self.subTest(response=r), patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}), patch('terminan.math_bridge.scientific_urlopen', return_value=io.BytesIO(json.dumps(r).encode())):
                with self.assertRaises(ValueError): self.call()

    def test_upstream_limit_and_unavailability(self):
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}):
            with patch('terminan.math_bridge.scientific_urlopen', return_value=io.BytesIO(b' '*2097153)):
                with self.assertRaisesRegex(ValueError,'RESPONSE_LIMIT'): self.call()
            with patch('terminan.math_bridge.scientific_urlopen', side_effect=URLError('offline')):
                with self.assertRaisesRegex(ValueError,'MATH_ENGINE_UNAVAILABLE'): self.call()

    def test_semantic_error_preserved_without_details(self):
        from urllib.error import HTTPError
        error=HTTPError('http://127.0.0.1',422,'bad',{},io.BytesIO(b'{"schema":"math.error.v2","error":"INVALID_SCIENTIFIC_REQUEST","private":"secret"}'))
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}), patch('terminan.math_bridge.scientific_urlopen', side_effect=error):
            with self.assertRaisesRegex(ValueError,'INVALID_SCIENTIFIC_REQUEST'): self.call()

    def test_catalog_requires_non_authoritative_metadata(self):
        catalog=dict(schema='math.scientific.capabilities.v2', units=['m'],
                     unitMetadata=[dict(unit='m',dimensions=[1,0,0,0,0,0,0,0,0,0])],
                     dimensionBasis=['length','mass','time','current','temperature','amount','luminousIntensity','USD','USDT','BTC'],
                     execution_authority=False,training_authorized=False,trading_authorized=False,mathematicallyVerified=False)
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}), patch('terminan.math_bridge.scientific_urlopen', return_value=io.BytesIO(json.dumps(catalog).encode())):
            self.assertEqual(math_bridge.scientific_catalog()['unitMetadata'][0]['dimensions'][0],1)

    def test_unrelated_and_noncausal_responses_refused(self):
        for change in ('output','order','trace','time','availability'):
            r=result()
            if change=='output':r['outputs'][0]['node']='other'
            if change=='order':r['order']=[]
            if change=='trace':r['trace']=[]
            if change=='time':r['outputs'][0]['timestamps']=[120000,60000,0]
            if change=='availability':r['outputs'][0]['availableAt']=[60000,60000,120000]
            with self.subTest(change=change), patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}), patch('terminan.math_bridge.scientific_urlopen', return_value=io.BytesIO(json.dumps(r).encode())):
                with self.assertRaisesRegex(ValueError,'UNTRUSTED_GRAPH_RESULT'):self.call()

