"""R4 offline-only contracts. No DB driver, connection, migration or live authority."""
import copy,hashlib,json,math
from pathlib import Path
from .synthetic import BASE_MS,SYMBOLS,PERIODS
from .synthetic_contracts import LOCK,validate_fixture
ROOT=Path(__file__).with_name('fixtures')
IDS={('grid','candles'):'grid.pg18.candles_1m',('grid','footprint'):'grid.pg18.footprint_1m',('strattester','candles'):'strattester.sqlite2.candles',('strattester','research'):'strattester.sqlite.research_results'}
FIELDS={'version','mode','source','kind','source_id','schema_version','server_major','symbol','timeframe','observed_at_ms','epoch','sequence','source_state','provenance','rows','coverage','seed','dataset_id','complete_price_levels','data_sha256'}
def encoded(raw):return json.dumps(raw,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def seal(raw):raw['data_sha256']=hashlib.sha256(encoded({k:v for k,v in raw.items() if k!='data_sha256'})).hexdigest();return raw
def fixtures():
 path=ROOT/'r4-contract-v1.json';lock=json.loads((ROOT/'r4-contract-lock-v1.json').read_text())
 if hashlib.sha256(encoded(json.loads(path.read_text(encoding='utf8')))).hexdigest()!=lock['fixture_sha256'] or lock['source_pins']!=LOCK:raise ValueError()
 return json.loads(path.read_text())
def stamp(v):
 if type(v) is not int or not 946684800000<=v<=2**53-1:raise ValueError()
 return v
def number(v,nullable=False):
 if v is None and nullable:return
 if type(v) not in (int,float) or not math.isfinite(v):raise ValueError()
def validate(raw,*,symbol,timeframe,as_of_ms,previous=None):
 out=dict(version=1,mode='SYNTHETIC',runtime_source='NONE',authority='UNVERIFIED',data_semantics='HISTORICAL_ONLY',state='INVALID_DATA',rows=[],permissions=['OFFLINE_FIXTURE_READ'],coverage={'verified':False,'scope':'BOUNDED_FIXTURE'})
 try:
  stamp(as_of_ms)
  if not isinstance(raw,dict) or set(raw)!=FIELDS:return out
  source=raw['source'];kind=raw['kind'];pair=(source,kind)
  if pair not in IDS or raw['source_id']!=IDS[pair] or type(raw['version']) is not int or raw['version']!=1 or raw['mode']!='SYNTHETIC':return out
  out.update(source=source,kind=kind,source_id=raw['source_id'],symbol=symbol if symbol in SYMBOLS else 'UNVERIFIED',timeframe=raw['timeframe'] if raw['timeframe'] in PERIODS else 'UNVERIFIED')
  path='grid/schema.sql' if source=='grid' else 'strattester/persistence/result_store.py' if kind=='research' else 'strattester/marketdata/schema.py'
  provenance=raw['provenance'];template=hashlib.sha256(encoded(json.loads((ROOT/'r2-contract-v1.json').read_text(encoding='utf8')))).hexdigest()
  if provenance!=dict(kind='SYNTHETIC',source_sha=LOCK[source]['sha'],schema_sha256=LOCK[source]['files'][path],template_sha256=template) or seal(copy.deepcopy(raw))['data_sha256']!=raw['data_sha256']:
   out['state']='INVALID_PROVENANCE';return out
  expected='pg18-structural-v1' if source=='grid' else 'research-structural-v1' if kind=='research' else 2
  if type(raw['schema_version']) is not type(expected) or raw['schema_version']!=expected or source=='grid' and (type(raw['server_major']) is not int or raw['server_major']!=18):
   out['state']='SCHEMA_MISMATCH';return out
  if source!='grid' and (type(raw['schema_version']) is not type(expected) or raw['schema_version']!=expected or raw['server_major'] is not None):out['state']='SCHEMA_MISMATCH';return out
  if symbol not in SYMBOLS or timeframe not in PERIODS or raw['symbol']!=symbol:out['state']='IDENTITY_MISMATCH';return out
  if raw['timeframe'] not in PERIODS:raise ValueError()
  if source=='grid' and (raw['timeframe']!='1m' or timeframe!='1m'):out['state']='UNSUPPORTED_TIMEFRAME';return out
  if raw['timeframe']!=timeframe:out['state']='IDENTITY_MISMATCH';return out
  for key in ('epoch','sequence'):
   if type(raw[key]) is not int or not 1<=raw[key]<=2**31-1:raise ValueError()
  cursor=(raw['epoch'],raw['sequence'])
  if previous is not None and cursor<=previous:out['state']='DUPLICATE' if cursor==previous else 'OUT_OF_ORDER';return out
  observed=stamp(raw['observed_at_ms']);cover=raw['coverage'];period=PERIODS[timeframe]
  if observed>as_of_ms:out['state']='FUTURE_LEAKAGE';return out
  if set(cover)!={'from_ms','to_ms','verified'} or cover['verified'] is not False or not stamp(cover['from_ms'])<=stamp(cover['to_ms'])<=observed:raise ValueError()
  if type(raw['complete_price_levels']) is not bool or raw['source_state'] not in ('AVAILABLE','PARTIAL','UNAVAILABLE','TIMEOUT'):raise ValueError()
  if type(raw['seed']) is not int or not 0<=raw['seed']<=2**31-1 or raw['dataset_id']!=f"synthetic-v1:{raw['seed']}:{symbol}":raise ValueError()
  rows=raw['rows']
  if not isinstance(rows,list) or len(rows)>300:raise ValueError()
  for row in rows:
   if not isinstance(row,dict):raise ValueError()
   if row.get('symbol')!=symbol or row.get('timeframe')!=timeframe:raise ValueError()
   if stamp(row['available_at_ms'])>as_of_ms or row['available_at_ms']>observed:out['state']='FUTURE_LEAKAGE';return out
   if kind=='research':
    if set(row)!={'symbol','timeframe','run_id','dataset_id','created_at_ms','dataset_to_ms','available_at_ms','metrics','publication_authority'} or row['publication_authority']!='UNVERIFIED':raise ValueError()
    if not isinstance(row['run_id'],str) or not row['run_id'].startswith('synthetic-run-') or len(row['run_id'])>64:raise ValueError()
    if not cover['from_ms']<=stamp(row['dataset_to_ms'])<=cover['to_ms']<=stamp(row['created_at_ms'])<=row['available_at_ms']:raise ValueError()
    if set(row['metrics'])!={'sample_count','pnl'} or type(row['metrics']['sample_count']) is not int or not 0<=row['metrics']['sample_count']<=1000000:raise ValueError()
    number(row['metrics']['pnl'],nullable=True)
   else:
    allowed={'symbol','timeframe','t','available_at_ms'}|({'o','h','l','c','v','complete','poc'} if kind=='candles' else {'price','buy','sell','delta','volume'})
    if set(row)!=allowed or not cover['from_ms']<=stamp(row['t'])<cover['to_ms'] or row['t']%period:raise ValueError()
  if kind!='research' and rows and (min(r['t'] for r in rows)!=cover['from_ms'] or max(r['t'] for r in rows)+period!=cover['to_ms']):raise ValueError()
  if kind=='research' and len({r['run_id'] for r in rows})!=len(rows):raise ValueError()
  legacy=copy.deepcopy(raw);legacy['fixture_version']=1
  if raw['source_state']=='TIMEOUT':legacy['source_state']='AVAILABLE'
  inner=validate_fixture(legacy,as_of_ms)
  if inner['state'] in ('INVALID_DATA','INVALID_PROVENANCE','SCHEMA_MISMATCH','FUTURE_LEAKAGE'):out['state']=inner['state'];return out
  state='UNAVAILABLE' if raw['source_state']=='UNAVAILABLE' else 'TIMEOUT' if raw['source_state']=='TIMEOUT' else 'NO_DATA' if not rows else 'STALE' if as_of_ms-observed>120000 or inner['state']=='STALE' else 'GAP' if inner['coverage'].get('missing_intervals',0) else 'PARTIAL' if raw['source_state']=='PARTIAL' or inner['state']=='PARTIAL' else 'HISTORICAL_ONLY'
  out.update(state=state,authority='SYNTHETIC_ONLY',provenance=copy.deepcopy(provenance),schema_version=expected,epoch=raw['epoch'],sequence=raw['sequence'],observed_at_ms=observed,freshness_ms=as_of_ms-observed,data_sha256=raw['data_sha256'],coverage=copy.deepcopy(cover),rows=[] if state in ('UNAVAILABLE','TIMEOUT') else copy.deepcopy(rows))
 except (ValueError,TypeError,KeyError,OverflowError,RecursionError):out.update(state='INVALID_DATA',rows=[],authority='UNVERIFIED')
 return out

def views(*,symbol='BTCUSDT',timeframe='1m',seed=17,step=0,scenario='normal'):
 if symbol not in SYMBOLS or timeframe not in PERIODS or type(seed) is not int or not 0<=seed<=2**31-1 or type(step) is not int or not 0<=step<=600:raise ValueError()
 now=BASE_MS+step*1000;result=[]
 for template in fixtures():
  raw=copy.deepcopy(template);native='1m' if raw['source']=='grid' else timeframe;period=PERIODS[native];end=now//period*period
  raw.update(symbol=symbol,timeframe=native,seed=seed,dataset_id=f'synthetic-v1:{seed}:{symbol}',observed_at_ms=now,sequence=step+1)
  rows=raw['rows'];kind=raw['kind'];raw['coverage']=dict(from_ms=end-(3*period if kind=='candles' else period),to_ms=end,verified=False)
  for i,row in enumerate(rows):
   row.update(symbol=symbol,timeframe=native)
   if kind=='research':row.update(dataset_id=raw['dataset_id'],dataset_to_ms=end,created_at_ms=now,available_at_ms=now)
   else:row.update(t=end-(3-i)*period if kind=='candles' else end-period,available_at_ms=end-(2-i)*period if kind=='candles' else end)
  if scenario=='unavailable':raw['source_state']='UNAVAILABLE'
  elif scenario=='schema-mismatch':raw['schema_version']='unknown'
  elif scenario=='future':rows[0]['available_at_ms']=now+1
  elif scenario=='nan':rows[0]['available_at_ms']=None
  elif scenario=='partial':raw['source_state']='PARTIAL';raw['complete_price_levels']=False
  seal(raw);result.append(validate(raw,symbol=symbol,timeframe=timeframe,as_of_ms=now))
 return result
