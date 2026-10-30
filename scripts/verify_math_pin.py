"""Verify source objects and tracked checkout; hashes do not attest authenticity."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

lock=json.loads(Path('math-engine.lock.json').read_text())
root=os.environ.get('MATH_REPO','../math-engine')
def git(*args):return subprocess.check_output(['git','-C',root,*args])
if git('rev-parse','HEAD').decode().strip()!=lock['sha']:raise SystemExit('MATH_HEAD_MISMATCH')
if git('rev-parse','HEAD^{tree}').decode().strip()!=lock['tree']:raise SystemExit('MATH_TREE_MISMATCH')
if git('status','--porcelain','--untracked-files=no').strip():raise SystemExit('DIRTY_MATH_SOURCE')
for path,want in lock['files'].items():
    canonical=git('show',lock['sha']+':'+path)
    if hashlib.sha256(canonical).hexdigest()!=want:raise SystemExit('SOURCE_OBJECT_MISMATCH')
    working=Path(root,path).read_bytes()
    if working.replace(b'\r\n',b'\n')!=canonical:raise SystemExit('WORKING_SOURCE_MISMATCH')
print(json.dumps({'state':'PIN_MATCH','head':lock['sha'],'source_authenticity':'UNATTESTED'}))
