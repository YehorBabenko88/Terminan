"""Adversarial package name verification, no build or network required."""
import unittest
import importlib.util
from pathlib import Path
_source=Path(__file__).resolve().parent/'check_archive_artifact_exclusion.py'
_spec=importlib.util.spec_from_file_location('d_archive_artifact_checker',_source)
_module=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
check_archive_members=_module.check_archive_members


class ArchivedFixtureExclusionTests(unittest.TestCase):
    def test_good_wheel_and_sdist_member_shapes(self):
        self.assertEqual(check_archive_members(
            ('terminan/__init__.py','unified_terminan-0.1.dist-info/RECORD'),
            wheel=True),2)
        self.assertEqual(check_archive_members(
            ('unified_terminan-0.1/terminan/__init__.py',
             'unified_terminan-0.1/README.md'),wheel=False),2)

    def test_reject_archived_python_source_in_either_distribution(self):
        for wheel in (True,False):
            prefix='' if wheel else 'unified_terminan-0.1/'
            for source in ('legacy_grid.py','volume_profile.py','scalp_entries.py'):
                members=(prefix+'terminan/__init__.py',
                         prefix+'tests/fixtures/d_round13_strattester/'+source)
                with self.subTest(wheel=wheel,source=source):
                    with self.assertRaisesRegex(ValueError,'HISTORICAL_PYTHON'):
                        check_archive_members(members,wheel=wheel)

    def test_reject_path_escape_and_missing_runtime(self):
        with self.assertRaisesRegex(ValueError,'UNSAFE'):
            check_archive_members(('terminan/__init__.py','../tests/evil.py'),wheel=True)
        with self.assertRaisesRegex(ValueError,'CODE_MISSING'):
            check_archive_members(('tests/bad.py',),wheel=True)
