"""Real Windows Ctrl+C, only in a newly owned hidden console. No raw output retained."""
import argparse,ctypes,hashlib,json,os,subprocess,sys,tempfile,time,uuid
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
def worker(token):
    if os.getenv('R4_CONSOLE_TOKEN')!=token or len(token)!=32:raise ValueError()
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    def members():
        buffer=(ctypes.c_uint*16)();count=api.GetConsoleProcessList(buffer,16)
        if not 0<count<=16:raise ValueError()
        return set(buffer[:count])
    if members()!={os.getpid()}:raise ValueError()
    handler_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_uint)
    handler=handler_type(lambda event: True)
    if not api.SetConsoleCtrlHandler(handler,True):raise ValueError()
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();records=[]
    with tempfile.TemporaryDirectory(prefix='r4-console-contract-') as td:
        td=Path(td)
        for shell in ('powershell.exe','pwsh.exe'):
            marker=td/(shell+'.marker');shim=td/(shell+'.ps1');out=td/(shell+'-evidence')
            shim.write_text("[IO.File]::WriteAllText($env:R4_BROWSER_MARKER,'reached')\nwhile($true){[Threading.Thread]::Sleep(100)}\n")
            process=subprocess.Popen([shell,'-NoProfile','-NonInteractive','-File',str(REPO/'scripts/Invoke-R4.ps1'),'-ExpectedSha',sha,'-Python',sys.executable,'-Node',str(shim),'-EvidenceRoot',str(out),'-ReviewSeconds','0'],cwd=REPO,env=dict(os.environ,R4_BROWSER_MARKER=str(marker)),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            deadline=time.monotonic()+30
            while not marker.is_file() and process.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            reached=marker.is_file();sent=False;timeout=False
            if reached:
                deadline=time.monotonic()+5
                while not members()<={os.getpid(),process.pid} and time.monotonic()<deadline:time.sleep(.05)
                if members()<={os.getpid(),process.pid}:sent=bool(api.GenerateConsoleCtrlEvent(0,0))
            try:stdout,stderr=process.communicate(timeout=20)
            except subprocess.TimeoutExpired:timeout=True;process.kill();stdout,stderr=process.communicate(timeout=5)
            stdout=None;stderr=None
            summaries=list(out.glob('*/summary.json'));summary=json.loads(summaries[0].read_text()) if len(summaries)==1 else None
            passed=reached and sent and not timeout and process.returncode==50 and summary and summary['exit_code']==50 and summary['result']=='FAIL' and summary['failure_stage']=='browser_run'
            records.append(dict(candidate_sha=sha,shell=shell,signal='CTRL_C_EVENT_OWN_CONSOLE',browser_reached=reached,signal_sent=sent,timeout=timeout,native_exit=process.returncode,summary_exit=summary.get('exit_code') if summary else None,failure_stage=summary.get('failure_stage') if summary else None,expectations='PASS' if passed else 'FAIL'))
    print(json.dumps(records));return 0 if all(r['expectations']=='PASS' for r in records) else 1

def main():
    p=argparse.ArgumentParser();p.add_argument('--report');p.add_argument('--worker');a=p.parse_args()
    if os.name!='nt':raise ValueError()
    if a.worker:return worker(a.worker)
    if not a.report or subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip():raise ValueError()
    token=uuid.uuid4().hex;startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',token],cwd=REPO,creationflags=subprocess.CREATE_NEW_CONSOLE,startupinfo=startup,env=dict(os.environ,R4_CONSOLE_TOKEN=token),capture_output=True,text=True,timeout=125)
    records=json.loads(child.stdout);target=Path(a.report);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records))
    return 0 if child.returncode==0 and len(records)==2 and all(r['expectations']=='PASS' for r in records) else 1
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:print('R4 console contract FAIL error_class=DRIVER_FAILURE');raise SystemExit(1)
