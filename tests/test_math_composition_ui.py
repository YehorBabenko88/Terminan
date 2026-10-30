import subprocess
import unittest
from pathlib import Path

class MathGraphCompositionTests(unittest.TestCase):
    def test_freeform_document_behavior(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run(['node', '--test', 'tests/test_lab_graph.cjs'], cwd=root, check=True, capture_output=True)
