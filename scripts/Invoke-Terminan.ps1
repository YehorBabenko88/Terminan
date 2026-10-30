# Dedicated -File host: propagate the actual Python exit, including cancellation.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$ExpectedSha,
 [int]$Port=8765,[switch]$Demo,[string]$SourceConfig,[string]$CacheDb,
 [ValidateSet(0,15,600)][int]$ReviewSeconds=0,[string]$EvidenceRoot,[string]$PreviousSmoke)
if ([Environment]::CommandLine -notmatch '(?i)(?:^|\s)-File(?:\s|:)') {
 Write-Host 'USE_DEDICATED_FILE_HOST'; $global:LASTEXITCODE=50; return
}
$ErrorActionPreference='Stop'
$code=50
try {
 if ($MyInvocation.InvocationName -eq '.') { throw 'DEDICATED_FILE_HOST_REQUIRED' }
 Set-Location (Split-Path -Parent $PSScriptRoot)
 $env:UNIFIED_SHELL=$PSVersionTable.PSVersion.ToString()
 $python=(& py -3.12 -c 'import sys; print(sys.executable)')
 if ($LASTEXITCODE -ne 0) { throw 'PYTHON312_REQUIRED' }
 if ($ReviewSeconds -eq 0) {
  $argv=@('-m','terminan.unified_runner','--expected-sha',$ExpectedSha,'--port',"$Port")
  if ($Demo) { $argv+='--demo' }
  if ($SourceConfig) { $argv+=@('--config',$SourceConfig) }
  if ($CacheDb) { $argv+=@('--cache-db',$CacheDb) }
 } else {
  if (-not $EvidenceRoot) { throw 'NEW_EVIDENCE_ROOT_REQUIRED' }
  $argv=@('-m','terminan.unified_harness','--sha',$ExpectedSha,'--out',$EvidenceRoot,'--seconds',"$ReviewSeconds")
  if ($PreviousSmoke) { $argv+=@('--previous',$PreviousSmoke) }
 }
 & $python @argv
 $code=$LASTEXITCODE
 if ($null -eq $code) { $code=50 }
} catch { Write-Host 'UNIFIED_LAUNCH_FAILED' }
finally { [Environment]::Exit([int]$code) }
