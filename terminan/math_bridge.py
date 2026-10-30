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

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

# No environment proxy or redirects may turn loopback research into external access.
scientific_urlopen = build_opener(ProxyHandler({}), _NoRedirect()).open

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
    req = Request(URL+'/v2/graph/execute', data=raw, headers={'Content-Type':'application/json'}, method='POST')
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
    return result

def enabled():
    return os.environ.get("TERMINAN_MATH_OFFLINE_BRIDGE") == "1"

def check():
    result={"schema":"terminan.math-health.v1","state":"NOT_CONNECTED",
            "research_enabled":False,"trading_authorized":False}
    if not enabled():
        return result
    try:
        with urlopen(URL+"/healthz", timeout=2) as response:
            data=json.load(response)
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
    req=Request(URL+"/v1/evaluate",data=body,headers={"Content-Type":"application/json","Host":"127.0.0.1:8788"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:
            result=json.load(response)
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
    req=Request(URL+"/v1/graph/execute",data=raw,headers={"Content-Type":"application/json","Host":"127.0.0.1:8788"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:result=json.load(response)
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
    req=Request(URL+"/v1/graph/ports",data=raw,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:result=json.load(response)
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
    req=Request(URL+"/v1/formula",data=raw,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=5) as response:result=json.load(response)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise ValueError("MATH_FORMULA_UNAVAILABLE") from exc
    if result.get("schema")!="math.formula.result.v1" or result.get("source")!="CALLER_SUPPLIED_UNATTESTED" or result.get("trading_authorized") is not False or result.get("execution_authority") is not False:
        raise ValueError("UNTRUSTED_FORMULA_RESULT")
    return result
