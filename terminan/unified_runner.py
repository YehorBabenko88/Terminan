"""Single owner, single listener, no source/worker processes started implicitly."""
import argparse,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
from .unified_server import UnifiedServer,UnifiedHandler
from .saved_sources import SavedSources,demo_config
from .r2_diagnostics import FATAL

def provenance():
    repo=Path(__file__).resolve().parents[1]
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
    return dict(candidate_sha=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),source_clean=not bool(git('status','--porcelain')))

def main():
    server=None;thread=None;code=50
    try:
        parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--expected-sha');parser.add_argument('--cache-db')
        choice=parser.add_mutually_exclusive_group();choice.add_argument('--demo',action='store_true');choice.add_argument('--config')
        args=parser.parse_args()
        if not 0<=args.port<=65535:raise ValueError()
        source=provenance()
        if not source['source_clean'] or args.expected_sha and source['candidate_sha']!=args.expected_sha:raise ValueError()
        # Legacy env connectors must never silently opt this runtime into production.
        for key in ('TERMINAN_GRID_DSN','TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB'):os.environ.pop(key,None)
        config=demo_config() if args.demo else None
        if args.config:
            with Path(args.config).open(encoding='utf-8-sig') as stream:raw=stream.read(65537)
            if len(raw)>65536:raise ValueError()
            config=json.loads(raw)
        sources=SavedSources(config)
        server=UnifiedServer(('127.0.0.1',args.port),UnifiedHandler);server.saved=sources
        server.candidate_sha=source['candidate_sha'];server.source_clean=source['source_clean'];server.cache_error=False
        if args.cache_db:
            try:
                from .cache_monitor import reader,read_status,require_index
                from .saved_cache import ALGORITHM,EXACT_INDEX
                db=Path(args.cache_db).resolve(strict=True)
                with reader(db) as con:
                    require_index(con,EXACT_INDEX);require_index(con,'cache_jobs_updated_idx')
                    columns={row[1] for row in con.execute('PRAGMA table_info(cache_previews)')}
                    if not {'cache_key','entry_hash','identity_hash','content_hash','payload'}<=columns:raise ValueError()
                    if con.execute("SELECT 1 FROM cache_jobs WHERE json_valid(identity_json)=0 OR json_extract(identity_json,'$.algorithm') IS NOT ? LIMIT 1",(ALGORITHM,)).fetchone():raise ValueError()
                read_status(db);server.cache_db=db
            except (OSError,ValueError,__import__('sqlite3').Error):server.cache_error=True
        thread=threading.Thread(target=server.serve_forever,name='terminan-http-owner');thread.start()
        print(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}',port=server.server_port,pid=os.getpid(),**source,mode='READ_ONLY',terminal='SYNTHETIC',sources='SYNTHETIC_FIXTURES' if args.demo else 'CONFIGURED' if config else 'UNAVAILABLE',cache='UNAVAILABLE' if server.cache_error else 'READ_ONLY' if server.cache_db else 'DISABLED')),flush=True)
        code=0
        try:sys.stdin.readline()
        except KeyboardInterrupt:pass
    except (Exception,KeyboardInterrupt):
        print('UNIFIED_STARTUP_FAILED',file=sys.stderr);code=50
    finally:
        if server:
            # Repeated console Ctrl+C must not skip owner cleanup.
            signal.signal(signal.SIGINT,signal.SIG_IGN)
            if hasattr(signal,'SIGBREAK'):signal.signal(signal.SIGBREAK,signal.SIG_IGN)
            try:
                server.session.end()
                if thread:
                    time.sleep(3) # receipt grace, listener still serving SESSION_ENDED
                    server.shutdown()
                server.server_close()
                if thread:thread.join(6)
                diag=server.diagnostics.snapshot()
                if thread and thread.is_alive() or diag['active_workers'] or any(diag['counters'][k] for k in FATAL):code=40
            except (Exception,KeyboardInterrupt):code=40;print('UNIFIED_SHUTDOWN_FAILED',file=sys.stderr)
    return code
if __name__=='__main__':raise SystemExit(main())
