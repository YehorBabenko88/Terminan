"""Read-only display admission. Integrity is not source authentication.

Python verifies the producer's canonical SHA256, including float spelling (1.0)
that JSON.stringify would change. No model execution, scoring, DB or file I/O.
"""
import hashlib
import json
import math
import re

LIMIT = 2 * 1024 * 1024
UNIFIED_LIMIT = 8 * 1024 * 1024
SCIENTIFIC_SHA = '1f97e56701c0fce01dc8dd05952111fa8df3f2d1'

def fail(code):raise ValueError(code)
def require(ok,code):
    if not ok:fail(code)
def obj(v):return type(v) is dict
def clock(v):return type(v) is int and 0 <= v <= 2**53-1
def finite(v):return type(v) in (int,float) and math.isfinite(v)
def text(v):return type(v) is str and 1 <= len(v) <= 256
def sha(v):return type(v) is str and re.fullmatch('[a-f0-9]{64}',v) is not None
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()

def _provenance(source):
    """Allow identity fields, never arbitrary nested outcome-bearing objects."""
    result={k:source[k] for k in ('dataset_id','snapshot_fingerprint','source_authenticity') if text(source.get(k))}
    if clock(source.get('watermark_ms')):result['watermark_ms']=source['watermark_ms']
    identity=source.get('identity')
    if obj(identity):result['identity']={k:identity[k] for k in ('identity','source_revision','epoch','venue','market_type','symbol') if text(identity.get(k))}
    receipts=source.get('receipt_hashes')
    if type(receipts) is list:result['receipt_hashes']=[x for x in receipts if sha(x)]
    return result

def _model(model):
    if not obj(model):return 'UNKNOWN'
    result={k:model[k] for k in ('commit','tree','python_sha256','node_sha256') if text(model.get(k))}
    if obj(model.get('manifest')):result['manifest']={k:v for k,v in model['manifest'].items() if sha(v)}
    return result

def _pairs(items):
    d={}
    for k,v in items:
        require(k not in d,'DUPLICATE_KEY');d[k]=v
    return d

def _bounded(v,depth=0):
    require(depth<=24,'DEPTH_LIMIT')
    if obj(v):
        require(len(v)<=256,'OBJECT_LIMIT')
        for flag in ('execution_authority','trading_authorized','training_authorized','mathematicallyVerified'):
            if flag in v:require(v[flag] is False,'AUTHORITY_DENIED')
        if 'source_authenticity' in v:
            require(v['source_authenticity'] in ('UNATTESTED','REQUIRES_INDEPENDENT_RECEIPT_PROVISIONING','NOT_EVALUATED_BY_MATH'),'UNSUPPORTED_OR_UNTRUSTED_PACKET')
        for k,x in v.items():
            require(len(k)<=256,'KEY_LIMIT');_bounded(x,depth+1)
    elif type(v) is list:
        require(len(v)<=2000,'ROW_LIMIT')
        for x in v:_bounded(x,depth+1)
    elif type(v) is str:require(len(v)<=4096,'TEXT_LIMIT')
    elif type(v) in (int,float):require(finite(v),'NONFINITE')

def _authority(p):
    require(obj(p),'PACKET_REQUIRED')
    require(all(p.get(k) is False for k in ('execution_authority','training_authorized','trading_authorized')),'AUTHORITY_DENIED')
    require(p.get('mathematicallyVerified',False) is False,'AUTHORITY_DENIED')

def _identity(p):
    market=p.get('market');units=p.get('units')
    require(obj(market) and all(text(market.get(k)) for k in ('venue','market_type','symbol')),'MARKET_IDENTITY_REQUIRED')
    require(obj(units) and text(units.get('price')) and units.get('time')=='UTC_MS','UNITS_REQUIRED')
    require(sha(p.get('dataset_id')) and sha(p.get('snapshot_fingerprint')),'DATASET_REQUIRED')
    return {k:p[k] for k in ('dataset_id','snapshot_fingerprint','market','units')}

def _history(p):
    require(p.get('scientific_api')=='NOT_EXECUTED' and p.get('math_history_api')=='math.history.result.v1.1','UNSUPPORTED_API')
    require(all(sha(p.get(k)) for k in ('review_fingerprint','result_receipt')),'RECEIPT_REQUIRED')
    source=p.get('source');require(obj(source),'SOURCE_REQUIRED')
    # Legacy producer carries price units only under source. Never invent them.
    units=p.get('units',source.get('units'))
    require(units==source.get('units'),'UNITS_MISMATCH')
    identity=_identity({**p,'units':units})
    require(text(p.get('strategy')),'MODEL_REQUIRED')
    prices=p.get('observed_prices');forecasts=p.get('forecast_points')
    require(type(prices) is list and 1<=len(prices)<=2000 and type(forecasts) is list and len(forecasts)<=2000,'ROW_LIMIT')
    observations=[];previous=-1
    for r in prices:
        require(obj(r),'INVALID_OBSERVATION')
        e,a,w=(r.get(k) for k in ('event_end_ms','available_at_ms','watermark_ms'))
        require(all(clock(x) for x in (e,a,w)) and previous<e<=w<=a,'INVALID_SOURCE_CLOCK')
        require(finite(r.get('value')) and r['value']>0,'INVALID_PRICE')
        observations.append({'time':e,'available':a,'value':r['value'],'watermark':w});previous=e
    points=[];seen=set()
    available_by_event={r['time']:max(x['available'] for x in observations if x['time']<=r['time']) for r in observations}
    for r in forecasts:
        require(obj(r),'INVALID_FORECAST')
        e,a,d,t=(r.get(k) for k in ('feature_event_end_ms','feature_available_at_ms','decision_ms','target_event_end_ms'))
        require(all(clock(x) for x in (e,a,d,t)) and e<=a<=d<t,'INVALID_FORECAST_CLOCK')
        require(e in available_by_event and a>=available_by_event[e],'FORECAST_SOURCE_BINDING')
        require(finite(r.get('value')) and r['value']>0 and sha(r.get('request_digest')),'INVALID_FORECAST')
        require((d,t,r['request_digest']) not in seen,'DUPLICATE_FORECAST');seen.add((d,t,r['request_digest']))
        points.append({'time':t,'available':a,'decision':d,'feature_event':e,'value':r['value'],'request_digest':r['request_digest']})
    version=p.get('model_version','UNKNOWN');require(text(version),'MODEL_REQUIRED')
    require(obj(p.get('split_receipts',{})),'INVALID_SPLITS')
    oos=None
    if 'oos_available_at_ms' in p:
        a=p['oos_available_at_ms'];splits=p.get('split_receipts')
        require(obj(splits) and obj(splits.get('test')),'OOS_SPLITS_REQUIRED')
        start,end=(splits['test'].get(k) for k in ('start_ms','end_ms'))
        require(clock(start) and clock(end) and start<end and clock(a) and a>=max(end,max(r['available'] for r in observations),max((r['decision'] for r in points),default=0)),'INVALID_OOS_CLOCK')
        metrics=p.get('oos_metrics');require(obj(metrics) and all(finite(v) for v in metrics.values()),'INVALID_OOS_METRICS')
        oos={'available':a,'start':start,'end':end,'metrics':metrics,'units':units,'label':'PRODUCER_REPORTED_OOS_UNATTESTED'}
    return {'identity':identity,'observations':observations,'observation_digest':digest(observations),
        'layers':[{'label':version+' / '+p['strategy'],'kind':'forecast','unit':units['price'],'points':points}],
        'metadata':{'model_version':version,'model':_model(p.get('model')),'source':_provenance(source),
            'api':p['math_history_api'],'strategy':p['strategy'],
            'split_bounds':{k:{f:v.get(f) for f in ('start_ms','end_ms')} for k,v in p.get('split_receipts',{}).items() if obj(v)},
            'review_fingerprint':p['review_fingerprint'],'result_receipt':p['result_receipt']},'oos':oos}

def _scientific(p):
    identity=_identity(p.get('history_binding',{}));engine=p.get('engine')
    require(engine=={'repository':'YehorBabenko88/math','commit':SCIENTIFIC_SHA,'api_revision':'2.1'},'UNSUPPORTED_ENGINE_PIN')
    request=p.get('request');result=p.get('result')
    require(obj(request) and request.get('schema')=='math.scientific.graph.v2' and request.get('mode')=='HISTORICAL_RESEARCH'
        and request.get('execution_authority') is False and clock(request.get('asOf')),'INVALID_SCIENTIFIC_REQUEST')
    require(obj(result),'INVALID_SCIENTIFIC_RESULT');_authority(result)
    require(result.get('schema')=='math.scientific.result.v2' and result.get('status')=='RESEARCH_ONLY'
        and result.get('source')=='CALLER_SUPPLIED_UNATTESTED' and sha(result.get('requestSHA256')),'INVALID_SCIENTIFIC_RESULT')
    require(type(request.get('nodes')) is list and 1<=len(request['nodes'])<=12 and type(request.get('edges')) is list and len(request['edges'])<=24,'GRAPH_LIMIT')
    outputs=result.get('outputs');require(type(outputs) is list and 1<=len(outputs)<=8,'OUTPUT_LIMIT')
    require(type(request.get('outputs')) is list and all(obj(o) for o in outputs+request['outputs']),'OUTPUT_REQUIRED')
    require([(o.get('node'),o.get('port')) for o in outputs]==[(o.get('node'),o.get('port')) for o in request['outputs']],'OUTPUT_BINDING')
    sources=[n for n in request['nodes'] if obj(n) and n.get('kind')=='source']
    require(len(sources)==1,'SOURCE_BINDING')
    src=sources[0];provenance=src.get('provenance')
    require(provenance=={'sourceId':identity['dataset_id'],'version':identity['snapshot_fingerprint'],'sha256':identity['snapshot_fingerprint']}
        and src.get('unit')==identity['units']['price'],'SOURCE_BINDING')
    require(type(src.get('values')) is list and type(src.get('timestamps')) is list and type(src.get('availableAt')) is list
        and 1<=len(src['values'])<=2000 and len(src['values'])==len(src['timestamps'])==len(src['availableAt']),'SOURCE_BINDING')
    observations=[];previous=-1
    for v,t,a in zip(src['values'],src['timestamps'],src['availableAt']):
        require(finite(v) and v>0 and clock(t) and clock(a) and previous<t<=request['asOf'] and a<=t,'INVALID_SCIENTIFIC_CLOCK')
        observations.append({'time':t,'available':a,'value':v,'watermark':t});previous=t
    layers=[]
    for out in outputs:
        require(out.get('type')=='series' and out.get('unit')==identity['units']['price'],'INCOMPATIBLE_OUTPUT_UNITS_OR_TYPE')
        vals=out.get('values');ts=out.get('timestamps');aa=out.get('availableAt')
        require(type(vals) is list and type(ts) is list and type(aa) is list and 1<=len(vals)<=2000 and len(vals)==len(ts)==len(aa),'OUTPUT_AXIS')
        points=[];previous=-1
        for v,t,a in zip(vals,ts,aa):
            require(finite(v) and clock(t) and clock(a) and previous<t<=request['asOf'] and a<=t,'INVALID_SCIENTIFIC_CLOCK')
            points.append({'time':t,'available':a,'value':v});previous=t
        layers.append({'label':out['node']+':'+out['port'],'kind':'scientific','unit':out['unit'],'points':points})
    return {'identity':identity,'observations':observations,'observation_digest':digest(observations),'layers':layers,
        'metadata':{'model_version':'Scientific v2.1',
            'model':[{k:n[k] for k in ('id','kind','model','expression','outputUnit','window','steps') if k in n and type(n[k]) in (str,int,float)} for n in request['nodes'] if obj(n)],'engine':engine,
            'api':'math.scientific.result.v2','request_sha256':result['requestSHA256'],
            'source':provenance,'result_status':'CALLER_SUPPLIED_UNATTESTED'},'oos':None}

def admit(raw, *, allow_unified=False):
    require(type(raw) is bytes and 2<=len(raw)<=UNIFIED_LIMIT,'FILE_LIMIT')
    try:
        p=json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:fail('NONFINITE'))
        unified=obj(p) and p.get('schema')=='terminan.unified-display.v1'
        if unified:require(allow_unified,'UNIFIED_CONTRACT_IMPORT_DISABLED')
        else:require(len(raw)<=LIMIT,'FILE_LIMIT')
        _bounded(p)
        require(obj(p),'PACKET_REQUIRED');_authority(p)
        require(p.get('evidence_class')=='SYNTHETIC' and p.get('source_authenticity')=='UNATTESTED','UNSUPPORTED_OR_UNTRUSTED_PACKET')
        schema=p.get('schema')
        require(schema in ('terminan.history.scientific-handoff.v1','terminan.scientific-overlay.v1','terminan.unified-display.v1'),'UNSUPPORTED_SCHEMA')
        key='handoff_sha256' if schema=='terminan.history.scientific-handoff.v1' else 'packet_sha256'
        receipt=p.get(key);require(sha(receipt),'RECEIPT_REQUIRED')
        require(digest({k:v for k,v in p.items() if k!=key})==receipt,'DIGEST_MISMATCH')
        if unified:
            from .unified_display import adapt
            result=adapt(p)
        else:result=_history(p) if key=='handoff_sha256' else _scientific(p)
        return {**result,'receipt':receipt,'integrity':'SHA256_MATCH','authenticity':'UNATTESTED','schema':schema}
    except (KeyError,TypeError,OverflowError,RecursionError,UnicodeError):
        raise ValueError('INVALID_PACKET') from None
