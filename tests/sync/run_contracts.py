"""Exact-source preliminary contract receipt. Never runtime qualification."""
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TESTS = 84
SOURCES = ["terminan/sync/protocol.js", "terminan/sync/client.js", "terminan/sync/c3.js", "terminan/sync/mux-stream.js", "terminan/sync/serve.py", "tests/sync/fixtures.cjs", "tests/sync/test_contract.cjs", "tests/sync/test_client.cjs", "tests/sync/test_c3.cjs", "tests/sync/test_mux_stream.cjs", "tests/sync/c3-review4-vectors.json", "tests/sync/test_browser.spec.cjs", "tests/sync/run_contracts.py", "tests/sync/test_ci_receipt.py", ".github/workflows/terminan-sync.yml"]

def counts_from_tap(text):
    counts = {}
    for name in ["tests", "pass", "fail", "cancelled", "skipped", "todo"]:
        matches = re.findall(r"^# " + name + r" (\d+)\s*$", text, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError("missing or ambiguous count: " + name)
        counts[name] = int(matches[0])
    if counts != {"tests": EXPECTED_TESTS, "pass": EXPECTED_TESTS, "fail": 0, "cancelled": 0, "skipped": 0, "todo": 0}:
        raise ValueError("contract test count/zero-skip gate failed: " + str(counts))
    return counts

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def main():
    head = git("rev-parse", "HEAD").decode().strip()
    expected = os.environ.get("SYNC_EXPECTED_HEAD", head)
    if not re.fullmatch(r"[a-f0-9]{40}", expected) or head != expected:
        raise ValueError("exact HEAD mismatch")
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError("tracked source tree is dirty")
    sources = {}
    for name in SOURCES:
        blob = git("show", head + ":" + name)
        blob_id = git("rev-parse", head + ":" + name).decode().strip()
        normalized_id = git("hash-object", "--path=" + name, name).decode().strip()
        if blob_id != normalized_id:
            raise ValueError("worktree source mismatch: " + name)
        sources[name] = {"git_blob": blob_id, "blob_sha256": hashlib.sha256(blob).hexdigest(), "worktree_sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
    output = Path(os.environ.get("SYNC_EVIDENCE_DIR", str(ROOT / "test-results/sync-contracts")))
    output.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(["node", "--test", "--test-reporter=tap", "tests/sync/test_contract.cjs", "tests/sync/test_client.cjs", "tests/sync/test_c3.cjs", "tests/sync/test_mux_stream.cjs"], cwd=ROOT, text=True, capture_output=True)
    (output / "contracts.tap").write_text(run.stdout, encoding="utf-8")
    (output / "contracts.stderr.txt").write_text(run.stderr, encoding="utf-8")
    receipt = {"qualification": "MODEL_CONTRACT_ONLY_NOT_RUNTIME", "expected_head": expected, "head": head, "tree": git("rev-parse", "HEAD^{tree}").decode().strip(), "sources": sources, "node": subprocess.check_output(["node", "--version"], text=True).strip(), "python": platform.python_version(), "platform": platform.platform(), "run_id": os.environ.get("GITHUB_RUN_ID"), "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "job": os.environ.get("GITHUB_JOB"), "exit_code": run.returncode, "result": "FAIL"}
    error = None
    try:
        receipt["counts"] = counts_from_tap(run.stdout)
        if run.returncode != 0:
            raise ValueError("test process failed")
        receipt["result"] = "PASS"
    except ValueError as exc:
        error = str(exc)
        receipt["error"] = error
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ["head", "tree", "result", "exit_code"]}))
    if error:
        raise SystemExit(error)

if __name__ == "__main__":
    main()
