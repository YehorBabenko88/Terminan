"""Offline, single-worker SQLite job queue for Terminan visualization cache.

No network, upstream DBs or automatic service installation. One dedicated
worker process owns computations. Leases fence stale worker completions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from .saved_cache import open_cache, key_for, compute_mtf, CacheError, MAX_INPUT, transaction, prepare, write_entry, canonical, get, EXACT_INDEX

MAX_JOBS = 128
LEASE_SECONDS = 120

def init_queue(con):
    con.execute("""CREATE TABLE IF NOT EXISTS cache_jobs(
        job_id TEXT PRIMARY KEY, cache_key TEXT NOT NULL UNIQUE,
        identity_json TEXT NOT NULL, source_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','READY','FAILED')),
        attempt INTEGER NOT NULL DEFAULT 0, token TEXT,
        lease_until INTEGER, error_code TEXT,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS cache_jobs_state_idx ON cache_jobs(state,created_at)")
    con.execute("CREATE INDEX IF NOT EXISTS cache_jobs_updated_idx ON cache_jobs(updated_at DESC,job_id)")
    con.execute(f"""CREATE INDEX IF NOT EXISTS {EXACT_INDEX} ON cache_jobs(
        json_extract(identity_json,'$.source_revision'),json_extract(identity_json,'$.symbol'),
        json_extract(identity_json,'$.timeframe'),json_extract(identity_json,'$.from_ms'),
        json_extract(identity_json,'$.to_ms'),json_extract(identity_json,'$.algorithm'),job_id)
        WHERE state='READY' AND json_valid(identity_json)
        AND json_extract(identity_json,'$.source')='grid'
        AND json_extract(identity_json,'$.dataset')='candles_1m'""")
    return con

def submit(con, identity, source, now=None, retry=False):
    now=int(time.time()) if now is None else int(now)
    key=key_for(identity)
    if type(source) is not dict or source.get('source_revision')!=identity['source_revision']:
        raise CacheError('SOURCE_REVISION_MISMATCH')
    raw=canonical(source).decode()
    if len(raw.encode())>MAX_INPUT:raise CacheError('INPUT_TOO_LARGE')
    with transaction(con):
        existing=con.execute('SELECT job_id,state,source_json FROM cache_jobs WHERE cache_key=?',(key,)).fetchone()
        if existing:
            if existing[2]!=raw:raise CacheError('SOURCE_CONTENT_CONFLICT')
            state=existing[1]
            usable=False
            if state=='READY':
                from .cache_monitor import result_in_snapshot
                usable=get(con,identity,now)['state']=='HIT' and result_in_snapshot(con,existing[0],now)['state']=='READY'
            if state=='READY' and not usable or state=='FAILED' and retry:
                con.execute("UPDATE cache_jobs SET state='QUEUED',attempt=0,token=NULL,lease_until=NULL,error_code=NULL,updated_at=? WHERE job_id=?",(now,existing[0]));state='QUEUED'
            return dict(job_id=existing[0],state=state)
        if con.execute('SELECT count(*) FROM cache_jobs').fetchone()[0]>=MAX_JOBS:raise CacheError('QUEUE_FULL')
        job_id=uuid.uuid4().hex
        con.execute("INSERT INTO cache_jobs(job_id,cache_key,identity_json,source_json,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(job_id,key,canonical(identity).decode(),raw,'QUEUED',now,now))
    return dict(job_id=job_id,state='QUEUED')


def claim(con, now=None):
    now = int(time.time()) if now is None else int(now)
    token = uuid.uuid4().hex
    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("UPDATE cache_jobs SET state='FAILED',error_code='LEASE_EXHAUSTED',token=NULL,lease_until=NULL,updated_at=? WHERE state='RUNNING' AND lease_until<=? AND attempt>=3",(now,now))
        # At most three claims per automatic attempt cycle; terminal failure is visible.
        row = con.execute("""SELECT job_id,identity_json,source_json,attempt
            FROM cache_jobs WHERE state='QUEUED'
            OR (state='RUNNING' AND lease_until<=? AND attempt<3)
            ORDER BY created_at,job_id LIMIT 1""",(now,)).fetchone()
        if row is None:
            con.execute("COMMIT")
            return None
        job_id, identity, source, attempt = row
        con.execute("""UPDATE cache_jobs SET state='RUNNING',attempt=attempt+1,
            token=?,lease_until=?,updated_at=? WHERE job_id=?""",
            (token,now+LEASE_SECONDS,now,job_id))
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    return dict(job_id=job_id,token=token,identity=json.loads(identity),
                source=json.loads(source),attempt=attempt+1)

def finish(con, job, payload=None, error=None, now=None):
    # Validation/hash outside the writer lock; publication itself is atomic.
    if error not in (None,'COMPUTE_FAILED','INCOMPLETE','CACHE_FAILED'):error='COMPUTE_FAILED'
    prepared=None
    if error is None:
        try:prepared=prepare(job['identity'],payload)
        except (CacheError,ValueError,TypeError,KeyError,OverflowError):error='CACHE_FAILED'
    with transaction(con):
        tick=int(time.time()) if now is None else int(now)
        row=con.execute('SELECT state,token,lease_until,cache_key,identity_json FROM cache_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
        if row is None or row[0]!='RUNNING' or row[1]!=job['token'] or row[2]<=tick:return False
        try:
            if key_for(job['identity'])!=row[3] or canonical(json.loads(row[4]))!=canonical(job['identity']):return False
        except (CacheError,ValueError,TypeError):return False
        if error is None:write_entry(con,job['identity'],prepared,86400,tick)
        # BEGIN IMMEDIATE prevents a reclaim between this fence and COMMIT.
        con.execute("UPDATE cache_jobs SET state=?,error_code=?,token=NULL,lease_until=NULL,updated_at=? WHERE job_id=? AND token=?",('READY' if error is None else 'FAILED',error,tick,job['job_id'],job['token']))
    return True


def run_once(con, now=None):
    job = claim(con,now)
    if job is None:
        return {"state":"IDLE"}
    try:
        payload = compute_mtf(job["identity"],job["source"])
        error = None if payload["complete"] else "INCOMPLETE"
    except (CacheError,ValueError,TypeError,OverflowError):
        payload,error = None,"COMPUTE_FAILED"
    accepted = finish(con,job,payload,error,now)
    return {"state":"FINISHED" if accepted else "STALE_LEASE","job_id":job["job_id"]}

def status(con, job_id):
    row=con.execute("""SELECT state,attempt,error_code FROM cache_jobs
        WHERE job_id=?""",(job_id,)).fetchone()
    return {"state":row[0],"attempt":row[1],"error_code":row[2]} if row else {"state":"NOT_FOUND"}

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline cache queue; no network or upstream DB")
    p.add_argument("--db",required=True)
    p.add_argument("--identity")
    p.add_argument("--source")
    p.add_argument("--job-id")
    p.add_argument("--retry",action="store_true",help="Explicitly reset a FAILED attempt cycle")
    p.add_argument("--poll-seconds",type=float,default=0.25)
    p.add_argument("--max-seconds",type=int,default=60)
    p.add_argument("action",choices=("submit","run-once","work","status"))
    a=p.parse_args(argv)
    try:
        con=init_queue(open_cache(a.db))
        try:
            if a.action=="submit":
                if not a.identity or not a.source:
                    raise CacheError("INPUT_REQUIRED")
                for name in (a.identity,a.source):
                    if Path(name).stat().st_size>MAX_INPUT:
                        raise CacheError("INPUT_TOO_LARGE")
                result=submit(con,json.loads(Path(a.identity).read_text(encoding="utf8")),
                              json.loads(Path(a.source).read_text(encoding="utf8")),retry=a.retry)
            elif a.action=="status":
                if not a.job_id:
                    raise CacheError("JOB_ID_REQUIRED")
                result=status(con,a.job_id)
            elif a.action=="run-once":
                result=run_once(con)
            else:
                if not 0.05<=a.poll_seconds<=5 or not 1<=a.max_seconds<=3600:
                    raise CacheError("INVALID_LIMIT")
                until=time.monotonic()+a.max_seconds
                processed=0
                while time.monotonic()<until:
                    result=run_once(con)
                    if result["state"]=="FINISHED":
                        processed+=1
                    else:
                        time.sleep(a.poll_seconds)
                result={"state":"STOPPED","processed":processed}
            print(json.dumps(result,sort_keys=True))
            return 0
        finally:
            con.close()
    except (CacheError,ValueError,TypeError,sqlite3.Error,OSError) as e:
        print(json.dumps({"state":"ERROR","code":str(e) if isinstance(e,CacheError) else "LOCAL_IO_ERROR"}))
        return 3

if __name__=="__main__":
    sys.exit(main())
