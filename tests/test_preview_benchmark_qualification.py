"""Pure guard-contract source, execution HELD pending Root allocation.

Only actual qualifier helpers are loaded, no copied implementation. Filesystem
metadata is modeled; all byte reads/process starts inside guard calls tripwire.
No Node/browser/fixture/client, real timeout, process kill or filesystem mutation.
Missing helper on old parent is NEW_FEATURE_PREREQUISITE_RED, not R40 proof.
"""
import copy
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

IDS = (
    'r2_metrics_count_held_benchmark_raf',
    'r2_dispose_settles_held_benchmark_without_frame',
    'r2_seek_settles_superseded_benchmark_without_frame',
    'r4_metrics_count_held_benchmark_raf',
    'r4_dispose_settles_held_benchmark_without_frame',
    'r4_seek_settles_superseded_benchmark_without_frame',
)


def actual_helper():
    # The one allocated helper source is verified by Root before this import.
    filename = Path(__file__).with_name('preview_benchmark_qualification.py')
    spec = importlib.util.spec_from_file_location('owned_preview_qualification', filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_tap():
    facts = dict(version='v24.22.1', exec_path='/UNIT_DATA/node',
                 exec_argv=[], platform='linux', arch='x64')
    lines = ['# PREVIEW_NODE_FACT ' + json.dumps(facts), 'TAP version 13']
    for number, name in enumerate(IDS, 1):
        lines.extend(['# Subtest: ' + name, 'ok ' + str(number) + ' - ' + name])
    lines.extend(['1..6', '# tests 6', '# suites 0', '# pass 6', '# fail 0',
                  '# cancelled 0', '# skipped 0', '# todo 0', '# duration_ms 1'])
    return ('\n'.join(lines) + '\n').encode('utf-8')


def valid_outcome():
    return dict(exit_code=0, timed_out=False, output_overflow=False, kill_used=False,
                cleanup_uncertain=False, reader_error=False, readers_retired=True,
                elapsed_seconds=0.1, captured_bytes=1024)


class PreviewQualificationGuardTests(unittest.TestCase):
    def test_root_first_unsafe_parent_stops_before_child_metadata_bytes_or_process(self):
        q = actual_helper()
        root = Path(Path.cwd().anchor)
        unsafe = root / 'UNIT_PARENT' / 'UNSAFE'
        target = unsafe / 'source.cjs'
        for mode, attributes in [(stat.S_IFLNK | 0o777, 0), (stat.S_IFDIR | 0o755, 0x400)]:
            visited = []

            def metadata(item):
                visited.append(item)
                if item == unsafe:
                    return SimpleNamespace(st_mode=mode, st_nlink=1, st_file_attributes=attributes)
                return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_nlink=1, st_file_attributes=0)

            with self.subTest(mode=mode, attributes=attributes):
                with patch.object(Path, 'lstat', metadata), \
                        patch.object(Path, 'read_bytes', side_effect=AssertionError('SOURCE_BYTES_READ')) as read, \
                        patch('subprocess.Popen', side_effect=AssertionError('PROCESS_STARTED')) as spawn:
                    with self.assertRaisesRegex(RuntimeError, 'LINK_OR_REPARSE_PATH'):
                        q.ordinary(target)
                    self.assertEqual(visited[0], root)
                    self.assertEqual(visited[-1], unsafe)
                    self.assertNotIn(target, visited)
                    read.assert_not_called()
                    spawn.assert_not_called()

    def test_exact_six_tap_accepts_manifest_without_io(self):
        q = actual_helper()
        # Data-only extension: original LF vector AND original raw CRLF bytes.
        for raw in [valid_tap(), valid_tap().replace(b'\n', b'\r\n')]:
            with self.subTest(line_endings='CRLF' if b'\r\n' in raw else 'LF'):
                with patch.object(Path, 'read_bytes', side_effect=AssertionError('BYTE_IO')), \
                        patch('subprocess.Popen', side_effect=AssertionError('PROCESS')):
                    parsed = q._parse_six_tap(raw)
                self.assertEqual(parsed['ids'], list(IDS))
                self.assertEqual(parsed['counts'], dict(tests=6, **{'pass': 6}, fail=0,
                                                        cancelled=0, skipped=0, todo=0))
                self.assertEqual(parsed['node_fact']['version'], 'v24.22.1')

    def test_tap_rejects_missing_extra_duplicate_wrong_or_reordered_ids(self):
        q = actual_helper()
        raw = valid_tap()
        cases = [raw.replace(('# Subtest: ' + IDS[0] + '\n').encode(), b''),
                 raw + b'# Subtest: unexpected_case\n',
                 raw.replace(IDS[1].encode(), IDS[0].encode()),
                 raw.replace(IDS[0].encode(), b'wrong_case'),
                 raw.replace(IDS[0].encode(), b'REPLACE_A').replace(IDS[1].encode(), IDS[0].encode()).replace(b'REPLACE_A', IDS[1].encode())]
        for index, case in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                q._parse_six_tap(case)

    def test_tap_rejects_missing_duplicate_counts_skip_cancel_todo_fail_or_wrong_total(self):
        q = actual_helper()
        raw = valid_tap()
        cases = [raw.replace(b'# tests 6\n', b''), raw + b'# pass 6\n',
                 raw.replace(b'# tests 6\n', b'# tests 5\n'),
                 raw.replace(b'# pass 6\n', b'# pass 5\n')]
        for name in ['skipped', 'cancelled', 'todo', 'fail']:
            cases.append(raw.replace(('# ' + name + ' 0\n').encode(), ('# ' + name + ' 1\n').encode()))
        for index, case in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                q._parse_six_tap(case)

    def test_tap_rejects_failed_rows_invalid_utf8_and_overlimit_despite_success_summary(self):
        q = actual_helper()
        raw = valid_tap()
        cases = [raw.replace(b'\nok 1 - ', b'\nnot ok 1 - '),
                 raw.replace(('ok 1 - ' + IDS[0] + '\n').encode(), ('ok 1 - ' + IDS[0] + ' # SKIP\n').encode()),
                 b'\xff' + raw, b'#' * 262145, raw.decode('utf-8')]
        for index, case in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                q._parse_six_tap(case)

    def test_tap_requires_single_valid_node_version_fact(self):
        q = actual_helper()
        raw = valid_tap()
        first = raw.split(b'\n')[0] + b'\n'
        cases = [raw[len(first):], raw + first, raw.replace(b'v24.22.1', b'v24.20.0'),
                 raw.replace(b'"arch": "x64"', b'"arch": "arm64"'),
                 raw.replace(first, b'# PREVIEW_NODE_FACT not_json\n')]
        for index, case in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                q._parse_six_tap(case)

    def test_nonzero_timeout_overflow_kill_and_cleanup_uncertainty_deny(self):
        q = actual_helper()
        q._require_node_success(valid_outcome())
        changes = [dict(exit_code=1), dict(exit_code=None), dict(timed_out=True),
                   dict(output_overflow=True), dict(kill_used=True), dict(cleanup_uncertain=True),
                   dict(reader_error=True), dict(readers_retired=False),
                   dict(elapsed_seconds=15.1), dict(captured_bytes=262145)]
        for change in changes:
            bad = dict(valid_outcome(), **change)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                q._require_node_success(bad)

    def test_process_evidence_must_be_complete_finite_and_strictly_typed(self):
        q = actual_helper()
        for name in valid_outcome():
            bad = copy.copy(valid_outcome())
            del bad[name]
            with self.subTest(missing=name), self.assertRaises(RuntimeError):
                q._require_node_success(bad)
        for change in [dict(exit_code=False), dict(timed_out='false'),
                       dict(readers_retired=1), dict(elapsed_seconds=float('nan')),
                       dict(elapsed_seconds=-1), dict(captured_bytes=True), dict(captured_bytes=-1)]:
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                q._require_node_success(dict(valid_outcome(), **change))


if __name__ == '__main__':
    unittest.main()
