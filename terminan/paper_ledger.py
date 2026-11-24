"""Local, append-only receipts for Terminan's offline paper replay."""

from contextlib import closing, contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
import sqlite3
import stat
import tempfile
import os
from pathlib import Path


_APPLICATION_ID = 0x54505231  # TPR1
_HISTORICAL_RECEIPT = {
    "schema": "meta.persisted-state.digest.v1",
    "table": "paper_fills",
    "source_status": "UNVERIFIED_LOCAL_READBACK",
    "execution_authority": False,
    "trading_authorized": False,
}


def _historical_digest():
    return sha256(b"meta.persisted-state.digest.v1\0paper_fills\0")


def _add_historical_row(digest, raw):
    digest.update(len(raw).to_bytes(4, "big"))
    digest.update(raw)


def _encode_historical_fill(row):
    if (type(row) not in (tuple, list) or len(row) != 10
            or type(row[0]) is not int or not -(2**63) <= row[0] < 2**63
            or any(type(value) is not str for value in row[1:])):
        raise ValueError("invalid legacy paper fill row")
    raw = canonical_json(row)
    if len(raw) > 262_144:
        raise ValueError("legacy paper fill row exceeds byte limit")
    try:
        for index in (3, 4, 6, 7, 8):
            value = Decimal(row[index])
            if not value.is_finite() or str(value) != row[index]:
                raise ValueError("expected canonical finite Decimal text")
        stamp = datetime.fromisoformat(row[9])
        if (not row[9].endswith("+00:00")
                or stamp.isoformat(timespec="microseconds") != row[9]):
            raise ValueError("expected canonical UTC timestamp")
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid legacy fill decimal or timestamp") from exc
    return raw


def _validate_historical_source(source_id):
    if type(source_id) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", source_id):
        raise ValueError("invalid legacy fill source identifier")


class ReplayConflict(ValueError):
    """A run ID is already bound to a different request."""


def canonical_json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid JSON replay request") from exc


class PaperReplayLedger:
    """Store finalized receipts in a dedicated SQLite file on a local volume."""

    def __init__(self, path):
        self.path = path
        with closing(self._connect()) as database, database:
            if self._application_id(database) == _APPLICATION_ID:
                return
            database.execute("BEGIN IMMEDIATE")
            application_id = self._application_id(database)
            if application_id == _APPLICATION_ID:
                return
            if application_id or database.execute(
                "SELECT 1 FROM sqlite_schema LIMIT 1"
            ).fetchone():
                raise RuntimeError("paper replay requires a dedicated database")
            database.execute(
                "CREATE TABLE paper_replay_receipts ("
                "run_id TEXT PRIMARY KEY NOT NULL, "
                "request_sha256 TEXT NOT NULL, receipt TEXT NOT NULL)"
            )
            database.execute(f"PRAGMA application_id = {_APPLICATION_ID}")

    @classmethod
    @contextmanager
    def _existing_database(cls,path):
        """Owned standalone DELETE-mode read; never creates/replays sidecars."""
        location=Path(path).absolute()
        if str(location).startswith(('//',chr(92)*2)) or '..' in location.parts or ':' in str(location)[len(location.drive):]:
            raise RuntimeError('paper lookup requires an ordinary local path')
        def check():
            for suffix in ('-wal','-shm','-journal'):
                side=Path(str(location)+suffix)
                if side.exists() or side.is_symlink():raise RuntimeError('paper lookup requires a standalone backup without sidecars')
            for item in (*reversed(location.parents),location):
                try:info=item.lstat()
                except FileNotFoundError:continue
                if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise RuntimeError('paper lookup rejects linked paths')
        check()
        if not location.exists():
            yield None;return
        identity=location.stat()
        if not stat.S_ISREG(identity.st_mode) or identity.st_nlink!=1:raise RuntimeError('paper lookup requires an ordinary dedicated database')
        with location.open('rb') as stream:header=stream.read(100)
        if (len(header)!=100 or header[:16]!=b'SQLite format 3\0' or header[18:20]!=b'\x01\x01'
                or int.from_bytes(header[68:72],'big')!=_APPLICATION_ID):raise RuntimeError('paper lookup requires a dedicated standalone DELETE-mode database')
        with closing(sqlite3.connect(location.as_uri()+'?mode=ro',uri=True,timeout=5)) as database:
            database.execute('PRAGMA query_only=ON');database.execute('BEGIN')
            if cls._application_id(database)!=_APPLICATION_ID:raise RuntimeError('paper replay database identity mismatch')
            columns=tuple((row[1],row[2].upper(),row[3],row[5]) for row in database.execute('PRAGMA table_info(paper_replay_receipts)'))
            if (database.execute("SELECT type FROM sqlite_schema WHERE name='paper_replay_receipts'").fetchone()!=('table',)
                    or columns!=(('run_id','TEXT',1,1),('request_sha256','TEXT',1,0),('receipt','TEXT',1,0))):raise RuntimeError('paper replay receipt table identity mismatch')
            yield database
        check();current=location.stat()
        if (current.st_dev,current.st_ino,current.st_nlink)!=(identity.st_dev,identity.st_ino,1):raise RuntimeError('paper replay database identity changed')

    @classmethod
    def lookup_existing(cls,path,run_id,request_sha256):
        if (type(run_id) is not str or re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',run_id) is None
                or type(request_sha256) is not str or re.fullmatch('[a-f0-9]{64}',request_sha256) is None):raise ValueError('invalid paper lookup identity')
        try:
            with cls._existing_database(path) as database:
                if database is None:return None
                row=database.execute('SELECT length(CAST(receipt AS BLOB)) FROM paper_replay_receipts WHERE run_id=?',(run_id,)).fetchone()
                if row is not None and not 0<row[0]<=4*1024*1024:raise RuntimeError('paper replay receipt budget exceeded')
                return cls._read(database,run_id,request_sha256)
        except sqlite3.Error as exc:raise RuntimeError('paper replay read-only lookup rejected') from exc

    @classmethod
    def recover_owned(cls,path):
        """Explicit LOCAL owner recovery, never a read/HTTP/archive fallback.

        Existing dedicated DELETE-mode replay/v2-journal databases only. SQLite
        performs hot rollback and retires stale journals; no source sidecar is
        manually removed. A private copied snapshot is schema/data checked before
        the original is opened for recovery. This is not filesystem/source auth.
        """
        location=Path(path).absolute();limit=64*1024*1024
        if str(location).startswith(('//',chr(92)*2)) or '..' in location.parts or ':' in str(location)[len(location.drive):]:raise RuntimeError('owned recovery requires an ordinary local path')
        def snapshot():
            for item in (*reversed(location.parents),location):
                try:info=item.lstat()
                except FileNotFoundError:raise RuntimeError('owned recovery requires an existing dedicated database') from None
                if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise RuntimeError('owned recovery rejects linked paths')
            for suffix in ('-wal','-shm'):
                side=Path(str(location)+suffix)
                if side.exists() or side.is_symlink():raise RuntimeError('owned recovery refuses WAL/SHM')
            def read(file):
                info=file.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>limit or getattr(info,'st_file_attributes',0)&1024:raise RuntimeError('owned recovery requires ordinary bounded files')
                with file.open('rb') as stream:
                    opened=os.fstat(stream.fileno())
                    if (opened.st_dev,opened.st_ino,opened.st_nlink)!=(info.st_dev,info.st_ino,1):raise RuntimeError('owned recovery file identity changed')
                    raw=stream.read(limit+1)
                    final_fd=os.fstat(stream.fileno())
                    if (final_fd.st_dev,final_fd.st_ino,final_fd.st_nlink,final_fd.st_size,final_fd.st_mtime_ns)!=(opened.st_dev,opened.st_ino,opened.st_nlink,opened.st_size,opened.st_mtime_ns):raise RuntimeError('owned recovery source changed during read')
                if len(raw)>limit:raise RuntimeError('owned recovery file budget exceeded')
                after=file.lstat()
                identity=lambda value:(value.st_dev,value.st_ino,value.st_nlink,value.st_size,value.st_mtime_ns)
                if identity(info)!=identity(after):raise RuntimeError('owned recovery source changed')
                return identity(info),raw
            identity,data=read(location)
            if len(data)<100 or data[:16]!=b'SQLite format 3\0' or data[18:20]!=b'\x01\x01' or int.from_bytes(data[68:72],'big')!=_APPLICATION_ID:raise RuntimeError('owned recovery requires dedicated DELETE-mode identity')
            journal=Path(str(location)+'-journal');state=None
            if journal.exists() or journal.is_symlink():
                state=read(journal);raw=state[1];page=int.from_bytes(data[16:18],'big');page=65536 if page==1 else page
                sector=int.from_bytes(raw[20:24],'big');size=int.from_bytes(raw[24:28],'big')
                if (len(raw)<28 or raw[:8] not in (b'\0'*8,bytes.fromhex('d9d505f920a163d7')) or not 512<=sector<=65536 or sector&(sector-1) or len(raw)<sector or size!=page or not 512<=page<=65536 or page&(page-1)):
                    raise RuntimeError('owned recovery refuses foreign or malformed journal')
                cls._validate_recovery_journal(data,raw)
            return identity,data,state
        before=snapshot()
        try:
            with tempfile.TemporaryDirectory(prefix='.paper-owner-recovery-',dir=location.parent) as temporary:
                copy=Path(temporary)/'snapshot.db';copy.write_bytes(before[1])
                if before[2] is not None:Path(str(copy)+'-journal').write_bytes(before[2][1])
                with closing(sqlite3.connect(copy.as_uri()+'?mode=rw',uri=True,timeout=0,isolation_level=None)) as database:
                    database.execute('BEGIN EXCLUSIVE')
                    expected=cls._owned_recovery_contents(database)
                    database.execute('ROLLBACK')
            if snapshot()!=before:raise RuntimeError('owned recovery source changed after staging')
            if before[2] is None:return None
            with closing(sqlite3.connect(location.as_uri()+'?mode=rw',uri=True,timeout=0,isolation_level=None)) as database:
                database.execute('PRAGMA synchronous=FULL')
                database.execute('BEGIN EXCLUSIVE')
                if database.execute('PRAGMA journal_mode').fetchone()!=('delete',):raise RuntimeError('owned recovery journal mode changed')
                if (location.stat().st_dev,location.stat().st_ino,location.stat().st_nlink)!=(before[0][0],before[0][1],1):raise RuntimeError('owned recovery identity changed')
                if cls._owned_recovery_contents(database)!=expected:raise RuntimeError('owned recovery data changed')
                # A zero-header journal is not hot, so read-only opens leave it.
                # A same-value SQLite header write commits/cleans it via SQLite.
                if Path(str(location)+'-journal').exists():database.execute('PRAGMA user_version='+str(expected[1]))
                database.execute('COMMIT')
            for suffix in ('-journal','-wal','-shm'):
                side=Path(str(location)+suffix)
                if side.exists() or side.is_symlink():raise RuntimeError('owned recovery sidecar outcome unknown')
            current=location.stat()
            if (current.st_dev,current.st_ino,current.st_nlink)!=(before[0][0],before[0][1],1):raise RuntimeError('owned recovery identity changed')
            with cls._existing_database(location) as database:
                if cls._owned_recovery_contents(database)!=expected:raise RuntimeError('owned recovery committed data changed')
        except sqlite3.Error as exc:raise RuntimeError('owned paper recovery refused or outcome unknown') from exc
        return None

    @staticmethod
    def _validate_recovery_journal(data,raw):
        """Bounded rollback-page checksum preflight; SQLite alone rolls back.

        Canonical single-database journals only; master/attached/torn/unknown
        forms refuse. Zero-header final records are checked too, not repaired.
        Format: sqlite.org/fileformat2.html section4 (rollback journal).
        """
        page=int.from_bytes(data[16:18],'big');page=65536 if page==1 else page
        sector=int.from_bytes(raw[20:24],'big');initial=int.from_bytes(raw[16:20],'big')
        offset=0;seen=set();magic=bytes.fromhex('d9d505f920a163d7')
        while offset<len(raw):
            header=raw[offset:offset+sector]
            if (len(header)!=sector or header[:8] not in (b'\0'*8,magic) or any(header[28:]) or int.from_bytes(header[16:20],'big')!=initial or int.from_bytes(header[20:24],'big')!=sector or int.from_bytes(header[24:28],'big')!=page or not 0<initial<=len(data)//page):raise RuntimeError('owned recovery malformed journal segment')
            count=int.from_bytes(header[8:12],'big');nonce=int.from_bytes(header[12:16],'big');position=offset+sector
            if header[:8]==b'\0'*8 and count!=0:raise RuntimeError('owned recovery malformed nonhot journal')
            terminal=count in (0,2**32-1)
            if terminal:
                if (len(raw)-position)%(page+8):raise RuntimeError('owned recovery torn journal record')
                count=(len(raw)-position)//(page+8)
            if count>(len(raw)-position)//(page+8):raise RuntimeError('owned recovery truncated journal')
            for _ in range(count):
                number=int.from_bytes(raw[position:position+4],'big');image=raw[position+4:position+4+page];checksum=int.from_bytes(raw[position+4+page:position+8+page],'big')
                expected=(nonce+sum(image[index] for index in range(page-200,-1,-200)))%(2**32)
                if not 1<=number<=initial or number in seen or checksum!=expected:raise RuntimeError('owned recovery journal page integrity failure')
                seen.add(number);position+=page+8
            if position==len(raw):return
            if terminal:raise RuntimeError('owned recovery unknown journal tail')
            next_header=((position+sector-1)//sector)*sector
            if next_header>len(raw) or any(raw[position:next_header]):raise RuntimeError('owned recovery malformed journal padding')
            offset=next_header
        return

    @classmethod
    def _owned_recovery_contents(cls,database):
        schemas={
            'paper_replay_receipts':(('run_id','TEXT',1,1),('request_sha256','TEXT',1,0),('receipt','TEXT',1,0)),
            'paper_streams_v2':(('source_id','TEXT',1,1),('run_id','TEXT',1,2),('symbol','TEXT',1,0),('checkpoint','INTEGER',1,0)),
            'paper_events_v2':(('source_id','TEXT',1,1),('run_id','TEXT',1,2),('sequence','INTEGER',1,3),('event','BLOB',1,0),('ack','BLOB',1,0),('ack_sha256','TEXT',1,0)),
        }
        expected_sql={
            'paper_replay_receipts':'CREATE TABLE paper_replay_receipts (run_id TEXT PRIMARY KEY NOT NULL, request_sha256 TEXT NOT NULL, receipt TEXT NOT NULL)',
            'paper_streams_v2':'CREATE TABLE paper_streams_v2 (source_id TEXT NOT NULL, run_id TEXT NOT NULL, symbol TEXT NOT NULL, checkpoint INTEGER NOT NULL, PRIMARY KEY (source_id, run_id))',
            'paper_events_v2':'CREATE TABLE paper_events_v2 (source_id TEXT NOT NULL, run_id TEXT NOT NULL, sequence INTEGER NOT NULL, event BLOB NOT NULL, ack BLOB NOT NULL, ack_sha256 TEXT NOT NULL, PRIMARY KEY (source_id, run_id, sequence))',
        }
        if cls._application_id(database)!=_APPLICATION_ID:raise RuntimeError('owned recovery application identity mismatch')
        tables={name for kind,name,table,sql in database.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema') if kind=='table'}
        if (not {'paper_replay_receipts'}<=tables or not tables<=set(schemas) or ('paper_streams_v2' in tables)!=('paper_events_v2' in tables)):
            raise RuntimeError('owned recovery requires the complete canonical paper schema')
        for kind,name,table,sql in database.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema'):
            if kind=='table':
                if re.sub(r'\s+','',sql).casefold()!=re.sub(r'\s+','',expected_sql[name]).casefold():raise RuntimeError('owned recovery canonical DDL mismatch')
                columns=tuple((row[1],row[2].upper(),row[3],row[5]) for row in database.execute('PRAGMA table_info('+name+')'))
                if columns!=schemas[name]:raise RuntimeError('owned recovery table identity mismatch')
            elif kind!='index' or sql is not None or table not in tables or name!='sqlite_autoindex_'+table+'_1':raise RuntimeError('owned recovery refuses unknown schema objects')
        if database.execute('PRAGMA quick_check(1)').fetchall()!=[('ok',)]:raise RuntimeError('owned recovery SQLite integrity failure')
        digest=sha256();total=0
        for name in sorted(tables):
            columns=schemas[name];order=','.join(item[0] for item in sorted(columns,key=lambda x:x[3]) if item[3])
            for row in database.execute('SELECT * FROM '+name+' ORDER BY '+order):
                for value,column in zip(row,columns):
                    if type(value) is not {'TEXT':str,'INTEGER':int,'BLOB':bytes}[column[1]]:raise RuntimeError('owned recovery stored type mismatch')
                    if type(value) in (str,bytes) and len(value)>4*1024*1024:raise RuntimeError('owned recovery cell budget exceeded')
                raw=canonical_json([name,[{'bytes':v.hex()} if type(v) is bytes else v for v in row]])
                total+=len(raw)
                if total>64*1024*1024:raise RuntimeError('owned recovery logical data budget exceeded')
                digest.update(len(raw).to_bytes(8,'big'));digest.update(raw)
                if name=='paper_replay_receipts':
                    if re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',row[0]) is None or re.fullmatch('[a-f0-9]{64}',row[1]) is None:raise RuntimeError('owned recovery receipt identity mismatch')
                    if len(row[2].encode('utf8'))>4*1024*1024:raise RuntimeError('owned recovery receipt budget exceeded')
                    cls._read(database,row[0],row[1])
                elif name=='paper_events_v2' and sha256(row[4]).hexdigest()!=row[5]:raise RuntimeError('owned recovery ACK integrity failure')
        if 'paper_streams_v2' in tables:
            from .paper_journal import PaperJournal
            PaperJournal._validate_existing_state(database)
        version=database.execute('PRAGMA user_version').fetchone()[0]
        if type(version) is not int or not -(2**31)<=version<2**31:raise RuntimeError('owned recovery version identity mismatch')
        return digest.hexdigest(),version

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    @contextmanager
    def _paper_event_transaction(self, *, write):
        with closing(self._connect()) as database, database:
            if not write:
                database.execute("PRAGMA query_only = ON")
            else:
                database.execute("PRAGMA synchronous = FULL")
            database.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            yield database

    @staticmethod
    def _application_id(database):
        return database.execute("PRAGMA application_id").fetchone()[0]

    def read(self, run_id, request_sha256):
        with closing(self._connect()) as database, database:
            database.execute("BEGIN")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            return self._read(database, run_id, request_sha256)

    @staticmethod
    def _read(database, run_id, request_sha256):
        row = database.execute(
            "SELECT request_sha256, receipt FROM paper_replay_receipts "
            "WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        stored_request_sha256, raw_receipt = row
        try:
            receipt = json.loads(raw_receipt)
            digest = receipt.pop("result_sha256")
            if (digest != sha256(canonical_json(receipt)).hexdigest()
                    or receipt["run_id"] != run_id
                    or receipt["request_sha256"] != stored_request_sha256
                    or receipt["status"] != "OFFLINE_UNATTESTED"
                    or receipt["provenance"] != "CALLER_SUPPLIED_UNATTESTED"
                    or receipt["execution_authority"] is not False
                    or receipt["trading_authorized"] is not False):
                raise ValueError("invalid receipt")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise RuntimeError("paper replay receipt integrity failure") from exc
        if stored_request_sha256 != request_sha256:
            raise ReplayConflict("paper replay run_id already used for another request")
        receipt["result_sha256"] = digest
        return receipt

    def record(self, receipt):
        run_id = receipt["run_id"]
        request_sha256 = receipt["request_sha256"]
        with closing(self._connect()) as database, database:
            database.execute("PRAGMA synchronous = FULL")
            database.execute("BEGIN IMMEDIATE")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            database.execute(
                "INSERT INTO paper_replay_receipts VALUES (?, ?, ?) "
                "ON CONFLICT(run_id) DO NOTHING",
                (run_id, request_sha256, canonical_json(receipt).decode("utf-8")),
            )
            return self._read(database, run_id, request_sha256)

    def migrate_historical_archive_schema(self):
        """Explicit transactional cutover; preserve a backup before caller use."""
        mapping=(("meta_fill_archives","historical_fill_archives",
                  ("source_id","row_count","sha256")),
                 ("meta_fill_rows","historical_fill_rows",
                  ("source_id","fill_id","row_json")))
        with closing(self._connect()) as database, database:
            database.execute("BEGIN IMMEDIATE")
            if self._application_id(database)!=_APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            names={row[0] for row in database.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
            old={old for old,new,columns in mapping if old in names}
            if not old:return False
            if len(old)!=2 or any(new in names for old,new,columns in mapping):
                raise ValueError("ambiguous historical archive schema")
            for old,new,columns in mapping:
                actual=tuple(row[1] for row in database.execute('PRAGMA table_info("'+old+'")'))
                if actual!=columns:raise ValueError("unrecognized historical archive schema")
            archives=list(database.execute("SELECT source_id,row_count,sha256 FROM meta_fill_archives"))
            for old,new,columns in mapping:
                database.execute('ALTER TABLE "'+old+'" RENAME TO "'+new+'"')
            for source_id,count,digest in archives:
                self._verify_historical_archive(database,source_id,(count,digest))
            return True

    def import_historical_fills(self, source_id, rows, source_receipt):
        """Archive one immutable Meta digest-v1 snapshot from a trusted export.

        The caller provides canonical SQL rows and the separately captured
        source receipt for that same frozen snapshot. This local operator API
        never opens the source database or grants execution authority. Use a
        stable opaque identifier for retries and a new ID for a new snapshot.
        """
        _validate_historical_source(source_id)
        if (type(source_receipt) is not dict
                or source_receipt.keys() != _HISTORICAL_RECEIPT.keys() | {"row_count", "sha256"}
                or any(type(source_receipt[key]) is not type(expected)
                       or source_receipt[key] != expected
                       for key, expected in _HISTORICAL_RECEIPT.items())):
            raise ValueError("unsupported legacy fill source receipt")
        count = source_receipt["row_count"]
        expected = source_receipt["sha256"]
        if (type(count) is not int or not 0 <= count <= 1_000_000
                or type(expected) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected)):
            raise ValueError("invalid legacy fill source digest or row count")

        with closing(self._connect()) as database, database:
            database.execute("BEGIN IMMEDIATE")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            database.execute(
                "CREATE TABLE IF NOT EXISTS historical_fill_archives ("
                "source_id TEXT PRIMARY KEY NOT NULL, row_count INTEGER NOT NULL, "
                "sha256 TEXT NOT NULL)"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS historical_fill_rows ("
                "source_id TEXT NOT NULL, fill_id INTEGER NOT NULL, row_json BLOB NOT NULL, "
                "PRIMARY KEY (source_id, fill_id))"
            )
            archive = self._historical_archive(database, source_id)
            if archive is not None and archive != (count, expected):
                raise ReplayConflict("legacy fill source ID already bound to a different snapshot")
            digest = _historical_digest()
            total = size = 0
            previous = None
            for row in rows:
                raw = _encode_historical_fill(row)
                total += 1
                size += len(raw)
                if (total > count or size > 2**30
                        or (previous is not None and previous >= row[0])):
                    raise ValueError("legacy fill export exceeds bounds or IDs are out of order")
                previous = row[0]
                _add_historical_row(digest, raw)
                if archive is None:
                    database.execute("INSERT INTO historical_fill_rows VALUES (?, ?, ?)",
                                     (source_id, row[0], raw))
            if (total, digest.hexdigest()) != (count, expected):
                raise ValueError("legacy fill export does not match source receipt")
            if archive is None:
                database.execute("INSERT INTO historical_fill_archives VALUES (?, ?, ?)",
                                 (source_id, count, expected))
            self._verify_historical_archive(database, source_id, (count, expected))
        return dict(_HISTORICAL_RECEIPT, row_count=count, sha256=expected)

    def restore_historical_fills(self, source_id):
        """Yield verified canonical rows from a single read-only snapshot.

        Exhaust the iterator or close it promptly to release the reader lock.
        """
        _validate_historical_source(source_id)
        with closing(self._connect()) as database, database:
            database.execute("PRAGMA query_only = ON")
            database.execute("BEGIN")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            archive = self._historical_archive(database, source_id)
            if archive is None:
                raise KeyError(source_id)
            self._verify_historical_archive(database, source_id, archive)
            for _, raw in self._historical_rows(database, source_id):
                yield json.loads(raw)

    @staticmethod
    def _historical_archive(database, source_id):
        if not database.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'historical_fill_archives'"
        ).fetchone():
            return None
        return database.execute(
            "SELECT row_count, sha256 FROM historical_fill_archives WHERE source_id = ?",
            (source_id,),
        ).fetchone()

    @staticmethod
    def _historical_rows(database, source_id):
        return database.execute(
            "SELECT fill_id, row_json FROM historical_fill_rows WHERE source_id = ? ORDER BY fill_id",
            (source_id,),
        )

    def _verify_historical_archive(self, database, source_id, archive):
        digest = _historical_digest()
        total = 0
        for fill_id, raw in self._historical_rows(database, source_id):
            if (type(raw) is not bytes or len(raw) > 262_144
                    or not raw.startswith(f"[{fill_id},".encode("ascii"))):
                raise RuntimeError("legacy fill archive integrity failure")
            total += 1
            if total > archive[0]:
                raise RuntimeError("legacy fill archive integrity failure")
            _add_historical_row(digest, raw)
        if (total, digest.hexdigest()) != archive:
            raise RuntimeError("legacy fill archive integrity failure")
