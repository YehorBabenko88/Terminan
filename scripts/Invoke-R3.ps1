#requires -Version 5.1
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$ExpectedSha,
 [string]$Python='python', [string]$Node='node',
 [string]$EvidenceRoot='.r3-evidence', [switch]$OpenBrowser,
 [string]$ReviewSeconds='15'
)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$code=50
try {
 $repo=[IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot,'..'))
 $root=if([IO.Path]::IsPathRooted($EvidenceRoot)){[IO.Path]::GetFullPath($EvidenceRoot)}else{[IO.Path]::Combine($repo,$EvidenceRoot)}
 $shell=if($PSVersionTable.PSEdition -eq 'Core'){[IO.Path]::Combine($PSHOME,'pwsh.exe')}else{[IO.Path]::Combine($PSHOME,'powershell.exe')}
 $argsR2=@('-NoProfile','-File',[IO.Path]::Combine($PSScriptRoot,'Invoke-R2.ps1'),'-ExpectedSha',$ExpectedSha,'-Python',$Python,'-EvidenceRoot',[IO.Path]::Combine($root,'lifecycle'),'-ReviewSeconds',$ReviewSeconds)
 if($OpenBrowser){$argsR2+='-OpenBrowser'}
 & $shell @argsR2
 $code=$LASTEXITCODE
 if($code -eq 0){
  Push-Location $repo
  try {
   $savedPython=$env:R2_PYTHON
   $savedInvocation=$env:R3_INVOCATION
   $env:R3_INVOCATION=[Guid]::NewGuid().ToString('N')
   try {
    $env:R2_PYTHON=$Python
    & $Node 'node_modules/@playwright/test/cli.js' test --config=playwright.r3.config.cjs '--project=chromium-*'
    $browserCode=$LASTEXITCODE
   } finally { $env:R2_PYTHON=$savedPython }
   $runId=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
   & $Python -m terminan.r3_evidence --sha $ExpectedSha --scope chromium --out ([IO.Path]::Combine($root,$runId))
   $evidenceCode=$LASTEXITCODE
   if($evidenceCode -eq 0){
    & $Python -m terminan.r3_evidence --verify --sha $ExpectedSha --out ([IO.Path]::Combine($root,$runId))
    $evidenceCode=$LASTEXITCODE
   }
   $env:R3_INVOCATION=$savedInvocation
   $code=if($browserCode -eq 0 -and $evidenceCode -eq 0){0}else{50}
  } finally { Pop-Location }
 }
} catch { $code=50;[Console]::WriteLine('R3 FAIL error_class=LAUNCHER_ERROR exit_code=50') }
$global:LASTEXITCODE=$code
exit $code
