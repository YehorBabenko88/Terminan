"""Windows-only native-shell contract tests. No browser or real source is opened."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from terminan.r2_harness import inspect_run

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--shell',required=True);parser.add_argument('--report',required=True)
    args=parser.parse_args();sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    records=[];bad=0
    with tempfile.TemporaryDirectory(prefix='r2-shell-contract-') as temp:
        temp=Path(temp);driver=temp/'fake-python.py'
        driver.write_text("""
import argparse,sys
from pathlib import Path
repo=Path(sys.argv[1]);fault=sys.argv[2];sys.path.insert(0,str(repo));sys.path.insert(0,str(repo/'tests'))
from terminan.r2_harness import Harness,inspect_run
import test_harness_failclosed as fixture
p=argparse.ArgumentParser();p.add_argument('--expected-sha');p.add_argument('--evidence-root');p.add_argument('--run-id');p.add_argument('--review-seconds',default='0');p.add_argument('--open-browser',action='store_true');p.add_argument('--inspect-run',action='store_true')
a,unused=p.parse_known_args(sys.argv[3:])
fixture.SHA=a.expected_sha
target=Path(a.evidence_root)/a.run_id
if a.inspect_run:raise SystemExit(inspect_run(target,a.expected_sha))
runtime=fixture.FakeRuntime(fault)
if fault=='publish_once':
 original=runtime.publish
 def publish(pending,final):
  if not hasattr(runtime,'failed_publish'):
   runtime.failed_publish=True;raise OSError(fixture.SECRET)
  original(pending,final)
 runtime.publish=publish
h=Harness(expected_sha=a.expected_sha,evidence_root=a.evidence_root,run_id=a.run_id,review_seconds='15',open_browser=True,runtime=runtime)
raise SystemExit(h.run())
""",encoding='utf-8')
        missing=temp/'missing-python.cmd';missing.write_text('@exit /b 0\n')
        outer=temp/'outer.ps1'
        outer.write_text("""
param([string]$Harness,[string]$Sha,[string]$Root,[string]$Forward,[string]$Python='python')
$PSNativeCommandUseErrorActionPreference=$true
& $Harness -ExpectedSha $Sha -EvidenceRoot $Root -Python $Python -ReviewSeconds 0
$captured=$LASTEXITCODE
[Console]::WriteLine('R2_CALLER_CAPTURED='+$captured)
if($Forward -eq 'yes'){exit $captured}
""",encoding='utf-8-sig')
        cases=[('success',sha,0,None),('invalid_sha','PRIVATE_PATH_DSN_RAW_EXCEPTION',10,None),('wrong_sha','b'*40,10,None),
               ('missing_evidence',sha,50,'missing'),('browser_launch',sha,31,'browser_launch'),
               ('early_child',sha,33,'early_child'),('shutdown_timeout',sha,40,'shutdown_timeout'),
               ('review_wait',sha,32,'review_wait'),('finalize',sha,50,'publish_once'),
               ('outer_forward', 'b'*40,10,None),('outer_no_forward','b'*40,0,None),
               ('command_forward','b'*40,10,None)]
        for name,expected_sha,expected_exit,fault in cases:
            root=temp/name;python=sys.executable
            if fault=='missing':python=str(missing)
            elif fault:
                shim=temp/(name+'.cmd')
                # All paths are test-generated; no string from source data is executed.
                shim.write_text('@echo off\n"'+sys.executable+'" "'+str(driver)+'" "'+str(REPO)+'" '+fault+' %*\nexit /b %ERRORLEVEL%\n')
                python=str(shim)
            script=REPO/'scripts/Invoke-R2.ps1'
            command=[args.shell,'-NoProfile','-NonInteractive']
            if name.startswith('outer_'):
                command+=['-File',str(outer),'-Harness',str(script),'-Sha',expected_sha,'-Root',str(root),'-Forward','no' if name=='outer_no_forward' else 'yes','-Python',python]
            elif name=='command_forward':
                quote=lambda value:"'"+str(value).replace("'","''")+"'"
                source='& '+quote(script)+' -ExpectedSha '+quote(expected_sha)+' -EvidenceRoot '+quote(root)+' -Python '+quote(python)+'; $r2Exit=$LASTEXITCODE; exit $r2Exit'
                command+=['-Command',source]
            else:command+=['-File',str(script),'-ExpectedSha',expected_sha,'-EvidenceRoot',str(root),'-Python',python,'-ReviewSeconds','0']
            record=dict(case=name,scope='SYNTHETIC_SHELL_CONTRACT',shell=args.shell,candidate_sha=sha,expected_process_exit=expected_exit,acceptable_usage=name!='outer_no_forward')
            try:
                process=subprocess.run(command,cwd=REPO,capture_output=True,text=True,timeout=45)
                record['process_exit']=process.returncode
                summaries=[p for p in root.glob('*/summary.json') if not p.parent.name.startswith('.pending-')]
                summary=json.loads(summaries[0].read_text()) if summaries else None
                record['summary_exit']=summary['exit_code'] if summary else None
                if summary:
                    for key in ('failure_stage','error_class','run_id'):record[key]=summary[key]
                    manifest=summaries[0].with_name('manifest.json');entries=json.loads(manifest.read_text())
                    record['manifest_entries']=len(entries);record['manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
                    record['summary_sha256']=hashlib.sha256(summaries[0].read_bytes()).hexdigest()
                    assert isinstance(entries,list)
                    assert inspect_run(summaries[0].parent,expected_sha)==summary['exit_code']
                assert process.returncode==expected_exit
                if name=='outer_no_forward':
                    assert 'R2_CALLER_CAPTURED=10' in process.stdout and summary['exit_code']==10
                    record['diagnostic']='Caller discards native status; never acceptable release usage'
                elif name!='missing_evidence':
                    assert summary and summary['exit_code']==process.returncode
                if name=='invalid_sha':
                    assert record['manifest_entries']==1 and summary['error_class']=='INVALID_SHA'
                assert 'PRIVATE_PATH_DSN_RAW_EXCEPTION' not in process.stdout+process.stderr+(summaries[0].read_text() if summaries else '')
                record['expectations']='PASS'
            except Exception as error:
                bad+=1;record['expectations']='FAIL';record['test_error_class']=type(error).__name__
            records.append(record)
            print(name+': '+record['expectations'])
    output=Path(args.report);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(dict(candidate_sha=sha,shell=args.shell,tests=records,failures=bad,physical='PENDING'),indent=2)+'\n')
    return 1 if bad else 0

if __name__=='__main__':raise SystemExit(main())
