param(
    [Parameter(Mandatory=$true)][string]$ExpectedSha,
    [Parameter(Mandatory=$true)][string]$EvidenceRoot,
    [string]$Python=''
)
# Dedicated native host only: never terminate the user's interactive shell.
if ([Environment]::CommandLine -notmatch '(?i)(?:^|\s)-File(?:\s|:)') {
    Write-Host 'USE_DEDICATED_FILE_HOST'; $global:LASTEXITCODE=50; return
}
$ErrorActionPreference='Stop'
$code=50
$pushed=$false
try {
    $repo=Split-Path -Parent $PSScriptRoot
    $out=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($EvidenceRoot)
    Push-Location -LiteralPath $repo
    $pushed=$true
    if (-not $Python) { $Python=(& py -3.12 -c 'import sys;print(sys.executable)').Trim() }
    if (-not $Python) { throw 'PYTHON_REQUIRED' }
    & $Python scripts/audit_cache.py --sha $ExpectedSha --out $out --shell-version ($PSVersionTable.PSVersion.ToString())
    $native=$LASTEXITCODE
    if ($native -eq 0) { $code=0 }
    Write-Host "CACHE_AUDIT_NATIVE_EXIT=$code"
} catch { Write-Host 'CACHE_AUDIT_FAILED' }
finally {
    if ($pushed) { Pop-Location }
    [Environment]::Exit($code)
}
