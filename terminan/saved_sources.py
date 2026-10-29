"""Opt-in historical providers. No upstream Store constructors or automatic I/O.

Only this module opens configured read-only snapshots. Public failures are codes,
never driver messages, paths or DSNs. Fixture data never acquires live authority.
"""
from __future__ import annotations
import base64, contextlib, hashlib, hmac, json, math, os, re, secrets, sqlite3, time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE=Path(__file__).parent
CATALOG=json.loads((HERE/'fixtures/saved-catalog-v1.json').read_text(encoding='utf8'))
SYMBOL=re.compile(r'^[A-Z0-9]{2,30}$')
TF=re.compile(r'^[1-9][0-9]{0,4}[smhdwM]$')
MAX_BYTES=1024*1024

class SourceError(ValueError):
 def __init__(self,code='INVALID_REQUEST'):self.code=code;super().__init__(code)

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def fail(code):raise SourceError(code)
def number(v):
 if type(v) not in (int,float) or not math.isfinite(v):fail('INVALID_DATA')
 return v
def utc(v):
 if type(v) is not int or not 946684800000<=v<=2**53-1:fail('INVALID_UTC')
 return v
def safe_json(value,depth=0):
 if depth>8:fail('RESOURCE_LIMIT')
 if value is None or type(value) is bool:return value
 if type(value) in (int,float):return number(value)
 if isinstance(value,Decimal):return number(float(value))
 if isinstance(value,datetime):
  if value.tzinfo is None:fail('INVALID_UTC')
  return utc(int(value.timestamp()*1000))
 if type(value) is str:
  if len(value)>4096:fail('RESOURCE_LIMIT')
  return value
 if isinstance(value,(list,tuple)):
  if len(value)>512:fail('RESOURCE_LIMIT')
  return [safe_json(x,depth+1) for x in value]
 if type(value) is dict:
  if len(value)>128 or any(type(k) is not str or len(k)>128 for k in value):fail('RESOURCE_LIMIT')
  return {k:safe_json(v,depth+1) for k,v in value.items()}
 fail('INVALID_DATA')

def demo_config():
 return {'version':1,'sources':[dict(id=id,source=source,backend='fixture',path=str(HERE/'fixtures'/file),source_sha=CATALOG[source]['sha'],schema_id=schema) for id,source,file,schema in [('grid-demo','grid','saved-grid-v1.json','grid46'),('market-demo','strattester','saved-market-v1.json','market2'),('research-demo','strattester','saved-research-v1.json','results1')]]}

class SavedSources:
 def __init__(self,config=None):
  self.sources={};self.secret=secrets.token_bytes(32)
  if config is None:return
  if type(config) is not dict or set(config)!={'version','sources'} or type(config['version']) is not int or config['version']!=1 or type(config['sources']) is not list or len(config['sources'])>8:fail('INVALID_CONFIG')
  for src in config['sources']:
   if type(src) is not dict or set(src)-{'id','source','backend','path','dsn_env','source_sha','schema_id','buckets'}:fail('INVALID_CONFIG')
   if not re.fullmatch(r'[a-z0-9-]{1,40}',src.get('id','')) or src['id'] in self.sources:fail('INVALID_CONFIG')
   source=src.get('source');backend=src.get('backend');schema=src.get('schema_id')
   if source not in CATALOG or src.get('source_sha')!=CATALOG[source]['sha']:fail('SOURCE_PIN_MISMATCH')
   if (source,schema) not in {('grid','grid46'),('strattester','market2'),('strattester','results1'),('strattester','legacy-candles1')}:fail('SCHEMA_MISMATCH')
   if backend not in ('fixture','sqlite','sqlite-shards','postgres') or backend in ('sqlite','sqlite-shards') and source!='strattester' or backend=='postgres' and source!='grid':fail('INVALID_CONFIG')
   if backend=='sqlite-shards' and (schema!='market2' or type(src.get('buckets',64)) is not int or not 1<=src.get('buckets',64)<=1024):fail('INVALID_CONFIG')
   if backend!='sqlite-shards' and 'buckets' in src:fail('INVALID_CONFIG')
   if backend=='postgres':
    if 'path' in src or not re.fullmatch(r'TERMINAN_SAVED_[A-Z0-9_]{1,40}',src.get('dsn_env','')):fail('INVALID_CONFIG')
   elif type(src.get('path')) is not str or 'dsn_env' in src:fail('INVALID_CONFIG')
   self.sources[src['id']]=dict(src)

 def catalog(self):
  return dict(version=1,mode='SAVED_WORKSPACE',sources=[dict(id=s['id'],source=s['source'],backend=s['backend'],schema_id=s['schema_id'],source_sha=s['source_sha'],authority='SYNTHETIC_ONLY' if s['backend']=='fixture' else 'HISTORICAL_ONLY',datasets=[dict(name=n,supported=d['supported'],reason=d['reason'],scope=d['scope'],timeframe=d['native_timeframe'],time_column=d['time_column'],time_columns=[k for k,v in d['columns'].items() if v['type']=='timestamptz' or k==d['time_column']],columns=d['projection']) for n,d in CATALOG[s['source']]['datasets'].items() if d['schema_id']==s['schema_id']]) for s in self.sources.values()],limitations=['NO_LIVE_AUTHORITY','SOURCE_SHA_IS_OPERATOR_PIN_FOR_DATABASES','INTERNAL_STATE_EXCLUDED','BOOK_SNAPSHOTS_ARE_HISTORICAL_NOT_L2'])

 def _cursor(self,text,scope):
  if not text:return None,0
  if type(text) is not str or len(text)>4096:fail('INVALID_CURSOR')
  try:
   raw=base64.urlsafe_b64decode(text.encode());body,signature=raw[:-32],raw[-32:]
   if not hmac.compare_digest(hmac.digest(self.secret,body,'sha256'),signature):fail('INVALID_CURSOR')
   x=json.loads(body)
   if set(x)!={'scope','last','sequence'} or x['scope']!=scope or type(x['sequence']) is not int or x['sequence']<1:fail('STALE_CURSOR')
   return x['last'],x['sequence']
  except SourceError:raise
  except (ValueError,TypeError,UnicodeError):fail('INVALID_CURSOR')

 def page(self,source_id,dataset,*,symbol='BTCUSDT',timeframe='1m',limit=100,cursor=None,cutoff_ms=None,from_ms=None):
  if source_id not in self.sources:fail('SOURCE_DISABLED')
  src=self.sources[source_id];spec=CATALOG[src['source']]['datasets'].get(dataset)
  if not spec or not spec['supported'] or spec['schema_id']!=src['schema_id']:fail('UNSUPPORTED_DATASET')
  if type(symbol) is not str or not SYMBOL.fullmatch(symbol) or type(timeframe) is not str or not TF.fullmatch(timeframe) or type(limit) is not int or not 1<=limit<=200:fail('INVALID_REQUEST')
  if spec['native_timeframe'] and spec['native_timeframe']!=timeframe:fail('UNSUPPORTED_TIMEFRAME')
  try:
   if src['backend']=='fixture':
    p=Path(src['path'])
    with p.open('rb') as file:raw=file.read(4*MAX_BYTES+1)
    if len(raw)>4*MAX_BYTES:fail('RESOURCE_LIMIT')
    fixture=json.loads(raw);epoch=hashlib.sha256(raw).hexdigest();asof=utc(fixture['as_of_ms'])
    if type(fixture['version']) is not int or fixture['version']!=1 or fixture['source_sha']!=src['source_sha'] or fixture['schema_id']!=src['schema_id']:fail('SCHEMA_MISMATCH')
    if fixture.get('source')!=src['source']:fail('SOURCE_IDENTITY_MISMATCH')
    data=fixture['datasets'].get(dataset,[])
    if type(data) is not list or len(data)>2000:fail('RESOURCE_LIMIT')
    # Fixtures are deliberately small; validate the complete stored dataset before filtering.
    data=[self._row(r,spec,src,dataset,asof) for r in data]
    if spec['scope']=='SYMBOL' and any(r.get('symbol') not in fixture.get('symbols',[]) for r in data):fail('SOURCE_IDENTITY_MISMATCH')
    keys=[tuple(r[k] for k in spec['key']) for r in data]
    if len(set(keys))!=len(keys) or keys!=sorted(keys):fail('SEQUENCE_ERROR')
   else:
    if src['backend']=='sqlite-shards':src=self._shard(src,symbol)
    epoch=self._epoch(src);asof=int(time.time()*1000);data=None
   cutoff=asof if cutoff_ms is None else utc(cutoff_ms)
   if cutoff>asof:fail('FUTURE_LEAKAGE')
   start=946684800000 if from_ms is None else utc(from_ms)
   if start>cutoff:fail('INVALID_RANGE')
   identity=dict(source_id=source_id,dataset=dataset,symbol=symbol if spec['scope']=='SYMBOL' else None,timeframe=timeframe if 'timeframe' in spec['columns'] or spec['native_timeframe'] else None,from_ms=start,cutoff_ms=cutoff,epoch=epoch,source_sha=src['source_sha'],schema_sha=digest(spec))
   # Cursor retains the original cutoff; caller must pass it explicitly for live DB pages.
   scope=digest(identity);last,sequence=self._cursor(cursor,scope)
   if last is not None and (type(last) is not list or len(last)!=len(spec['key'])):fail('INVALID_CURSOR')
   if data is None:data=self._database(src,spec,dataset,symbol,timeframe,limit,last,start,cutoff,epoch)
   else:
    data=[r for r in data if (spec['scope']!='SYMBOL' or r['symbol']==symbol) and ('timeframe' not in spec['columns'] or r['timeframe']==timeframe) and (not spec['time_column'] or r[spec['time_column']] is None or start<=r[spec['time_column']]<=cutoff) and (last is None or tuple(r[k] for k in spec['key'])>tuple(last))][:limit+1]
   rows=[self._row(r,spec,src,dataset,cutoff,projected=True) for r in data]
   keys=[tuple(r[k] for k in spec['key']) for r in rows]
   if keys!=sorted(keys) or len(set(keys))!=len(keys):fail('SEQUENCE_ERROR')
   if any(spec['scope']=='SYMBOL' and r.get('symbol')!=symbol or 'timeframe' in spec['columns'] and r.get('timeframe')!=timeframe for r in rows):fail('SOURCE_IDENTITY_MISMATCH')
   more=len(rows)>limit;rows=rows[:limit];next_cursor=None
   if more:
    body=json.dumps(dict(scope=scope,last=[rows[-1][k] for k in spec['key']],sequence=sequence+1),sort_keys=True,separators=(',',':')).encode();next_cursor=base64.urlsafe_b64encode(body+hmac.digest(self.secret,body,'sha256')).decode()
   times=[r[spec['time_column']] for r in rows if spec['time_column'] and r.get(spec['time_column']) is not None]
   partial=any(r.get('complete') in (0,False) for r in rows)
   result=dict(version=1,**identity,sequence=sequence+1,previous_sequence=sequence,mode='SYNTHETIC' if src['backend']=='fixture' else 'HISTORICAL',authority='SYNTHETIC_ONLY' if src['backend']=='fixture' else 'HISTORICAL_ONLY',state='NO_DATA' if not rows else 'PARTIAL' if partial else 'HISTORICAL_ONLY',freshness=('NO_DATA' if not rows else 'NOT_TIMESTAMPED') if not times else 'STALE' if asof-max(times)>300000 else 'RECENT_SAVED_DATA',as_of_ms=asof,coverage=dict(from_ms=min(times) if times else None,to_ms=max(times) if times else None,complete=False,scope='PAGE_ONLY_NOT_FULL_HISTORY'),rows=rows,next_cursor=next_cursor,limit=limit,provenance=dict(source_sha=src['source_sha'],schema_sha=digest(spec),schema_id=src['schema_id'],source_attestation='FIXTURE_PIN' if src['backend']=='fixture' else 'OPERATOR_PIN_NOT_RUNTIME_ATTESTATION',publication='PUBLISHED_UNVERIFIED' if dataset=='research_results' else 'HISTORICAL_UNVERIFIED'))
   if len(json.dumps(result,allow_nan=False).encode())>MAX_BYTES:fail('RESOURCE_LIMIT')
   return result
  except SourceError:raise
  except (sqlite3.OperationalError,TimeoutError):fail('SOURCE_UNAVAILABLE')
  except (OSError,ImportError):fail('SOURCE_UNAVAILABLE')
  except (ValueError,KeyError,TypeError,OverflowError):fail('INVALID_DATA')
  except Exception:fail('SOURCE_UNAVAILABLE')

 def _row(self,row,spec,src,dataset,cutoff,projected=False):
  if type(row) is not dict:fail('INVALID_DATA')
  allowed=set(spec['projection'])
  if projected and dataset=='research_results':row={k:v for k,v in row.items() if k!='publication_state'}
  if set(row)!=allowed:fail('SCHEMA_MISMATCH')
  out={}
  for k,v in row.items():
   col=spec['columns'][k];typ=col['type']
   if v is None:
    if not col['nullable'] or k in spec['key']:fail('INVALID_DATA')
    out[k]=None;continue
   if k=='created_at' and src['schema_id']=='results1' and type(v) is float:v=int(v*1000)
   if typ in ('json','jsonb') or k=='metrics':
    if isinstance(v,str):
     if len(v)>65536:fail('RESOURCE_LIMIT')
     v=json.loads(v)
    v=safe_json(v)
    if type(v) is not dict and k=='metrics':fail('INVALID_DATA')
   elif typ.endswith('[]'):
    if not isinstance(v,list):fail('INVALID_DATA')
    v=safe_json(v)
   elif typ in ('numeric','real','double precision'):v=number(float(v)) if isinstance(v,Decimal) else number(v)
   elif typ in ('integer','bigint','bigserial','serial','smallint'):
    if type(v) is not int:fail('INVALID_DATA')
    if k in ('trade_count','buy_count','sell_count') and v<0:fail('INVALID_DATA')
   elif typ=='boolean':
    if type(v) is not bool:fail('INVALID_DATA')
   elif typ in ('timestamptz','timestamp'):v=safe_json(v)
   elif typ=='uuid':v=str(v)
   elif typ=='date':
    if isinstance(v,date):v=v.isoformat()
    if type(v) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\d',v):fail('INVALID_UTC')
    if date.fromisoformat(v)>datetime.fromtimestamp(cutoff/1000,timezone.utc).date():fail('FUTURE_LEAKAGE')
   else:
    if type(v) is not str:fail('INVALID_DATA')
    safe_json(v)
   if k==spec['time_column'] or typ in ('timestamptz','timestamp') or k=='event_ts_ms':
    utc(v)
    if v>cutoff and k!='cooldown_until':fail('FUTURE_LEAKAGE')
   out[k]=v
  if dataset in ('candles','legacy_candles','candles_1m','ohlcv_1m','mark_prices','index_prices','premium_index'):
   if dataset!='premium_index' and min(out[k] for k in ('open','high','low','close'))<=0:fail('INVALID_OHLC')
   if not out['low']<=min(out['open'],out['close'])<=max(out['open'],out['close'])<=out['high']:fail('INVALID_OHLC')
   for k in ('volume','buy_volume','sell_volume','turnover'):
    if out.get(k) is not None and out[k]<0:fail('INVALID_DATA')
  if dataset in ('footprint_1m','public_trade_aggregates','candles_1m'):
   buy,sell=out['buy_volume'],out['sell_volume']
   if min(buy,sell)<0:fail('INVALID_DATA')
   if 'delta' in out and not math.isclose(out['delta'],buy-sell,rel_tol=1e-8,abs_tol=1e-8):fail('DELTA_MISMATCH')
   if dataset=='footprint_1m' and (out['price']<=0 or not math.isclose(out['volume'],buy+sell,rel_tol=1e-8,abs_tol=1e-8)):fail('VOLUME_MISMATCH')
  if dataset=='research_results':
   out['publication_state']='PUBLISHED_UNVERIFIED'
   for k in ('trades','wins','losses','win_rate','gross_pnl','net_pnl','fees','expectancy','profit_factor','max_drawdown','avg_mae','avg_mfe','avg_r_multiple','avg_holding_ms','max_consecutive_losses'):
    if out['metrics'].get(k) is not None:number(out['metrics'][k])
  return out

 def _epoch(self,src):
  if src['backend']=='sqlite':
   p=Path(src['path']).resolve();parts=[]
   paths=[p,Path(str(p)+'-wal')]
   if '_manifest' in src:paths.extend([Path(src['_manifest']),Path(src['_manifest']+'-wal')])
   for f in paths:
    if f.exists():st=f.stat();parts.append((st.st_size,st.st_mtime_ns))
   if not parts:fail('SOURCE_UNAVAILABLE')
   return digest(parts)
  # A later authorized PostgreSQL reader must observe a stable WAL boundary.
  with self._pg(src) as con:
   return digest(str(con.execute('SELECT pg_current_wal_lsn()').fetchone()[0]))

 def _shard(self,src,symbol):
  root=Path(src['path']).resolve();manifest=root/'manifest.sqlite3'
  with contextlib.closing(sqlite3.connect(manifest.as_uri()+'?mode=ro',uri=True,timeout=.5)) as con:
   con.execute('PRAGMA query_only=ON')
   row=con.execute('SELECT state FROM shard_manifest WHERE symbol=?',(symbol,)).fetchone()
   if not row or row[0]!='SHARD_READY':fail('SHARD_NOT_READY')
  bucket=int(hashlib.sha256(symbol.encode()).hexdigest()[:8],16)%src.get('buckets',64)
  path=(root/f'{bucket:02d}'/f'{symbol}.sqlite3').resolve()
  if not path.is_relative_to(root):fail('INVALID_CONFIG')
  return dict(src,backend='sqlite',path=str(path),_manifest=str(manifest))

 @contextlib.contextmanager
 def _pg(self,src):
  import psycopg
  dsn=os.environ.get(src['dsn_env'])
  if not dsn:fail('SOURCE_UNAVAILABLE')
  with psycopg.connect(dsn,connect_timeout=3,options='-c default_transaction_read_only=on -c statement_timeout=2000 -c lock_timeout=500 -c idle_in_transaction_session_timeout=3000') as con:
   con.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
   if not 180000<=con.info.server_version<190000:fail('SCHEMA_MISMATCH')
   yield con

 def _database(self,src,spec,dataset,symbol,timeframe,limit,last,start,cutoff,epoch):
  dataset=spec.get('table',dataset)
  sqlite=src['backend']=='sqlite'
  manager=contextlib.closing(sqlite3.connect(Path(src['path']).resolve().as_uri()+'?mode=ro',uri=True,timeout=.5)) if sqlite else self._pg(src)
  with manager as con:
   if sqlite:
    con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    deadline=time.monotonic()+2;con.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
    if src['schema_id']=='market2':
     meta=dict(con.execute('SELECT key,value FROM schema_meta'))
     if meta.get('schema_version')!='2':fail('SCHEMA_MISMATCH')
    info=list(con.execute(f'PRAGMA table_info("{dataset}")'))
    actual={r[1]:r[2].lower() for r in info};key=[r[1] for r in sorted(info,key=lambda r:r[5]) if r[5]]
   else:
    history=[dict(version=r[0],name=r[1]) for r in con.execute('SELECT version,name FROM schema_migrations ORDER BY version')]
    if history!=CATALOG['grid']['migration_history']:fail('SCHEMA_MISMATCH')
    actual={r[0]:r[1] for r in con.execute('SELECT column_name,data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s',(dataset,))}
    key=[r[0] for r in con.execute("SELECT kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema AND tc.table_name=kcu.table_name WHERE tc.table_schema=current_schema() AND tc.table_name=%s AND tc.constraint_type='PRIMARY KEY' ORDER BY kcu.ordinal_position",(dataset,))]
   if key!=spec['key']:fail('SCHEMA_MISMATCH')
   if not set(spec['columns'])<=set(actual):fail('SCHEMA_MISMATCH')
   # Types are checked in addition to values; additive columns require a new reviewed catalog.
   aliases={'numeric':'numeric','timestamptz':'timestamp with time zone','bigserial':'bigint','serial':'integer','text[]':'ARRAY','integer[]':'ARRAY','bigint[]':'ARRAY'}
   if set(actual)!=set(spec['columns']) or any(actual[k]!=(aliases.get(c['type'],c['type']) if not sqlite else c['type']) for k,c in spec['columns'].items()):fail('SCHEMA_MISMATCH')
   placeholder='?' if sqlite else '%s'
   def expr(k):
    if not sqlite and spec['columns'][k]['type'] in ('timestamptz','timestamp'):return f'CAST(extract(epoch from "{k}")*1000 AS bigint)'
    if src['schema_id']=='results1' and k=='created_at':return 'CAST("created_at"*1000 AS INTEGER)' if sqlite else 'CAST("created_at"*1000 AS bigint)'
    return f'"{k}"'
   where=[];args=[]
   if spec['scope']=='SYMBOL':where.append('symbol='+placeholder);args.append(symbol)
   if 'timeframe' in spec['columns']:where.append('timeframe='+placeholder);args.append(timeframe)
   if spec['time_column']:where.append(f'({expr(spec["time_column"])}<={placeholder} OR {expr(spec["time_column"])} IS NULL)');args.append(cutoff)
   if spec['time_column']:where.append(f'({expr(spec["time_column"])}>={placeholder} OR {expr(spec["time_column"])} IS NULL)');args.append(start)
   if last is not None:
    where.append('('+','.join(expr(k) for k in spec['key'])+')>('+','.join(placeholder for _ in last)+')');args.extend(last)
   size=' + '.join(f'COALESCE(length(CAST("{k}" AS BLOB)),0)' if sqlite else f'COALESCE(octet_length(CAST("{k}" AS text)),0)' for k in spec['projection'])
   large='('+size+')>16384'
   projection=','.join(f'CASE WHEN {large} THEN NULL ELSE {expr(k)} END AS "{k}"' for k in spec['projection'])
   sql='SELECT '+projection+',('+large+') AS "__oversized"'+f' FROM "{dataset}"'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY '+','.join(expr(k) for k in spec['key'])+' LIMIT '+placeholder
   args.append(limit+1);cur=con.execute(sql,args);raw=cur.fetchmany(limit+1)
   if any(r[-1] for r in raw):fail('RESOURCE_LIMIT')
   rows=[dict(zip(spec['projection'],r[:-1])) for r in raw]
  if self._epoch(src)!=epoch:fail('SOURCE_CHANGED')
  return rows
