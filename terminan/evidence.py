"""Verify generated allowlisted smoke evidence; never grants physical acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

def verify(root,sha):
    root=Path(root)
    entries=json.loads((root/'manifest.json').read_text(encoding='utf-8-sig'))
    if not isinstance(entries,list) or not entries:raise ValueError('invalid manifest')
    names=set()
    for entry in entries:
        name=entry['file']
        if not isinstance(name,str) or '/' in name or '\\' in name or ':' in name or name in ('.','..','manifest.json') or name in names:
            raise ValueError('invalid manifest path')
        names.add(name)
        path=root/name
        if path.is_symlink():raise ValueError('symlink evidence')
        body=path.read_bytes()
        if len(body)!=entry['bytes'] or hashlib.sha256(body).hexdigest()!=entry['sha256']:
            raise ValueError('evidence integrity failure')
    if names!={p.name for p in root.iterdir() if p.is_file() and p.name!='manifest.json'}:raise ValueError('unmanifested evidence')
    summary=json.loads((root/'summary.json').read_text(encoding='utf-8-sig'))
    if summary['candidate_sha']!=sha or summary['exit_code']!=0 or summary['physical']!='PENDING' or summary['result']!='AUTOMATED_SMOKE_PASS':
        raise ValueError('evidence not a passing exact candidate smoke')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('--sha',required=True)
    args=parser.parse_args()
    manifests=list(args.root.rglob('manifest.json'))
    if not manifests:raise SystemExit('No evidence manifest')
    for manifest in manifests:verify(manifest.parent,args.sha)
    print(f'{len(manifests)} exact candidate smoke manifests verified; PHYSICAL PENDING')

if __name__=='__main__':main()
