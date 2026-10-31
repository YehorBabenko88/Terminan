"""Independent node-local v2 consumer. No network, fleet control or admission."""
import copy
import ctypes
import json
import os
from pathlib import Path
import re
import stat

CORE=frozenset(('unified-system','grid','strattester','math','meta_analyse','terminan'))
LIMIT=262144
STATES={'STOPPED','WAITING','STARTING','READY','BACKOFF','FAILED'}
REASONS={'NONE','DEPENDENCY_NOT_READY','DRIVER_FAILURE','FUNCTIONAL_READINESS_REQUIRED','STOP_FAILED'}

def require(ok):
 if not ok:raise ValueError('INVALID_RUNTIME_V2')
def exact(value,keys):require(type(value) is dict and set(value)==set(keys))
def integer(v):return type(v) is int and 0<=v<=2**53-1
def match(v,pattern):return type(v) is str and re.fullmatch(pattern,v) is not None

def validate_runtime(p):
 exact(p,('schema','api_version','producer','node_id','release_id','release_sha256','revision','mode','modules','ready','fleet_authority','trading_authorized','physical','physical_deployment_allowed'))
 exact(p['api_version'],('major','minor'))
 require(type(p['api_version']['major']) is int and p['api_version']['major']==2 and type(p['api_version']['minor']) is int and p['api_version']['minor']==0)
 require(p['schema']=='unified.runtime.v2' and p['producer']=='unified-system' and p['mode']=='LOCAL_RUNTIME_PREDEPLOYMENT' and p['fleet_authority']=='grid')
 require(p['trading_authorized'] is False and p['physical_deployment_allowed'] is False and p['physical']=='NOT_RUN')
 require(match(p['node_id'],r'[A-Za-z0-9_-]{1,64}') and match(p['release_id'],r'[A-Za-z0-9_.:-]{1,128}') and match(p['release_sha256'],r'[a-f0-9]{64}') and integer(p['revision']))
 modules=p['modules'];require(type(modules) is dict and CORE<=set(modules) and 6<=len(modules)<=64)
 for name,m in modules.items():
  require(match(name,r'[a-z][a-z0-9_-]{0,63}'))
  exact(m,('version','api_major','dependencies','state','ready','attempt','reason','administrative_stop'))
  require(match(m['version'],r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,40})?') and type(m['api_major']) is int and m['api_major']==1)
  require(type(m['state']) is str and m['state'] in STATES and type(m['reason']) is str and m['reason'] in REASONS)
  require(type(m['ready']) is bool and m['ready']==(m['state']=='READY') and type(m['administrative_stop']) is bool and integer(m['attempt']))
  deps=m['dependencies'];require(type(deps) is list and len(deps)<=64 and all(type(d) is str and d in modules and d!=name for d in deps) and len(set(deps))==len(deps))
 done=set();active=set()
 def visit(n):
  require(n not in active)
  if n in done:return
  active.add(n)
  for dep in modules[n]['dependencies']:visit(dep)
  active.remove(n);done.add(n)
 for n in modules:visit(n)
 require(type(p['ready']) is bool and p['ready']==all(modules[n]['ready'] for n in CORE))
 return copy.deepcopy(p)

def _pairs(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError('DUPLICATE_FIELD')
  out[k]=v
 return out

def runtime_snapshot():
 unavailable=dict(schema='terminan.runtime-v2.unavailable.v1',state='UNAVAILABLE',reason='LOCAL_SNAPSHOT_UNAVAILABLE',source_authenticity='UNVERIFIED',physical='NOT_RUN',trading_authorized=False,physical_deployment_allowed=False)
 source=os.environ.get('TERMINAN_RUNTIME_V2_SNAPSHOT')
 if not source:return unavailable
 try:
  require(type(source) is str and len(source)<=4096 and not source.startswith(('\\\\','//')))
  path=Path(source).absolute()
  if os.name=='nt':
   # Reject mapped/network drives before touching any path metadata.
   kernel=ctypes.WinDLL('kernel32',use_last_error=True)
   kernel.GetDriveTypeW.argtypes=[ctypes.c_wchar_p];kernel.GetDriveTypeW.restype=ctypes.c_uint
   require(kernel.GetDriveTypeW(path.anchor)==3)  # DRIVE_FIXED only
  for part in (*reversed(path.parents),path):
   facts=part.lstat();require(not stat.S_ISLNK(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&1024)
  flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
  fd=os.open(path,flags)
  with os.fdopen(fd,'rb') as stream:
   info=os.fstat(stream.fileno());require(stat.S_ISREG(info.st_mode) and 2<=info.st_size<=LIMIT)
   raw=stream.read(LIMIT+1);require(len(raw)<=LIMIT)
  def invalid(_):raise ValueError('NONFINITE')
  return validate_runtime(json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=invalid))
 except (OSError,ValueError,TypeError,RecursionError,OverflowError):return unavailable
