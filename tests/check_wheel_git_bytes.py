"""Compare one wheel's complete runtime payload with an exact Git commit.

A source-consistency proof only; no publisher or execution authority is issued.
"""
import argparse,hashlib,json,pathlib,shutil,stat,subprocess,zipfile

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('repo','sha','wheel-dir','out'):p.add_argument('--'+name,required=True)
 p.add_argument('--source-prefix',default='');a=p.parse_args()
 repo=pathlib.Path(a.repo).resolve(strict=True);wheels=list(pathlib.Path(a.wheel_dir).glob('*.whl'))
 if len(wheels)!=1:raise ValueError('exactly one wheel required')
 git=shutil.which('git')
 if not git:raise ValueError('Git unavailable')
 def read(*args):return subprocess.check_output([git,'--no-replace-objects','-c','core.fsmonitor=false','-c','core.hooksPath='+__import__('os').devnull,'-C',str(repo),*args])
 if read('rev-parse','HEAD').decode().strip()!=a.sha:raise ValueError('source HEAD mismatch')
 files={};seen=set();total=0
 with zipfile.ZipFile(wheels[0]) as z:
  for info in z.infolist():
   name=pathlib.PurePosixPath(info.filename)
   if name.is_absolute() or '..' in name.parts or info.filename in seen or stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK:raise ValueError('unsafe wheel member')
   seen.add(info.filename);total+=info.file_size
   if len(seen)>512 or total>64*1024*1024:raise ValueError('wheel budget')
   if info.is_dir() or name.parts[0].endswith('.dist-info'):continue
   raw=z.read(info);expected=read('show',a.sha+':'+a.source_prefix+info.filename)
   if raw!=expected:raise ValueError('wheel differs from raw Git blob: '+info.filename)
   files[info.filename]=hashlib.sha256(raw).hexdigest()
 if not files:raise ValueError('empty runtime payload')
 report=dict(status='PASS_SOURCE_CONSISTENCY',source_sha=a.sha,wheel_sha256=hashlib.sha256(wheels[0].read_bytes()).hexdigest(),files=files)
 pathlib.Path(a.out).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(source_sha=a.sha,files=len(files),status=report['status'])))

if __name__=='__main__':main()
