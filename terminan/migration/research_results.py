"""Restore caller-pinned historical research rows into the existing archive.

Original Strattester13998 reader blob943715544c52d513e6307d92d32b5e75642eeee8.
The original is opened only as bytes; SQLite reads a private immutable copy.
A destination must be separately fresh. No existing database is adopted, and
historical metrics/strategy IDs are preserved without performance authority.
"""
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse,json,os,re,sqlite3,stat
from ..paper_ledger import PaperReplayLedger
from ..research_archive import ResearchArchive,research_result_receipt,_source_id
from .paper_receipts import _digest_file

# name, declared type, NOT NULL, default, primary-key ordinal, hidden flag
_LEGACY = (
    ("run_id", "TEXT", 1, None, 1, 0),
    ("symbol", "TEXT", 1, None, 2, 0),
    ("strategy_id", "TEXT", 1, None, 3, 0),
    ("strategy_version", "TEXT", 1, None, 4, 0),
    ("created_at", "REAL", 1, None, 0, 0),
    ("metrics", "TEXT", 1, None, 0, 0),
)
_PUBLISHED = (
    *_LEGACY,
    ("job_id", "TEXT", 0, None, 0, 0),
    ("lease_token", "INTEGER", 1, "0", 0, 0),
    ("node_generation", "INTEGER", 1, "0", 0, 0),
)
_STAGED = (
    ("stage_id", "TEXT", 0, None, 1, 0),
    *((name, declared, required, default, 0, hidden)
      for name, declared, required, default, _, hidden in _PUBLISHED),
)
_MAX_BACKUP_BYTES=4*1024**3
_SIDECAR_SUFFIXES=('-wal','-shm','-journal')

def _ordinary_path(raw,*,source):
 path=Path(raw)
 if not path.is_absolute() or '..' in path.parts or str(path).startswith(('//',chr(92)*2)) or ':' in str(path)[len(path.drive):]:raise ValueError('ordinary absolute local path required')
 for part in (*reversed(path.parents),path):
  try:info=part.lstat()
  except FileNotFoundError:
   if source or part!=path:raise ValueError('snapshot or destination parent missing') from None
   continue
  if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('linked migration path refused')
  if part!=path and not stat.S_ISDIR(info.st_mode):raise ValueError('ordinary migration parent required')
  if part==path:
   if not source:raise FileExistsError('fresh destination required')
   if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>_MAX_BACKUP_BYTES:raise ValueError('bounded ordinary snapshot required')
 return path

def _no_sidecars(path):
 for suffix in _SIDECAR_SUFFIXES:
  side=Path(str(path)+suffix)
  try:side.lstat()
  except FileNotFoundError:continue
  raise ValueError('standalone frozen database without sidecars required')

def _facts(info):return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink

def _copy_verified(source,destination,expected):
 _no_sidecars(source);digest=sha256();count=0
 with source.open('rb') as origin,destination.open('xb') as copy:
  before=os.fstat(origin.fileno())
  if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>_MAX_BACKUP_BYTES:raise ValueError('bounded ordinary snapshot required')
  header=origin.read(100)
  if len(header)!=100 or header[:16]!=b'SQLite format 3\0' or header[18:20]!=b'\1\1':raise ValueError('standalone DELETE-mode SQLite snapshot required')
  origin.seek(0)
  for block in iter(lambda:origin.read(1048576),b''):
   count+=len(block)
   if count>_MAX_BACKUP_BYTES:raise ValueError('snapshot byte budget exceeded')
   digest.update(block);copy.write(block)
  after=os.fstat(origin.fileno())
 _no_sidecars(source)
 if _facts(before)!=_facts(after) or _facts(after)!=_facts(source.lstat()) or count!=after.st_size:raise ValueError('snapshot changed during copy')
 if digest.hexdigest()!=expected:raise ValueError('snapshot SHA256 mismatch')

def _unchanged(source,expected):
 _ordinary_path(source,source=True);_no_sidecars(source)
 if _digest_file(source)!=expected:raise ValueError('snapshot changed')

def _columns(connection, table):
    # Only inspect real tables, never views that could synthesize rows.
    found = connection.execute(
        "SELECT type FROM pragma_table_list WHERE schema = 'main' AND name = ?", (table,)
    ).fetchone()
    if found is None:
        return ()
    if found != ("table",):
        raise ValueError("expected Strattester result table")
    return tuple(
        (name, declared.upper(), required, default, key, hidden)
        for _, name, declared, required, default, key, hidden
        in connection.execute(f"PRAGMA main.table_xinfo({table})")
    )


def restore_frozen_research_results(source,expected_sha256,source_id,target):
 """Preflight every historical row before exclusively creating a new archive."""
 if type(expected_sha256) is not str or re.fullmatch('[a-f0-9]{64}',expected_sha256) is None:raise ValueError('snapshot SHA256 required')
 _source_id(source_id);source=_ordinary_path(source,source=True);target=_ordinary_path(target,source=False)
 source_files={source,*(Path(str(source)+s) for s in _SIDECAR_SUFFIXES)}
 target_files={target,*(Path(str(target)+s) for s in _SIDECAR_SUFFIXES)}
 if source_files&target_files:raise ValueError('separate source and destination required')
 _no_sidecars(source);_no_sidecars(target)
 with TemporaryDirectory(prefix='terminan-frozen-research-') as directory:
  copy=Path(directory)/'snapshot.sqlite';_copy_verified(source,copy,expected_sha256)
  with closing(sqlite3.connect(copy.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=2)) as db:
   db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
   published=_columns(db,'research_results');staged=_columns(db,'staged_research_results')
   if published not in (_LEGACY,_PUBLISHED):raise ValueError('unrecognized historical published schema')
   legacy=published==_LEGACY
   if legacy and staged or not legacy and staged!=_STAGED:raise ValueError('unrecognized historical staged schema')
   def rows(table,columns,order):
    # Cap TEXT/BLOB fields inside SQLite before they can be copied into Python.
    projection=', '.join('CASE WHEN length(CAST('+c[0]+' AS BLOB))<=262144 THEN '+c[0]+' END' if c[1]=='TEXT' else c[0] for c in columns)
    return db.execute('SELECT '+projection+' FROM '+table+' ORDER BY '+order)
   def tables():
    result={'research_results':rows('research_results',published,'run_id COLLATE BINARY,symbol COLLATE BINARY,strategy_id COLLATE BINARY,strategy_version COLLATE BINARY')}
    if not legacy:result['staged_research_results']=rows('staged_research_results',_STAGED,'stage_id COLLATE BINARY')
    return result
   receipt=research_result_receipt(expected_sha256,tables())
   _unchanged(source,expected_sha256);_ordinary_path(target,source=False);_no_sidecars(target)
   fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
   try:identity=os.fstat(fd)
   finally:os.close(fd)
   def owned():
    info=target.lstat()
    if (info.st_dev,info.st_ino)!=(identity.st_dev,identity.st_ino) or info.st_nlink!=1 or not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise RuntimeError('destination identity changed')
   owned();archive=ResearchArchive(PaperReplayLedger(target));owned()
   result=archive.import_snapshot(source_id,tables(),receipt);owned();_unchanged(source,expected_sha256)
   return result

def main(argv=None,*,stdout=None):
 import sys
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('source','source_sha256','source_id','target'):parser.add_argument(name)
 args=parser.parse_args(argv)
 try:result=restore_frozen_research_results(args.source,args.source_sha256,args.source_id,args.target);code=0
 except Exception:result={'status':'HISTORICAL_RESTORE_REJECTED','execution_authority':False,'trading_authorized':False};code=1
 print(json.dumps(result,sort_keys=True,allow_nan=False),file=stdout or sys.stdout);return code

if __name__=='__main__':raise SystemExit(main())
