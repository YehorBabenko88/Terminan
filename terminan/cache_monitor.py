"""Standalone, opt-in loopback-only read-only cache status dashboard.

No queue writes, computation, upstream access, or background worker startup.
Open only an explicitly selected SQLite file in WAL-aware read-only mode.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import math
import time
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .saved_cache import key_for, canonical, PERIODS, CacheError, ALGORITHM, EXACT_INDEX

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

@contextlib.contextmanager
def reader(db):
    con=sqlite3.connect(Path(db).resolve().as_uri()+"?mode=ro",uri=True,timeout=.25,isolation_level=None)
    try:
        con.execute('PRAGMA query_only=ON');con.execute('PRAGMA busy_timeout=250')
        deadline=time.monotonic()+.25
        con.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
        con.execute('BEGIN') # one WAL snapshot for lookup, identities and result
        yield con
    finally:con.close()


def require_index(con,name):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",(name,)).fetchone():
        raise ValueError('CACHE_INDEX_REQUIRED')


def read_status(db):
    with reader(db) as con:
        require_index(con,'cache_jobs_updated_idx')
        jobs=con.execute("SELECT substr(job_id,1,33),substr(state,1,9),CASE WHEN typeof(attempt)='integer' THEN attempt END,substr(error_code,1,33) FROM cache_jobs ORDER BY updated_at DESC,job_id LIMIT 100").fetchall()
        for job,state,attempt,error in jobs:
            if type(job) is not str or len(job)!=32 or any(c not in '0123456789abcdef' for c in job) or state not in ('QUEUED','RUNNING','READY','FAILED') or type(attempt) is not int or not 0<=attempt<=3 or error not in (None,'COMPUTE_FAILED','INCOMPLETE','CACHE_FAILED','LEASE_EXHAUSTED'):raise ValueError('CACHE_METADATA_INVALID')
        entries=con.execute('SELECT count(*) FROM cache_entries').fetchone()[0]
        return dict(mode='READ_ONLY',authority='OFFLINE_ONLY',entries=entries,
            jobs=[dict(job_id=j[0],state=j[1],attempt=j[2],error_code=j[3]) for j in jobs])


def checked_preview(identity,data,full_hash):
    minutes=PERIODS.get(identity['timeframe']);start,end=identity['from_ms'],identity['to_ms']
    if not minutes or start%(minutes*60000) or (end+60000)%(minutes*60000):raise ValueError()
    expected=(end-start+60000)//(minutes*60000)
    keys={'state','authority','dataset','symbol','timeframe','source_revision','sha256','from_ms','to_ms','algorithm','parameters_hash','total_candles','truncated','integrity_scope','candles','expires_at'}
    if type(data) is not dict or set(data)!=keys or type(full_hash) is not str or len(full_hash)!=64 or any(c not in '0123456789abcdef' for c in full_hash) or data.get('state')!='READY' or data.get('authority')!='OFFLINE_ONLY' or data.get('sha256')!=full_hash or data.get('integrity_scope')!='PREVIEW_SHA256_WORKER_VALIDATED_FULL_DIGEST':raise ValueError()
    for k in ('source_revision','dataset','symbol','timeframe','from_ms','to_ms','algorithm','parameters_hash'):
        if type(data.get(k)) is not type(identity[k]) or data[k]!=identity[k]:raise ValueError()
    if type(data.get('total_candles')) is not int or data['total_candles']!=expected or not 1<=expected<=10000 or type(data.get('truncated')) is not bool or data['truncated']!=(expected>64):raise ValueError()
    rows=data.get('candles')
    if type(rows) is not list or len(rows)!=min(expected,64):raise ValueError()
    for i,c in enumerate(rows):
        if type(c) is not dict or set(c)!={'ts','open','high','low','close','volume','delta'} or type(c['ts']) is not int or c['ts']!=start+i*minutes*60000:raise ValueError()
        if any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) for k in ('open','high','low','close','volume','delta')):raise ValueError()
        if min(c[k] for k in ('open','high','low','close'))<=0 or not c['low']<=min(c['open'],c['close'])<=max(c['open'],c['close'])<=c['high'] or c['volume']<0 or abs(c['delta'])>c['volume']+1e-8:raise ValueError()


def result_in_snapshot(con,job_id,now):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cache_previews'").fetchone():return dict(state='UNAVAILABLE',code='CACHE_UPGRADE_REQUIRED')
    row=con.execute("""SELECT substr(j.state,1,9),substr(j.cache_key,1,65),
        CASE WHEN length(j.identity_json)<=4096 THEN j.identity_json END,
        substr(p.entry_hash,1,65),substr(p.identity_hash,1,65),substr(p.content_hash,1,65),
        CASE WHEN length(p.payload)<=32768 THEN p.payload END
        FROM cache_jobs j LEFT JOIN cache_previews p ON p.cache_key=j.cache_key WHERE j.job_id=?""",(job_id,)).fetchone()
    if row is None:return dict(state='NOT_FOUND')
    state,key,job_id_json,full_hash,identity_hash,expected,raw=row
    if state!='READY':return dict(state=state if state in ('QUEUED','RUNNING','FAILED') else 'UNAVAILABLE')
    if full_hash is None:
        exists=con.execute('SELECT 1 FROM cache_entries WHERE cache_key=?',(key,)).fetchone()
        return dict(state='CORRUPT' if exists else 'MISSING')
    if not isinstance(raw,bytes) or len(raw)>32768 or hashlib.sha256(raw).hexdigest()!=expected:return dict(state='CORRUPT')
    try:
        identity=json.loads(job_id_json)
        if key_for(identity)!=key or identity_hash!=key:return dict(state='STALE')
        data=json.loads(raw);checked_preview(identity,data,full_hash)
        if type(data['expires_at']) is not int:return dict(state='CORRUPT')
        if data['expires_at']<=now:return dict(state='EXPIRED')
    except (CacheError,ValueError,TypeError,KeyError,AttributeError,OverflowError):return dict(state='CORRUPT')
    return dict(data,preview_sha256=expected)


def read_job_result(db,job_id,now=None):
    if type(job_id) is not str or len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):raise ValueError('INVALID_JOB_ID')
    with reader(db) as con:return result_in_snapshot(con,job_id,int(time.time()) if now is None else int(now))


LOOKUP_SQL=f"""SELECT substr(j.job_id,1,33) FROM cache_jobs j INDEXED BY {EXACT_INDEX}
    WHERE j.state='READY' AND json_valid(j.identity_json)
    AND json_extract(j.identity_json,'$.source')='grid'
    AND json_extract(j.identity_json,'$.dataset')='candles_1m'
    AND json_extract(j.identity_json,'$.source_revision')=?
    AND json_extract(j.identity_json,'$.symbol')=?
    AND json_extract(j.identity_json,'$.timeframe')=?
    AND json_extract(j.identity_json,'$.from_ms')=?
    AND json_extract(j.identity_json,'$.to_ms')=?
    AND json_extract(j.identity_json,'$.algorithm')=?
    ORDER BY j.job_id LIMIT 2"""


def lookup_exact_cache(db,source_revision,symbol,timeframe,from_ms,to_ms,now=None):
    if type(source_revision) is not str or len(source_revision)!=64 or any(c not in '0123456789abcdef' for c in source_revision):raise ValueError('INVALID_REVISION')
    if type(symbol) is not str or not 1<=len(symbol)<=80 or not all(c.isalnum() or c in '_-' for c in symbol):raise ValueError('INVALID_SYMBOL')
    if timeframe not in PERIODS:raise ValueError('INVALID_TIMEFRAME')
    if type(from_ms) is not int or type(to_ms) is not int or not 946684800000<=from_ms<=to_ms<=2**53-1:raise ValueError('INVALID_RANGE')
    args=(source_revision,symbol,timeframe,from_ms,to_ms,ALGORITHM)
    with reader(db) as con:
        require_index(con,EXACT_INDEX)
        plan=con.execute('EXPLAIN QUERY PLAN '+LOOKUP_SQL,args).fetchall()
        if not any('SEARCH j USING INDEX '+EXACT_INDEX in r[3] for r in plan) or any('SCAN ' in r[3] or 'TEMP B-TREE' in r[3] for r in plan):raise ValueError('CACHE_INDEX_REQUIRED')
        rows=con.execute(LOOKUP_SQL,args).fetchall()
        if not rows:return dict(state='MISS',authority='OFFLINE_ONLY')
        if len(rows)>1:return dict(state='AMBIGUOUS',authority='OFFLINE_ONLY')
        result=result_in_snapshot(con,rows[0][0],int(time.time()) if now is None else int(now))
        if result.get('state')!='READY':return dict(state=result.get('state','UNAVAILABLE'),authority='OFFLINE_ONLY')
        if tuple(result[k] for k in ('source_revision','symbol','timeframe','from_ms','to_ms','algorithm'))!=args:return dict(state='STALE',authority='OFFLINE_ONLY')
        return dict(result,match='EXACT_SOURCE_REVISION_AND_RANGE')


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
