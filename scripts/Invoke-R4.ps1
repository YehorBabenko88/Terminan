#requires -Version 5.1
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$ExpectedSha,
 [string]$Python='python', [string]$Node='node',
 [string]$EvidenceRoot='.r4-evidence', [switch]$OpenBrowser,
 [string]$ReviewSeconds='15'
)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
# Remain failed until lifecycle AND current browser evidence are verified.
$code=50
$savedPython=$env:R2_PYTHON
$savedInvocation=$env:R4_INVOCATION
$savedWork=$env:R4_WORK_ROOT
$pushed=$false
# A direct process exit is safe only in the dedicated -File host we own.
$dedicated=$false
$hostArguments=[Environment]::GetCommandLineArgs()
for($i=0;$i -lt ($hostArguments.Length-1);$i++){
 if($hostArguments[$i] -ieq '-File'){
  try {$dedicated=[String]::Equals([IO.Path]::GetFullPath($hostArguments[$i+1]),[IO.Path]::GetFullPath($PSCommandPath),[StringComparison]::OrdinalIgnoreCase)} catch {}
  break
 }
}
try {
 if(-not $dedicated){throw 'DEDICATED_FILE_HOST_REQUIRED'}
 $repo=[IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot,'..'))
 $root=if([IO.Path]::IsPathRooted($EvidenceRoot)){[IO.Path]::GetFullPath($EvidenceRoot)}else{[IO.Path]::Combine($repo,$EvidenceRoot)}
 $env:R4_INVOCATION=[Guid]::NewGuid().ToString('N')
 $invRoot=[IO.Path]::Combine($root,$env:R4_INVOCATION)
 $env:R4_WORK_ROOT=[IO.Path]::Combine($repo,'.r4-work',$env:R4_INVOCATION)
 $env:R2_PYTHON=$Python
 Push-Location $repo
 $pushed=$true
 & $Python -m terminan.r4_gate begin --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot
 if($LASTEXITCODE -ne 0){throw 'PREFLIGHT_FAILED'}
 $kind='LIFECYCLE_FAILED'
 & $Python -m terminan.r4_gate stage --stage lifecycle --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot
 if($LASTEXITCODE -ne 0){throw 'EVIDENCE_INVALID'}
 [Console]::WriteLine('R4 invocation='+$env:R4_INVOCATION)
 $runId=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
 $lifeRoot=[IO.Path]::Combine($invRoot,'lifecycle')
 $arguments=@('-m','terminan.r4_harness','--expected-sha',$ExpectedSha,'--evidence-root',$lifeRoot,'--run-id',$runId,'--review-seconds',$ReviewSeconds,'--shell-version',$PSVersionTable.PSVersion.ToString())
 if($OpenBrowser){$arguments+='--open-browser'}
 & $Python @arguments
 $lifecycleCode=$LASTEXITCODE
 if($lifecycleCode -ne 0){throw 'LIFECYCLE_FAILED'}
 & $Python -m terminan.r4_harness --inspect-run --expected-sha $ExpectedSha --evidence-root $lifeRoot --run-id $runId
 if($LASTEXITCODE -ne 0){throw 'EVIDENCE_INVALID'}
 $kind='BROWSER_FAILED'
 & $Python -m terminan.r4_gate stage --stage browser_run --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot
 if($LASTEXITCODE -ne 0){throw 'EVIDENCE_INVALID'}
 & $Node 'node_modules/@playwright/test/cli.js' test --config=playwright.r4.config.cjs '--project=chromium-*'
 $browserCode=$LASTEXITCODE
 if($browserCode -ne 0){throw 'BROWSER_FAILED'}
 $kind='EVIDENCE_INVALID'
 & $Python -m terminan.r4_gate stage --stage browser_evidence --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot
 if($LASTEXITCODE -ne 0){throw 'EVIDENCE_INVALID'}
 $report=[IO.Path]::Combine($env:R4_WORK_ROOT,'reports','r4-browser.json')
 & $Python -m terminan.r4_evidence --sha $ExpectedSha --scope chromium --report $report --out ([IO.Path]::Combine($invRoot,'browser'))
 if($LASTEXITCODE -ne 0){throw 'EVIDENCE_INVALID'}
 & $Python -m terminan.r4_gate complete --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot
 if($LASTEXITCODE -ne 0){throw 'EVIDENCE_INVALID'}
 & $Python -m terminan.r4_gate verify --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot
 if($LASTEXITCODE -eq 0 -and [IO.File]::Exists([IO.Path]::Combine($invRoot,'manifest.json')) -and [IO.File]::Exists([IO.Path]::Combine($invRoot,'browser','manifest.json'))){$code=0}
} catch {
 $code=50
 if($invRoot -and [IO.File]::Exists([IO.Path]::Combine($invRoot,'summary.json'))){
  if(-not $kind){$kind='LAUNCHER_ERROR'}
  & $Python -m terminan.r4_gate fail --sha $ExpectedSha --invocation $env:R4_INVOCATION --out $invRoot --error-class $kind
 }
 # No ErrorRecord/raw message, executable, path or report content is public.
 [Console]::WriteLine('R4 FAIL error_class=GATE_FAILED exit_code=50')
} finally {
 # PipelineStoppedException (Ctrl+C) bypasses catch and code after try/finally.
 # Exit INSIDE finally: lifecycle's native0 can never escape as aggregate PASS.
 try {
  $env:R2_PYTHON=$savedPython
  $env:R4_INVOCATION=$savedInvocation
  $env:R4_WORK_ROOT=$savedWork
  if($pushed){Pop-Location}
 } finally {
  $global:LASTEXITCODE=$code
  # Console Ctrl+C can turn PowerShell's language exit50 into native0.
  # Direct OS process termination preserves50; embedded calls are refused.
  if($dedicated){[Environment]::Exit([int]$code)}
  exit $code
 }
}
