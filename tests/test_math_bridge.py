import json
import unittest
from unittest.mock import patch
from terminan import math_bridge

class MathBridgeTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(math_bridge.check()['state'], 'NOT_CONNECTED')
            with self.assertRaises(ValueError):
                math_bridge.evaluate(b'{}')

    def test_rejects_unsafe_contract_without_network(self):
        with patch.dict('os.environ', {'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}, clear=True):
            for body in [
                {'schema':'math.evaluate.v1','mode':'LIVE','execution_authority':False,'closes':[1]*500},
                {'schema':'math.evaluate.v1','mode':'HISTORICAL_RESEARCH','execution_authority':True,'closes':[1]*500},
                {'schema':'math.evaluate.v1','mode':'HISTORICAL_RESEARCH','execution_authority':False,'closes':[1]*499},
            ]:
                with self.assertRaises(ValueError):
                    math_bridge.evaluate(json.dumps(body).encode())

if __name__=='__main__':unittest.main()
