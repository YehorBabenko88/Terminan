"""Separate opt-in workspace; preserves R4 synthetic endpoints and ladder."""
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from .r4_server import R4Server,R4Handler
from .saved_sources import SavedSources,SourceError

class SavedServer(R4Server):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.saved=SavedSources()

class SavedHandler(R4Handler):
 def do_GET(self):
  path=urlsplit(self.path).path
  if path not in ('/saved','/saved.js','/saved_mtf.js','/saved.css','/api/saved/catalog','/api/saved/page'):return super().do_GET()
  host=self.headers.get('Host','')
  if host not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'} or self.headers.get('Origin') not in (None,'http://'+host):return self.send(403,dict(error='LOCAL_ORIGIN_REQUIRED'))
  if len(self.path)>8192:return self.send(414,dict(error='REQUEST_LIMIT'))
  try:
   if self.server.session.receipt(self.server.candidate_sha)['state']=='SESSION_ENDED':return self.send(410,dict(error='SESSION_ENDED'))
   q=parse_qs(urlsplit(self.path).query,keep_blank_values=True,max_num_fields=8)
   if any(len(v)!=1 for v in q.values()):raise SourceError()
   q={k:v[0] for k,v in q.items()}
   if path in ('/saved','/saved.js','/saved_mtf.js','/saved.css'):
    if q:raise SourceError()
    file=Path(__file__).with_name('saved.html' if path=='/saved' else path[1:]);return self.send(200,file.read_bytes(),('text/html' if path=='/saved' else 'text/javascript' if path.endswith('.js') else 'text/css')+'; charset=utf-8')
   if path.endswith('/catalog'):
    if q:raise SourceError()
    return self.send(200,dict(**self.server.saved.catalog(),candidate_sha=self.server.candidate_sha))
   if set(q)-{'source','dataset','symbol','timeframe','limit','cursor','from_ms','cutoff_ms'} or not {'source','dataset'}<=set(q):raise SourceError()
   for k in ('limit','from_ms','cutoff_ms'):
    if k in q:
     if not q[k].isascii() or not q[k].isdigit() or len(q[k])>16:raise SourceError()
     q[k]=int(q[k])
   source=q.pop('source');dataset=q.pop('dataset');return self.send(200,dict(**self.server.saved.page(source,dataset,**q),candidate_sha=self.server.candidate_sha))
  except SourceError as e:
   status=503 if e.code in ('SOURCE_UNAVAILABLE','SOURCE_DISABLED') else 409 if e.code in ('SOURCE_CHANGED','STALE_CURSOR','SCHEMA_MISMATCH','SOURCE_PIN_MISMATCH') else 400
   return self.send(status,dict(error=e.code,authority='UNVERIFIED',rows=[]))
  except (ValueError,TypeError,KeyError):return self.send(400,dict(error='INVALID_REQUEST',authority='UNVERIFIED',rows=[]))
