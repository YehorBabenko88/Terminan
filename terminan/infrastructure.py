"""Bounded source-only lifecycle snapshot adapter. No network or host discovery."""
import json
import os
from pathlib import Path
from uuid import UUID

LIMIT = 262144
STAGES = ('INFRA_PREFLIGHT','INFRA_READY','STRAT_HISTORY_SYNC','STRAT_RESULT_SEALED','HANDOFF_VERIFY','GRID_MARKET_READY','STEADY_STATE')

def unavailable(reason='SOURCE_NOT_CONFIGURED'):
    return dict(schema='terminan.infrastructure.v1',state='UNAVAILABLE',reason=reason,nodes=[],links=[],stages=[],available_modules=[],math={'status':'UNAVAILABLE'},source_provenance='UNVERIFIED',physical_acceptance='NOT_RUN',execution_authorized=False,trading_authorized=False)

def validate(value):
    if not isinstance(value,dict) or value.get('schema')!='unified.lifecycle.v1' or value.get('producer')!='unified-system' or value.get('mode')!='PLAN_ONLY' or value.get('execution_authorized') is not False or value.get('trading_authorized') is not False:
        raise ValueError('CONTRACT_INVALID')
    UUID(value['epoch'])
    if type(value.get('sequence')) is not int or value['sequence']<0:raise ValueError('SEQUENCE_INVALID')
    version=value.get('api_version',{'major':1,'minor':0})
    if not isinstance(version,dict) or version.get('major')!=1:raise ValueError('VERSION_INVALID')
    modules=value.get('available_modules',[])
    if not isinstance(modules,list) or len(modules)>5 or any(not isinstance(m,str) or m not in ('unified-system','terminan','strattester','grid','math') for m in modules) or len(set(modules))!=len(modules):raise ValueError('MODULES_INVALID')
    stages=value.get('stages',[])
    if len(stages)>7:raise ValueError('STAGES_INVALID')
    for stage in stages:
        if stage.get('stage') not in STAGES or stage.get('status') not in ('NOT_STARTED','RUNNING','WAITING','BLOCKED','COMPLETE','CANCELLED'):raise ValueError('STAGE_INVALID')
        if any(type(stage.get(k)) is not int or stage[k]<0 for k in ('completed','total')) or stage['completed']>stage['total']:raise ValueError('COUNTERS_INVALID')
    fleet=value.get('fleet',{})
    nodes=fleet.get('nodes',[])
    if not isinstance(nodes,list) or len(nodes)>256:raise ValueError('NODES_INVALID')
    nodes=[{**node,'node_id':node.get('node_id',node.get('id'))} for node in nodes]
    ids=[node.get('node_id') for node in nodes]
    if any(not isinstance(n,str) or not 1<=len(n)<=128 for n in ids) or len(set(ids))!=len(ids):raise ValueError('NODE_ID_INVALID')
    for node in nodes:
        for metric in ('cpu','memory','disk'):
            v=node.get(metric)
            if v is not None and (type(v) not in (int,float) or not 0<=v<1e18):raise ValueError('METRIC_INVALID')
    # Links require independently qualified endpoint identity; absent qualification renders no edges.
    links=[link for link in fleet.get('links',[]) if link.get('verified') is True and link.get('source') in ids and link.get('target') in ids]
    return {**unavailable(),**value,'schema':'terminan.infrastructure.v1','state':'AVAILABLE_UNVERIFIED','nodes':nodes,'links':links,'source_provenance':'UNVERIFIED','physical_acceptance':'NOT_RUN'}

def infrastructure_snapshot():
    raw=os.environ.get('TERMINAN_LIFECYCLE_SNAPSHOT')
    if not raw:return unavailable()
    try:
        with Path(raw).open('rb') as stream:data=stream.read(LIMIT+1)
        if len(data)>LIMIT:raise ValueError('BODY_LIMIT')
        return validate(json.loads(data))
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return unavailable('SOURCE_INVALID_OR_UNAVAILABLE')
