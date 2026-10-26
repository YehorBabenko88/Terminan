"""Synthetic-only HTTP dispatch. Legacy DB routes are never delegated."""
import copy
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from .server import ThreadingHTTPServer
from .synthetic import frame, BASE_MS, SCENARIOS
from .synthetic_contracts import fixtures, validate_fixture

class R2Server(ThreadingHTTPServer):
    candidate_sha='UNVERIFIED'
    source_clean=False

class R2Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,value,content='application/json; charset=utf-8'):
        body=value if isinstance(value,bytes) else json.dumps(value,allow_nan=False,separators=(',',':')).encode()
        self.send_response(status)
        for name,val in [('Content-Type',content),('Content-Length',str(len(body))),
                         ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),
                         ('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")]:
            self.send_header(name,val)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):
        host=self.headers.get('Host','')
        if host not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'} or self.headers.get('Origin') not in (None,'http://'+host):
            return self.send(403,{'error':'local origin required','mode':'SYNTHETIC'})
        if len(self.path)>2048:return self.send(414,{'error':'request too long'})
        url=urlsplit(self.path)
        if url.scheme or url.netloc:return self.send(400,{'error':'relative path required'})
        assets={'/':'r2_preview.html','/preview':'r2_preview.html','/r2_preview.js':'r2_preview.js','/r2_preview.css':'r2_preview.css'}
        if url.path=='/favicon.ico':return self.send(204,b'','image/x-icon')
        if url.path in assets:
            path=Path(__file__).with_name(assets[url.path])
            content='text/html' if path.suffix=='.html' else 'text/javascript' if path.suffix=='.js' else 'text/css'
            return self.send(200,path.read_bytes(),content+'; charset=utf-8')
        if url.path=='/api/status':
            return self.send(200,dict(mode='SYNTHETIC',sources='DISABLED',execution='DISABLED',candidate_sha=self.server.candidate_sha,source_clean=self.server.source_clean))
        if url.path not in ('/api/synthetic/frame','/api/synthetic/contracts'):return self.send(404,{'error':'synthetic route not found'})
        try:
            query=parse_qs(url.query,keep_blank_values=True,max_num_fields=6)
            if any(len(v)!=1 for v in query.values()) or set(query)-{'seed','step','symbol','timeframe','scenario'}:raise ValueError()
            params={k:v[0] for k,v in query.items()}
            for key in ('seed','step'):
                if key in params:
                    if not params[key].isascii() or not params[key].isdecimal() or len(params[key])>10:raise ValueError()
                    params[key]=int(params[key])
            if url.path.endswith('/frame'):
                result=frame(**params)
            else:
                # Validate even parameters unused by fixtures; same public bounds.
                if 'step' in params and not 0<=params['step']<=600:raise ValueError()
                if 'seed' in params and not 0<=params['seed']<=2**31-1:raise ValueError()
                if params.get('symbol','BTCUSDT') not in ('BTCUSDT','ETHUSDT','SOLUSDT') or params.get('timeframe','1m') not in ('1m','5m','15m','1h'):raise ValueError()
                scenario=params.get('scenario','normal')
                if scenario not in SCENARIOS:raise ValueError()
                now=BASE_MS+params.get('step',0)*1000
                views=[]
                for raw in fixtures():
                    raw=copy.deepcopy(raw)
                    if scenario=='unavailable':raw['source_state']='UNAVAILABLE'
                    elif scenario=='schema-mismatch':raw['schema_version']=99
                    elif scenario=='future':raw['rows'][0]['available_at_ms']=now+1
                    elif scenario=='nan':
                        raw['rows'][0]['available_at_ms']=float('nan')
                    elif scenario=='partial':
                        raw['rows']=raw['rows'][::2]
                        raw['complete_price_levels']=False
                    views.append(validate_fixture(raw,now))
                result=dict(version=1,mode='SYNTHETIC',sources=views)
            result['candidate_sha']=self.server.candidate_sha
            return self.send(200,result)
        except (ValueError,TypeError,KeyError):
            return self.send(400,{'error':'invalid synthetic replay request','mode':'SYNTHETIC'})
        except Exception:
            return self.send(500,{'error':'synthetic generator failure','mode':'SYNTHETIC'})
