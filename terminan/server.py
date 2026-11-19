"""Loopback-only static UI and bounded JSON endpoints."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit
from . import data
from .levels import merge_levels
from .monitor import fleet_snapshot

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Offline paper replay only. Never exposes order or market-write routes."""
        from .paper import replay_paper
        from urllib.parse import urlsplit
        from json import JSONDecodeError

        if urlsplit(self.path).path != "/api/paper/replay" or urlsplit(self.path).query:
            return self.send_error(404)
        status, result = 400, {"error": "INVALID_OFFLINE_REPLAY"}
        try:
            self.connection.settimeout(3)
            host = self.headers.get("Host", "")
            if (not (host.startswith("127.0.0.1:") or
                     host.startswith("localhost:")) or
                    not host.rsplit(":", 1)[-1].isdigit() or
                    self.headers.get("Origin") not in
                    (None, "http://" + host) or
                    self.headers.get("Transfer-Encoding") or
                    self.headers.get("Content-Encoding") or
                    (self.headers.get("Content-Type") or "").split(";", 1)[0]
                    .strip().lower() != "application/json"):
                raise ValueError("invalid request provenance")
            length = self.headers.get("Content-Length", "")
            if not length.isdecimal() or not 0 < int(length) <= 262144:
                raise ValueError("bounded offline request required")
            raw = self.rfile.read(int(length))
            if len(raw) != int(length):
                raise ValueError("incomplete offline request")
            def unique_pairs(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate JSON key")
                    result[key] = value
                return result
            request = json.loads(
                raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(
                    ValueError("non-finite JSON number")))
            result = replay_paper(request)
            status = 200
        except ImportError:
            status, result = 503, {"error": "MATH_SDK_UNAVAILABLE"}
        except (ValueError, UnicodeError, JSONDecodeError):
            pass  # Never leak input or internal errors.
        except Exception:
            status, result = 503, {"error": "OFFLINE_REPLAY_UNAVAILABLE"}
        body = json.dumps(result, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
                elif url.path == "/api/grid/source": result = data.grid_source_status()
                elif url.path == "/api/status": result = {"mode":"READ_ONLY","strattester":bool(os.environ.get("TERMINAN_STRATTESTER_DB")),"grid":bool(os.environ.get("TERMINAN_GRID_DSN") or os.environ.get("TERMINAN_GRID_API_PORT")),"grid_source":data.grid_source_status(),"research":bool(os.environ.get("TERMINAN_RESULTS_DB"))}
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
