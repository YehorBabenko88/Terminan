#requires -Version 5.1
<#
Read-only G0 evidence preflight. No service launch, DB access, ACL or system mutation.
Usage: powershell -NoProfile -File .\tools\g0_evidence_preflight.ps1 -EvidenceDir C:\g0-evidence
Exit: 0 completed preflight; 10 missing dependency; 20 unsafe listener; 60 evidence failure.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$EvidenceDir,
    [int[]]$Ports = @(8765,8766),
    [string]$PythonCommand = 'python'
)
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$exitCode = 0
function Fail([int]$code, [string]$reason) {
    if ($script:exitCode -eq 0) { $script:exitCode = $code }
    $script:checks.Add([ordered]@{ name='error'; status='FAIL'; detail=$reason })
}
function Sha([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
$checks = New-Object System.Collections.ArrayList
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
try {
    $target = [System.IO.Path]::GetFullPath($EvidenceDir)
    if ($target.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'EvidenceDir must be outside the source checkout'
    }
    if ($Ports.Count -eq 0 -or @($Ports | Where-Object { $_ -lt 1 -or $_ -gt 65535 }).Count -gt 0) {
        throw 'Ports must be in range 1..65535'
    }
    if (Test-Path -LiteralPath $target) {
        if (@(Get-ChildItem -LiteralPath $target -Force).Count -gt 0) {
            throw 'EvidenceDir must be empty to avoid overwriting evidence'
        }
    } else { New-Item -ItemType Directory -Path $target -Force | Out-Null }
    $commit = (& git -C $repoRoot rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or $commit -notmatch '^[0-9a-f]{40}$') { throw 'Cannot pin git commit' }
    $tree = (& git -C $repoRoot rev-parse 'HEAD^{tree}' 2>$null)
    if ($LASTEXITCODE -ne 0 -or $tree -notmatch '^[0-9a-f]{40}$') { throw 'Cannot pin git tree' }
    $dirty = (& git -C $repoRoot status --porcelain --untracked-files=no 2>$null)
    $checks.Add([ordered]@{name='source_clean';status=$(if ($dirty) {'FAIL'} else {'PASS'});detail='Tracked working tree only'}) | Out-Null
    if ($dirty) { $exitCode = 10 }
    $psVersion = $PSVersionTable.PSVersion.ToString()
    $checks.Add([ordered]@{name='powershell';status='PASS';version=$psVersion}) | Out-Null
    $pythonVersion = (& $PythonCommand -c 'import sys; print(".".join(map(str,sys.version_info[:3])))' 2>$null)
    if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
        Fail 10 'Python interpreter unavailable or version malformed'
    } elseif ([int]$Matches[1] -lt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -lt 11)) {
        Fail 10 'Python 3.11+ required'
    } else {
        $checks.Add([ordered]@{name='python';status='PASS';version=$pythonVersion}) | Out-Null
    }
    $listenerChecks = New-Object System.Collections.ArrayList
    foreach ($port in ($Ports | Sort-Object -Unique)) {
        $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
        $addresses = @($listeners | ForEach-Object { $_.LocalAddress } | Sort-Object -Unique)
        $unsafe = @($addresses | Where-Object { $_ -notin @('127.0.0.1','::1') })
        $state = if ($unsafe.Count -gt 0) { 'FAIL' } elseif ($addresses.Count -eq 0) { 'UNBOUND' } else { 'LOOPBACK_ONLY' }
        if ($unsafe.Count -gt 0) { if ($exitCode -eq 0) { $exitCode = 20 } }
        $listenerChecks.Add([ordered]@{port=$port;state=$state;addresses=$addresses}) | Out-Null
    }
    $checks.Add([ordered]@{name='port_listeners';status=$(if ($exitCode -eq 20) {'FAIL'} else {'OBSERVED'});ports=@($listenerChecks)}) | Out-Null
    $browserChecks = New-Object System.Collections.ArrayList
    foreach ($browser in @('chrome.exe','msedge.exe')) {
        $found = @(Get-Command $browser -ErrorAction SilentlyContinue).Count -gt 0
        $browserChecks.Add([ordered]@{browser=$browser;on_path=$found;physical_browser_test='NOT_RUN'}) | Out-Null
    }
    $checks.Add([ordered]@{name='browser_discovery';status='OBSERVED';browsers=@($browserChecks)}) | Out-Null
    $payload = [ordered]@{
        schema_version='g0-evidence-v1'
        classification='PHYSICAL_NOT_VERIFIED'
        source=[ordered]@{terminan_commit=$commit;terminan_tree=$tree;grid_commit=$null;strattester_commit=$null}
        environment=[ordered]@{powershell=$psVersion;python=$pythonVersion}
        checks=@($checks)
        physical_gates='NOT_RUN'
        privacy_redaction='PASS_FOR_STRUCTURED_PREFLIGHT_ONLY'
    }
    $json = ConvertTo-Json -InputObject $payload -Depth 12
    $json = ($json -replace "`r`n", "`n") + "`n"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $manifest = Join-Path $target 'manifest.json'
    [System.IO.File]::WriteAllText($manifest,$json,$utf8)
    [System.IO.File]::WriteAllText((Join-Path $target 'manifest.sha256'),((Sha $manifest) + "  manifest.json`n"),$utf8)
    Write-Output ("G0 preflight exit code: " + $exitCode)
    Write-Output ("Evidence: " + $target)
} catch {
    Write-Error ('G0 preflight aborted: ' + $_.Exception.Message) -ErrorAction Continue
    if ($exitCode -eq 0) { $exitCode = 60 }
}
exit $exitCode
