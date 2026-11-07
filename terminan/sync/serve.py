"""Independent loopback static UI harness. No Control API or synthetic data routes."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT = Path(__file__).resolve().parent
ASSETS = {"/sync.html": (ROOT.parent / "sync.html", "text/html; charset=utf-8"), **{"/sync/" + name: (ROOT / name, mime) for name, mime in [("protocol.js", "text/javascript"), ("client.js", "text/javascript"), ("c3.js", "text/javascript"), ("mux-stream.js", "text/javascript"), ("view.js", "text/javascript"), ("style.css", "text/css")]}}
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never log URLs/cursors, credentials or request bodies.
    def do_GET(self):
        host = self.headers.get("Host", "")
        if host not in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}") or self.headers.get("Origin") not in (None, "http://" + host):
            self.send_error(403); return
        asset = ASSETS.get(self.path)
        if asset is None:
            self.send_error(404); return
        body = asset[0].read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", asset[1])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'none'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(body)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--port", type=int, default=8896)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
