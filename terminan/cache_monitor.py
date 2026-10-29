"""Standalone, opt-in loopback-only read-only cache status dashboard.

No queue writes, computation, upstream access, or background worker startup.
Open only an explicitly selected SQLite file in immutable read-only mode.
"""
from __future__ import annotations
import argparse
import hashlib
import math
import time
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Terminan cache monitor</title>
<style>body{font:14px system-ui;background:#101925;color:#dce8f4;margin:24px}
h1{font-size:20px}table{border-collapse:collapse;width:100%}
th,td{padding:9px;border-bottom:1px solid #334359;text-align:left}
small{color:#94a9bd}button{background:#20364b;color:#fff;border:1px solid #567;padding:8px}
.error{color:#ff9aa4}</style>
<h1>Terminan — Offline Cache Monitor</h1>
<p><small>Local read-only SQLite status. No live Grid / Strattester authority.</small></p>
<button id="refresh">Refresh</button> <span id="state">Loading</span>
<table><thead><tr><th>Job</th><th>State</th><th>Attempts</th><th>Error</th></tr></thead>
<tbody id="jobs"></tbody></table>
<script>
'use strict';
const el=id=>document.getElementById(id);
async function refresh(){
 try{
  const r=await fetch('/api/cache/status',{cache:'no-store'});
  if(!r.ok)throw Error('STATUS_UNAVAILABLE');
  const d=await r.json();
  el('state').textContent='Entries '+d.entries+' · Jobs '+d.jobs.length+' · '+d.mode;
  el('state').className='';
  el('jobs').replaceChildren();
  for(const j of d.jobs){
   const tr=document.createElement('tr');
   for(const k of ['job_id','state','attempt','error_code']){
    const td=document.createElement('td');td.textContent=String(j[k]??'');tr.append(td);
   }
   el('jobs').append(tr);
  }
 }catch(_){el('state').textContent='UNAVAILABLE';el('state').className='error';}
}
el('refresh').onclick=refresh;refresh();
</script></html>"""

def read_status(db):
    # URI mode=ro guarantees no schema creation or mutation.
    con=sqlite3.connect(Path(db).resolve().as_uri()+"?mode=ro",uri=True,timeout=1)
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("PRAGMA busy_timeout=1000")
        jobs=con.execute("""SELECT job_id,state,attempt,error_code FROM cache_jobs
            ORDER BY updated_at DESC,job_id LIMIT 100""").fetchall()
        entries=con.execute("SELECT count(*) FROM cache_entries").fetchone()[0]
        return {"mode":"READ_ONLY","authority":"OFFLINE_ONLY","entries":entries,
                "jobs":[dict(job_id=j[0],state=j[1],attempt=j[2],error_code=j[3]) for j in jobs]}
    finally:
        con.close()

def read_job_result(db, job_id, now=None):
    """Return only bounded, integrity-checked, completed offline cache results."""
    if not isinstance(job_id,str) or len(job_id)!=32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("INVALID_JOB_ID")
    now=int(time.time()) if now is None else int(now)
    con=sqlite3.connect(Path(db).resolve().as_uri()+"?mode=ro",uri=True,timeout=1)
    try:
        con.execute("PRAGMA query_only=ON")
        row=con.execute("""SELECT j.state,j.identity_json,e.identity_json,
            e.content_hash,e.payload,e.expires_at
            FROM cache_jobs j LEFT JOIN cache_entries e ON e.cache_key=j.cache_key
            WHERE j.job_id=?""",(job_id,)).fetchone()
        if row is None:return {"state":"NOT_FOUND"}
        state,job_identity,entry_identity,expected,raw,expires=row
        if state!="READY":return {"state":state}
        if raw is None:return {"state":"MISSING"}
        if expires<=now:return {"state":"EXPIRED"}
        if len(raw)>4*1024*1024 or hashlib.sha256(raw).hexdigest()!=expected:
            return {"state":"CORRUPT"}
        try:
            identity=json.loads(job_identity)
            if identity!=json.loads(entry_identity):return {"state":"STALE"}
            data=json.loads(raw)
            if data.get("state")!="HISTORICAL_ONLY" or data.get("complete") is not True or data.get("source_revision")!=identity["source_revision"]:
                return {"state":"STALE"}
            candles=data.get("candles")
            if not isinstance(candles,list) or len(candles)>10000:return {"state":"CORRUPT"}
            if any(not isinstance(c,dict) or not isinstance(c.get("ts"),int) or
                   not all(type(c.get(k)) in (int,float) and math.isfinite(c[k]) for k in ("open","high","low","close","volume","delta"))
                   for c in candles):return {"state":"CORRUPT"}
        except (ValueError,TypeError,KeyError,AttributeError):
            return {"state":"CORRUPT"}
        # Deliberately do not return raw footprint, source payload, paths or identity.
        return {"state":"READY","authority":"OFFLINE_ONLY","dataset":identity["dataset"],
                "symbol":identity["symbol"],"timeframe":identity["timeframe"],
                "source_revision":identity["source_revision"],"sha256":expected,
                "total_candles":len(candles),
                "candles":[{k:c[k] for k in ("ts","open","high","low","close","volume","delta")}
                           for c in candles[:64]]}
    finally:
        con.close()

def lookup_exact_cache(db, source_revision, symbol, timeframe, from_ms, to_ms, now=None):
    """Only return a cache hit for a unique, exact, revision-pinned query."""
    if not isinstance(source_revision,str) or len(source_revision)!=64 or any(c not in "0123456789abcdef" for c in source_revision):
        raise ValueError("INVALID_REVISION")
    if not isinstance(symbol,str) or not 1<=len(symbol)<=80 or not all(c.isalnum() or c in "_-" for c in symbol):
        raise ValueError("INVALID_SYMBOL")
    if timeframe not in ("1m","5m","15m","1h","4h","1d"):
        raise ValueError("INVALID_TIMEFRAME")
    if type(from_ms) is not int or type(to_ms) is not int or not 946684800000<=from_ms<=to_ms<=2**53-1:
        raise ValueError("INVALID_RANGE")
    con=sqlite3.connect(Path(db).resolve().as_uri()+"?mode=ro",uri=True,timeout=1)
    try:
        con.execute("PRAGMA query_only=ON")
        # Filter before limiting: unrelated jobs must never mask a valid hit.
        # JSON fields are bound parameters, not interpolated SQL.
        rows=con.execute("""SELECT j.job_id,j.identity_json FROM cache_jobs j
            WHERE j.state='READY'
            AND json_valid(j.identity_json)
            AND json_extract(j.identity_json,'$.source')='grid'
            AND json_extract(j.identity_json,'$.dataset')='candles_1m'
            AND json_extract(j.identity_json,'$.source_revision')=?
            AND json_extract(j.identity_json,'$.symbol')=?
            AND json_extract(j.identity_json,'$.timeframe')=?
            AND json_extract(j.identity_json,'$.from_ms')=?
            AND json_extract(j.identity_json,'$.to_ms')=?
            ORDER BY j.job_id LIMIT 2""",
            (source_revision,symbol,timeframe,from_ms,to_ms)).fetchall()
        if not rows:return {"state":"MISS","authority":"OFFLINE_ONLY"}
        if len(rows)>1:return {"state":"AMBIGUOUS","authority":"OFFLINE_ONLY"}
        try:
            identity=json.loads(rows[0][1])
            if not isinstance(identity,dict) or identity.get("source_revision")!=source_revision:
                return {"state":"UNAVAILABLE","authority":"OFFLINE_ONLY"}
        except (ValueError,TypeError,AttributeError):
            return {"state":"UNAVAILABLE","authority":"OFFLINE_ONLY"}
        job_id=rows[0][0]
    finally:
        con.close()
    result=read_job_result(db,job_id,now=now)
    if result.get("state")!="READY":return {"state":result.get("state","UNAVAILABLE"),"authority":"OFFLINE_ONLY"}
    if result.get("source_revision")!=source_revision or result.get("symbol")!=symbol or result.get("timeframe")!=timeframe:
        return {"state":"STALE","authority":"OFFLINE_ONLY"}
    return dict(result,match="EXACT_SOURCE_REVISION_AND_RANGE")

def serve(db,port):
    if not Path(db).is_file():
        raise ValueError("CACHE_DB_NOT_FOUND")
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            host=self.headers.get("Host","")
            if host not in (f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"):
                return self.respond(403,{"error":"LOCAL_HOST_REQUIRED"})
            origin=self.headers.get("Origin")
            if origin not in (None,"http://"+host):
                return self.respond(403,{"error":"LOCAL_ORIGIN_REQUIRED"})
            path=urlsplit(self.path)
            if path.query or len(self.path)>1024:
                return self.respond(400,{"error":"INVALID_REQUEST"})
            if path.path=="/":
                return self.respond(200,HTML,"text/html; charset=utf-8")
            if path.path!="/api/cache/status":
                return self.respond(404,{"error":"NOT_FOUND"})
            try:
                return self.respond(200,read_status(db))
            except (sqlite3.Error,OSError,ValueError):
                return self.respond(503,{"error":"CACHE_UNAVAILABLE"})
        def respond(self,status,data,ctype="application/json"):
            raw=data.encode() if isinstance(data,str) else json.dumps(data,sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type",ctype)
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(raw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    server.daemon_threads=True
    try:
        print(json.dumps({"mode":"READ_ONLY","url":f"http://127.0.0.1:{server.server_port}/"}),flush=True)
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--port",type=int,default=0)
    a=p.parse_args(argv)
    try:
        if not 0<=a.port<=65535:raise ValueError("INVALID_PORT")
        serve(a.db,a.port)
        return 0
    except (ValueError,OSError) as e:
        print(json.dumps({"error":"LOCAL_MONITOR_START_FAILED"}))
        return 3

if __name__=="__main__":
    sys.exit(main())
