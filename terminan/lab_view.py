"""Strict, bounded read-only view of reported public-market/paper observations."""
import json, math, os, re, stat, time
from pathlib import Path

NODES={'LS5','PC1','PC2','PC3','PC4','LS7'}
LIMIT=1048576
LABEL=re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
CODE=re.compile(r'[A-Z][A-Z0-9_]{0,63}\Z')
SYMBOL=re.compile(r'[A-Z0-9]{1,24}USDT\Z')
def require(ok):
 if not ok:raise ValueError('INVALID_SNAPSHOT')
def closed(obj,keys):require(type(obj) is dict and set(obj)==set(keys.split()))
def label(v):require(type(v) is str and LABEL.fullmatch(v) is not None and 'ADMINIT' not in v.upper())
def code(v,nullable=True):require((v is None and nullable) or (type(v) is str and CODE.fullmatch(v) is not None))
def integer(v):require(type(v) is int and 0<=v<=9007199254740991)
def number(v,positive=False):require(type(v) in (int,float) and math.isfinite(v) and abs(v)<=1e15 and (not positive or v>0))
def stamp(v,now):integer(v);require(0<v<=now)
def rows(v,limit):require(type(v) is list and len(v)<=limit)
def unique(items,key):require(len({x[key] for x in items})==len(items))
def pairs(items):
 obj={}
 for k,v in items:
  require(k not in obj);obj[k]=v
 return obj

def validate(d,now):
 closed(d,'schema mode trading_authorized release_id run_id sequence generated_at_ms quotes trades strategies nodes errors')
 require(d['schema']=='unified.lab.market-paper.v1' and d['mode']=='LAB_SIMULATION' and d['trading_authorized'] is False)
 label(d['release_id']);label(d['run_id']);integer(d['sequence']);stamp(d['generated_at_ms'],now)
 generated=d['generated_at_ms']
 rows(d['quotes'],10);require(len(d['quotes'])==10)
 for q in d['quotes']:
  closed(q,'symbol last_price bid ask event_ts_ms source');require(type(q['symbol']) is str and SYMBOL.fullmatch(q['symbol']) is not None and q['source']=='BYBIT_PUBLIC')
  for k in ('last_price','bid','ask'):number(q[k],True)
  require(q['bid']<=q['ask']);stamp(q['event_ts_ms'],generated)
 unique(d['quotes'],'symbol');symbols={q['symbol'] for q in d['quotes']}
 rows(d['strategies'],128)
 for s in d['strategies']:
  closed(s,'id status trades error_code');label(s['id']);require(s['status'] in ('READY','RUNNING','FAILED','DISABLED'));integer(s['trades']);code(s['error_code'])
 unique(d['strategies'],'id');strategies={s['id'] for s in d['strategies']}
 rows(d['trades'],200)
 for t in d['trades']:
  closed(t,'trade_id symbol strategy side entry_ts_ms exit_ts_ms entry_price exit_price qty fees funding slippage pnl status')
  label(t['trade_id']);require(t['symbol'] in symbols and t['strategy'] in strategies and t['side'] in ('BUY','SELL') and t['status'] in ('OPEN','CLOSED','REJECTED'))
  stamp(t['entry_ts_ms'],generated)
  for k in ('entry_price','qty'):number(t[k],True)
  for k in ('fees','funding','slippage','pnl'):number(t[k])
  require(t['fees']>=0 and t['slippage']>=0)
  if t['status']=='CLOSED':
   stamp(t['exit_ts_ms'],generated);require(t['exit_ts_ms']>=t['entry_ts_ms']);number(t['exit_price'],True)
  else:require(t['exit_ts_ms'] is None and t['exit_price'] is None)
 unique(d['trades'],'trade_id')
 rows(d['nodes'],6);require(len(d['nodes'])==6)
 for n in d['nodes']:
  closed(n,'node_id role state last_heartbeat_ms error_code');require(n['node_id'] in NODES and n['role'] in ('CONTROL','WORKER','RESEARCH','MONITOR') and n['state'] in ('STARTING','READY','STALE','OFFLINE','FAILED'));stamp(n['last_heartbeat_ms'],generated);code(n['error_code'])
 unique(d['nodes'],'node_id')
 rows(d['errors'],100)
 for e in d['errors']:
  closed(e,'code component ts_ms');code(e['code'],False);label(e['component']);stamp(e['ts_ms'],generated)
 return d

def read_snapshot(path):
 require(type(path) is str and path and not path.startswith(('\\\\','//')))
 p=Path(path);require(p.is_absolute() and '..' not in p.parts and ':' not in path[len(p.drive):])
 # Check every parent too: a junction directory is as unsafe as a linked file.
 for part in (*reversed(p.parents),p):
  st=part.lstat();require(not stat.S_ISLNK(st.st_mode) and not getattr(st,'st_file_attributes',0)&0x400)
 initial=p.lstat();require(stat.S_ISREG(initial.st_mode) and initial.st_nlink==1 and initial.st_size<=LIMIT)
 fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0)|getattr(os,'O_NONBLOCK',0))
 with os.fdopen(fd,'rb') as f:
  before=os.fstat(f.fileno());require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and (before.st_dev,before.st_ino)==(initial.st_dev,initial.st_ino))
  raw=f.read(LIMIT+1);after=os.fstat(f.fileno())
  require(len(raw)<=LIMIT and (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino))
  final=p.lstat();require((final.st_dev,final.st_ino)==(after.st_dev,after.st_ino) and final.st_nlink==1 and not getattr(final,'st_file_attributes',0)&0x400)
 return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda _:require(False)),after.st_mtime_ns//1000000

def overview(path=None,*,now_ms=None):
 now=int(time.time()*1000) if now_ms is None else now_ms
 base=dict(schema='unified.lab.market-paper.v1',mode='LAB_SIMULATION',trading_authorized=False,authority='REPORTED_UNATTESTED',state='UNAVAILABLE',error='LAB_SNAPSHOT_UNAVAILABLE',quotes=[],trades=[],strategies=[],nodes=[],errors=[])
 try:
  d,mtime=read_snapshot(os.environ.get('TERMINAN_LAB_SNAPSHOT','') if path is None else path)
  validate(d,now);require(mtime<=now)
  stale=now-d['generated_at_ms']>15000 or now-mtime>15000 or any(now-q['event_ts_ms']>15000 for q in d['quotes'])
  for n in d['nodes']:
   if now-n['last_heartbeat_ms']>30000:n['state']='STALE'
  base.update(d,state='STALE' if stale else 'AVAILABLE',error='LAB_SNAPSHOT_STALE' if stale else None)
 except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError):pass
 return base



