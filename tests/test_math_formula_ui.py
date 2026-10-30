import subprocess
import unittest
from pathlib import Path

class FormulaUITests(unittest.TestCase):
    def test_browser_scripts_parse(self):
        root = Path(__file__).resolve().parents[1]
        for path in ('terminan/lab_graph.js', 'terminan/lab_ui.js', 'terminan/lab_catalog.js', 'terminan/lab_results.js','terminan/lab_protocol.js'):
            subprocess.run(['node', '--check', path], cwd=root, check=True, capture_output=True)
