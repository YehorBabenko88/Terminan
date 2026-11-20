"""Explicit frozen-v1 reads and isolated v2 restore; no active legacy alias.

Only a caller-pinned standalone backup is read. The original bytes and IDs are
never rewritten. Restore creates a different fresh ledger and uses the sole
canonical PaperEngine/Journal implementation after a complete preflight.
"""
from contextlib import contextmanager
from hashlib import sha256
import json,os,re,stat
from pathlib import Path
from ..paper import PaperEngine,STRATEGIES
from ..paper_ledger import PaperReplayLedger,canonical_json
from ..paper_journal import PaperJournal,_validate,_utc,_available_at,_apply_event

_LIMIT=4*1024**3
_MAX_EVENTS=1_000_000

def _identity(value):
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',value) is None:raise ValueError('invalid historical identity')

def _digest_file(path):
    digest=sha256();count=0
    with Path(path).open('rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>_LIMIT:raise ValueError('bounded ordinary snapshot required')
        for chunk in iter(lambda:stream.read(1048576),b''):
            count+=len(chunk)
            if count>_LIMIT:raise ValueError('snapshot budget exceeded')
            digest.update(chunk)
        after=os.fstat(stream.fileno())
    current=Path(path).lstat()
    fields=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)
    if fields(before)!=fields(after) or fields(after)!=fields(current) or count!=after.st_size:raise RuntimeError('historical snapshot changed')
    return digest.hexdigest()

@contextmanager
def _snapshot(source,expected_sha256):
    if type(expected_sha256) is not str or re.fullmatch('[a-f0-9]{64}',expected_sha256) is None:raise ValueError('snapshot SHA256 required')
    with PaperReplayLedger._existing_database(source) as database:
        if database is None:raise ValueError('frozen source missing')
        if _digest_file(source)!=expected_sha256:raise ValueError('snapshot SHA256 mismatch')
        yield database
        if _digest_file(source)!=expected_sha256:raise RuntimeError('historical snapshot changed')

def read_historical_paper_receipt(source,expected_sha256,run_id,request_sha256):
    _identity(run_id)
    if type(request_sha256) is not str or re.fullmatch('[a-f0-9]{64}',request_sha256) is None:raise ValueError('historical request digest required')
    with _snapshot(source,expected_sha256) as database:
        size=database.execute('SELECT length(CAST(receipt AS BLOB)) FROM paper_replay_receipts WHERE run_id=?',(run_id,)).fetchone()
        if size is None or not 0<size[0]<=4*1024*1024:raise ValueError('bounded historical receipt required')
        receipt=PaperReplayLedger._read(database,run_id,request_sha256)
        if (receipt.get('schema')!='terminan.paper.result.v1' or type(receipt.get('strategy')) is not dict or receipt['strategy'].get('id')!='meta.poc.next_minute'
                or receipt['strategy'].get('version')!='1'):raise ValueError('not a historical v1 paper receipt')
        return receipt

def _stream(database,source_id,run_id):
    _identity(source_id);_identity(run_id)
    names=dict(database.execute("SELECT name,type FROM sqlite_schema WHERE name IN ('paper_streams_v1','paper_events_v1')"))
    if names!={'paper_streams_v1':'table','paper_events_v1':'table'}:raise RuntimeError('historical stream tables required')
    expected={'paper_streams_v1':(('source_id','TEXT',1,1),('run_id','TEXT',1,2),('symbol','TEXT',1,0),('checkpoint','INTEGER',1,0)), 'paper_events_v1':(('source_id','TEXT',1,1),('run_id','TEXT',1,2),('sequence','INTEGER',1,3),('event','BLOB',1,0),('ack','BLOB',1,0),('ack_sha256','TEXT',1,0))}
    for table,columns in expected.items():
        actual=tuple((item[1],item[2].upper(),item[3],item[5]) for item in database.execute('PRAGMA table_info('+table+')'))
        if actual!=columns:raise RuntimeError('unknown historical stream schema')
    row=database.execute('SELECT symbol,checkpoint FROM paper_streams_v1 WHERE source_id=? AND run_id=?',(source_id,run_id)).fetchone()
    if row is None or type(row[0]) is not str or re.fullmatch('[A-Z0-9]{2,30}',row[0]) is None or type(row[1]) is not int or not 0<=row[1]<=_MAX_EVENTS:raise RuntimeError('invalid historical stream metadata')
    return row

def _rows(database,source_id,run_id,symbol,checkpoint):
    recovered=0;watermark=None
    rows=database.execute('SELECT sequence,CASE WHEN length(event)<=262144 THEN event END,CASE WHEN length(ack)<=262144 THEN ack END,ack_sha256 FROM paper_events_v1 WHERE source_id=? AND run_id=? ORDER BY sequence',(source_id,run_id))
    for sequence,event_raw,ack_raw,digest in rows:
        if sequence!=recovered+1 or sequence>checkpoint or type(event_raw) is not bytes or type(ack_raw) is not bytes or sha256(ack_raw).hexdigest()!=digest:raise RuntimeError('historical event/ACK integrity failure')
        try:
            event=json.loads(event_raw);ack=json.loads(ack_raw)
            if type(event) is not dict or type(ack) is not dict:raise ValueError('historical objects required')
            if canonical_json(event)!=event_raw or canonical_json(ack)!=ack_raw or event.get('schema')!='terminan.paper.event.v1':raise ValueError('noncanonical historical event')
            transformed={**event,'schema':'terminan.paper.event.v2'};_validate(transformed)
            if event['sequence']!=sequence:raise ValueError('historical sequence mismatch')
            _utc(ack['ingested_at'])
            expected={'schema':'terminan.paper.event.ack.v1','source_id':source_id,'run_id':run_id,'symbol':symbol,'strategy_id':'meta.poc.next_minute','strategy_version':'1','checkpoint':sequence,'event_sha256':sha256(event_raw).hexdigest(),'event_time':event['event_time'],'ingested_at':ack['ingested_at'],'fill':ack['fill'],'fill_id':[source_id,run_id,sequence] if ack['fill'] is not None else None,'provenance':'CALLER_SUPPLIED_UNATTESTED','execution_authority':False,'trading_authorized':False}
            if canonical_json(ack)!=canonical_json(expected):raise ValueError('historical ACK identity mismatch')
            available=_available_at(transformed)
            if watermark is not None and available<watermark:raise ValueError('historical availability regressed')
        except (TypeError,KeyError,ValueError) as exc:raise RuntimeError('historical event/ACK validation refused') from exc
        recovered=sequence;watermark=available
        yield event,ack,transformed,digest
    if recovered!=checkpoint:raise RuntimeError('historical checkpoint gap')

def export_historical_paper_stream(source,expected_sha256,source_id,run_id,*,limit=1024,after_sequence=0):
    if type(limit) is not int or not 1<=limit<=1024 or type(after_sequence) is not int or after_sequence<0:raise ValueError('bounded historical export required')
    with _snapshot(source,expected_sha256) as database:
        symbol,checkpoint=_stream(database,source_id,run_id);events=[];acks=[]
        for event,ack,_,_ in _rows(database,source_id,run_id,symbol,checkpoint):
            if event['sequence']>after_sequence and len(events)<limit:events.append(event);acks.append(ack)
        return dict(schema='terminan.paper.historical-stream.v1',source_snapshot_sha256=expected_sha256,source_id=source_id,run_id=run_id,symbol=symbol,checkpoint=checkpoint,events=events,acks=acks,execution_authority=False,trading_authorized=False)

def restore_historical_paper_stream(source,expected_sha256,source_id,run_id,target,*,target_source_id,target_run_id):
    _identity(target_source_id);_identity(target_run_id);target=Path(target).absolute()
    if target.exists() or target.is_symlink() or not target.parent.is_dir() or any(Path(str(target)+suffix).exists() for suffix in ('-wal','-shm','-journal')):raise ValueError('restore requires a different fresh owned destination')
    for item in (*reversed(target.parents),target):
        try:info=item.lstat()
        except FileNotFoundError:continue
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('restore rejects linked destination')
    if not any(item.id=='poc_next_minute' and item.version=='2' and item.enabled for item in STRATEGIES.discover()):raise ValueError('canonical paper strategy disabled')
    with _snapshot(source,expected_sha256) as database:
        symbol,checkpoint=_stream(database,source_id,run_id);engine=PaperEngine();lineage=sha256()
        for _,ack,event,digest in _rows(database,source_id,run_id,symbol,checkpoint):
            if _apply_event(engine,symbol,event)!=ack['fill']:raise RuntimeError('historical financial replay differs from canonical Math policy')
            lineage.update(digest.encode('ascii'))
        # All historical rows and state transitions were checked before this
        # atomic fresh-file claim. Failures retain inactive new output only.
        descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            original=os.fstat(descriptor);ledger=PaperReplayLedger(target)
            def current():
                info=target.lstat()
                if (info.st_dev,info.st_ino,info.st_nlink)!=(original.st_dev,original.st_ino,1):raise RuntimeError('restore destination changed')
            current();journal=PaperJournal(ledger,target_source_id,target_run_id,symbol)
            for _,_,event,_ in _rows(database,source_id,run_id,symbol,checkpoint):current();journal.submit(event)
            current()
        finally:os.close(descriptor)
        return dict(schema='terminan.paper.restore.v1',source_snapshot_sha256=expected_sha256,source_ack_sha256=lineage.hexdigest(),source_id=source_id,run_id=run_id,target_source_id=target_source_id,target_run_id=target_run_id,checkpoint=checkpoint,status='RESTORED_UNATTESTED_PAPER_ONLY',execution_authority=False,trading_authorized=False)
