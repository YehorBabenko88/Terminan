"""Pure historical research import validation; no source authentication or execution grant."""
from hashlib import sha256
import json
import re
import uuid
from .paper_ledger import canonical_json

MAX_BYTES=8*1024*1024
MAX_NODES=262144
MAX_DEPTH=16
MAX_FIELDS=4096
MAX_ITEMS=65536
MAX_TEXT=65536
MAX_TRUST=4096
MAX_INTEGER_BITS=4096
_REQUIRED=frozenset(('api_version','producer','producer_identity','source_revision','producer_epoch','run_id','mode','execution_authority','dataset','strategy','model','execution_assumptions','metrics','completed_at_ms','completion_receipt'))
_OPTIONAL=frozenset(('input_snapshot',))

def _snapshot(value):
    """Copy only literal JSON types, bounded before each allocation/encoding."""
    box=[None];stack=[(value,box,0,0)];nodes=1;size=0
    def charge(count):
        nonlocal size
        size+=count
        if size>MAX_BYTES:raise ValueError('research JSON byte budget')
    while stack:
        item,parent,key,depth=stack.pop()
        if depth>MAX_DEPTH:raise ValueError('research JSON depth budget')
        kind=type(item)
        if kind is dict:
            count=len(item)
            if count>MAX_FIELDS:raise ValueError('research object field budget')
            nodes+=count
            if nodes>MAX_NODES:raise ValueError('research JSON node budget')
            charge(2+count+max(0,count-1));out={};parent[key]=out
            for name,child in item.items():
                if type(name) is not str or len(name)>MAX_TEXT:raise ValueError('literal bounded JSON key required')
                charge(len(canonical_json(name)));stack.append((child,out,name,depth+1))
        elif kind is list:
            count=len(item)
            if count>MAX_ITEMS:raise ValueError('research array item budget')
            nodes+=count
            if nodes>MAX_NODES:raise ValueError('research JSON node budget')
            charge(2+max(0,count-1));out=[None]*count;parent[key]=out
            for index in range(count):stack.append((item[index],out,index,depth+1))
        elif kind is str or kind is int or kind is float or kind is bool or kind is type(None):
            if kind is str and len(item)>MAX_TEXT:raise ValueError('research text budget')
            if kind is int and item.bit_length()>MAX_INTEGER_BITS:raise ValueError('research JSON integer representation budget')
            charge(len(canonical_json(item)));parent[key]=item
        else:raise ValueError('literal JSON types required')
    raw=canonical_json(box[0])
    if len(raw)>MAX_BYTES:raise ValueError('research JSON byte budget')
    return json.loads(raw)

def _trust_snapshot(sources):
    if not (type(sources) is set or type(sources) is frozenset or type(sources) is tuple or type(sources) is list) or len(sources)>MAX_TRUST:raise ValueError('bounded external trust tuples required')
    copied=[]
    for item in sources:
        if type(item) is not tuple or len(item)!=4 or any(type(value) is not str for value in item):raise ValueError('literal external source pin required')
        identity,revision,run,receipt=item
        if not 0<len(identity)<=128 or re.fullmatch('[a-f0-9]{40}',revision) is None or not 0<len(run)<=64 or re.fullmatch('[a-f0-9]{64}',receipt) is None:raise ValueError('bounded external source pin required')
        uuid.UUID(run);copied.append(item)
    return frozenset(copied)

def _label(value):return type(value) is str and 0<len(value)<=128

def validate_research_import(record,trusted_sources):
    """Validate a detached declared summary against independently supplied tuple pins.

    Acceptance is historical metadata/receipt consistency, not research metric
    recomputation, market authenticity, coverage, native admission or permission.
    Resource bounds describe this DTO representation, never provider history.
    """
    denied=dict(status='UNAVAILABLE',reason='RESEARCH_HANDOFF_INVALID',execution_authority=False,trading_authorized=False,source_capability=False,source_authenticity='NOT_EVALUATED',native='NOT_RUN')
    if type(record) is not dict or not len(_REQUIRED)<=len(record)<=len(_REQUIRED|_OPTIONAL):return denied
    try:
        if any(type(key) is not str for key in record) or not _REQUIRED<=record.keys()<=_REQUIRED|_OPTIONAL:return denied
        trusted=_trust_snapshot(trusted_sources);value=_snapshot(record)
        version=value['api_version']
        if type(version) is not dict or set(version)!= {'major','minor'} or type(version['major']) is not int or version['major']!=1 or type(version['minor']) is not int or version['minor']!=1:return denied
        if type(value['run_id']) is not str or not 0<len(value['run_id'])<=64:return denied
        uuid.UUID(value['run_id'])
        if value['producer']!='terminan' or value['mode']!='HISTORICAL' or value['execution_authority'] is not False:return denied
        identity,revision,receipt=value['producer_identity'],value['source_revision'],value['completion_receipt']
        if not _label(identity) or type(revision) is not str or re.fullmatch('[a-f0-9]{40}',revision) is None or type(receipt) is not str or re.fullmatch('[a-f0-9]{64}',receipt) is None:return denied
        if (identity,revision,value['run_id'],receipt) not in trusted:return dict(denied,reason='SOURCE_IDENTITY_UNATTESTED')
        if type(value['producer_epoch']) is not str or not 0<len(value['producer_epoch'])<=64:return denied
        uuid.UUID(value['producer_epoch']);dataset=value['dataset']
        if type(dataset) is not dict or type(dataset.get('fingerprint')) is not str or re.fullmatch('[a-f0-9]{64}',dataset['fingerprint']) is None:return denied
        if any(type(dataset.get(key)) is not int for key in ('start_ms','end_ms')) or not 0<=dataset['start_ms']<=dataset['end_ms']:return denied
        if any(not _label(dataset.get(key)) for key in ('source_identity','market_type','symbol','timeframe')) or dataset.get('missing_data')!=[] or dataset.get('coverage')!='COMPLETE':return dict(denied,reason='RESEARCH_DATA_INCOMPLETE')
        if type(value['completed_at_ms']) is not int or value['completed_at_ms']<dataset['end_ms']:return denied
        strategy,model,assumptions,metrics=(value[key] for key in ('strategy','model','execution_assumptions','metrics'))
        if any(type(item) is not dict or not item for item in (strategy,model,assumptions,metrics)):return denied
        if not _label(strategy.get('id')) or not _label(strategy.get('version')) or type(strategy.get('fingerprint')) is not str or re.fullmatch('[a-f0-9]{64}',strategy['fingerprint']) is None or type(strategy.get('parameters')) is not dict:return denied
        if not _label(model.get('kind')) or not _label(model.get('version')) or not _label(assumptions.get('execution')):return denied
        from market_math import finite_nonnegative_number_valid
        if any(finite_nonnegative_number_valid(assumptions.get(key)) is not True for key in ('fees','slippage')):return denied
        if receipt!=sha256(canonical_json({key:item for key,item in value.items() if key!='completion_receipt'})).hexdigest():return dict(denied,reason='RESEARCH_RECEIPT_CORRUPT')
        return dict(status='ACCEPTED_HISTORICAL',run_id=value['run_id'],completion_receipt=receipt,execution_authority=False,trading_authorized=False,source_capability=False,source_authenticity='NOT_EVALUATED',native='NOT_RUN',validation_scope='STRUCTURE_RECEIPT_EXTERNAL_PIN_NOT_RESEARCH_ORACLE',receipt_integrity='MATCHED_CANONICAL_BYTES',external_source_pin='MATCHED_DECLARED_TUPLE_NOT_AUTHENTICATION')
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError,RecursionError,IndexError,RuntimeError,ImportError):
        return denied
