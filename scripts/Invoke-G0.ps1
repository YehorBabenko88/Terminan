#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{40}$')][string]$ExpectedSha,
    [string]$Python = 'python',
    [string]$EvidenceRoot = '.g0-evidence',
    [switch]$OpenBrowser,
    [ValidateRange(0,3600)][int]$ReviewSeconds = 0
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$code = 10
$child = $null
$evidence = $null
$savedLocation = Get-Location
try {
    Set-Location -LiteralPath $repo
    $sha = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $sha -cne $ExpectedSha) { throw 'Source SHA mismatch' }
    $dirty = & git status --porcelain --untracked-files=normal
    if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Clean checkout required' }
    $version = & $Python -c 'import sys; print(sys.version.split()[0]); sys.exit(sys.version_info < (3,11))'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ required' }
    # No admin check: no privileged operation is performed, and hosted CI may be
    # elevated. The operator runbook requires an ordinary non-admin shell.
    $root = [IO.Path]::GetFullPath((Join-Path $repo $EvidenceRoot))
    $evidence = Join-Path $root ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
    New-Item -ItemType Directory -Path $evidence -Force | Out-Null
    $ready = Join-Path $evidence 'ready.json'
    if ($ready.Contains('"')) { throw 'Unsupported evidence path' }
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = (Get-Command $Python -ErrorAction Stop).Source
    $info.Arguments = '-m terminan.g0_runner --ready "' + $ready + '"'
    $info.WorkingDirectory = $repo
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($key in @($info.EnvironmentVariables.Keys)) {
        if ($key -like 'TERMINAN_*') { $info.EnvironmentVariables.Remove($key) }
    }
    $child = New-Object System.Diagnostics.Process
    $child.StartInfo = $info
    $code = 20
    if (-not $child.Start()) { throw 'Child startup failed' }
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    while (-not (Test-Path -LiteralPath $ready)) {
        if ($child.HasExited -or [DateTime]::UtcNow -gt $deadline) { throw 'Child readiness timeout' }
        Start-Sleep -Milliseconds 100
    }
    $state = Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json
    if ($state.host -ne '127.0.0.1' -or $state.port -lt 1 -or $state.port -gt 65535) { throw 'Invalid listener' }
    $url = 'http://127.0.0.1:' + $state.port
    $code = 30
    $smoke = @()
    foreach ($route in @('/api/status','/api/sources?symbol=BTCUSDT','/api/candles?symbol=BTCUSDT','/api/grid/footprint?symbol=BTCUSDT','/api/research?symbol=BTCUSDT','/api/levels?diagnostics=1','/')) {
        $response = Invoke-WebRequest -UseBasicParsing -Uri ($url + $route) -TimeoutSec 15
        if ($response.StatusCode -ne 200) { throw 'Smoke HTTP failure' }
        if ($route -like '/api/sources*') {
            $sources = $response.Content | ConvertFrom-Json
            if ($sources.state -ne 'NOT_CONFIGURED' -or $sources.l2 -ne 'UNAVAILABLE') { throw 'Source isolation failure' }
        }
        $smoke += [ordered]@{ route=$route; status=[int]$response.StatusCode }
    }
    $smoke | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'smoke.json') -Encoding UTF8
    $checklist = @"
PHYSICAL REVIEW PENDING. Automated API smoke is not physical PASS.
Candidate: $sha
Open $url while harness is running (ReviewSeconds).
Record browser/version, DPR 100/150/200%, resize, rapid symbol/timeframe switching,
refresh cancellation, console errors, disconnected sources, no fabricated DOM,
historical/footprint labels, stale/GAP recovery via synthetic tests, bounded UI.
Save redacted screenshots and performance observations separately; remove machine
names, usernames, paths, private network addresses, DB URLs, tokens and account IDs.
Do not enable sources, exchange streams or orders. Stop browser after review.
"@
    $checklist | Set-Content -LiteralPath (Join-Path $evidence 'browser-checklist.txt') -Encoding UTF8
    Write-Host ('G0 disconnected UI: ' + $url)
    if ($OpenBrowser) { Start-Process $url | Out-Null }
    $until = [DateTime]::UtcNow.AddSeconds($ReviewSeconds)
    while ([DateTime]::UtcNow -lt $until) {
        if ($child.HasExited) { throw 'Child exited during review' }
        Start-Sleep -Milliseconds 250
    }
    $code = 40
    $child.StandardInput.WriteLine('quit')
    $child.StandardInput.Close()
    if (-not $child.WaitForExit(10000)) { throw 'Graceful shutdown timeout' }
    if ($child.ExitCode -ne 0) { throw 'Child exit failure' }
    # Never persist raw stderr/stdout: an unexpected library error may include paths.
    $rawError = $child.StandardError.ReadToEnd()
    if ($rawError.Length -gt 0) { throw 'Child reported an error (raw output withheld)' }
    $code = 0
} catch {
    Write-Host ('G0 failed; exit code ' + $code + '. Raw exception withheld for privacy.')
} finally {
    if ($child) {
        if (-not $child.HasExited) {
            try { $child.StandardInput.WriteLine('quit'); $child.StandardInput.Close() } catch {}
            if (-not $child.WaitForExit(10000)) { $child.Kill(); $child.WaitForExit(); if ($code -eq 0) { $code=40 } }
        }
        $child.Dispose()
    }
    if ($evidence) {
        $summary = [ordered]@{ candidate_sha=$ExpectedSha; utc=[DateTime]::UtcNow.ToString('o'); exit_code=$code; result=$(if($code -eq 0){'AUTOMATED_SMOKE_PASS'}else{'FAIL'}); physical='PENDING'; python="$version"; powershell=$PSVersionTable.PSVersion.ToString(); machine='REDACTED'; sources='DISCONNECTED' }
        $summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'summary.json') -Encoding UTF8
        $manifest = @(Get-ChildItem -LiteralPath $evidence -File | Sort-Object Name | ForEach-Object {
            [ordered]@{ file=$_.Name; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); bytes=$_.Length }
        })
        $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'manifest.json') -Encoding UTF8
        Write-Host ('Evidence: ' + $evidence)
    }
    Set-Location -LiteralPath $savedLocation
}
exit $code
