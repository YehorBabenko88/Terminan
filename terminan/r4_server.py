"""R4 synthetic-only dispatcher; no runtime source adapters or write routes."""
import json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from .r2_server import R2Handler,R2Server
from .r4_session import Session
from .r4_contracts import views
from .synthetic import frame,SCENARIOS
class R4Server(R2Server):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.session=Session()
class R4Handler(R2Handler):
 def do_GET(self):
  host=self.headers.get('Host','')
  if host not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'} or self.headers.get('Origin') not in (None,'http://'+host):return self.send(403,{'error':'LOCAL_ORIGIN_REQUIRED'})
  if len(self.path)>2048:return self.send(414,{'error':'REQUEST_LIMIT'})
  try:
   url=urlsplit(self.path)
   if url.scheme or url.netloc:raise ValueError()
   assets={'/':'r4_preview.html','/preview':'r4_preview.html','/r2_preview.js':'r4_preview.js','/r4_protocol.js':'r4_protocol.js'}
   if url.path in assets:
    p=Path(__file__).with_name(assets[url.path]);return self.send(200,p.read_bytes(),('text/html' if p.suffix=='.html' else 'text/javascript')+'; charset=utf-8')
   if url.path not in ('/api/session','/api/synthetic/frame','/api/synthetic/contracts'):return super().do_GET()
   q=parse_qs(url.query,keep_blank_values=True,max_num_fields=6)
   if any(len(v)!=1 for v in q.values()):raise ValueError()
   q={k:v[0] for k,v in q.items()}
   if url.path=='/api/session':
    if set(q)-{'session_id'}:raise ValueError()
    return self.send(200,self.server.session.receipt(self.server.candidate_sha,q.get('session_id')))
   if set(q)-{'seed','step','symbol','timeframe','scenario'}:raise ValueError()
   for k in ('seed','step'):
    if k in q:
     if not q[k].isascii() or not q[k].isdecimal() or len(q[k])>10:raise ValueError()
     q[k]=int(q[k])
   if q.get('scenario','normal') not in SCENARIOS:raise ValueError()
   result=frame(**q) # Same strict bounds even for contract-only queries.
   session=self.server.session.receipt(self.server.candidate_sha)
   if session['state']=='SESSION_ENDED':return self.send(410,dict(error='SESSION_ENDED',session=session,mode='SYNTHETIC'))
   if url.path.endswith('/contracts'):
    result=dict(version=1,mode='SYNTHETIC',sources=views(**q),symbol=q.get('symbol','BTCUSDT'),timeframe=q.get('timeframe','1m'))
   result.update(candidate_sha=self.server.candidate_sha,session=session,authority='SYNTHETIC_ONLY',contract_version=1)
   return self.send(200,result)
  except (ValueError,KeyError,TypeError):return self.send(400,dict(error='INVALID_R4_REQUEST',mode='SYNTHETIC'))
