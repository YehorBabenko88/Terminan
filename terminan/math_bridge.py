"""Opt-in loopback-only bridge: no DB, no credentials, no orders."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

URL = "http://127.0.0.1:8788"
LIMIT = 262144

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
