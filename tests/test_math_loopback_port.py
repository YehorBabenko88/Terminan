import os
import unittest
from unittest.mock import patch
from terminan import math_bridge
class LoopbackPortTests(unittest.TestCase):
 def test_optional_port_is_loopback_only(self):
  with patch.dict(os.environ,{'TERMINAN_MATH_PORT':'18788'}):self.assertEqual(math_bridge.engine_url(),'http://127.0.0.1:18788')
  for raw in ['0','65536','http://evil','-1','8788/path','']:
   with patch.dict(os.environ,{'TERMINAN_MATH_PORT':raw}):
    with self.assertRaises(ValueError):math_bridge.engine_url()
class LegacyPortRoutingTests(unittest.TestCase):
 def test_all_legacy_calls_use_the_selected_loopback_port(self):
  import io,json
  calls=[]
  def upstream(req,**kwargs):
   url=req if isinstance(req,str) else req.full_url;calls.append(url)
   if url.endswith('/healthz'):d={'schema':'math.engine.v1','state':'READY_OFFLINE','trading_authorized':False}
   else:d={'schema':'math.formula.result.v1' if url.endswith('/v1/formula') else 'math.result.v1' if url.endswith('/v1/evaluate') else 'math.graph.result.v1','source':'CALLER_SUPPLIED_UNATTESTED','execution_authority':False,'trading_authorized':False}
   return io.BytesIO(json.dumps(d).encode())
  with patch.dict(os.environ,{'TERMINAN_MATH_PORT':'18788','TERMINAN_MATH_OFFLINE_BRIDGE':'1'}),patch('terminan.math_bridge.urlopen',side_effect=upstream):
   math_bridge.check()
   def send(fn,d):fn(json.dumps(d).encode())
   send(math_bridge.evaluate,dict(schema='math.evaluate.v1',mode='HISTORICAL_RESEARCH',execution_authority=False,closes=[1]*500))
   send(math_bridge.execute_graph,dict(schema='math.graph.execute.v1',mode='HISTORICAL_RESEARCH',execution_authority=False,nodes=[]))
   send(math_bridge.execute_port_graph,dict(schema='math.port-graph.v1',execution_authority=False,nodes=[{},{}],edges=[]))
   send(math_bridge.evaluate_formula,dict(schema='math.formula.v1',execution_authority=False,values=[1,2],formula='x',inputUnit='dimensionless',outputUnit='dimensionless'))
  self.assertEqual(calls,['http://127.0.0.1:18788'+p for p in ['/healthz','/v1/evaluate','/v1/graph/execute','/v1/graph/ports','/v1/formula']])
