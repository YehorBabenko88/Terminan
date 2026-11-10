"""Reviewed-source six-case unit qualification, not browser/native admission.

Invoked ONLY by the primary-Git-verified workflow bootstrap. The explicit eight
qualified pure guard controls load the actual helper; no broad project discovery.
One Node test process; checkout/setup actions and read-only Git processes are
separate platform/tool roles. Version/hash records are observations, not signed
binary provenance or protection against a malicious runner/kernel.
"""
import contextlib
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import unittest

BASE = 'dc810b03c3accf0e6f28fca1d5068f4171bb909d'
IDS = [
    'r2_metrics_count_held_benchmark_raf',
    'r2_dispose_settles_held_benchmark_without_frame',
    'r2_seek_settles_superseded_benchmark_without_frame',
    'r4_metrics_count_held_benchmark_raf',
    'r4_dispose_settles_held_benchmark_without_frame',
    'r4_seek_settles_superseded_benchmark_without_frame',
]
PURE_MODULE = 'preview_qualification_guard_lane'
PURE_METHODS = [
    'test_exact_six_tap_accepts_manifest_without_io',
    'test_nonzero_timeout_overflow_kill_and_cleanup_uncertainty_deny',
    'test_process_evidence_must_be_complete_finite_and_strictly_typed',
    'test_root_first_unsafe_parent_stops_before_child_metadata_bytes_or_process',
    'test_tap_rejects_failed_rows_invalid_utf8_and_overlimit_despite_success_summary',
    'test_tap_rejects_missing_duplicate_counts_skip_cancel_todo_fail_or_wrong_total',
    'test_tap_rejects_missing_extra_duplicate_wrong_or_reordered_ids',
    'test_tap_requires_single_valid_node_version_fact',
]

DELTA = {
    '.github/workflows/preview-benchmark-disposal.yml': 'A',
    'docs/operations/operations-dashboard-contract.md': 'M',
    'docs/operations/preview-benchmark-disposal-review1.md': 'A',
    'terminan/r2_preview.js': 'M',
    'terminan/r4_preview.js': 'M',
    'tests/preview_benchmark_qualification.py': 'A',
    'tests/test_preview_benchmark_disposal.cjs': 'A',
    'tests/test_preview_benchmark_qualification.py': 'A',
}
FROZEN = {
    'tests/test_preview_benchmark_disposal.cjs': '0ad02bc7f756300de21aac34036be27881cc23038a3f6e2500318ebace81d57a',
    'terminan/r2_preview.js': '6416aed7911835ab3473e04564c1f4856f008d9fa29b21af6e4415805ede53cb',
    'terminan/r4_preview.js': '48ff173084e273ab2a90c08fca3cf19b79392389a836cba656aef5255153c617',
    'terminan/r4_protocol.js': '99b4f3f31710594637f005034ff36f655ce89c12a0e33a2ad218545bbf73eb54',
}
NODE_ENV = ('NODE_OPTIONS', 'NODE_PATH', 'NODE_COMPILE_CACHE', 'NODE_V8_COVERAGE')


def deny(code):
    raise RuntimeError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ordinary(value, directory=False):
    """Root-first lstat, before any bytes/Git/tool use; reject links/reparse."""
    p = Path(value)
    if not p.is_absolute() or '..' in p.parts:
        deny('ABSOLUTE_ORDINARY_PATH_REQUIRED')
    for item in [*reversed(p.parents), p]:
        s = item.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
            deny('LINK_OR_REPARSE_PATH')
        if item != p or directory:
            if not stat.S_ISDIR(s.st_mode):
                deny('DIRECTORY_REQUIRED')
        elif not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
            deny('ORDINARY_SINGLE_LINK_FILE_REQUIRED')
    return p


def ordinary_tree(root):
    ordinary(root, directory=True)
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            ordinary(Path(directory) / name, directory=True)
        for name in files:
            ordinary(Path(directory) / name)


def save(out, name, raw):
    ordinary(out, directory=True)
    p = out / name
    # Exclusive evidence; no existing artifact may be silently replaced.
    with p.open('xb') as stream:
        stream.write(raw)
    ordinary(p)
    return digest(raw)


def _parse_six_tap(raw):
    """Pure bounded evidence validation; newline normalization is metadata only."""
    if type(raw) is not bytes or len(raw) > 262144:
        deny('TAP_BYTES_OR_CAP')
    try:
        text = raw.decode('utf-8', errors='strict').replace('\r\n', '\n')
        if '\r' in text:
            deny('TAP_LINE_ENDING')
        ids = re.findall(r'^# Subtest: (.+)$', text, re.M)
        if ids != IDS:
            deny('EXACT_SIX_IDS_REQUIRED')
        rows = re.findall(r'^(not ok|ok) ([0-9]+) - (.+)$', text, re.M)
        if rows != [('ok', str(i), name) for i, name in enumerate(IDS, 1)]:
            deny('TAP_RESULT_ROWS')
        counts = {}
        for name in ('tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo'):
            values = re.findall(r'^# ' + name + r' ([0-9]+)[ \t]*$', text, re.M)
            if len(values) != 1:
                deny('TAP_COUNT_AMBIGUOUS')
            counts[name] = int(values[0])
        if counts != dict(tests=6, **{'pass': 6}, fail=0, cancelled=0, skipped=0, todo=0):
            deny('SIX_PASS_ZERO_SKIP_REQUIRED')
        facts = re.findall(r'^# PREVIEW_NODE_FACT (.+)$', text, re.M)
        if len(facts) != 1:
            deny('ONE_NODE_RUNTIME_FACT_REQUIRED')

        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    deny('NODE_FACT_DUPLICATE')
                value[key] = item
            return value

        fact = json.loads(facts[0], object_pairs_hook=unique)
        if (type(fact) is not dict or set(fact) != {'version', 'exec_path', 'exec_argv', 'platform', 'arch'}
                or fact['version'] != 'v24.22.1' or fact['arch'] != 'x64'
                or fact['platform'] not in ('win32', 'linux')
                or type(fact['exec_path']) is not str or not 1 <= len(fact['exec_path']) <= 4096
                or type(fact['exec_argv']) is not list or len(fact['exec_argv']) > 32
                or any(type(x) is not str or len(x) > 4096 for x in fact['exec_argv'])):
            deny('NODE_RUNTIME_FACT_MISMATCH')
        return dict(ids=ids, counts=counts, node_fact=fact)
    except RuntimeError:
        raise
    except Exception:
        deny('TAP_INVALID_ENCODING_OR_FACT')


def _require_node_success(outcome):
    """Pure validation of process evidence DATA, not proof of cleanup mechanics."""
    if type(outcome) is not dict:
        deny('NODE_OUTCOME_REQUIRED')
    flags = {'timed_out': False, 'output_overflow': False, 'kill_used': False,
             'cleanup_uncertain': False, 'reader_error': False, 'readers_retired': True}
    if type(outcome.get('exit_code')) is not int or outcome['exit_code'] != 0:
        deny('NODE_EXIT_DENIED')
    if any(type(outcome.get(k)) is not bool or outcome[k] is not value for k, value in flags.items()):
        deny('NODE_CLEANUP_OR_EXECUTION_DENIED')
    elapsed, size = outcome.get('elapsed_seconds'), outcome.get('captured_bytes')
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= 15
            or type(size) is not int or not 0 <= size <= 262144 or outcome.get('controller_error_type')):
        deny('NODE_BOUNDS_OR_CONTROLLER_DENIED')


def held_node(argv, root):
    """One held Node; every post-Popen operation is inside unconditional finally.

    Execution deadline15s plus bounded kill/wait/reader retirement. Not strict
    real-time or host-wide/family containment. No PID lookup or tree kill.
    """
    start = time.monotonic()
    proc = None
    chunks = [bytearray(), bytearray()]
    lock = threading.Lock()
    overflow = threading.Event()
    reader_error = threading.Event()
    readers = []
    total = 0
    outcome = dict(launched=False, exit_code=None, timed_out=False, output_overflow=False,
                   kill_used=False, cleanup_uncertain=False, reader_error=False,
                   readers_retired=False, elapsed_seconds=0, captured_bytes=0)

    def read(pipe, slot):
        nonlocal total
        try:
            while True:
                block = pipe.read(4096)
                if not block:
                    return
                with lock:
                    room = max(0, 262144 - total)
                    chunks[slot].extend(block[:room])
                    total += len(block)
                    if total > 262144:
                        overflow.set()
        except BaseException:
            reader_error.set()

    try:
        proc = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                bufsize=0, shell=False,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        outcome['launched'] = True
        # Handle is owned immediately. Thread creation/start/poll exceptions
        # cannot bypass the kill/wait/retirement below.
        for slot, pipe in enumerate((proc.stdout, proc.stderr)):
            thread = threading.Thread(target=read, args=(pipe, slot), daemon=True)
            readers.append(thread)
            thread.start()
        while proc.poll() is None:
            if overflow.is_set() or time.monotonic() - start >= 15:
                outcome['timed_out'] = not overflow.is_set()
                break
            time.sleep(0.01)
    except BaseException as error:
        outcome['controller_error_type'] = type(error).__name__
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:
                    outcome['kill_used'] = True
                    proc.kill()
                proc.wait(timeout=2)
            except BaseException:
                outcome['cleanup_uncertain'] = True
                try:
                    # Even a poll/wait failure must attempt the held kill/wait.
                    outcome['kill_used'] = True
                    proc.kill()
                    proc.wait(timeout=2)
                except BaseException:
                    outcome['cleanup_uncertain'] = True
            for thread in readers:
                try:
                    if thread.ident is not None:
                        thread.join(timeout=0.5)
                except BaseException:
                    outcome['cleanup_uncertain'] = True
            try:
                if len(readers) != 2 or any(thread.is_alive() for thread in readers):
                    outcome['cleanup_uncertain'] = True
            except BaseException:
                outcome['cleanup_uncertain'] = True
            for pipe in (proc.stdout, proc.stderr):
                try:
                    pipe.close()
                except BaseException:
                    outcome['cleanup_uncertain'] = True
            outcome['exit_code'] = proc.returncode
        else:
            outcome['cleanup_uncertain'] = True
        outcome['output_overflow'] = overflow.is_set()
        outcome['reader_error'] = reader_error.is_set()
        outcome['readers_retired'] = len(readers) == 2 and all(not t.is_alive() for t in readers)
        outcome['elapsed_seconds'] = time.monotonic() - start
        with lock:
            outcome['captured_bytes'] = sum(map(len, chunks))
            stdout, stderr = map(bytes, chunks)
    return stdout, stderr, outcome


def _run_pure_guards(root, out, before):
    """Separate eight-control lane in this isolated Python process, never Node.

    Only trusted exact qualified test source is loaded. An observed 15s bound is
    fail-closed AFTER completion, not hard same-process test preemption. The job
    is the external cap. DATA outcome validation is not actual kill/wait proof.
    """
    start = time.monotonic()
    evidence = dict(scope='EIGHT_PURE_GUARD_CONTROLS_NOT_PROCESS_MECHANICS',
                    result='FAIL', tests_started=False, test_subprocess_count=0,
                    actual_started_ids=[], actual_succeeded_ids=[])
    expected = [PURE_MODULE + '.PreviewQualificationGuardTests.' + name for name in PURE_METHODS]
    saved_objects = (Path.lstat, Path.read_bytes, subprocess.Popen)
    budget = {'bytes': 0, 'overflow': False}

    class Sink:
        def __init__(self):
            self.raw = bytearray()

        def write(self, text):
            raw = text.encode('utf-8', errors='strict')
            room = max(0, 262144 - budget['bytes'])
            self.raw.extend(raw[:room])
            budget['bytes'] += len(raw)
            if budget['bytes'] > 262144:
                budget['overflow'] = True
                deny('PURE_OUTPUT_CAP')
            return len(text)

        def flush(self):
            pass

    transcript, stdout, stderr = Sink(), Sink(), Sink()
    try:
        for name in ('tests/test_preview_benchmark_qualification.py', 'tests/preview_benchmark_qualification.py'):
            raw = ordinary(root / name).read_bytes()
            if digest(raw) != before['files'][name]['sha256']:
                deny('PURE_IMPORT_SOURCE_CHANGED')
        evidence['source_pins'] = {name: before['files'][name] for name in
                                  ('tests/test_preview_benchmark_qualification.py', 'tests/preview_benchmark_qualification.py')}
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            spec = importlib.util.spec_from_file_location(PURE_MODULE, root / 'tests/test_preview_benchmark_qualification.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # __main__ false; no unittest.main or helper main.
            suite = unittest.TestLoader().loadTestsFromTestCase(module.PreviewQualificationGuardTests)
            collected = [case.id() for case in suite]
            if collected != expected:
                deny('PURE_EXACT_EIGHT_COLLECTION_REQUIRED')
            evidence['collected_ids'] = collected

            class RecordedResult(unittest.TextTestResult):
                def startTest(self, case):
                    evidence['actual_started_ids'].append(case.id())
                    super().startTest(case)

                def addSuccess(self, case):
                    evidence['actual_succeeded_ids'].append(case.id())
                    super().addSuccess(case)

            evidence['tests_started'] = True
            result = unittest.TextTestRunner(stream=transcript, verbosity=2, resultclass=RecordedResult).run(suite)
            counts = dict(tests=result.testsRun, passed=len(evidence['actual_succeeded_ids']),
                          failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                          expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses))
            evidence['counts'] = counts
            if (not result.wasSuccessful() or evidence['actual_started_ids'] != expected
                    or evidence['actual_succeeded_ids'] != expected
                    or counts != dict(tests=8, passed=8, failures=0, errors=0, skipped=0,
                                      expected_failures=0, unexpected_successes=0)):
                deny('PURE_EIGHT_RESULT_DENIED')
        if budget['overflow'] or time.monotonic() - start > 15:
            deny('PURE_OUTPUT_OR_OBSERVED_TIME_BOUND')
        evidence['result'] = 'PASS'
    except BaseException as error:
        evidence['error_type'] = type(error).__name__
    finally:
        evidence['patches_restored'] = saved_objects == (Path.lstat, Path.read_bytes, subprocess.Popen)
        evidence['output_overflow'] = budget['overflow']
        evidence['elapsed_seconds'] = time.monotonic() - start
        if not evidence['patches_restored']:
            evidence['result'] = 'FAIL'
        # Existing context-managed tests restore patches; residue is DENY. Never
        # proceed to Git/Node through a mock or silently repair it into success.
        if not evidence['patches_restored']:
            deny('PURE_SHARED_PATCH_RESIDUE')
        evidence['transcript_sha256'] = save(out, 'pure-eight-original.txt', bytes(transcript.raw))
        evidence['stdout_sha256'] = save(out, 'pure-eight-stdout.txt', bytes(stdout.raw))
        evidence['stderr_sha256'] = save(out, 'pure-eight-stderr.txt', bytes(stderr.raw))
        raw = (json.dumps(evidence, indent=2) + '\n').encode()
        receipt_hash = save(out, 'pure-eight-receipt.json', raw)
    return evidence, receipt_hash


def run(root, head, out, node, git, bootstrap_sha):
    receipt = dict(scope='ACTUAL_JS_FAKE_DOM_RAF_UNIT_ONLY_NOT_BROWSER_NATIVE_PHYSICAL',
                   result='FAIL', expected_head=head, implementation_base=BASE,
                   tests_started=False, test_node_process_count=0,
                   bootstrap_verified_qualifier_sha256=bootstrap_sha)
    # Failures before an output directory is safely established are written by
    # the external workflow bootstrap; do not write through unverified paths.
    root = ordinary(root, directory=True)
    ordinary_tree(root)
    out = Path(out)
    ordinary(out.parent, directory=True)
    if not out.is_absolute() or out.exists() or root == out or root in out.parents or out in root.parents:
        deny('FRESH_EXTERNAL_EVIDENCE_REQUIRED')
    out.mkdir()
    ordinary(out, directory=True)
    try:
        if sys.version_info[:3] != (3, 12, 10) or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
            deny('PYTHON_RUNTIME_FLAGS_OR_VERSION')
        if any(os.environ.get(k) for k in NODE_ENV):
            deny('AMBIENT_NODE_CONFIG')
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                    'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE', 'GIT_REPLACE_REF_BASE'):
            if os.environ.get(key):
                deny('AMBIENT_GIT_SOURCE_OVERRIDE')
        node = ordinary(node)
        git = ordinary(git)
        python = ordinary(sys.executable)
        expected_git = Path('C:/Program Files/Git/bin/git.exe') if os.name == 'nt' else Path('/usr/bin/git')
        if git != expected_git:
            deny('FIXED_GIT_PATH_REQUIRED')
        if not re.fullmatch('[a-f0-9]{40}', head):
            deny('EXACT_HEAD_REQUIRED')
        receipt['tools'] = {
            'python': dict(path=str(python), version=sys.version, sha256=digest(python.read_bytes()), role='QUALIFIER_STDLIB_ISOLATED_3_12_10'),
            'node': dict(path=str(node), expected_version='v24.22.1', sha256=digest(node.read_bytes()), role='ONE_ACTUAL_TEST_PROCESS_SETUP_NODE_24_22_1_OBSERVED_BINARY_NOT_SIGNED_ATTESTATION'),
            'git': dict(path=str(git), sha256=digest(git.read_bytes()), role='READ_ONLY_PRIMARY_SOURCE_TOOL_NO_CMD_FALLBACK'),
        }

        def g(*args, input=None):
            ordinary(root, directory=True)
            ordinary(git)
            p = subprocess.run([str(git), '--no-replace-objects', '--no-optional-locks',
                                '-c', 'core.fsmonitor=false', *args], cwd=root,
                               input=input, capture_output=True, timeout=10, shell=False)
            if p.returncode or len(p.stdout) > 67108864 or len(p.stderr) > 65536:
                deny('PRIMARY_GIT_COMMAND_FAILED')
            return p.stdout

        def inventory():
            ordinary_tree(root)
            if g('rev-parse', 'HEAD').decode().strip() != head:
                deny('HEAD_MISMATCH')
            g('merge-base', '--is-ancestor', BASE, head)
            gitdir = Path(g('rev-parse', '--absolute-git-dir').decode().strip())
            ordinary(gitdir, directory=True)
            if any((gitdir / name).exists() for name in ('info/grafts', 'objects/info/alternates')) or g('for-each-ref', 'refs/replace'):
                deny('ALTERNATE_SOURCE_GRAPH')
            delta = {}
            for line in g('diff', '--name-status', BASE, head).decode().splitlines():
                kind, name = line.split('\t')
                delta[name] = kind
            if delta != DELTA:
                deny('EXACT_EIGHT_PATH_SCOPE_REQUIRED')
            entries = []
            for row in g('ls-tree', '-rz', '--full-tree', head).split(b'\0'):
                if not row:
                    continue
                meta, name = row.split(b'\t')
                mode, kind, oid = meta.decode().split()
                name = name.decode('utf-8')
                if kind != 'blob' or mode not in ('100644', '100755') or Path(name).is_absolute() or Path(name).drive or '\\' in name or any(x in ('', '.', '..') for x in name.split('/')):
                    deny('SOURCE_MODE_OR_PATH')
                entries.append((name, oid))
            batch = g('cat-file', '--batch', input=''.join(oid + '\n' for _, oid in entries).encode('ascii'))
            files = {}
            offset = 0
            for name, oid in entries:
                end = batch.index(b'\n', offset)
                actual_oid, kind, length = batch[offset:end].decode().split()
                size = int(length)
                if actual_oid != oid or kind != 'blob' or not 0 <= size <= 16777216:
                    deny('BLOB_HEADER')
                raw = batch[end + 1:end + 1 + size]
                offset = end + 2 + size
                if batch[offset - 1:offset] != b'\n' or len(raw) != size:
                    deny('BLOB_LENGTH')
                actual = ordinary(root / name).read_bytes()
                if actual != raw:
                    deny('RAW_SOURCE_MISMATCH')
                files[name] = dict(git_blob=oid, bytes=size, sha256=digest(raw))
            if offset != len(batch):
                deny('EXTRA_GIT_OUTPUT')
            for directory, dirs, names in os.walk(root):
                if Path(directory) == root and '.git' in dirs:
                    dirs.remove('.git')
                for name in names:
                    rel = (Path(directory) / name).relative_to(root).as_posix()
                    if rel not in files:
                        deny('UNTRACKED_OR_IGNORED_SOURCE')
            if g('status', '--porcelain', '--untracked-files=all'):
                deny('DIRTY_SOURCE')
            for name, required in FROZEN.items():
                if files[name]['sha256'] != required:
                    deny('REGRESSION_OR_PRODUCTION_PIN_CHANGED')
            return dict(head=head, tree=g('rev-parse', 'HEAD^{tree}').decode().strip(), files=files)

        before = inventory()
        receipt['before'] = before
        receipt['source_file_count'] = len(before['files'])  # Full actual map; no stale hardcoded count.
        if before['files']['tests/preview_benchmark_qualification.py']['sha256'] != bootstrap_sha:
            deny('BOOTSTRAP_QUALIFIER_PIN_MISMATCH')
        pure, pure_hash = _run_pure_guards(root, out, before)
        receipt['pure_guard_receipt_sha256'] = pure_hash
        receipt['pure_guard_counts'] = pure.get('counts')
        receipt['pure_guard_result'] = pure['result']
        after_pure = inventory()
        receipt['after_pure_guards'] = after_pure
        if before != after_pure:
            deny('SOURCE_CHANGED_AFTER_PURE_GUARDS')
        if pure['result'] != 'PASS':
            deny('PURE_GUARDS_FAILED_NODE_NOT_STARTED')
        # Constant owned preload, external to source; checks runtime version in
        # the SAME test Node process. No additional node --version process.
        prelude = ("'use strict';if(process.version!=='v24.22.1'||process.arch!=='x64')throw Error('NODE_RUNTIME_VERSION');"
                   "process.stdout.write('# PREVIEW_NODE_FACT '+JSON.stringify({version:process.version,exec_path:process.execPath,exec_argv:process.execArgv,platform:process.platform,arch:process.arch})+String.fromCharCode(10));").encode()
        save(out, 'node-preflight.cjs', prelude)
        argv = [str(node), '--no-addons', '--test', '--test-isolation=none', '--test-concurrency=1',
                '--test-reporter=tap', '--require', str(out / 'node-preflight.cjs'),
                str(root / 'tests/test_preview_benchmark_disposal.cjs')]
        receipt['node_argv'] = argv
        receipt['preload_sha256'] = digest(prelude)
        receipt['tests_started'] = True
        receipt['node_launch_attempts'] = 1
        stdout, stderr, outcome = held_node(argv, root)
        receipt['test_node_process_count'] = int(outcome['launched'])
        receipt['process'] = outcome
        receipt['stdout_sha256'] = save(out, 'node-original.tap', stdout)
        receipt['stderr_sha256'] = save(out, 'node-original.stderr', stderr)
        after = inventory()
        receipt['after'] = after
        if before != after:
            deny('SOURCE_CHANGED_AFTER_TEST')
        _require_node_success(outcome)
        parsed = _parse_six_tap(stdout)
        fact = parsed['node_fact']
        if not ordinary(fact['exec_path']).samefile(node):
            deny('NODE_RUNTIME_FACT_MISMATCH')
        receipt['node_runtime_fact'] = fact
        receipt['counts'] = parsed['counts']
        receipt['executed_ids'] = parsed['ids']
        receipt['result'] = 'PASS'
    except Exception as error:
        code = str(error)
        receipt['error'] = code if re.fullmatch('[A-Z_]+', code) else 'QUALIFICATION_FAILED'
    finally:
        save(out, 'source-receipt.json', (json.dumps(receipt, indent=2) + '\n').encode())
    return receipt


if __name__ == '__main__':
    try:
        result = run(*sys.argv[1:])
        print(json.dumps({k: result[k] for k in ('scope', 'result', 'expected_head', 'tests_started')}))
        raise SystemExit(0 if result['result'] == 'PASS' else 1)
    except Exception:
        print('PREVIEW_QUALIFICATION_DENIED', file=sys.stderr)
        raise SystemExit(1)
