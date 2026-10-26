"""Loopback-only static UI and bounded JSON endpoints."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

MAX_TARGET_LENGTH = 2048
MAX_QUERY_FIELDS = 12


def valid_host(value, port):
    """Reject DNS rebinding and ambiguous/multiple Host headers."""
    allowed = {f'127.0.0.1:{port}', f'localhost:{port}', f'[::1]:{port}',
               '127.0.0.1', 'localhost', '[::1]'}
    return value in allowed

from . import data
from .levels import merge_levels
from .monitor import fleet_snapshot

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        host_values = self.headers.get_all('Host', [])
        if len(host_values) != 1 or not valid_host(host_values[0], self.server.server_port):
            return self.send_error(403, 'Forbidden host')
        if len(self.path) > MAX_TARGET_LENGTH:
            return self.send_error(414, 'Request target too long')
        url = urlsplit(self.path)
        if url.scheme or url.netloc or url.fragment:
            return self.send_error(400, 'Invalid request target')
        if url.query.count('&') >= MAX_QUERY_FIELDS:
            return self.send_error(400, 'Too many query fields')
        if url.path in ("/", "/monitor"):
            body = files("terminan").joinpath("monitor.html" if url.path == "/monitor" else "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        elif url.path.startswith("/api/"):
            q = parse_qs(url.query)
            symbol = q.get("symbol",["BTCUSDT"])[0]
            timeframe = q.get("timeframe",["1m"])[0]
            try:
                if url.path == "/api/monitor": result = fleet_snapshot()
                elif url.path == "/api/instruments": result = data.instruments()
                elif url.path == "/api/candles": result = data.candles(symbol,timeframe)
                elif url.path == "/api/research": result = data.research(symbol)
                elif url.path == "/api/levels":
                    data.validate(symbol)
                    from datetime import datetime, timezone
                    now=int(datetime.now(timezone.utc).timestamp()*1000)
                    series={}
                    for tf in ("1h","4h","1d"):
                        series[tf]=[{"t":int(r["t"]),"h":r["h"],"l":r["l"]} for r in data.candles(symbol,tf,1000)]
                    result=merge_levels(series,now)
                elif url.path == "/api/logs":
                    data.validate(symbol)
                    result={"symbol":symbol,"events":[],"state":"SOURCE_ADAPTER_NOT_CONNECTED"}
                elif url.path == "/api/grid/candles": result = data.grid_candles(symbol)
                elif url.path == "/api/grid/footprint": result = data.footprint(symbol)
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
    server=ThreadingHTTPServer((host,8765),Handler)
    print("Terminan read-only: http://127.0.0.1:8765")
    server.serve_forever()
