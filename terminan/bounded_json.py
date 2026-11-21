"""Constant-memory structural budgets before JSON builds Python containers.
Grammar/schema validation follows. No global node cap truncates a legitimate
200-row by128-funding-event graph.
"""
import json
SPACE=b' \t\r\n'
HEX=b'0123456789abcdefABCDEF'
def preflight_json(raw,*,max_bytes):
 if type(raw) is not bytes or not 0<len(raw)<=max_bytes:raise ValueError('bounded exact JSON bytes required')
 stack=[];i=0;n=len(raw)
 def value_start():
  if stack and stack[-1][0]==91 and stack[-1][1]:
   frame=stack[-1];frame[2]+=1;frame[1]=False
   if frame[2]>frame[3]:raise ValueError('JSON array item budget exceeded')
 while i<n:
  byte=raw[i]
  if byte in SPACE:i+=1;continue
  if byte in (91,123):
   value_start()
   if len(stack)>=16:raise ValueError('JSON container depth exceeded')
   limit=128 if byte==91 and stack and stack[-1][0]==123 and stack[-1][4] else 200
   stack.append([byte,True,0,limit,False,True]);i+=1;continue
  if byte in (93,125):
   if not stack or stack[-1][0]!=(91 if byte==93 else 123):raise ValueError('JSON container mismatch')
   stack.pop();i+=1;continue
  if byte==44:
   if stack and stack[-1][0]==91:stack[-1][1]=True
   elif stack and stack[-1][0]==123:stack[-1][5]=True
   i+=1;continue
  if byte==58:
   if not stack or stack[-1][0]!=123:raise ValueError('JSON member separator outside object')
   stack[-1][2]+=1;stack[-1][5]=False
   if stack[-1][2]>32:raise ValueError('JSON object field budget exceeded')
   i+=1;continue
  if byte==34:
   value_start();start=i;i+=1
   while i<n:
    if i-start-1>1536:raise ValueError('JSON encoded string budget exceeded')
    char=raw[i]
    if char==34:
     if stack and stack[-1][0]==123 and stack[-1][5]:stack[-1][4]=raw[start+1:i]==b'events'
     i+=1;break
    if char<32:raise ValueError('JSON string control byte')
    if char==92:
     i+=1
     if i>=n:raise ValueError('incomplete JSON escape')
     if raw[i]==117:
      if i+4>=n or any(raw[j] not in HEX for j in range(i+1,i+5)):raise ValueError('invalid JSON unicode escape')
      i+=5;continue
     if raw[i] not in b'"\\/bfnrt':raise ValueError('invalid JSON escape')
    i+=1
   else:raise ValueError('unterminated JSON string')
   continue
  value_start()
  if byte in (116,102,110):
   token=b'true' if byte==116 else b'false' if byte==102 else b'null'
   if raw[i:i+len(token)]!=token:raise ValueError('invalid JSON literal')
   i+=len(token);continue
  if byte==45 or 48<=byte<=57:
   start=i;i+=1
   while i<n and raw[i] not in b' \t\r\n,]}:':
    i+=1
    if i-start>64:raise ValueError('JSON numeric token budget exceeded')
   continue
  raise ValueError('invalid JSON token')
 if stack:raise ValueError('unterminated JSON container')

def _refuse(*args):raise ValueError('noncanonical JSON scalar')
def _pairs(items):
 if len(items)>32:raise ValueError('JSON object cardinality')
 result={}
 for key,value in items:
  if type(key) is not str or not 1<=len(key)<=64 or key in result:raise ValueError('duplicate or oversized JSON key')
  result[key]=value
 return result

def load_bounded_json(raw,*,max_bytes):
 preflight_json(raw,max_bytes=max_bytes)
 try:return json.loads(raw,object_pairs_hook=_pairs,parse_float=_refuse,parse_constant=_refuse)
 except (UnicodeError,ValueError,RecursionError) as exc:raise ValueError('closed bounded JSON required') from exc


def ascii_json_string_size(value,*,max_bytes):
 """Count ensure_ascii JSON string bytes without creating escaped text.

 This is a representation budget, not a JSON encoder. Quotes, backslashes,
 short control escapes, BMP escapes and astral surrogate pairs match json.dumps.
 """
 if (type(value) is not str or type(max_bytes) is not int
     or not 2<=max_bytes<=1048576):
  raise ValueError('bounded literal JSON string budget required')
 size=2
 for character in value:
  code=ord(character)
  if character in ('"','\\') or code in (8,9,10,12,13):size+=2
  elif 32<=code<=126:size+=1
  elif code<=65535:size+=6
  else:size+=12
  if size>max_bytes:raise ValueError('JSON escaped string byte budget exceeded')
 return size
