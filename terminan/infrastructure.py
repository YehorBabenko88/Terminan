"""Bounded source-only lifecycle snapshot adapter. No network or host discovery."""
import json
import os
import stat
from pathlib import Path
from uuid import UUID

LIMIT = 262144
STAGES = ('INFRA_PREFLIGHT','INFRA_READY','STRAT_HISTORY_SYNC','STRAT_RESULT_SEALED','HANDOFF_VERIFY','GRID_MARKET_READY','STEADY_STATE')

def unavailable(reason='SOURCE_NOT_CONFIGURED'):
    return dict(schema='terminan.infrastructure.v1',state='UNAVAILABLE',reason=reason,nodes=[],links=[],stages=[],available_modules=[],math={'status':'UNAVAILABLE'},source_provenance='UNVERIFIED',physical_acceptance='NOT_RUN',execution_authorized=False,trading_authorized=False)

def validate(value):
    if not isinstance(value,dict) or value.get('schema')!='unified.lifecycle.v1' or value.get('producer')!='unified-system' or value.get('mode')!='PLAN_ONLY' or value.get('execution_authorized') is not False or value.get('trading_authorized') is not False:
        raise ValueError('CONTRACT_INVALID')
    if len(json.dumps(value,allow_nan=False).encode())>LIMIT:raise ValueError('BODY_LIMIT')
    UUID(value['epoch'])
    if type(value.get('sequence')) is not int or not 0<=value['sequence']<=2**53-1:raise ValueError('SEQUENCE_INVALID')
    version=value.get('api_version')
    if not isinstance(version,dict) or version!={'major':1,'minor':0} or any(type(x) is not int for x in version.values()):raise ValueError('VERSION_INVALID')
    modules=value.get('available_modules',[])
    if not isinstance(modules,list) or len(modules)>5 or any(not isinstance(m,str) or m not in ('unified-system','terminan','strattester','grid','math') for m in modules) or len(set(modules))!=len(modules):raise ValueError('MODULES_INVALID')
    stages=value.get('stages',[])
    if not isinstance(stages,list) or len(stages)!=len(STAGES) or [s.get('stage') for s in stages]!=list(STAGES):raise ValueError('STAGES_INVALID')
    for stage in stages:
        if not isinstance(stage,dict) or set(stage)-{'stage','status','completed','total','reason'} or ('reason' in stage and (not isinstance(stage['reason'],str) or len(stage['reason'])>128)):raise ValueError('STAGE_SCHEMA_INVALID')
        if stage.get('stage') not in STAGES or stage.get('status') not in ('NOT_STARTED','RUNNING','WAITING','BLOCKED','COMPLETE','CANCELLED'):raise ValueError('STAGE_INVALID')
        if any(type(stage.get(k)) is not int or not 0<=stage[k]<=2**53-1 for k in ('completed','total')) or stage['completed']>stage['total']:raise ValueError('COUNTERS_INVALID')
    fleet,nodes = validate_fleet(value.get('fleet',{}))
    for key,expected in (('source_provenance','UNVERIFIED'),('physical_acceptance','NOT_RUN')):
        if key in value and value[key]!=expected:raise ValueError('AUTHORITY_INVALID')
    for key in ('observer','math'):
        if key in value:
            item=value[key]
            if not isinstance(item,dict) or set(item)!={'status','reason'} or item['status'] not in ('NOT_STARTED','RUNNING','WAITING','BLOCKED','COMPLETE','CANCELLED') or not isinstance(item['reason'],str) or len(item['reason'])>128:raise ValueError('MODULE_STATUS_INVALID')
    if 'paper' in value and value['paper']!={'status':'NOT_AUTHORIZED'}:raise ValueError('PAPER_INVALID')
    known={'schema','producer','mode','epoch','sequence','api_version','available_modules','stages','fleet','execution_authorized','trading_authorized','source_provenance','physical_acceptance','observer','math','paper','recovery'}
    if set(value)-known:raise ValueError('UNKNOWN_FIELD')
    if 'recovery' in value and value['recovery'] not in ('NONE','REVALIDATION_REQUIRED'):raise ValueError('RECOVERY_INVALID')
    result=unavailable()
    result.update({k:value[k] for k in ('epoch','sequence','available_modules','observer','math') if k in value})
    result.update(state='AVAILABLE_UNVERIFIED',reason='SOURCE_UNATTESTED',nodes=nodes,links=[],link_status='UNVERIFIED',stages=stages,fleet=fleet)
    return result


def validate_fleet(fleet):
    """Accept producer v1 PLAN_ONLY or narrowly defined empty-metric legacy exports."""
    import math
    if not isinstance(fleet,dict):raise ValueError('FLEET_INVALID')
    legacy=set(fleet)<={'nodes','links'} or fleet=={'status':'UNAVAILABLE','nodes':[],'links':[]}
    if not legacy:
        if set(fleet)!={'mode','status','execution_authorized','nodes','links','databases','alerts','source_provenance','physical','production'}:raise ValueError('FLEET_SCHEMA_INVALID')
        for key,expected in (('mode','PLAN_ONLY'),('status','PLAN_ONLY'),('execution_authorized',False),('source_provenance','NOT_EVALUATED'),('physical','NOT_RUN'),('production','NO_GO')):
            if fleet[key]!=expected or key=='execution_authorized' and fleet[key] is not False:raise ValueError('FLEET_AUTHORITY_INVALID')
        if any(fleet[k]!=[] for k in ('links','databases','alerts')):raise ValueError('FLEET_UNQUALIFIED')
    raw=fleet.get('nodes',[])
    if not isinstance(raw,list) or len(raw)>256:raise ValueError('NODES_INVALID')
    nodes=[];ids=set()
    fields={'id','epoch','sequence','state','zone','modules','last_heartbeat_ms','cpu','memory','disk','available_resources','db_sizes','identity_verified'}
    for node in raw:
        if not isinstance(node,dict):raise ValueError('NODE_INVALID')
        if legacy:
            if set(node)-{'id','cpu'} or node.get('cpu') is not None:raise ValueError('LEGACY_NODE_INVALID')
        else:
            if set(node)!=fields:raise ValueError('NODE_SCHEMA_INVALID')
            if node['identity_verified'] is not False or node['modules']!=[] or any(node[k] is not None for k in ('cpu','memory','disk','db_sizes')):raise ValueError('UNQUALIFIED_TELEMETRY')
            if node['state'] not in ('APPROVED','ACTIVE','DRAINING','RETIRED','OFFLINE','SUSPECT','QUARANTINED') or not isinstance(node['zone'],str) or not 1<=len(node['zone'])<=1024:raise ValueError('NODE_STATE_INVALID')
            for key,low in (('epoch',1),('sequence',0),('last_heartbeat_ms',0)):
                v=node[key]
                if key=='last_heartbeat_ms' and v is None:continue
                if type(v) is not int or not low<=v<=2**53-1:raise ValueError('NODE_COUNTER_INVALID')
            resources=node['available_resources']
            if resources is not None and (not isinstance(resources,dict) or set(resources)!={'cpu','memory','disk'} or any(type(v) not in (int,float) or not 0<=v<=2**53-1 or not math.isfinite(v) for v in resources.values())):raise ValueError('RESOURCE_INVALID')
        ident=node.get('id')
        if not isinstance(ident,str) or not 1<=len(ident)<=128 or ident in ids:raise ValueError('NODE_ID_INVALID')
        ids.add(ident)
        projected={k:node.get(k) for k in fields-{'id','identity_verified'}}
        projected.update(node_id=ident,identity_verified=False,observation_status='UNATTESTED')
        nodes.append(projected)
    return {'status':'UNAVAILABLE' if not nodes else 'PLAN_ONLY','nodes':nodes,'links':[],'databases':[],'alerts':[]},nodes

def infrastructure_snapshot():
    raw=os.environ.get('TERMINAN_LIFECYCLE_SNAPSHOT')
    if not raw:return unavailable()
    try:
        if not isinstance(raw,str) or raw.replace('\\','/').startswith('//') or '\x00' in raw:raise ValueError('LOCAL_REGULAR_FILE_REQUIRED')
        path=Path(raw)
        info=path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&1024 or info.st_size>LIMIT:raise ValueError('LOCAL_REGULAR_FILE_REQUIRED')
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(info.st_dev,info.st_ino):raise ValueError('FILE_CHANGED')
            data=stream.read(LIMIT+1)
        if len(data)>LIMIT:raise ValueError('BODY_LIMIT')
        return validate(json.loads(data))
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):return unavailable('SOURCE_INVALID_OR_UNAVAILABLE')
