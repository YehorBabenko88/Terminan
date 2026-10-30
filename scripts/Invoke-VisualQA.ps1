param([Parameter(Mandatory=$true)][string]$ExpectedSha,[Parameter(Mandatory=$true)][string]$EvidenceRoot)
if ([Environment]::CommandLine -notmatch '(?i)(?:^|\s)-File(?:\s|:)') { Write-Host 'USE_DEDICATED_FILE_HOST'; $global:LASTEXITCODE=50; return }
$ErrorActionPreference='Stop';$code=50
try {
 Set-Location (Split-Path -Parent $PSScriptRoot)
 $env:VISUAL_SHELL=$PSVersionTable.PSVersion.ToString()
 $python=(& py -3.12 -c 'import sys;print(sys.executable)').Trim()
 if ($LASTEXITCODE -ne 0) { throw 'PYTHON312_REQUIRED' }
 & $python scripts/visual_qa.py --expected-sha $ExpectedSha --out $EvidenceRoot
 if ($null -ne $LASTEXITCODE) { $code=$LASTEXITCODE }
} catch { Write-Host 'VISUAL_QA_FAILED' }
finally { [Environment]::Exit([int]$code) }
