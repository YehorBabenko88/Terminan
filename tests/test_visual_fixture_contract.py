"""Exercise the actual visual generator against the strict consumer contract."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from terminan.infrastructure import validate

class VisualFixtureContract(unittest.TestCase):
 def test_generated_snapshot_is_readonly_and_contains_seven_nodes(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)/'fixture'
   subprocess.run([sys.executable,'scripts/prepare_visual_qa.py',str(root)],check=True,capture_output=True)
   raw=json.loads((root/'snapshot.json').read_text(encoding='utf8'))
   result=validate(raw)
   self.assertEqual(result['reason'],'SOURCE_UNATTESTED')
   self.assertEqual(len(result['nodes']),7)
   self.assertEqual(len({n['id'] for n in raw['fleet']['nodes']}),7)
   self.assertIs(result['execution_authorized'],False)
   self.assertIs(result['trading_authorized'],False)
   self.assertTrue((root/'cache.sqlite').is_file())
