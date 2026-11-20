"""Loopback-only static UI and bounded JSON endpoints."""
import json
import os
import argparse
import hmac
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit
from . import data
from .monitor import fleet_snapshot

def capability_snapshot():
    """Module API admission is distinct from process liveness."""
    return dict(api_version=dict(major=1,minor=0),producer='terminan',
        read_only=True,status='UNAVAILABLE',reason='SOURCE_PROVENANCE_UNAVAILABLE',
        capabilities=dict(offline_analytics=True,offline_paper=True,research_import_validation=True,live_trading=False),
        execution_authority=False,trading_authorized=False)

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Offline paper replay only. Never exposes order or market-write routes."""
        from .paper import replay_paper
        from urllib.parse import urlsplit
        from json import JSONDecodeError

        status, result = 400, {"error": "INVALID_OFFLINE_REPLAY"}
        try:
            self.connection.settimeout(3)
            length = self.headers.get("Content-Length", "")
            if (self.headers.get("Transfer-Encoding")
                    or len(self.headers.get_all("Content-Length", [])) != 1
                    or not length.isdecimal() or not 0 < int(length) <= 262144):
                raise ValueError("bounded offline request required")
            # Consume only the bounded body before rejecting route/origin.
            # Closing with unread TCP data can discard the HTTP rejection
            # through a connection reset on Windows. No rejected JSON is parsed.
            raw = self.rfile.read(int(length))
            if len(raw) != int(length):
                raise ValueError("incomplete offline request")
            if urlsplit(self.path).path not in ("/api/paper/replay", "/api/analytics/orderflow", "/api/analytics/historical") or urlsplit(self.path).query:
                return self.send_error(404)
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
            if urlsplit(self.path).path == "/api/analytics/orderflow":
                from .analytics.api import analyze_orderflow
                result=analyze_orderflow(request)
            elif urlsplit(self.path).path == "/api/analytics/historical":
                from .analytics.api import analyze_historical
                result=analyze_historical(request)
            else:
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
        if url.path in ('/internal/v1/health','/internal/v1/capabilities'):
            body=json.dumps(capability_snapshot(),allow_nan=False).encode()
            self.send_response(503 if url.path.endswith('/health') else 200)
            self.send_header('Content-Type','application/json; charset=utf-8')
        elif url.path == "/health":
            expected=os.environ.get("UNIFIED_INSTANCE_TOKEN","")
            qualified=(re.fullmatch(r"[a-f0-9]{64}",expected) is not None
                and os.environ.get("UNIFIED_MODULE_ID")=="terminan"
                and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+",os.environ.get("UNIFIED_MODULE_VERSION","")) is not None
                and 0<len(os.environ.get("UNIFIED_RELEASE_ID",""))<=128)
            supplied=self.headers.get("Authorization","")
            admission=getattr(self.server,"startup_admission",None)
            current=False
            if qualified and admission is not None:
                try:current=admission.require_current() is True
                except Exception:current=False
            authorized=current and hmac.compare_digest(supplied,"Bearer "+expected)
            if authorized:
                result=dict(module_id="terminan",version=os.environ["UNIFIED_MODULE_VERSION"],
                    release_id=os.environ["UNIFIED_RELEASE_ID"],instance_token=expected,
                    ready=True,mode="READ_ONLY",execution_authority=False,trading_authorized=False)
            else:
                result=dict(module_id="terminan",ready=False,error="RUNTIME_IDENTITY_NOT_AUTHORIZED",
                    execution_authority=False,trading_authorized=False)
            body=json.dumps(result,allow_nan=False).encode()
            self.send_response(200 if authorized else 503)
            self.send_header("Content-Type","application/json; charset=utf-8")
        elif url.path in ("/", "/monitor"):
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
                    raise RuntimeError("qualified MarketData timeframe series unavailable")
                elif url.path == "/api/logs":
                    data.validate(symbol)
                    result={"symbol":symbol,"events":[],"state":"SOURCE_ADAPTER_NOT_CONNECTED"}
                elif url.path == "/api/market-data/candles": result = data.market_data_candles(symbol)
                elif url.path == "/api/market-data/footprint": result = data.footprint(symbol)
                elif url.path == "/api/market-data/source": result = data.market_data_source_status()
                elif url.path == "/api/status": result = {"mode":"READ_ONLY","market_data":bool(data._market_data_port()),"market_data_source":data.market_data_source_status(),"research":bool(os.environ.get("TERMINAN_RESULTS_DB"))}
                else: return self.send_error(404)
                body = json.dumps(result,allow_nan=False,default=str).encode()
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
                if url.path in ("/api/instruments", "/api/candles"):
                    self.send_header("X-Terminan-Data-Status", "SOURCE_UNQUALIFIED")
            except ValueError as exc:
                body = json.dumps({"error":str(exc)}).encode(); self.send_response(400); self.send_header("Content-Type","application/json")
            except Exception:
                body = b'{"error":"source unavailable"}'; self.send_response(503); self.send_header("Content-Type","application/json")
        else:
            return self.send_error(404)
        self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Security-Policy","default-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

def main(argv=None, *, startup_admission=None):
    parser=argparse.ArgumentParser(description="Canonical read-only terminal and offline paper UI")
    parser.add_argument("--host",default=os.environ.get("TERMINAN_HOST","127.0.0.1"))
    parser.add_argument("--port",type=int,default=int(os.environ.get("TERMINAN_PORT","8765")))
    args=parser.parse_args(argv)
    if args.host not in ("127.0.0.1","localhost") or not 0<=args.port<=65535:
        raise SystemExit("Only bounded IPv4 loopback terminal binding is supported")
    if os.environ.get("UNIFIED_MODULE_ID"):
        if startup_admission is None or startup_admission.require_current() is not True:
            raise ValueError("STARTUP_SOURCE_ADMISSION_REQUIRED")
    data.configure_market_data_client(startup_admission)
    try:
        with ThreadingHTTPServer((args.host,args.port),Handler) as server:
            server.startup_admission=startup_admission
            server.serve_forever()
    finally:
        data._private_market_data_client=None
