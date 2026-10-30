import io,json,os,unittest
from unittest.mock import patch
from terminan import math_bridge
class UnitBridgeTests(unittest.TestCase):
 def test_units_delegate_to_selected_loopback_and_require_exact_descriptions(self):
  def upstream(req,**kwargs):
   self.assertEqual(req.full_url,'http://127.0.0.1:18788/v2/units/describe')
   return io.BytesIO(json.dumps(dict(schema='math.units.result.v1',units=[dict(unit='m^2',factor=1,dimensions=[2,0,0,0,0,0,0,0,0,0])],execution_authority=False,trading_authorized=False)).encode())
  with patch.dict(os.environ,{'TERMINAN_MATH_OFFLINE_BRIDGE':'1','TERMINAN_MATH_PORT':'18788'}),patch('terminan.math_bridge.scientific_urlopen',side_effect=upstream):
   r=math_bridge.describe_units(json.dumps(dict(schema='math.units.describe.v1',execution_authority=False,units=['m^2'])).encode());self.assertEqual(r['units'][0]['dimensions'][0],2)
 def test_authority_invalid_and_duplicate_unit_requests_reject(self):
  with patch.dict(os.environ,{'TERMINAN_MATH_OFFLINE_BRIDGE':'1'}):
   for d in [dict(schema='math.units.describe.v1',execution_authority=True,units=['m']),dict(schema='math.units.describe.v1',execution_authority=False,units=['m','m'])]:
    with self.assertRaises(ValueError):math_bridge.describe_units(json.dumps(d).encode())
