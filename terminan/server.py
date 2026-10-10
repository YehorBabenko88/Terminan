"""Loopback-only static UI and bounded JSON endpoints."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit
from . import data
from .levels import merge_levels
from .monitor import fleet_snapshot
from .gateway_client import fetch_source

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in ("/", "/monitor"):
            body = files("terminan").joinpath("monitor.html" if url.path == "/monitor" else "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        elif url.path.startswith("/api/"):
            q = parse_qs(url.query)
            symbol = q.get("symbol",["BTCUSDT"])[0]
            timeframe = q.get("timeframe",["1m"])[0]
            try:
                if url.path == "/api/monitor":
                    remote=fetch_source("grid","/v1/nodes")
                    if remote.get("state")=="NOT_CONFIGURED": result=fleet_snapshot()
                    else:
                        from datetime import datetime,timezone
                        now=datetime.now(timezone.utc)
                        nodes=[]
                        for n in remote["nodes"]:
                            last=datetime.fromisoformat(n["last_seen"]) if n.get("last_seen") else None
                            age=max(0,(now-last).total_seconds()) if last else None
                            nodes.append({**n,"age_seconds":age,"online":age is not None and age<=120})
                        result={"source":"cluster-grid.gateway","nodes":nodes,"online":sum(n["online"] for n in nodes),"total":len(nodes),"database_sizes":{"state":"NOT_EXPOSED_BY_SOURCE"},"auxiliary_services":{"state":"NOT_EXPOSED_BY_SOURCE"}}
                elif url.path == "/api/instruments":
                    remote=fetch_source("grid","/v1/instruments")
                    result=data.instruments() if remote.get("state")=="NOT_CONFIGURED" else remote["symbols"]
                elif url.path == "/api/candles": result = data.candles(symbol,timeframe)
                elif url.path == "/api/research":
                    remote=fetch_source("strattester","/v1/runs",{"symbol":symbol})
                    result=data.research(symbol) if remote.get("state")=="NOT_CONFIGURED" else remote["runs"]
                elif url.path == "/api/levels":
                    data.validate(symbol)
                    from datetime import datetime, timezone
                    now=int(datetime.now(timezone.utc).timestamp()*1000)
                    series={}
                    for tf in ("1h","4h","1d"):
                        series[tf]=[{"t":int(r["t"]),"h":r["h"],"l":r["l"]} for r in data.candles(symbol,tf,1000)]
                    result=merge_levels(series,now)
                elif url.path == "/api/trades":
                    data.validate(symbol)
                    run_id=q.get("run_id",[""])[0]
                    if not run_id or len(run_id)>160: raise ValueError("invalid run ID")
                    result=fetch_source("strattester","/v1/trades",{"symbol":symbol,"run_id":run_id})
                elif url.path == "/api/logs":
                    data.validate(symbol)
                    result={"symbol":symbol,"events":[],"state":"SOURCE_ADAPTER_NOT_CONNECTED"}
                elif url.path == "/api/grid/candles":
                    remote=fetch_source("grid","/v1/candles",{"symbol":symbol})
                    result=data.grid_candles(symbol) if remote.get("state")=="NOT_CONFIGURED" else remote["rows"]
                elif url.path == "/api/grid/footprint":
                    remote=fetch_source("grid","/v1/footprint",{"symbol":symbol})
                    result=data.footprint(symbol) if remote.get("state")=="NOT_CONFIGURED" else remote["rows"]
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
