"""Opt-in loopback-only bridge: no DB, no credentials, no orders."""
import json
import os
import math
import re
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

URL = "http://127.0.0.1:8788"
LIMIT = 262144
RESPONSE_LIMIT = 2097152

def engine_url():
    raw=os.environ.get('TERMINAN_MATH_PORT')
    if raw is None:return URL
    if not raw.isascii() or not raw.isdecimal() or len(raw)>5 or not 1<=int(raw)<=65535:
        raise ValueError('INVALID_MATH_LOOPBACK_PORT')
    return 'http://127.0.0.1:'+str(int(raw))

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

# No environment proxy or redirects may turn loopback research into external access.
scientific_urlopen = build_opener(ProxyHandler({}), _NoRedirect()).open
urlopen = scientific_urlopen

def _read_object(response):
    raw=response.read(RESPONSE_LIMIT+1)
    if len(raw)>RESPONSE_LIMIT: raise ValueError('RESPONSE_LIMIT')
    result=json.loads(raw)
    if not isinstance(result,dict): raise ValueError('UNTRUSTED_RESPONSE')
    return result

def scientific_catalog():
    if not enabled(): raise ValueError('BRIDGE_DISABLED')
    try:
        with scientific_urlopen(engine_url()+'/v2/catalog', timeout=3) as response:
            body=response.read(RESPONSE_LIMIT+1)
        if len(body)>RESPONSE_LIMIT: raise ValueError('RESPONSE_LIMIT')
        result=json.loads(body)
    except (HTTPError, URLError, OSError): raise ValueError('MATH_ENGINE_UNAVAILABLE') from None
    if (not isinstance(result,dict) or result.get('schema')!='math.scientific.capabilities.v2'
            or any(result.get(k) is not False for k in ('execution_authority','training_authorized','trading_authorized','mathematicallyVerified'))
            or not isinstance(result.get('units'),list) or len(result['units'])>128
            or any(not isinstance(u,str) or len(u)>64 for u in result['units'])
            or not isinstance(result.get('unitMetadata'),list) or len(result['unitMetadata'])>128
            or not isinstance(result.get('dimensionBasis'),list) or len(result['dimensionBasis'])!=10
            or any(not isinstance(x,str) or len(x)>64 for x in result['dimensionBasis'])):
        raise ValueError('UNTRUSTED_CATALOG')
    for item in result['unitMetadata']:
        if (not isinstance(item,dict) or item.get('unit') not in result['units'] or not isinstance(item.get('dimensions'),list)
                or len(item['dimensions'])!=10 or any(type(x) is not int or abs(x)>100 for x in item['dimensions'])):
            raise ValueError('UNTRUSTED_CATALOG')
    return result

def execute_scientific(raw):
    if not enabled(): raise ValueError('BRIDGE_DISABLED')
    if not isinstance(raw, bytes) or not 2 <= len(raw) <= LIMIT: raise ValueError('BODY_LIMIT')
    def reject_constant(_): raise ValueError('NONFINITE_JSON')
    payload = json.loads(raw, parse_constant=reject_constant)
    if (not isinstance(payload, dict) or set(payload) != {'schema','mode','execution_authority','asOf','nodes','edges','outputs'}
            or payload.get('schema') != 'math.scientific.graph.v2' or payload.get('mode') != 'HISTORICAL_RESEARCH'
            or payload.get('execution_authority') is not False or type(payload.get('asOf')) is not int
            or not 0 <= payload['asOf'] <= 9007199254740991):
        raise ValueError('INVALID_SCIENTIFIC_REQUEST')
    for key, limit in [('nodes',12),('edges',24),('outputs',12)]:
        if not isinstance(payload[key],list) or len(payload[key])>limit: raise ValueError('INVALID_SCIENTIFIC_REQUEST')
    if not payload['nodes'] or not payload['outputs']: raise ValueError('INVALID_SCIENTIFIC_REQUEST')
    req = Request(engine_url()+'/v2/graph/execute', data=raw, headers={'Content-Type':'application/json'}, method='POST')
    try:
        with scientific_urlopen(req, timeout=5) as response:
            body = response.read(RESPONSE_LIMIT+1)
        if len(body)>RESPONSE_LIMIT: raise ValueError('RESPONSE_LIMIT')
        result = json.loads(body, parse_constant=reject_constant)
    except HTTPError as exc:
        exc.close()
        raise ValueError('INVALID_SCIENTIFIC_REQUEST' if exc.code==422 else 'MATH_ENGINE_UNAVAILABLE') from None
    except (URLError, OSError): raise ValueError('MATH_ENGINE_UNAVAILABLE') from None
    if (not isinstance(result,dict) or result.get('schema')!='math.scientific.result.v2'
            or result.get('status')!='RESEARCH_ONLY' or result.get('source')!='CALLER_SUPPLIED_UNATTESTED'
            or any(result.get(k) is not False for k in ('execution_authority','trading_authorized','training_authorized','mathematicallyVerified'))
            or not isinstance(result.get('requestSHA256'),str) or not re.fullmatch('[a-f0-9]{64}',result['requestSHA256'])
            or not isinstance(result.get('trace'),list) or len(result['trace'])>12
            or not isinstance(result.get('order'),list) or len(result['order'])>12
            or not isinstance(result.get('outputs'),list) or not 1<=len(result['outputs'])<=12):
        raise ValueError('UNTRUSTED_GRAPH_RESULT')
    for out in result['outputs']:
        if (not isinstance(out,dict) or not isinstance(out.get('node'),str) or out.get('port')!='value'
                or out.get('type') not in ('series','scalar') or not isinstance(out.get('unit'),str)
                or not isinstance(out.get('values'),list) or not 1<=len(out['values'])<=2000
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in out['values'])
                or any(not isinstance(out.get(k),list) or len(out[k])!=len(out['values'])
                       or any(type(v) is not int or not 0<=v<=payload['asOf'] for v in out[k]) for k in ('timestamps','availableAt'))):
            raise ValueError('UNTRUSTED_GRAPH_RESULT')
        if (any(t<=out['timestamps'][i-1] for i,t in enumerate(out['timestamps']) if i)
                or any(a>t for a,t in zip(out['availableAt'],out['timestamps']))):
            raise ValueError('UNTRUSTED_GRAPH_RESULT')
    node_ids=[n.get('id') for n in payload['nodes'] if isinstance(n,dict)]
    expected_outputs=[(o.get('node'),o.get('port')) for o in payload['outputs'] if isinstance(o,dict)]
    actual_outputs=[(o['node'],o['port']) for o in result['outputs']]
    if (len(node_ids)!=len(payload['nodes']) or len(set(node_ids))!=len(node_ids)
            or set(result['order'])!=set(node_ids) or len(result['order'])!=len(node_ids)
            or [t.get('node') if isinstance(t,dict) else None for t in result['trace']]!=result['order']
            or actual_outputs!=expected_outputs):
        raise ValueError('UNTRUSTED_GRAPH_RESULT')
    return result

def enabled():
    return os.environ.get("TERMINAN_MATH_OFFLINE_BRIDGE") == "1"

def check():
    result={"schema":"terminan.math-health.v1","state":"NOT_CONNECTED",
            "research_enabled":False,"trading_authorized":False}
    if not enabled():
        return result
    try:
        with urlopen(engine_url()+"/healthz", timeout=2) as response:
            data=_read_object(response)
        if data.get("schema")=="math.engine.v1" and data.get("state")=="READY_OFFLINE" and data.get("trading_authorized") is False:
            return {**result,"state":"READY_OFFLINE_UNTRUSTED","research_enabled":True}
    except (ValueError, OSError, KeyError, TypeError):
        pass
    return result

def evaluate(raw):
    if not enabled():raise ValueError("BRIDGE_DISABLED")
    if not isinstance(raw,bytes) or not 2<=len(raw)<=LIMIT:raise ValueError("BODY_LIMIT")
    payload=json.loads(raw)
    if not isinstance(payload,dict) or set(payload)!={"schema","mode","execution_authority","closes"} or payload.get("schema")!="math.evaluate.v1" or payload.get("mode")!="HISTORICAL_RESEARCH" or payload.get("execution_authority") is not False:
        raise ValueError("INVALID_CONTRACT")
    closes=payload["closes"]
    if not isinstance(closes,list) or not 500<=len(closes)<=2000 or any(type(x) not in (float,int) or not 0<x<1e12 for x in closes):
        raise ValueError("INVALID_SERIES")
    body=json.dumps(payload,allow_nan=False,separators=(",",":")).encode()
    req=Request(engine_url()+"/v1/evaluate",data=body,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:
            result=_read_object(response)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise ValueError("MATH_ENGINE_UNAVAILABLE") from exc
    if result.get("schema")!="math.result.v1" or result.get("trading_authorized") is not False or result.get("execution_authority") is not False or result.get("source")!="CALLER_SUPPLIED_UNATTESTED":
        raise ValueError("MATH_RESPONSE_UNTRUSTED")
    return result

def execute_graph(raw):
    if not enabled():raise ValueError("BRIDGE_DISABLED")
    if not isinstance(raw,bytes) or not 2<=len(raw)<=LIMIT:raise ValueError("BODY_LIMIT")
    payload=json.loads(raw)
    if not isinstance(payload,dict) or set(payload)!={"schema","mode","execution_authority","nodes"} or payload.get("schema")!="math.graph.execute.v1" or payload.get("mode")!="HISTORICAL_RESEARCH" or payload.get("execution_authority") is not False:
        raise ValueError("INVALID_GRAPH")
    if not isinstance(payload["nodes"],list) or len(payload["nodes"])>12:raise ValueError("INVALID_GRAPH_NODES")
    req=Request(engine_url()+"/v1/graph/execute",data=raw,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:result=_read_object(response)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise ValueError("MATH_GRAPH_UNAVAILABLE") from exc
    if result.get("schema")!="math.graph.result.v1" or result.get("source")!="CALLER_SUPPLIED_UNATTESTED" or result.get("trading_authorized") is not False or result.get("execution_authority") is not False:
        raise ValueError("UNTRUSTED_GRAPH_RESULT")
    return result

def execute_port_graph(raw):
    if not enabled():raise ValueError("BRIDGE_DISABLED")
    if not isinstance(raw,bytes) or not 2<=len(raw)<=LIMIT:raise ValueError("BODY_LIMIT")
    payload=json.loads(raw)
    if not isinstance(payload,dict) or set(payload)!={"schema","execution_authority","nodes","edges"} or payload.get("schema")!="math.port-graph.v1" or payload.get("execution_authority") is not False:
        raise ValueError("INVALID_PORT_GRAPH")
    if not isinstance(payload["nodes"],list) or not 2<=len(payload["nodes"])<=12 or not isinstance(payload["edges"],list) or len(payload["edges"])>24:
        raise ValueError("INVALID_PORT_GRAPH")
    req=Request(engine_url()+"/v1/graph/ports",data=raw,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:result=_read_object(response)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise ValueError("MATH_PORT_GRAPH_UNAVAILABLE") from exc
    if result.get("schema")!="math.graph.result.v1" or result.get("source")!="CALLER_SUPPLIED_UNATTESTED" or result.get("trading_authorized") is not False or result.get("execution_authority") is not False:
        raise ValueError("UNTRUSTED_GRAPH_RESULT")
    return result

def evaluate_formula(raw):
    if not enabled():raise ValueError("BRIDGE_DISABLED")
    if not isinstance(raw,bytes) or not 2<=len(raw)<=LIMIT:raise ValueError("BODY_LIMIT")
    payload=json.loads(raw)
    if not isinstance(payload,dict) or set(payload)-{"schema","execution_authority","values","formula","inputUnit","outputUnit","knowledge"} or payload.get("schema")!="math.formula.v1" or payload.get("execution_authority") is not False:
        raise ValueError("INVALID_FORMULA")
    if not isinstance(payload.get("values"),list) or not 2<=len(payload["values"])<=2000 or not isinstance(payload.get("formula"),str) or len(payload["formula"])>160:
        raise ValueError("INVALID_FORMULA")
    req=Request(engine_url()+"/v1/formula",data=raw,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:result=_read_object(response)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise ValueError("MATH_FORMULA_UNAVAILABLE") from exc
    if result.get("schema")!="math.formula.result.v1" or result.get("source")!="CALLER_SUPPLIED_UNATTESTED" or result.get("trading_authorized") is not False or result.get("execution_authority") is not False:
        raise ValueError("UNTRUSTED_FORMULA_RESULT")
    return result
