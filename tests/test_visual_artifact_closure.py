"""The visual manifest's hidden files ship only from the owned evidence root."""
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def uploads():
    text = (ROOT / '.github/workflows/visual-qa.yml').read_text()
    return [dict(re.findall(r'^          ([\w-]+): (.+)$', block, re.M))
            for block in text.split('      - uses: actions/upload-artifact@v4')[1:]]


class VisualArtifactClosureTests(unittest.TestCase):
    def test_visual_upload_preserves_every_manifest_name_including_hidden_state(self):
        visual = next(item for item in uploads() if item['name'].startswith('visual-'))
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            owned = workspace / 'candidate/reports/visual-ci'
            owned.mkdir(parents=True)
            names = ['summary.json', 'browser.json', 'results/.last-run.json',
                     'results/chromium/metrics.json', 'results/chromium/preview.png']
            for name in names:
                path = owned / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'owned evidence')
            (owned / 'manifest.json').write_text(json.dumps([{'path': name} for name in names]))
            # A sibling outside the manifest root must never enter the hidden-file upload.
            (owned.parent / '.private-sibling').write_text('not evidence')
            root = workspace / visual['path']
            actual = {file.relative_to(root).as_posix() for file in root.rglob('*')
                      if file.is_file() and (visual.get('include-hidden-files') == 'true'
                      or all(not part.startswith('.') for part in file.relative_to(root).parts))}
            expected = {entry['path'] for entry in json.loads((owned / 'manifest.json').read_text())}
            self.assertEqual(actual, expected | {'manifest.json'})

    def test_hidden_file_permission_is_scoped_to_fixed_visual_evidence_root(self):
        visual = next(item for item in uploads() if item['name'].startswith('visual-'))
        self.assertEqual(visual['path'], 'candidate/reports/visual-ci/')
        self.assertEqual(visual.get('include-hidden-files'), 'true')
        self.assertEqual([item['path'] for item in uploads()
                          if item.get('include-hidden-files') == 'true'],
                         ['candidate/reports/visual-ci/'])
        lab = next(item for item in uploads() if item['name'].startswith('lab-view-'))
        self.assertEqual(lab['path'], 'candidate/reports/lab-view-ci/')
        self.assertNotEqual(lab.get('include-hidden-files'), 'true')


if __name__ == '__main__':
    unittest.main()
