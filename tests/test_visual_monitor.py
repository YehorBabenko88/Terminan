import unittest
from importlib.resources import files
from terminan.infrastructure import validate
from test_infrastructure import fixture
class VisualMonitorTests(unittest.TestCase):
 def test_admitted_snapshot_never_claims_missing_config(self):
  view=validate(fixture(7))
  self.assertEqual(view['state'],'AVAILABLE_UNVERIFIED')
  self.assertEqual(view['reason'],'SOURCE_UNATTESTED')
  self.assertFalse(view['execution_authorized']);self.assertFalse(view['trading_authorized'])
  self.assertEqual(view['source_provenance'],'UNVERIFIED')
 def test_monitor_text_has_no_replacement_glyph(self):
  html=files('terminan').joinpath('infrastructure.html').read_text(encoding='utf8')
  self.assertNotIn(chr(0xfffd),html)
if __name__=='__main__':unittest.main()
