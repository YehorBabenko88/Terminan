"""Versioned read-only G0 views. No source credentials/paths enter responses."""
import json
from contextlib import closing
import math
import os
from pathlib import Path
import sqlite3
import time
from .data import validate

PINS = {'grid':'d537d525296ef34f727996e240ae6c60102c6082',
        'strattester':'37ff7e9d12a4d2dccd788fc493c28557dbe8bcea'}
ENV = {'grid':'TERMINAN_GRID_DSN','footprint':'TERMINAN_GRID_DSN','health':'TERMINAN_GRID_DSN',
       'strattester':'TERMINAN_STRATTESTER_DB','research':'TERMINAN_RESULTS_DB'}
GRID = {
 'nodes': {'node_id':'text','last_seen':'timestamp with time zone','cpu_pct':'double precision','ram_pct':'double precision','disk_free':'bigint','assigned_symbols':'integer'},
 'candles_1m': {'symbol':'text','ts':'timestamp with time zone','open':'numeric','high':'numeric','low':'numeric','close':'numeric','buy_volume':'numeric','sell_volume':'numeric','delta':'numeric','trade_count':'integer','poc_price':'numeric'},
 'footprint_1m': {'symbol':'text','ts':'timestamp with time zone','price':'numeric','buy_volume':'numeric','sell_volume':'numeric','delta':'numeric','volume':'numeric'},
}

class SchemaMismatch(ValueError): pass

def number(value, *, nonnegative=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise ValueError('invalid number')
    try: ok=math.isfinite(value)
    except OverflowError: ok=False
    if not ok or (nonnegative and value<0): raise ValueError('invalid number')
    return value

def milliseconds(value):
    if type(value) is not int or not 0<=value<=2**53-1: raise ValueError('invalid UTC milliseconds')
    return value

def sqlite_rows(kind,symbol,timeframe='1m'):
    path=Path(os.environ[ENV[kind]])
    if not path.is_file(): raise OSError('unavailable')
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as con:
        try:
            # Read transaction pins schema and rows to one consistent snapshot.
            con.execute('BEGIN')
            deadline=time.monotonic()+2
            con.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
            if kind=='strattester':
                version=con.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                if version!=('2',): raise SchemaMismatch()
                columns={r[1]:r[2].upper() for r in con.execute('PRAGMA table_info(candles)')}
                expected={'symbol':'TEXT','timeframe':'TEXT','open_time':'INTEGER','open':'REAL','high':'REAL','low':'REAL','close':'REAL','volume':'REAL','complete':'INTEGER'}
                if any(columns.get(k)!=v for k,v in expected.items()):raise SchemaMismatch()
                rows=con.execute('SELECT open_time,open,high,low,close,volume,complete FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT 300',(symbol,timeframe)).fetchall()
                result=[]
                for row in reversed(rows):
                    if type(row[6]) is not int or row[6] not in (0,1):raise ValueError('completion')
                    result.append(dict(zip(('t','o','h','l','c','v'),row[:6]),complete=bool(row[6])))
                return result,2
            columns={r[1] for r in con.execute('PRAGMA table_info(research_results)')}
            required={'run_id','symbol','strategy_id','strategy_version','created_at','metrics'}
            if not required.issubset(columns):raise SchemaMismatch()
            # Upstream result store has no numeric schema version. Structural v1
            # is explicitly adapter-owned and never presented as upstream version.
            rows=con.execute('SELECT run_id,strategy_id,strategy_version,created_at,metrics FROM research_results WHERE symbol=? ORDER BY created_at DESC LIMIT 50',(symbol,)).fetchall()
            result=[]
            for run,strategy,version,created,raw in rows:
                number(created,nonnegative=True)
                if not isinstance(raw,str) or len(raw)>262144:raise ValueError('metrics size')
                metrics=json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
                if not isinstance(metrics,dict):raise ValueError('metrics')
                json.dumps(metrics,allow_nan=False)
                result.append(dict(run_id=run,strategy=strategy,version=version,
                                   created_at_ms=milliseconds(int(created*1000)),metrics=metrics,
                                   publication_authority='UNVERIFIED',fencing='NOT_VERIFIED'))
            return result,'research-structural-v1'
        except sqlite3.OperationalError as exc:
            if 'no such' in str(exc):raise SchemaMismatch() from None
            raise

def grid_rows(kind,symbol):
    import psycopg
    table='nodes' if kind=='health' else 'footprint_1m' if kind=='footprint' else 'candles_1m'
    keys=('t','price','buy','sell','delta','volume') if kind=='footprint' else ('t','o','h','l','c','buy','sell','delta','trades','poc')
    fields='price,buy_volume,sell_volume,delta,volume' if kind=='footprint' else 'open,high,low,close,buy_volume,sell_volume,delta,trade_count,poc_price'
    # Fixed identifiers only. DSN cannot override the read-only transaction.
    with psycopg.connect(os.environ['TERMINAN_GRID_DSN'],connect_timeout=3,
                         options='-c default_transaction_read_only=on -c statement_timeout=3000 -c lock_timeout=1000') as con:
        con.read_only=True
        with con.cursor() as cur:
            cur.execute('SHOW server_version_num')
            if not 180000<=int(cur.fetchone()[0])<190000:raise SchemaMismatch()
            cur.execute("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",(table,))
            columns=dict(cur.fetchall())
            if any(columns.get(k)!=v for k,v in GRID[table].items()):raise SchemaMismatch()
            if kind=='health':
                cur.execute('SELECT node_id,(extract(epoch from last_seen)*1000)::bigint,cpu_pct,ram_pct,disk_free,assigned_symbols FROM public.nodes ORDER BY node_id LIMIT 200')
                return [dict(node_id=r[0],t=int(r[1]),cpu=r[2],ram=r[3],disk=r[4],symbols=r[5]) for r in cur.fetchall()],'pg18-structural-v1'
            cur.execute(f'SELECT extract(epoch from ts)*1000,{fields} FROM public.{table} WHERE symbol=%s ORDER BY ts DESC'+(',price DESC' if kind=='footprint' else '')+' LIMIT %s',(symbol,300))
            result=[]
            for row in cur.fetchall():
                if row[0]!=int(row[0]):raise ValueError('fractional source milliseconds')
                result.append(dict(zip(keys,(int(v) if i==0 or keys[i]=='trades' else float(v) if v is not None else None for i,v in enumerate(row)))))
            if kind!='footprint':result.reverse()
            return result,'pg18-structural-v1'

def snapshot(kind,symbol,*,now_ms=None,timeframe='1m'):
    validate(symbol,timeframe)
    if kind not in ENV:raise ValueError('unknown source')
    now_ms=milliseconds(int(time.time()*1000) if now_ms is None else now_ms)
    source='grid' if kind in ('grid','footprint','health') else 'strattester'
    out=dict(version=1,source=kind,symbol=symbol,observed_at_ms=now_ms,rows=[],
             timeframe=None if kind in ('research','health') else '1m' if source=='grid' else timeframe,
             state='NOT_CONFIGURED',schema_version=None,
             authority='TELEMETRY_ONLY' if kind=='health' else 'AGGREGATED_HISTORY_NOT_L2' if source=='grid' else 'HISTORICAL_ONLY',
             provenance={'contract_source_sha':PINS[source],'runtime_source_sha':'UNVERIFIED'},
             coverage={'scope':'BOUNDED_WINDOW','verified':False,'missing_intervals':None})
    if not os.environ.get(ENV[kind]):return out
    try:
        rows,schema=grid_rows(kind,symbol) if source=='grid' else sqlite_rows(kind,symbol,timeframe)
        if kind=='health':
            for row in rows:
                if not isinstance(row['node_id'],str) or not 1<=len(row['node_id'])<=160:raise ValueError('node id')
                stamp=milliseconds(row['t'])
                if stamp>now_ms:raise ValueError('future telemetry')
                for key in ('cpu','ram','disk','symbols'):
                    if row[key] is not None:number(row[key],nonnegative=True)
                row['age_seconds']=(now_ms-stamp)/1000
                row['online']=row['age_seconds']<=120
            out.update(rows=rows,schema_version=schema,state='NO_DATA' if not rows else 'STALE' if any(not r['online'] for r in rows) else 'FRESH')
            return out
        period={'1m':60000,'3m':180000,'5m':300000,'15m':900000,'30m':1800000,'1h':3600000,'4h':14400000,'1d':86400000}[out['timeframe'] or '1m']
        times=[];footprint_keys=set()
        for row in rows:
            if kind=='research':
                if milliseconds(row['created_at_ms'])>now_ms:raise ValueError('future research time')
                continue
            t=milliseconds(row['t'])
            if t>now_ms:raise ValueError('future source time')
            times.append(t)
            for key,value in row.items():
                if key in ('t','complete') or key=='poc' and value is None:continue
                number(value,nonnegative=key not in ('delta',))
            if kind in ('grid','strattester'):
                if not row['l']<=min(row['o'],row['c'])<=max(row['o'],row['c'])<=row['h']:raise ValueError('OHLC')
                if (kind=='grid' or row.get('complete')) and t+period>now_ms:raise ValueError('future close')
            if kind=='footprint':
                key=(t,row['price'])
                if key in footprint_keys:raise ValueError('duplicate price level')
                footprint_keys.add(key)
                if t+period>now_ms or not math.isclose(row['buy']+row['sell'],row['volume'],rel_tol=1e-9,abs_tol=1e-9) or not math.isclose(row['buy']-row['sell'],row['delta'],rel_tol=1e-9,abs_tol=1e-9):raise ValueError('invalid footprint')
        out.update(rows=rows,schema_version=schema,state='HISTORICAL' if rows else 'NO_DATA')
        if times:
            unique=sorted(set(times))
            if kind!='footprint' and len(unique)!=len(times):raise ValueError('duplicate')
            gaps=sum(max(0,(b-a)//period-1) for a,b in zip(unique,unique[1:]))
            irregular=any(t%period for t in unique)
            age=max(0,now_ms-unique[-1]-period)
            out['coverage'].update(from_ms=unique[0],to_ms=unique[-1]+period,missing_intervals=gaps,irregular=irregular,tail_age_ms=age)
            out['state']='STALE' if age>120000 else 'PARTIAL' if gaps or irregular or any(r.get('complete') is False for r in rows) else 'HISTORICAL'
            if kind=='footprint':
                out['coverage']['price_levels_complete']=False
                if out['state']=='HISTORICAL':out['state']='PARTIAL'
        return out
    except SchemaMismatch:out['state']='SCHEMA_MISMATCH'
    except (ValueError,TypeError,OverflowError):out['state']='INVALID_DATA'
    except Exception:out['state']='UNAVAILABLE'
    out['rows']=[]
    return out

def all_sources(symbol,timeframe='1m'):
    validate(symbol,timeframe)
    views={kind:snapshot(kind,symbol,timeframe=timeframe if kind=='strattester' else '1m') for kind in ENV}
    states={v['state'] for v in views.values()}
    state='NOT_CONFIGURED' if states=={'NOT_CONFIGURED'} else 'PARTIAL' if len(states)>1 else next(iter(states))
    return dict(version=1,mode='READ_ONLY',state=state,sources=views,l2='UNAVAILABLE',execution='DISABLED')
