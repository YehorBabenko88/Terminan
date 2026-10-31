import copy
import io
import json
import os
import unittest
from unittest.mock import patch
from terminan import math_bridge

class DelayedContractTests(unittest.TestCase):
    def response(self):
        return {'schema':'math.scientific.result.v2','status':'RESEARCH_ONLY','source':'CALLER_SUPPLIED_UNATTESTED',
            'requestSHA256':'a'*64,'execution_authority':False,'training_authorized':False,'trading_authorized':False,
            'mathematicallyVerified':False,'order':['history'],'trace':[{'node':'history'}],
            'outputs':[{'node':'history','port':'value','type':'series','unit':'USDT/BTC','values':[101],
                'timestamps':[60000],'availableAt':[60500]}]}
    def invoke(self,r):
        q={'schema':'math.scientific.graph.v2','mode':'HISTORICAL_RESEARCH','execution_authority':False,
            'asOf':61000,'nodes':[{'id':'history'}],'edges':[],'outputs':[{'node':'history','port':'value'}]}
        with patch.dict(os.environ,{'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}),patch.object(math_bridge,'scientific_urlopen',return_value=io.BytesIO(json.dumps(r).encode())):
            return math_bridge.execute_scientific(json.dumps(q).encode())
    def test_delayed_publication_retains_both_original_axes(self):
        r=self.response();self.assertEqual(self.invoke(r)['outputs'],r['outputs'])
    def test_future_event_or_publication_still_fails(self):
        for axis in ('timestamps','availableAt'):
            r=self.response();r['outputs'][0][axis]=[61001]
            with self.subTest(axis=axis),self.assertRaises(ValueError):self.invoke(r)
