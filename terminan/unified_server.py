"""One loopback dispatcher; existing Saved/R4 transport/session gates stay authoritative."""
import socket,threading,time
from pathlib import Path
from urllib.parse import urlsplit
from .saved_server import SavedServer, SavedHandler
from .server import Handler as LegacyHandler
from .infrastructure import infrastructure_snapshot
from .cache_monitor import HTML as CACHE_HTML

PAGES={'/':'terminal','/saved':'saved','/math':'math','/history-overlay':'history-overlay','/monitor':'monitor','/cache':'cache'}
ASSETS={'/unified.js':'unified.js','/unified.css':'unified.css'}
class UnifiedServer(SavedServer):
    # Track/join our bounded workers explicitly; a failed deadline cannot hang exit.
    daemon_threads=True
    block_on_close=False
    request_budget_seconds=5
    def __init__(self,*args,**kwargs):
        self.runtime_lock=threading.Lock();self.runtime_workers={}
        super().__init__(*args,**kwargs)
    def process_request_thread(self,request,address):
        worker=threading.current_thread()
        with self.runtime_lock:self.runtime_workers[worker]=request
        def expire():
            self.diagnostics.event('HTTP_IO_TIMEOUT','read')
            try:request.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        timer=threading.Timer(self.request_budget_seconds,expire);timer.daemon=True;timer.start()
        try:super().process_request_thread(request,address)
        finally:
            timer.cancel()
            with self.runtime_lock:self.runtime_workers.pop(worker,None)
    def server_close(self):
        super().server_close()
        with self.runtime_lock:workers=list(self.runtime_workers.items())
        for worker,request in workers:
            try:request.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        deadline=time.monotonic()+6
        for worker,request in workers:worker.join(max(0,deadline-time.monotonic()))

class UnifiedHandler(SavedHandler):
    def gate(self):
        host=self.headers.get('Host','')
        if host not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'} or self.headers.get('Origin') not in (None,'http://'+host):
            self.send(403,{'error':'LOCAL_ORIGIN_REQUIRED'});return None
        if len(self.path)>2048:
            self.send(414,{'error':'REQUEST_LIMIT'});return None
        try:
            url=urlsplit(self.path)
            if url.scheme or url.netloc or url.fragment:raise ValueError()
        except ValueError:
            self.send(400,{'error':'INVALID_TARGET'});return None
        return url
    def send_header(self,key,value):
        if key.lower()=='content-security-policy':
            # Only this loopback runtime permits its own same-origin frames.
            value="default-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'self'; object-src 'none'; frame-ancestors 'self'"
        return super().send_header(key,value)
    def do_GET(self):
        url=self.gate()
        if url is None:return
        path=url.path
        if path.startswith('/api/') and path not in ('/api/session','/api/status') and self.server.session.receipt(self.server.candidate_sha)['state']=='SESSION_ENDED':
            return self.send(410,{'error':'SESSION_ENDED'})
        if path in PAGES:
            if url.query:return self.send(400,{'error':'INVALID_REQUEST'})
            return self.send(200,Path(__file__).with_name('unified.html').read_bytes(),'text/html; charset=utf-8')
        if path in ASSETS:
            name=ASSETS[path]
            return self.send(200,Path(__file__).with_name(name).read_bytes(),'text/css' if name.endswith('.css') else 'text/javascript')
        if path.startswith('/workspace/'):
            if url.query:return self.send(400,{'error':'INVALID_REQUEST'})
            page=path[len('/workspace/'):]
            if page=='terminal':return self.mount('/')
            if page=='saved':return self.mount('/saved')
            if page in ('math','history-overlay'):return self.legacy('/'+page)
            if page=='monitor':return self.send(200,Path(__file__).with_name('infrastructure.html').read_bytes(),'text/html; charset=utf-8')
            if page=='cache':return self.send(200,CACHE_HTML.encode(),'text/html; charset=utf-8')
            return self.send(404,{'error':'NOT_FOUND'})
        if path=='/api/infrastructure':
            if url.query:return self.send(400,{'error':'INVALID_REQUEST'})
            return self.send(200,infrastructure_snapshot())
        if getattr(self.server,'cache_error',False) and (path=='/api/cache/status' or path.startswith('/api/saved/cache-')):
            return self.send(503,{'state':'UNAVAILABLE','error':'CACHE_SCHEMA_OR_SOURCE_UNAVAILABLE','authority':'OFFLINE_ONLY','jobs':[]})
        if path=='/api/cache/status':return self.mount('/api/saved/cache-status'+('?' + url.query if url.query else ''))
        if path=='/api/legacy/status':return self.legacy('/api/status')
        if path in ('/api/session','/api/status','/preview','/r2_preview.js','/r2_preview.css','/r4_protocol.js','/saved.js','/saved_mtf.js','/saved.css','/favicon.ico') or path.startswith(('/api/saved/','/api/synthetic/')):
            return super().do_GET()
        return self.legacy(self.path)
    def mount(self,target):
        original=self.path
        try:self.path=target;return super().do_GET()
        finally:self.path=original
    def legacy(self,target):
        original=self.path
        try:self.path=target;return LegacyHandler.do_GET(self)
        finally:self.path=original
    def do_POST(self):
        if self.gate() is None:return
        if self.server.session.receipt(self.server.candidate_sha)['state']=='SESSION_ENDED':return self.send(410,{'error':'SESSION_ENDED'})
        return LegacyHandler.do_POST(self)
