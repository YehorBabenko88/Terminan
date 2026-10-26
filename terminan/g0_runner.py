"""Disconnected G0 child. Bind before publishing port; stdin owns shutdown."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
from .server import Handler, ThreadingHTTPServer

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ready',required=True)
    args=parser.parse_args()
    if any(v for k,v in os.environ.items() if k.startswith('TERMINAN_')):
        raise SystemExit('G0 child requires disconnected TERMINAN environment')
    ready=Path(args.ready)
    if ready.exists():raise SystemExit('Ready file already exists')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        temporary=ready.with_suffix('.tmp')
        with temporary.open('x',encoding='utf-8') as out:
            json.dump(dict(host='127.0.0.1',port=server.server_port,mode='READ_ONLY',sources='DISCONNECTED'),out)
        os.replace(temporary,ready)
        try:sys.stdin.readline()
        except KeyboardInterrupt:pass
    finally:
        server.shutdown();server.server_close();thread.join(6)
    return 0

if __name__=='__main__':raise SystemExit(main())
