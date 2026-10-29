import json
import unittest
from unittest.mock import patch
from terminan import math_bridge

def graph():
    return {'schema':'math.graph.execute.v1','mode':'HISTORICAL_RESEARCH',
      'execution_authority':False,'nodes':[
        {'id':'a','kind':'source','values':[1,2,3]},
        {'id':'b','kind':'source','values':[3,4,5]},
        {'id':'d','kind':'transform','adapter':'series-difference','inputs':['a','b'],'parameters':{}},
        {'id':'energy','kind':'transform','adapter':'comparison-energy','inputs':['d'],'parameters':{}},
      ]}

class MathGraphBridgeTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(ValueError):
                math_bridge.execute_graph(json.dumps(graph()).encode())
    def test_live_and_oversized_graph_rejected(self):
        with patch.dict('os.environ',{'TERMINAN_MATH_OFFLINE_BRIDGE':'1'},clear=True):
            bad=graph();bad['execution_authority']=True
            with self.assertRaises(ValueError):math_bridge.execute_graph(json.dumps(bad).encode())
            bad=graph();bad['nodes']=[bad['nodes'][0]]*13
            with self.assertRaises(ValueError):math_bridge.execute_graph(json.dumps(bad).encode())

if __name__=='__main__':unittest.main()
