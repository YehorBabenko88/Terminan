"""Loopback saved-data preview. Sources stay disabled unless explicitly selected."""
import argparse,json,subprocess,threading,sys,time
from pathlib import Path
from .saved_server import SavedServer,SavedHandler
from .saved_sources import SavedSources,demo_config,SourceError

def main():
 server=None;thread=None;code=0
 try:
  parser=argparse.ArgumentParser();choice=parser.add_mutually_exclusive_group();choice.add_argument('--demo',action='store_true');choice.add_argument('--config');parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
  if not 0<=args.port<=65535:raise SourceError()
  config=demo_config() if args.demo else None
  if args.config:
   with Path(args.config).open('r',encoding='utf-8-sig') as f:
    text=f.read(65537)
   if len(text)>65536:raise SourceError('RESOURCE_LIMIT')
   config=json.loads(text)
  sources=SavedSources(config);server=SavedServer(('127.0.0.1',args.port),SavedHandler);server.saved=sources
  repo=Path(__file__).resolve().parents[1];server.candidate_sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
  thread=threading.Thread(target=server.serve_forever);thread.start()
  print(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}/saved',port=server.server_port,candidate_sha=server.candidate_sha,mode='SYNTHETIC' if args.demo else 'SOURCES_CONFIGURED' if config else 'SOURCES_DISABLED')),flush=True)
  try:sys.stdin.readline()
  except KeyboardInterrupt:pass
 except Exception:
  print('SAVED_PREVIEW_FAILED',file=sys.stderr);code=1
 finally:
  if server:
   try:
    server.session.end();time.sleep(3)
    if thread:server.shutdown()
    server.server_close()
    if thread:
     thread.join(5)
     if thread.is_alive():code=1
    from .r2_diagnostics import FATAL
    if any(server.diagnostics.snapshot()['counters'][k] for k in FATAL):code=1
   except Exception:print('SAVED_SHUTDOWN_FAILED',file=sys.stderr);code=1
 return code
if __name__=='__main__':raise SystemExit(main())
