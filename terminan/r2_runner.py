"""Owned loopback R2 child. No DB/exchange routes; inherited source config cleared."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from .r2_server import R2Handler, R2Server

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ready')
    args=parser.parse_args()
    for key in list(os.environ):
        if key.startswith('TERMINAN_'):os.environ.pop(key,None)
    server=R2Server(('127.0.0.1',0),R2Handler)
    repo=Path(__file__).resolve().parents[1]
    server.candidate_sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    server.source_clean=not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=normal'],text=True).strip()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    info=dict(host='127.0.0.1',port=server.server_port,mode='SYNTHETIC',sources='DISABLED',candidate_sha=server.candidate_sha,source_clean=server.source_clean)
    try:
        if args.ready:
            ready=Path(args.ready);tmp=ready.with_suffix('.tmp')
            if ready.exists():raise ValueError('ready file exists')
            with tmp.open('x',encoding='utf-8') as out:json.dump(info,out)
            os.replace(tmp,ready)
        print(json.dumps(info),flush=True)
        try:sys.stdin.readline()
        except KeyboardInterrupt:pass
    finally:
        server.shutdown();server.server_close();thread.join(6)
    return 0

if __name__=='__main__':raise SystemExit(main())
