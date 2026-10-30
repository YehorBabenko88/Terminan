"""Loopback-only static UI and bounded JSON endpoints."""
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as BaseHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit
from . import data
from .levels import merge_levels, level_history_quality
from .monitor import fleet_snapshot
from .g0_sources import all_sources, snapshot
from . import math_bridge
from . import history_overlay

def source_rows(kind,symbol,timeframe='1m'):
    view=snapshot(kind,symbol,timeframe=timeframe)
    if view['state'] in ('SCHEMA_MISMATCH','INVALID_DATA','UNAVAILABLE'):
        raise RuntimeError('source unavailable')
    return view['rows']

class ThreadingHTTPServer(BaseHTTPServer):
    daemon_threads=True
    block_on_close=False
    request_queue_size=16
    def __init__(self,*args,**kwargs):
        self.slots=threading.BoundedSemaphore(16)
        super().__init__(*args,**kwargs)
    def get_request(self):
        request,address=super().get_request()
        request.settimeout(5)
        return request,address
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n')
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,address)
        except BaseException:
            self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        host=self.headers.get('Host','')
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        origin=self.headers.get('Origin')
        if host not in allowed or origin!='http://'+host:
            return self.send_error(403,'Local origin required')
        if self.path not in ('/api/history-overlay/validate','/api/math/evaluate','/api/math/graph','/api/math/ports','/api/math/formula','/api/math/scientific','/api/math/units'):
            return self.send_error(404)
        if self.headers.get('Content-Type')!='application/json':
            return self.send_error(415)
        rawlen=self.headers.get('Content-Length','')
        allow_unified=os.environ.get('TERMINAN_UNIFIED_CONTRACT_IMPORT')=='1'
        limit=(history_overlay.UNIFIED_LIMIT if allow_unified else history_overlay.LIMIT) if self.path=='/api/history-overlay/validate' else 262144
        if not rawlen.isascii() or not rawlen.isdecimal() or len(rawlen)>8 or not 2<=int(rawlen)<=limit:
            return self.send_error(413)
        try:
            raw=self.rfile.read(int(rawlen))
            result=history_overlay.admit(raw,allow_unified=allow_unified) if self.path=='/api/history-overlay/validate' else math_bridge.describe_units(raw) if self.path=='/api/math/units' else math_bridge.execute_scientific(raw) if self.path=='/api/math/scientific' else math_bridge.evaluate_formula(raw) if self.path=='/api/math/formula' else math_bridge.execute_port_graph(raw) if self.path=='/api/math/ports' else math_bridge.execute_graph(raw) if self.path=='/api/math/graph' else math_bridge.evaluate(raw)
            body=json.dumps(result,allow_nan=False).encode()
            code=200
        except (ValueError, TypeError) as exc:
            safe = str(exc) if self.path in ('/api/math/scientific','/api/math/units') and str(exc) in ('BRIDGE_DISABLED','BODY_LIMIT','RESPONSE_LIMIT','INVALID_SCIENTIFIC_REQUEST','MATH_ENGINE_UNAVAILABLE','UNTRUSTED_GRAPH_RESULT') else 'MATH_RESEARCH_UNAVAILABLE'
            if self.path=='/api/history-overlay/validate':
                safe=str(exc) if str(exc).isascii() and str(exc).replace('_','').isalnum() and len(str(exc))<=64 else 'INVALID_PACKET'
            body=json.dumps({'error':safe,'execution_authority':False,'trading_authorized':False}).encode()
            code=422
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self,*args):
        pass  # Request paths/queries may contain private identifiers.
    def do_GET(self):
        if hasattr(self,'headers'):
            host=self.headers.get('Host','')
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}',f'[::1]:{self.server.server_port}'}
            if host not in allowed or self.headers.get('Origin') not in (None,'http://'+host):
                return self.send_error(403,'Local origin required')
        if len(self.path)>2048:return self.send_error(414)
        url = urlsplit(self.path)
        if url.path in ('/math-assets/lab.css','/math-assets/lab_graph.js','/math-assets/lab_ui.js','/math-assets/lab_catalog.js','/math-assets/lab_results.js','/math-assets/lab_protocol.js','/math-assets/math-example.json'):
            name = url.path.rsplit('/', 1)[1]
            body = files('terminan').joinpath(name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/css; charset=utf-8' if name.endswith('.css') else 'application/json; charset=utf-8' if name.endswith('.json') else 'application/javascript; charset=utf-8')
        elif url.path == "/history-overlay":
            body = files("terminan").joinpath("history_overlay.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        elif url.path == "/history-assets/overlay.js":
            body = files("terminan").joinpath("history_overlay.js").read_bytes()
            self.send_response(200); self.send_header("Content-Type","application/javascript; charset=utf-8")
        elif url.path in ("/", "/monitor", "/math"):
            body = files("terminan").joinpath("math_lab.html" if url.path == "/math" else "monitor.html" if url.path == "/monitor" else "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        elif url.path.startswith("/api/"):
            try:
                q = parse_qs(url.query,keep_blank_values=True,max_num_fields=12)
                if any(len(v)!=1 for v in q.values()):raise ValueError()
                data.validate(q.get('symbol',['BTCUSDT'])[0],q.get('timeframe',['1m'])[0])
            except ValueError:
                return self.send_error(400,'Invalid query')
            symbol = q.get("symbol",["BTCUSDT"])[0]
            timeframe = q.get("timeframe",["1m"])[0]
            try:
                if url.path == '/api/math/catalog': result=math_bridge.scientific_catalog()
                elif url.path == '/api/math/health': result=math_bridge.check()
                elif url.path == '/api/sources': result=all_sources(symbol,timeframe)
                elif url.path == "/api/monitor": result = fleet_snapshot()
                elif url.path == "/api/instruments": result = data.instruments()
                elif url.path == "/api/candles": result = source_rows('strattester',symbol,timeframe)
                elif url.path == "/api/research": result = source_rows('research',symbol)
                elif url.path == "/api/levels":
                    data.validate(symbol)
                    from datetime import datetime, timezone
                    now=int(datetime.now(timezone.utc).timestamp()*1000)
                    series={}
                    for tf in ("1h","4h","1d"):
                        series[tf]=[{"t":r.get("t"),"h":r.get("h"),"l":r.get("l"),"complete":r.get("complete",True)} for r in source_rows('strattester',symbol,tf)]
                    levels=merge_levels(series,now)
                    result={'version':1,'symbol':symbol,'levels':levels,'history':level_history_quality(series,now)} if q.get('diagnostics',['0'])[0]=='1' else levels
                elif url.path == "/api/logs":
                    data.validate(symbol)
                    result={"symbol":symbol,"events":[],"state":"SOURCE_ADAPTER_NOT_CONNECTED"}
                elif url.path == "/api/grid/candles": result = source_rows('grid',symbol)
                elif url.path == "/api/grid/footprint": result = source_rows('footprint',symbol)
                elif url.path == "/api/status": result = {"mode":"READ_ONLY","strattester":bool(os.environ.get("TERMINAN_STRATTESTER_DB")),"grid":bool(os.environ.get("TERMINAN_GRID_DSN")),"research":bool(os.environ.get("TERMINAN_RESULTS_DB"))}
                else: return self.send_error(404)
                body = json.dumps(result,allow_nan=False,default=str).encode()
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
            except ValueError as exc:
                body = json.dumps({"error":str(exc)}).encode(); self.send_response(400); self.send_header("Content-Type","application/json")
            except Exception:
                body = b'{"error":"source unavailable"}'; self.send_response(503); self.send_header("Content-Type","application/json")
        else:
            return self.send_error(404)
        self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Security-Policy","default-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

def run():
    host=os.environ.get("TERMINAN_HOST","127.0.0.1")
    if host not in ("127.0.0.1","localhost","::1"):
        raise SystemExit("Remote binding disabled until authentication is implemented")
    raw_port=os.environ.get("TERMINAN_PORT","8765")
    if not raw_port.isascii() or not raw_port.isdecimal() or len(raw_port)>5 or not 1<=int(raw_port)<=65535:
        raise SystemExit("TERMINAN_PORT must be an integer from 1 to 65535")
    port=int(raw_port)
    ThreadingHTTPServer.address_family=socket.AF_INET6 if host=='::1' else socket.AF_INET
    server=ThreadingHTTPServer((host,port),Handler)
    print(f"Terminan read-only: http://{host}:{port}")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
