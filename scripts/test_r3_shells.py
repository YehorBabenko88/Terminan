"""Actual PS pipeline cancellation/false-zero regressions; no browser/DB connection.
The lifecycle stub returns zero deliberately: only the aggregate gate may authorize PASS.
"""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--shell',required=True);p.add_argument('--report',required=True);a=p.parse_args()
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();results=[]
    with tempfile.TemporaryDirectory(prefix='r3-shell-gate-') as td:
        root=Path(td);(root/'scripts').mkdir()
        shutil.copyfile(REPO/'scripts/Invoke-R3.ps1',root/'scripts/Invoke-R3.ps1')
        (root/'scripts/Invoke-R2.ps1').write_text('$global:LASTEXITCODE=0\nexit 0\n')
        node=root/'browser.ps1'
        node.write_text("""
if($env:R3_FAULT -eq 'pipeline_stop'){$global:LASTEXITCODE=0;throw [System.Management.Automation.PipelineStoppedException]::new()}
if($env:R3_FAULT -eq 'nonzero'){$global:LASTEXITCODE=7;exit 7}
if($env:R3_FAULT -ne 'missing'){
 $dir=[IO.Path]::Combine($env:R3_WORK_ROOT,'reports');[IO.Directory]::CreateDirectory($dir)|Out-Null
 $nonce=$env:R3_INVOCATION
 if($env:R3_FAULT -eq 'stale'){$nonce='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'}
 $projects=@('chromium-dpr1','chromium-dpr1.5','chromium-dpr2')
 $tests=@();foreach($project in $projects){$tests+=@{projectId=$project;projectName=$project;expectedStatus='passed';status='expected';results=@(@{status='passed';retry=0;errors=@()})}}
 $expected=3;$skipped=0
 if($env:R3_FAULT -eq 'interrupted'){$tests[1].results[0].status='interrupted';$tests[2].results=@();$expected=1;$skipped=2}
 if($env:R3_FAULT -eq 'cancelled'){$tests[0].results[0].status='interrupted';$expected=0;$skipped=3}
 $raw=@{config=@{metadata=@{r3_invocation=$nonce;r3_source_sha=$env:R3_SHA}};errors=@();stats=@{expected=$expected;skipped=$skipped;unexpected=0;flaky=0};suites=@(@{specs=@(@{file='r3.spec.cjs';title='R3 bounded 10k 100k renderer workloads and cancellation';ok=$true;tests=$tests})})}|ConvertTo-Json -Depth 20
 if($env:R3_FAULT -eq 'malformed'){$raw='[]'}
 [IO.File]::WriteAllText([IO.Path]::Combine($dir,'r3-browser.json'),$raw)
}
$global:LASTEXITCODE=0
exit 0
""",encoding='utf8')
        for fault in ('pipeline_stop','nonzero','missing','stale','interrupted','cancelled','malformed','missing_artifacts'):
            out=root/fault;env=dict(os.environ,PYTHONPATH=str(REPO),R3_FAULT=fault,R3_SHA=sha)
            cmd=[a.shell,'-NoProfile','-NonInteractive','-File',str(root/'scripts/Invoke-R3.ps1'),'-ExpectedSha',sha,'-Python',sys.executable,'-Node',str(node),'-EvidenceRoot',str(out),'-ReviewSeconds','0']
            process=subprocess.run(cmd,cwd=REPO,env=env,capture_output=True,text=True,timeout=40)
            summaries=list(out.glob('*/summary.json'))
            summary=json.loads(summaries[0].read_text()) if len(summaries)==1 else None
            passed=process.returncode==50 and summary is not None and summary['result']=='FAIL' and summary['exit_code']==50
            results.append(dict(case=fault,shell=a.shell,candidate_sha=sha,native_exit=process.returncode,summary_exit=summary.get('exit_code') if summary else None,expectations='PASS' if passed else 'FAIL'))
    target=Path(a.report);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results));return 0 if all(r['expectations']=='PASS' for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
