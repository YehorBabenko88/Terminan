"""Process-owned synthetic session receipts, not live-source authentication."""
import hashlib,re,threading,uuid
FIELDS={'version','mode','session_id','candidate_sha','epoch','revision','state','lease_ms','poll_ms','end_grace_ms','authority','sources'}
class Session:
 def __init__(self):self.id=uuid.uuid4().hex;self.lock=threading.Lock();self.ended=False;self.receipts=0
 def end(self):
  with self.lock:self.ended=True
 def receipt(self,sha,session_id=None):
  with self.lock:
   if session_id is not None and session_id!=self.id:raise ValueError()
   if self.ended:self.receipts=min(2**31-1,self.receipts+1)
   return dict(version=1,mode='SYNTHETIC',session_id=self.id,candidate_sha=sha,epoch=1,revision=2 if self.ended else 1,state='SESSION_ENDED' if self.ended else 'ACTIVE',lease_ms=5000,poll_ms=500,end_grace_ms=3000,authority='SYNTHETIC_ONLY',sources='DISABLED')
 def diagnostics(self):
  with self.lock:return dict(version=1,session_sha256=hashlib.sha256(self.id.encode()).hexdigest(),state='SESSION_ENDED' if self.ended else 'ACTIVE',end_receipts=self.receipts)
def validate_receipt(value,sha,previous=None):
 if not isinstance(value,dict) or set(value)!=FIELDS:raise ValueError()
 if value['mode']!='SYNTHETIC' or value['authority']!='SYNTHETIC_ONLY' or value['sources']!='DISABLED' or value['candidate_sha']!=sha or not re.fullmatch('[0-9a-f]{40}',sha) or not re.fullmatch('[0-9a-f]{32}',value['session_id']):raise ValueError()
 if any(type(value[k]) is not int or value[k]!=v for k,v in dict(version=1,epoch=1,lease_ms=5000,poll_ms=500,end_grace_ms=3000).items()):raise ValueError()
 if type(value['revision']) is not int or (value['state'],value['revision']) not in (('ACTIVE',1),('SESSION_ENDED',2)):raise ValueError()
 if previous and (any(value[k]!=previous[k] for k in ('candidate_sha','session_id','epoch')) or value['revision']<previous['revision']):raise ValueError()
 return value
