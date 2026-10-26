"""Versioned source-shaped fixtures. Validation performs no source/DB access."""
import copy
import json
import math
from pathlib import Path

LOCK=json.loads((Path(__file__).resolve().parents[1]/'contracts.lock.json').read_text())
PERIODS={'1m':60000,'5m':300000,'15m':900000,'1h':3600000}

def fixtures():
    return json.loads(Path(__file__).with_name('fixtures').joinpath('r2-contract-v1.json').read_text())

def _stamp(value):
    if type(value) is not int or not 0<=value<=2**53-1:raise ValueError()
    return value

def _finite(value,nullable=False):
    if value is None and nullable:return
    if type(value) not in (int,float):raise ValueError()
    try:ok=math.isfinite(value)
    except OverflowError:ok=False
    if not ok:raise ValueError()

def _json_numbers(value):
    if isinstance(value,dict):
        for item in value.values():_json_numbers(item)
    elif isinstance(value,list):
        for item in value:_json_numbers(item)
    elif type(value) in (int,float):_finite(value)

def validate_fixture(raw,as_of_ms):
    out=dict(version=1,mode='SYNTHETIC',runtime_source='NONE',rows=[],state='INVALID_DATA',
             authority='SYNTHETIC_ONLY',coverage={'verified':False,'scope':'BOUNDED_FIXTURE'})
    try:
        _stamp(as_of_ms)
        source=raw['source'];kind=raw['kind'];provenance=raw['provenance']
        if source not in ('grid','strattester') or kind not in ('candles','footprint','research'):return out
        out.update(source=source,kind=kind)
        entry=LOCK[source];path='grid/schema.sql' if source=='grid' else 'strattester/persistence/result_store.py' if kind=='research' else 'strattester/marketdata/schema.py'
        if provenance.get('kind')!='SYNTHETIC' or provenance.get('source_sha')!=entry['sha'] or provenance.get('schema_sha256')!=entry['files'][path]:
            out['state']='INVALID_PROVENANCE';return out
        expected='pg18-structural-v1' if source=='grid' else 'research-structural-v1' if kind=='research' else 2
        if type(raw.get('fixture_version')) is not int or raw.get('fixture_version')!=1 or raw.get('schema_version')!=expected or source=='grid' and raw.get('server_major')!=18:
            out['state']='SCHEMA_MISMATCH';return out
        if raw['source_state']=='UNAVAILABLE':
            out['state']='UNAVAILABLE';return out
        symbol=raw['symbol'];tf=raw['timeframe'];rows=raw['rows']
        if symbol not in ('BTCUSDT','ETHUSDT','SOLUSDT') or not isinstance(rows,list) or len(rows)>300:raise ValueError()
        seed=raw['seed'];dataset=raw['dataset_id']
        if type(seed) is not int or not 0<=seed<=2**31-1 or dataset!=f'synthetic-v1:{seed}:{symbol}':raise ValueError()
        if raw['source_state'] not in ('AVAILABLE','PARTIAL','UNAVAILABLE'):raise ValueError()
        period=PERIODS[tf] if kind!='research' else 0
        stamps=[];keys=set();partial=raw['source_state']=='PARTIAL'
        for row in rows:
            _json_numbers(row)
            available=_stamp(row['available_at_ms'])
            if available>as_of_ms:
                out['state']='FUTURE_LEAKAGE';return out
            if kind=='research':
                created=_stamp(row['created_at_ms']);end=_stamp(row['dataset_to_ms'])
                if row['dataset_id']!=dataset:raise ValueError()
                if not end<=created<=available:
                    out['state']='FUTURE_LEAKAGE';return out
                if not isinstance(row['metrics'],dict):raise ValueError()
                continue
            t=_stamp(row['t'])
            if t>as_of_ms:out['state']='FUTURE_LEAKAGE';return out
            key=(t,row['price']) if kind=='footprint' else t
            if key in keys:raise ValueError()
            keys.add(key);stamps.append(t)
            if t%period:raise ValueError()
            if kind=='candles':
                for field in ('o','h','l','c','v'):_finite(row[field])
                if not 0<row['l']<=min(row['o'],row['c'])<=max(row['o'],row['c'])<=row['h'] or row['v']<0:raise ValueError()
                if type(row['complete']) is not bool:raise ValueError()
                if row['complete'] and (t+period>as_of_ms or available<t+period):
                    out['state']='FUTURE_LEAKAGE';return out
                partial|=not row['complete']
                if 'poc' in row:_finite(row['poc'],nullable=True)
            else:
                for field in ('price','buy','sell','delta','volume'):_finite(row[field])
                if row['price']<=0 or min(row['buy'],row['sell'],row['volume'])<0 or row['buy']+row['sell']!=row['volume'] or row['buy']-row['sell']!=row['delta']:raise ValueError()
                if t+period>as_of_ms or available<t+period:out['state']='FUTURE_LEAKAGE';return out
                partial|=not raw.get('complete_price_levels',False)
        unique=sorted(set(stamps))
        gaps=sum(max(0,(b-a)//period-1) for a,b in zip(unique,unique[1:])) if period else 0
        stale=bool(unique and as_of_ms-unique[-1]-period>120000)
        out.update(rows=copy.deepcopy(rows),source=source,kind=kind,symbol=symbol,timeframe=tf,
                   provenance=copy.deepcopy(provenance),schema_version=expected,
                   state='NO_DATA' if not rows else 'STALE' if stale else 'PARTIAL' if gaps or partial else 'HISTORICAL')
        out['coverage'].update(missing_intervals=gaps,complete_price_levels=raw.get('complete_price_levels',None))
    except (KeyError,TypeError,ValueError,OverflowError,RecursionError):
        out.update(rows=[],state='INVALID_DATA')
    return out
