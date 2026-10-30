"""Disposable test server: loopback, no configured DB, ephemeral port."""
import json
import sys
import threading
from terminan.server import Handler, ThreadingHTTPServer

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}/math'}), flush=True)
try:
    sys.stdin.readline()
finally:
    server.shutdown(); server.server_close(); thread.join()
