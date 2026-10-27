"""Owned synthetic loopback child; all request workers finish before interpreter exit."""
import argparse,json,os,subprocess,sys,threading,time
from pathlib import Path
from .r2_server import R2Handler,R2Server

def write_new(path,value):
    path=Path(path)
    if path.exists():raise ValueError()
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('x',encoding='utf-8') as stream:json.dump(value,stream,allow_nan=False)
    os.replace(temporary,path)

class PrivateParser(argparse.ArgumentParser):
    def error(self,message):raise ValueError()

def main(argv=None):
    server=None;thread=None;serving_started=False;code=0;args=None;shutdown_started=None
    try:
        parser=PrivateParser();parser.add_argument('--ready');parser.add_argument('--diagnostics');parser.add_argument('--r4',action='store_true');args=parser.parse_args(argv)
        for key in list(os.environ):
            if key.startswith('TERMINAN_'):os.environ.pop(key,None)
        server_type,handler=R2Server,R2Handler
        if args.r4:
            from .r4_server import R4Server,R4Handler
            server_type,handler=R4Server,R4Handler
        server=server_type(('127.0.0.1',0),handler)
        repo=Path(__file__).resolve().parents[1]
        server.candidate_sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
        server.source_clean=not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=normal'],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
        def serve():
            try:server.serve_forever()
            except BaseException:server.report_failure('RUNNER_FAILURE','runner')
        thread=threading.Thread(target=serve,daemon=False);thread.start();serving_started=True
        info=dict(host='127.0.0.1',port=server.server_port,mode='SYNTHETIC',sources='DISABLED',candidate_sha=server.candidate_sha,source_clean=server.source_clean,diagnostics_version=1)
        if args.ready:write_new(args.ready,info)
        print(json.dumps(info),flush=True)
        try:sys.stdin.readline()
        except KeyboardInterrupt:pass
    except (Exception,KeyboardInterrupt):
        code=1;sys.stderr.write('R2_DIAGNOSTIC RUNNER_FAILURE\n');sys.stderr.flush()
    finally:
        if server:
            try:
                shutdown_started=time.monotonic()
                if hasattr(server,'session'):
                    server.session.end();time.sleep(3) # Bounded explicit receipt grace, never inferred from refusal.
                if serving_started:server.shutdown()
                # Non-daemon bounded request workers are joined by server_close.
                # Parent owns the hard shutdown deadline and kills this child on timeout.
                server.server_close()
                if serving_started:
                    thread.join(6)
                    if thread.is_alive():raise RuntimeError()
                from .r2_diagnostics import FATAL
                if any(server.diagnostics.snapshot()['counters'][kind] for kind in FATAL):code=1
                if args and args.diagnostics:
                    write_new(args.diagnostics,dict(version=1,mode='SYNTHETIC',candidate_sha=server.candidate_sha,shutdown_complete=True,shutdown_elapsed_ms=round((time.monotonic()-shutdown_started)*1000,3),diagnostics=server.diagnostics.snapshot(),**({'r4_session':server.session.diagnostics()} if hasattr(server,'session') else {})))
            except (Exception,KeyboardInterrupt):code=1;sys.stderr.write('R2_DIAGNOSTIC RUNNER_FAILURE\n');sys.stderr.flush()
    return code
if __name__=='__main__':raise SystemExit(main())
