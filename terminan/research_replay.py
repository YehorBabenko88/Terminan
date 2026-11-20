"""Bounded offline signal replay through the single canonical PaperEngine.

No collection, live gateway, strategy scheduler or secondary execution engine.
Read JSON from stdin with python -m terminan.research_replay. Persistence is the
same opt-in dedicated paper ledger; no market rows or credentials are stored.
"""
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import argparse,json,os,re,sys
from .paper import PaperEngine,STRATEGIES,_serialize
from .contracts import strategy_fingerprint
from .paper_ledger import PaperReplayLedger,canonical_json
from .research_signals import ResearchSignal,ResearchBar

SCHEMA='terminan.paper.signal-replay.v1'
RESULT='terminan.paper.signal-result.v1'
_LIMIT=4*1024*1024

def _text(value):return type(value) is str and 1<=len(value)<=256 and value.isascii()

def _metadata(request):
    if type(request) is not dict or set(request)!={'schema','run_id','strategy','source','parameters','signal','bars'} or request['schema']!=SCHEMA:raise ValueError('canonical signal replay required')
    if type(request['run_id']) is not str or re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}',request['run_id']) is None or request['strategy']!={'id':'ohlc_signal','version':'1'}:raise ValueError('canonical signal strategy identity required')
    source=request['source']
    if (type(source) is not dict or set(source)!={'snapshot_sha256','as_of_ms','available_from_ms','units'} or type(source['snapshot_sha256']) is not str
            or re.fullmatch('[a-f0-9]{64}',source['snapshot_sha256']) is None or type(source['as_of_ms']) is not int or not 0<=source['as_of_ms']<=4102444800000
            or type(source['available_from_ms']) is not int or not 0<=source['available_from_ms']<=source['as_of_ms']
            or source['units']!={'price':'quote/base','volume':'base'}):raise ValueError('unattested source envelope required')
    policy=request['parameters']
    if (type(policy) is not dict or not {'bar_ms'}<=set(policy)<= {'bar_ms','ambiguity_policy','notional','fee_rate','slippage_bps'}
            or type(policy['bar_ms']) is not int or not 1<=policy['bar_ms']<=2678400000 or policy.get('ambiguity_policy','SL_FIRST') not in ('SL_FIRST','TP_FIRST')
            or any(not _text(value) for key,value in policy.items() if key in ('notional','fee_rate','slippage_bps'))):raise ValueError('bounded signal execution policy required')
    signal=request['signal']
    if (type(signal) is not dict or set(signal)!={'symbol','decision_ms','side','entry_kind','entry_price','stop','target'} or type(signal['symbol']) is not str
            or re.fullmatch('[A-Z0-9]{2,30}',signal['symbol']) is None or type(signal['decision_ms']) is not int or not source['available_from_ms']<=signal['decision_ms']<=source['as_of_ms']
            or signal['side'] not in ('long','short') or signal['entry_kind'] not in ('market','limit') or not _text(signal['stop']) or not _text(signal['target'])
            or (signal['entry_kind']=='market' and signal['entry_price'] is not None) or (signal['entry_kind']=='limit' and not _text(signal['entry_price']))):raise ValueError('typed signal descriptor required')
    rows=request['bars'];fields={'start_ms','open','high','low','close'}
    if type(rows) is not list or not 1<=len(rows)<=20000:raise ValueError('bounded OHLC batch required')
    for row in rows:
        if (type(row) is not dict or set(row) not in (fields,fields|{'volume'}) or type(row['start_ms']) is not int
                or any(not _text(value) for key,value in row.items() if key!='start_ms')):raise ValueError('typed OHLC descriptor required')

def run_signal_replay(request):
    _metadata(request);raw=canonical_json(request)
    if len(raw)>_LIMIT:raise ValueError('signal replay byte limit')
    request=json.loads(raw);pin=sha256(raw).hexdigest();path=os.environ.get('TERMINAN_PAPER_LEDGER')
    if path:
        existing=PaperReplayLedger.lookup_existing(path,request['run_id'],pin)
        if existing is not None:
            if existing.get('schema')!=RESULT or existing.get('strategy',{}).get('id')!='ohlc_signal' or existing['strategy'].get('version')!='1':raise RuntimeError('cached signal identity mismatch')
            return existing
    definition=next(item for item in STRATEGIES.discover() if item.id=='ohlc_signal' and item.version=='1')
    if definition.enabled is not True or definition.implementation is not PaperEngine:raise ValueError('signal strategy unavailable')
    policy=request['parameters'];signal=request['signal']
    descriptor=ResearchSignal(signal['symbol'],signal['decision_ms'],signal['side'],signal['entry_kind'],None if signal['entry_price'] is None else Decimal(signal['entry_price']),Decimal(signal['stop']),Decimal(signal['target']))
    bars=tuple(ResearchBar(row['start_ms'],*(Decimal(row[key]) for key in ('open','high','low','close')),Decimal(row.get('volume','0'))) for row in request['bars'])
    engine=PaperEngine(**{key:value for key,value in policy.items() if key in ('notional','fee_rate','slippage_bps')});engine.enabled=True
    execution=engine.execute_signal(descriptor,bars,bar_ms=policy['bar_ms'],as_of_ms=request['source']['as_of_ms'],available_from_ms=request['source']['available_from_ms'],ambiguity_policy=policy.get('ambiguity_policy','SL_FIRST'))
    result=dict(schema=RESULT,run_id=request['run_id'],request_sha256=pin,source=request['source'],strategy=dict(id=definition.id,version=definition.version,fingerprint=strategy_fingerprint(definition)),status='OFFLINE_UNATTESTED',provenance='CALLER_SUPPLIED_UNATTESTED',execution_authority=False,trading_authorized=False,bars_processed=len(bars),**_serialize(asdict(execution)))
    result['result_sha256']=sha256(canonical_json(result)).hexdigest()
    return PaperReplayLedger(path).record(result) if path else result

def main(argv=None,*,stdin=None,stdout=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args(argv)
    stdin=sys.stdin if stdin is None else stdin;stdout=sys.stdout if stdout is None else stdout
    try:
        raw=stdin.read(_LIMIT+1)
        if not raw or len(raw)>_LIMIT or len(raw.encode('utf8'))>_LIMIT:raise ValueError('bounded JSON required')
        def unique(pairs):
            out={}
            for key,value in pairs:
                if key in out:raise ValueError('duplicate field')
                out[key]=value
            return out
        result=run_signal_replay(json.loads(raw,object_pairs_hook=unique));code=0
    except Exception:result=dict(status='OFFLINE_REPLAY_REJECTED',execution_authority=False,trading_authorized=False);code=1
    print(json.dumps(result,sort_keys=True,allow_nan=False),file=stdout);return code

if __name__=='__main__':raise SystemExit(main())
