"""Inert Unified display adapter. No engine invocation or source admission."""
from .history_overlay import require,obj,clock,finite,text,sha,canonical,digest,_history,_model

def checked_receipt(p,key):
    require(obj(p) and sha(p.get(key)) and p[key]==digest({k:v for k,v in p.items() if k!=key}),'UNIFIED_RECEIPT')

def adapt(p):
    require(p.get('contract_only') is True and p.get('qualification')=='NOT_QUALIFIED','UNIFIED_QUALIFICATION_DENIED')
    history=p.get('history');q=p.get('joint_request');j=p.get('joint_result')
    checked_receipt(history,'handoff_sha256');checked_receipt(j,'completion_receipt')
    require(history.get('schema')=='terminan.history.scientific-handoff.v1'
        and history.get('evidence_class')=='SYNTHETIC' and history.get('source_authenticity')=='UNATTESTED','UNIFIED_HISTORY')
    require(all(history.get(k) is False and j.get(k) is False for k in ('execution_authority','training_authorized','trading_authorized')),'AUTHORITY_DENIED')
    base=_history(history)
    require(obj(q) and q.get('schema')=='math.history.scientific.request.v1'
        and j.get('schema')=='math.history.scientific.result.v1' and j.get('api_revision')=='history-1.1+scientific-2.1','UNIFIED_SCHEMA')
    h=q.get('history');result=j.get('history');graph=q.get('graph')
    require(obj(h) and obj(result) and obj(graph),'UNIFIED_REQUEST')
    require(j.get('joint_request',q)==q,'UNIFIED_CAPTURED_REQUEST')
    require(set(h)=={'schema','dataset_id','dataset_fingerprint','source','market','units','rows','decision_ms',
        'train_count','train_end_ms','max_age_ms','model_version'} and h.get('schema')=='math.history.request.v1.1'
        and h.get('model_version')=='grid-frozen-analog-v1' and history.get('model_version')==h['model_version'],'UNIFIED_HISTORY_REQUEST')
    require(j.get('request_digest')==digest(q) and result.get('request_digest')==digest(h),'UNIFIED_REQUEST_DIGEST')
    require(j.get('provenance')=={k:h.get(k) for k in ('dataset_id','dataset_fingerprint','source','market','units','decision_ms','rows')},'UNIFIED_PROVENANCE')
    require(h.get('dataset_id')==history['dataset_id'] and h.get('dataset_fingerprint')==history['snapshot_fingerprint']
        and h.get('source')==history['source'].get('identity') and h.get('market')==history['market']
        and obj(h.get('units')) and h['units']=={'price':history['units']['price'],'volume':'BTC'},'UNIFIED_SOURCE_BINDING')
    rows=h.get('rows');d=h.get('decision_ms');pub=p.get('joint_published_at_ms')
    require(type(rows) is list and 20<=len(rows)<=2000 and clock(d) and clock(pub) and d<=pub,'UNIFIED_PUBLICATION_CLOCK')
    require(type(h.get('train_count')) is int and 20<=h['train_count']<=len(rows)
        and clock(h.get('train_end_ms')) and h['train_end_ms']<=d and clock(h.get('max_age_ms')),'UNIFIED_TRAIN_CLOCK')
    require(all(obj(r) and all(clock(r.get(k)) for k in ('event_end_ms','available_at_ms','watermark_ms'))
        and r['event_end_ms']<=r['watermark_ms']<=r['available_at_ms']<=d and finite(r.get('close')) and r['close']>0 for r in rows),'UNIFIED_PREFIX_CLOCK')
    previous=None
    for i,row in enumerate(rows):
        start=row.get('event_start_ms');a=row.get('source_event_start_ms');b=row.get('source_event_end_ms');end=row['event_end_ms']
        require(all(clock(t) for t in (start,a,b)) and start%60000==0 and end==start+60000
            and start<=a<=b<end and (previous is None or previous==start),'UNIFIED_SOURCE_EVENT_CLOCK')
        require(sha(row.get('revision')) and sha(row.get('source_receipt_hash')),'UNIFIED_REVISION_RECEIPT')
        require(all(finite(row.get(k)) for k in ('open','high','low','volume')) and row['volume']>=0
            and 0<row['low']<=min(row['open'],row['close'])<=max(row['open'],row['close'])<=row['high'],'UNIFIED_OHLCV')
        require(i>=h['train_count'] or row['available_at_ms']<=h['train_end_ms'],'UNIFIED_TRAIN_LOOKAHEAD')
        previous=end
    require(d-rows[-1]['event_end_ms']<=h['max_age_ms'] and d<rows[-1]['event_end_ms']+60000,'UNIFIED_ELAPSED_HORIZON')
    prefix=[{'event_end_ms':r['event_end_ms'],'available_at_ms':r['available_at_ms'],'watermark_ms':r['watermark_ms'],'value':r['close']} for r in rows]
    require(history['observed_prices'][:len(rows)]==prefix and result.get('prefix_digest')==digest(rows),'UNIFIED_PREFIX_BINDING')
    require(result.get('decision_ms')==d and result.get('feature_event_end_ms')==rows[-1]['event_end_ms']
        and result.get('feature_available_at_ms')==max(r['available_at_ms'] for r in rows)
        and result.get('forecast_target_event_end_ms')==rows[-1]['event_end_ms']+60000,'UNIFIED_FEATURE_BINDING')
    require(any(r['decision_ms']==d and r['target_event_end_ms']==result.get('forecast_target_event_end_ms')
        and r['value']==result.get('forecast') and r['request_digest']==result.get('request_digest')
        and r['feature_event_end_ms']==result['feature_event_end_ms']
        and r['feature_available_at_ms']==result['feature_available_at_ms'] for r in history['forecast_points']),'UNIFIED_FROZEN_FORECAST')
    source=j.get('math_source');model=history.get('model')
    require(obj(source) and obj(model) and all(source.get(k)==model.get(k) for k in ('commit','tree','python_sha256')),'UNIFIED_MATH_SOURCE')
    require(all(type(source.get(k)) is str and len(source[k])==40 and all(c in '0123456789abcdef' for c in source[k]) for k in ('commit','tree'))
            and sha(source.get('python_sha256')) and sha(source.get('node_sha256')),'UNIFIED_MATH_SOURCE')
    manifest=source.get('manifest');old=model.get('manifest')
    require(obj(manifest) and obj(old) and old and all(sha(v) for v in manifest.values())
        and all(manifest.get(k)==v for k,v in old.items())
        and any(k.startswith('src/') for k in manifest) and any(k.startswith('python/') for k in manifest),'UNIFIED_MATH_MANIFEST')
    nodes=graph.get('nodes');edges=graph.get('edges');outputs=graph.get('outputs')
    require(type(nodes) is list and 1<=len(nodes)<=11 and all(obj(n) and text(n.get('id')) and n.get('id')!='history' and n.get('kind')!='source' for n in nodes)
        and len({n['id'] for n in nodes})==len(nodes) and type(edges) is list and len(edges)<=24
        and type(outputs) is list and 1<=len(outputs)<=64,'UNIFIED_GRAPH_LIMIT')
    injected={'id':'history','kind':'source','type':'series','unit':h['units']['price'],
        'values':[r['close'] for r in rows],'timestamps':[r['event_end_ms'] for r in rows],
        'availableAt':[r['available_at_ms'] for r in rows],
        'provenance':{'sourceId':h['source']['identity'],'version':h['source']['source_revision'],'sha256':result['prefix_digest']}}
    request={'schema':'math.scientific.graph.v2','mode':'HISTORICAL_RESEARCH','execution_authority':False,
        'asOf':d,'nodes':[injected]+nodes,'edges':edges,'outputs':outputs}
    science=j.get('scientific')
    require(obj(science) and science.get('schema')=='math.scientific.result.v2' and science.get('status')=='RESEARCH_ONLY'
        and science.get('source')=='CALLER_SUPPLIED_UNATTESTED' and science.get('mathematicallyVerified') is False
        and all(science.get(k) is False for k in ('execution_authority','training_authorized','trading_authorized')),'UNIFIED_SCIENTIFIC_AUTHORITY')
    returned=science.get('outputs');trace=science.get('trace');order=science.get('order');ids=['history']+[n['id'] for n in nodes]
    require(type(returned) is list and type(trace) is list and type(order) is list and len(order)==len(ids)
        and len(set(order))==len(ids) and set(order)==set(ids)
        and [t.get('node') if obj(t) else None for t in trace]==order,'UNIFIED_TRACE_BINDING')
    require(all(obj(o) and text(o.get('node')) and text(o.get('port')) for o in outputs+returned)
        and [(o['node'],o['port']) for o in returned]==[(o['node'],o['port']) for o in outputs]
        and len({(o['node'],o['port']) for o in outputs})==len(outputs),'UNIFIED_OUTPUT_BINDING')
    diagnostics=[];times=set(injected['timestamps'])
    for out in returned:
        values=out.get('values');ts=out.get('timestamps');aa=out.get('availableAt');typ=out.get('type');unit=out.get('unit')
        require(out['node'] in ids and typ in ('series','scalar') and text(unit)
            and type(values) is list and type(ts) is list and type(aa) is list and 1<=len(values)<=2000
            and len(values)==len(ts)==len(aa) and (typ!='scalar' or len(values)==1),'UNIFIED_OUTPUT_AXIS')
        require(all(finite(v) for v in values) and all(clock(t) and clock(a) and t<=d and a<=d and t in times for t,a in zip(ts,aa))
            and all(ts[i]>ts[i-1] for i in range(1,len(ts))),'UNIFIED_OUTPUT_CLOCK')
        if typ=='series' and unit==history['units']['price']:
            base['layers'].append({'label':out['node']+':'+out['port'],'kind':'scientific','unit':unit,'known_at':pub,
                'points':[{'time':t,'available':a,'value':v} for v,t,a in zip(values,ts,aa)]})
        else:
            diagnostics.append({**out,'kind':'DESCRIPTIVE_NOT_OOS','known_at':pub})
    require(len(base['layers'])<=16,'UNIFIED_LAYER_LIMIT')
    base.update(diagnostics=diagnostics,qualification='UNQUALIFIED_CONTRACT_ONLY',
        scientific_proof={'schema':'terminan.scientific-overlay.v1','request':request,'result':science})
    base['metadata'].update(engine={'repository':'YehorBabenko88/math',**_model(source)},
        joint_request_sha256=j['request_digest'],joint_completion_receipt=j['completion_receipt'],
        joint_published_at_ms=pub,qualification='UNQUALIFIED_CONTRACT_ONLY',api=j['api_revision'])
    return base
