#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{40}$')][string]$ExpectedSha,
    [string]$Python = '',
    [switch]$PreflightOnly,
    [switch]$OpenBrowser
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $root
try {
    $actual = (& git rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or $actual.Trim() -cne $ExpectedSha) {
        throw 'STOP: exact HEAD mismatch'
    }
    $tracked = @(& git diff --name-only)
    $staged = @(& git diff --cached --name-only)
    $untracked = @(& git ls-files --others --exclude-standard)
    if ($tracked.Count -gt 0 -or $staged.Count -gt 0 -or $untracked.Count -gt 0) {
        throw 'STOP: worktree is not clean'
    }
    if (-not $Python) {
        $Python = (& py -3.12 -c 'import sys; print(sys.executable)')
        if ($LASTEXITCODE -ne 0 -or -not $Python) { throw 'STOP: Python 3.12 unavailable' }
        $Python = $Python.Trim()
    }
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw 'STOP: Python executable missing'
    }
    & $Python -m py_compile (Join-Path $root 'terminan\server.py') (Join-Path $root 'terminan\monitor.py')
    if ($LASTEXITCODE -ne 0) { throw 'STOP: syntax check failed' }
    & $Python -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw 'STOP: tests failed' }
    Write-Host 'TERMINAN_PREFLIGHT_PASS'
    if ($PreflightOnly) { exit 0 }

    # Do not auto-start Grid, Strattester, a cache worker, PostgreSQL or any service.
    # This launcher intentionally starts only the existing main terminal.
    $listeners = @(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) { throw 'STOP: port 8765 already in use' }
    if ($OpenBrowser) {
        Start-Process 'http://127.0.0.1:8765/' | Out-Null
    }
    & $Python -m terminan
    $rc = $LASTEXITCODE
    Write-Host "TERMINAN_NATIVE_EXIT=$rc"
    exit $rc
}
finally {
    Pop-Location
}
