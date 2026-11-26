"""Fail an exact Terminan wheel/sdist if historical executable fixtures ship.

Safety boundary: archived Strattester test-only Python must not appear in the
installed Terminan wheel OR the source distribution. This verifies both archive
member names and their correct root strip, not just manifest text.
"""
from __future__ import annotations
import argparse
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


_FORBIDDEN='tests/fixtures/d_round13_strattester/'
_MARKERS=('legacy_grid.py','volume_profile.py','scalp_entries.py')


def check_archive_members(names, *, wheel):
    entries=tuple(names)
    if not entries:
        raise ValueError('EMPTY_PACKAGE_ARCHIVE')
    for raw in entries:
        if type(raw) is not str or '\\' in raw:
            raise ValueError('UNSAFE_PACKAGE_MEMBER')
        parts=PurePosixPath(raw).parts
        if not parts or raw.startswith('/') or '..' in parts:
            raise ValueError('UNSAFE_PACKAGE_MEMBER')
        # sdists contain a single dist root, wheels do not.
        rel=parts if wheel else parts[1:]
        normalized='/'.join(rel)
        if normalized.startswith(_FORBIDDEN) or (
                normalized.startswith('tests/fixtures/') and
                normalized.endswith('.py')):
            raise ValueError('HISTORICAL_PYTHON_FIXTURE_IN_PACKAGE')
    if wheel and not any(x.startswith('terminan/') for x in entries):
        raise ValueError('TERMINAN_WHEEL_CODE_MISSING')
    if not wheel and not any(len(PurePosixPath(x).parts)>1 and
                             PurePosixPath(x).parts[1]=='terminan'
                             for x in entries):
        raise ValueError('TERMINAN_SDIST_CODE_MISSING')
    return len(entries)


def check_artifacts(wheel_dir, sdist_dir):
    wheels=tuple(Path(wheel_dir).glob('*.whl'))
    sdists=tuple(Path(sdist_dir).glob('*.tar.gz'))
    if len(wheels)!=1 or len(sdists)!=1:
        raise ValueError('EXACTLY_ONE_WHEEL_AND_SDIST_REQUIRED')
    with zipfile.ZipFile(wheels[0]) as archive:
        wn=check_archive_members(archive.namelist(),wheel=True)
    with tarfile.open(sdists[0],mode='r:gz') as archive:
        sn=check_archive_members(archive.getnames(),wheel=False)
    print(f'ARCHIVED_HISTORICAL_PYTHON_EXCLUSION=PASS wheel_members={wn} sdist_members={sn}')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--wheel-dir',required=True)
    parser.add_argument('--sdist-dir',required=True)
    options=parser.parse_args()
    check_artifacts(options.wheel_dir,options.sdist_dir)
