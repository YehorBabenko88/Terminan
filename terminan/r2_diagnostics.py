"""Bounded diagnostics: enum/counters only; never exception text or request identity."""
from collections import deque
import threading,time
LIMIT=2**31-1
KINDS=('HTTP_PEER_RESET','HTTP_PEER_CLOSED','HTTP_PEER_ABORTED','HTTP_IO_TIMEOUT','HTTP_INVALID_TARGET','HTTP_OVERLOAD','HTTP_HANDLER_FAILURE','HTTP_GENERATOR_FAILURE','HTTP_ADMISSION_FAILURE','RUNNER_FAILURE')
FATAL=frozenset(KINDS[-4:])
STAGES=('read','write','flush','overload','parse','handler','generator','admission','runner','shutdown')
class Diagnostics:
    def __init__(self):
        self.lock=threading.Lock();self.started=time.monotonic();self.counts={k:0 for k in KINDS};self.events=deque(maxlen=16);self.active=0;self.peak=0;self.first_fatal=None
    def event(self,kind,stage):
        if kind not in KINDS or stage not in STAGES:raise ValueError()
        with self.lock:
            self.counts[kind]=min(LIMIT,self.counts[kind]+1)
            event=dict(error_class=kind,stage=stage,elapsed_ms=round((time.monotonic()-self.started)*1000,3))
            self.events.append(event)
            if kind in FATAL and self.first_fatal is None:self.first_fatal=event.copy()
    def worker(self,change):
        with self.lock:self.active+=change;self.peak=max(self.peak,self.active)
    def snapshot(self):
        with self.lock:return dict(version=1,counters=self.counts.copy(),active_workers=self.active,peak_workers=self.peak,events=list(self.events),first_fatal=self.first_fatal)

def validate(value):
    if not isinstance(value,dict) or set(value)!={'version','counters','active_workers','peak_workers','events','first_fatal'} or (type(value['version']) is not int or value['version']!=1):raise ValueError()
    if set(value['counters'])!=set(KINDS) or any(type(v) is not int or not 0<=v<=LIMIT for v in value['counters'].values()):raise ValueError()
    if any(type(value[k]) is not int or not 0<=value[k]<=16 for k in ('active_workers','peak_workers')) or value['active_workers']>value['peak_workers']:raise ValueError()
    if not isinstance(value['events'],list) or len(value['events'])>16:raise ValueError()
    for event in value['events']+([] if value['first_fatal'] is None else [value['first_fatal']]):
        import math
        if not isinstance(event,dict) or set(event)!={'error_class','stage','elapsed_ms'} or event['error_class'] not in KINDS or event['stage'] not in STAGES:raise ValueError()
        t=event['elapsed_ms']
        if type(t) not in (int,float) or not math.isfinite(t) or t<0:raise ValueError()
    if value['first_fatal'] is not None and value['first_fatal']['error_class'] not in FATAL:raise ValueError()
    if bool(any(value['counters'][kind] for kind in FATAL))!=(value['first_fatal'] is not None):raise ValueError()
    return value

class PeerDisconnected(ConnectionError):pass
class TransportIO:
    """Mark errors at actual stream calls, never by arbitrary handler exception type."""
    def __init__(self,stream,diagnostics):self.stream=stream;self.diagnostics=diagnostics
    def __getattr__(self,name):return getattr(self.stream,name)
    def call(self,stage,method,*args):
        try:return getattr(self.stream,method)(*args)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError) as exc:
            kind='HTTP_PEER_CLOSED' if isinstance(exc,BrokenPipeError) else 'HTTP_PEER_RESET' if isinstance(exc,ConnectionResetError) else 'HTTP_PEER_ABORTED'
            self.diagnostics.event(kind,stage);raise PeerDisconnected() from None
        except TimeoutError:
            self.diagnostics.event('HTTP_IO_TIMEOUT',stage);raise PeerDisconnected() from None
    def readline(self,*args):return self.call('read','readline',*args)
    def write(self,*args):return self.call('write','write',*args)
    def flush(self):return self.call('flush','flush')
