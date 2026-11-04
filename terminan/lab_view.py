"""Strict, bounded read-only view of reported public-market/paper observations."""
import hashlib, json, math, os, re, stat, time
from datetime import datetime, timezone
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

def read_snapshot(path,*,limit=LIMIT):
 require(type(path) is str and path and not path.startswith(('\\\\','//')))
 p=Path(path);require(p.is_absolute() and '..' not in p.parts and ':' not in path[len(p.drive):])
 # Check every parent too: a junction directory is as unsafe as a linked file.
 for part in (*reversed(p.parents),p):
  st=part.lstat();require(not stat.S_ISLNK(st.st_mode) and not getattr(st,'st_file_attributes',0)&0x400)
 initial=p.lstat();require(stat.S_ISREG(initial.st_mode) and initial.st_nlink==1 and initial.st_size<=limit)
 fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0)|getattr(os,'O_NONBLOCK',0))
 with os.fdopen(fd,'rb') as f:
  before=os.fstat(f.fileno());require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and (before.st_dev,before.st_ino)==(initial.st_dev,initial.st_ino))
  raw=f.read(limit+1);after=os.fstat(f.fileno())
  require(len(raw)<=limit and (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino))
  final=p.lstat();require((final.st_dev,final.st_ino)==(after.st_dev,after.st_ino) and final.st_nlink==1 and not getattr(final,'st_file_attributes',0)&0x400)
 return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda _:require(False)),after.st_mtime_ns//1000000

def overview(path=None,*,now_ms=None):
 now=int(time.time()*1000) if now_ms is None else now_ms
 base=dict(schema='unified.lab.market-paper.v1',mode='LAB_SIMULATION',trading_authorized=False,authority='REPORTED_UNATTESTED',state='UNAVAILABLE',error='LAB_SNAPSHOT_UNAVAILABLE',quotes=[],trades=[],strategies=[],nodes=[],errors=[])
 try:
  source=os.environ.get('TERMINAN_LAB_SNAPSHOT','') if path is None else path
  try:d,mtime=read_snapshot(source)
  except ValueError:
   d,mtime=read_snapshot(source,limit=2097152)
   require(type(d) is dict and d.get('schema')=='unified.lab.market-paper.v2')
  if type(d) is dict and d.get('schema')=='unified.lab.market-paper.v2':return overview_v2(d,mtime,now)
  validate(d,now);require(mtime<=now)
  stale=now-d['generated_at_ms']>15000 or now-mtime>15000 or any(now-q['event_ts_ms']>15000 for q in d['quotes'])
  for n in d['nodes']:
   if now-n['last_heartbeat_ms']>30000:n['state']='STALE'
  base.update(d,state='STALE' if stale else 'AVAILABLE',error='LAB_SNAPSHOT_STALE' if stale else None)
 except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError):pass
 return base


# Additive display-only v2. Source envelopes remain unchanged, never promoted to
# execution/readiness or recomputed accounting. Integer rejection is a browser
# displayability boundary: JSON.parse cannot preserve integers beyond 2**53-1.
V2_SYMBOLS=set('BTCUSDT ETHUSDT SOLUSDT XRPUSDT BNBUSDT DOGEUSDT ADAUSDT AVAXUSDT LINKUSDT DOTUSDT'.split())
V2_ERRORS={'SOURCE_NOT_CONFIGURED','SOURCE_UNAVAILABLE','EXPORT_BLOCKED','VALIDATION_FAILED','STALE_SOURCE'}
V2_TICKER=set('open_interest open_interest_value funding_rate funding_interval_hour next_funding_time mark_price index_price last_price basis_rate bid1_price bid1_size ask1_price ask1_size volume24h turnover24h'.split())
V2_BOOK=set('best_bid best_ask spread bid_depth ask_depth imbalance sequence update_id cts book_update_rate book_add_rate book_cancel_rate book_consume_rate depth_change_rate'.split())
V2_FEEDS={'ticker','orderbook','open_interest','funding'}
V2_MISSING=['OPEN_POSITIONS','ACCOUNT_EQUITY','BALANCE','UNREALIZED_PNL']
V2_DURABILITY='NODE_LOCAL_NOT_DISTRIBUTED_CONSENSUS_OR_FAILOVER'


def bounded_v2(value):
 stack=[(value,0)];count=0
 while stack:
  item,depth=stack.pop();count+=1;require(count<=100000 and depth<=16)
  if type(item) is dict:
   require(all(type(k) is str and len(k)<=128 for k in item));stack.extend((x,depth+1) for x in item.values())
  elif type(item) is list:require(len(item)<=1024);stack.extend((x,depth+1) for x in item)
  elif type(item) is int:require(abs(item)<=9007199254740991)
  elif type(item) is float:require(math.isfinite(item))
  elif type(item) is str:require(len(item)<=4096)
  else:require(item is None or type(item) is bool)


def source_label(value):require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value) is not None)
def source_hash(value):require(type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None)
def source_number(value):require(type(value) in (int,float) and math.isfinite(value))
def source_scalar(value):
 require(value is None or type(value) in (int,float) or type(value) is str and len(value)<=128 and re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',value) is not None)
def source_time(value):
 require(type(value) is str and len(value)<=64)
 parsed=datetime.fromisoformat(value);require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds()==0 and parsed.isoformat(timespec='microseconds')==value)
 delta=parsed-datetime(1970,1,1,tzinfo=timezone.utc)
 return (delta.days*86400+delta.seconds)*1000000+delta.microseconds


def quality_v2(value,symbol):
 if value is None:return
 require(type(value) is dict and set(value)<={'symbol','feeds','missing_counts','last_update'})
 if 'symbol' in value:require(value['symbol']==symbol)
 for group in set(value)-{'symbol'}:
  require(type(value[group]) is dict and set(value[group])<=V2_FEEDS)
  for feed,entry in value[group].items():
   if group=='feeds':closed(entry,'status');require(entry['status'] in ('unknown','available','missing','stale','unsupported','degraded'))
   else:
    source_number(entry);require(entry>=0)
    if group=='missing_counts':integer(entry)


def market_v2(value):
 rows(value,10);symbols=[]
 for packet in value:
  closed(packet,'schema request evidence_class execution_authority trading_authorized rows row_count output_truncated source_completeness selection_scope')
  require(packet['schema']=='grid.lab_observations.v1' and packet['evidence_class']=='persisted_observation_unverified' and packet['execution_authority'] is False and packet['trading_authorized'] is False and packet['output_truncated'] is False and packet['source_completeness']=='NOT_EVALUATED')
  q=packet['request'];closed(q,'symbol start_ms end_ms as_of_ms max_age_ms');require(q['symbol'] in V2_SYMBOLS);symbols.append(q['symbol'])
  for key in ('start_ms','end_ms','as_of_ms','max_age_ms'):integer(q[key]);require(q[key]<=253402300799999)
  require(0<q['end_ms']-q['start_ms']<=3600000 and 0<q['max_age_ms']<=3600000)
  require(packet['selection_scope']==dict(symbol=q['symbol'],event_types=['derivatives_ticker','orderbook_snapshot'],start_ms=q['start_ms'],end_ms=q['end_ms'],range='start_ms <= event_ts < end_ms',ordering=['event_ts','id']))
  rows(packet['rows'],1000);integer(packet['row_count']);require(packet['row_count']==len(packet['rows']));previous=None
  for row in packet['rows']:
   closed(row,'id symbol event_type source event_ts ingest_ts payload event_age_ms observation_status field_freshness')
   integer(row['id']);require(row['id']>0 and row['symbol']==q['symbol'] and row['source']=='bybit' and row['event_type'] in ('derivatives_ticker','orderbook_snapshot') and row['field_freshness']=='unknown')
   event=source_time(row['event_ts']);source_time(row['ingest_ts']);key=(event,row['id'])
   require(q['start_ms']*1000<=event<q['end_ms']*1000 and (previous is None or previous<key));previous=key
   age=q['as_of_ms']*1000-event;source_number(row['event_age_ms']);require(row['event_age_ms']==age/1000)
   require(row['observation_status']==('future' if age<0 else 'stale' if age>q['max_age_ms']*1000 else 'observed'))
   payload=row['payload'];allowed=V2_TICKER if row['event_type']=='derivatives_ticker' else V2_BOOK
   require(type(payload) is dict and set(payload)<=allowed|{'_quality'})
   for name,entry in payload.items():
    if name=='_quality':quality_v2(entry,q['symbol'])
    else:source_scalar(entry)
 require(len(set(symbols))==len(symbols))


def paper_v2(packet):
 closed(packet,'schema mode source_authenticity receipt_provenance durability execution_authority trading_authorized ledger_scope live_wal_supported missing_state selection_order validated_count returned_count has_more rows')
 require(packet['schema']=='stratt.paper.quote.snapshot.v1' and packet['mode']=='PUBLIC_QUOTE_PAPER_RESEARCH' and packet['source_authenticity']=='NOT_EVALUATED' and packet['receipt_provenance']=='CALLER_DECLARED' and packet['durability']==V2_DURABILITY and packet['execution_authority'] is False and packet['trading_authorized'] is False and packet['ledger_scope']=='CHECKPOINTED_ROLLBACK_JOURNAL_ONLY' and packet['live_wal_supported'] is False and packet['missing_state']==V2_MISSING and packet['selection_order']==['admitted_ms DESC','request_id DESC'])
 integer(packet['validated_count']);integer(packet['returned_count']);rows(packet['rows'],200)
 require(packet['returned_count']==len(packet['rows'])<=packet['validated_count']<=1024 and type(packet['has_more']) is bool and packet['has_more']==(packet['validated_count']>packet['returned_count']))
 ids=[];previous=None
 for row in packet['rows']:
  closed(row,'request_id signal_receipt_id request_sha256 result_sha256 admitted_ms result')
  source_label(row['request_id']);source_label(row['signal_receipt_id']);source_hash(row['request_sha256']);source_hash(row['result_sha256']);integer(row['admitted_ms']);ids.append(row['request_id'])
  key=(row['admitted_ms'],row['request_id']);require(previous is None or previous>key);previous=key
  r=row['result'];closed(r,'schema mode trade_id strategy strategy_revision evidence_class request_sha256 symbol units side status entry_ts_ms exit_ts_ms entry_price exit_price raw_entry_price raw_exit_price qty signed_qty gross_raw gross_fill fees slippage funding pnl receipt_bindings source_authenticity receipt_provenance fill_selection missing_capabilities execution_authority trading_authorized training_authorized grid_normal paper_eligible h_b durability')
  require(r['schema']=='stratt.paper.quote.result.v1' and r['mode']=='PUBLIC_QUOTE_PAPER_RESEARCH' and r['trade_id']==row['request_id'] and r['request_sha256']==row['request_sha256'] and r['symbol'] in V2_SYMBOLS and r['status']=='CLOSED' and r['side'] in ('BUY','SELL'))
  source_label(r['strategy']);require(type(r['strategy_revision']) is str and re.fullmatch('[a-f0-9]{40}',r['strategy_revision']) is not None and r['evidence_class'] in ('SYNTHETIC','HISTORICAL','LIVE'))
  require(r['units']==dict(price='USDT/'+r['symbol'][:-4],qty=r['symbol'][:-4]))
  for name in ('entry_ts_ms','exit_ts_ms'):integer(r[name])
  require(r['entry_ts_ms']<=r['exit_ts_ms']<=row['admitted_ms'])
  for name in ('entry_price','exit_price','raw_entry_price','raw_exit_price','qty','signed_qty','gross_raw','gross_fill','fees','slippage','funding','pnl'):source_number(r[name])
  require(all(r[name]>0 for name in ('entry_price','exit_price','raw_entry_price','raw_exit_price','qty')) and r['fees']>=0 and r['slippage']>=0)
  require(r['source_authenticity']=='NOT_EVALUATED' and r['receipt_provenance']=='CALLER_DECLARED' and r['fill_selection']=='CALLER_SUPPLIED_CAUSAL_QUOTES_NOT_COMPLETE_MARKET_STREAM' and r['missing_capabilities']==['MARKET_DEPTH_LIQUIDITY','ACTUAL_EXCHANGE_FILLS','STREAM_COMPLETENESS_ATTESTATION'] and r['durability']==V2_DURABILITY)
  require(all(r[name] is False for name in ('execution_authority','trading_authorized','training_authorized')) and all(r[name]=='NOT_QUALIFIED' for name in ('grid_normal','paper_eligible','h_b')))
  rows(r['receipt_bindings'],133);receipts=[]
  for binding in r['receipt_bindings']:closed(binding,'receipt_id sha256');source_label(binding['receipt_id']);source_hash(binding['sha256']);receipts.append(binding['receipt_id'])
  require(len(receipts)>=5 and len(set(receipts))==len(receipts) and row['signal_receipt_id'] in receipts)
  require(hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==row['result_sha256'])
 require(len(set(ids))==len(ids))


def fleet_v2(packet):
 closed(packet,'mode status execution_authorized nodes links databases alerts source_provenance physical production')
 require(packet['mode']=='PLAN_ONLY' and packet['status']=='PLAN_ONLY' and packet['execution_authorized'] is False and packet['links']==[] and packet['databases']==[] and packet['alerts']==[] and packet['source_provenance']=='NOT_EVALUATED' and packet['physical']=='NOT_RUN' and packet['production']=='NO_GO')
 rows(packet['nodes'],6);ids=[]
 for n in packet['nodes']:
  closed(n,'id epoch sequence state zone modules last_heartbeat_ms cpu memory disk available_resources db_sizes identity_verified')
  require(type(n['id']) is str and 1<=len(n['id'])<=128 and type(n['zone']) is str and 1<=len(n['zone'])<=1024);ids.append(n['id']);integer(n['epoch']);integer(n['sequence']);require(n['epoch']>0)
  require(n['state'] in ('APPROVED','ACTIVE','DRAINING','RETIRED','OFFLINE','SUSPECT','QUARANTINED') and n['identity_verified'] is False and n['modules']==[] and all(n[k] is None for k in ('cpu','memory','disk','db_sizes')))
  if n['last_heartbeat_ms'] is not None:integer(n['last_heartbeat_ms'])
  if n['available_resources'] is not None:
   closed(n['available_resources'],'cpu memory disk')
   for value in n['available_resources'].values():source_number(value);require(0<=value<=9007199254740991)
 require(len(set(ids))==len(ids))


def validate_v2(d,now):
 bounded_v2(d);closed(d,'schema mode trading_authorized authority release_id run_id sequence generated_at_ms sections')
 require(d['schema']=='unified.lab.market-paper.v2' and d['mode']=='LAB_SIMULATION' and d['trading_authorized'] is False and d['authority']=='REPORTED_UNATTESTED')
 label(d['release_id']);label(d['run_id']);integer(d['sequence']);stamp(d['generated_at_ms'],now);closed(d['sections'],'market paper fleet')
 for name,section in d['sections'].items():
  closed(section,'state error_code payload');require(section['state'] in ('AVAILABLE','STALE','UNAVAILABLE') and (section['error_code'] is None or section['error_code'] in V2_ERRORS))
  if section['state']=='UNAVAILABLE':require(section['payload'] is None and section['error_code'] is not None)
  else:
   require(section['error_code']==('STALE_SOURCE' if section['state']=='STALE' else None))
   {'market':market_v2,'paper':paper_v2,'fleet':fleet_v2}[name](section['payload'])
 return d


def overview_v2(d,mtime,now):
 try:
  validate_v2(d,now);require(mtime<=now)
  aged=now-d['generated_at_ms']>15000 or now-mtime>15000
  states={name:('STALE' if aged and s['state']!='UNAVAILABLE' else s['state']) for name,s in d['sections'].items()}
  # Response-only event/declaration age is not per-field freshness or source
  # authentication. Historical paper admission/fill clocks never drive this.
  if states['market']!='UNAVAILABLE':
   clocks=[]
   for packet in d['sections']['market']['payload']:
    clocks.append(packet['request']['as_of_ms'])
    clocks.extend(source_time(row['event_ts'])/1000 for row in packet['rows'])
   if any(now-clock>15000 or clock>now for clock in clocks):states['market']='STALE'
  state='UNAVAILABLE' if all(v=='UNAVAILABLE' for v in states.values()) else 'STALE' if 'STALE' in states.values() else 'PARTIAL' if 'UNAVAILABLE' in states.values() else 'AVAILABLE'
  return dict(d,state=state,error='STALE_SOURCE' if state=='STALE' else None,section_states=states)
 except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
  sections={name:dict(state='UNAVAILABLE',error_code='VALIDATION_FAILED',payload=None) for name in ('market','paper','fleet')}
  return dict(schema='unified.lab.market-paper.v2',mode='LAB_SIMULATION',trading_authorized=False,authority='REPORTED_UNATTESTED',state='UNAVAILABLE',error='VALIDATION_FAILED',sections=sections,section_states={name:'UNAVAILABLE' for name in sections})
