#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExpectedSha,
    [string]$Python = 'python',
    [string]$EvidenceRoot = '.r2-evidence',
    [switch]$OpenBrowser,
    [string]$ReviewSeconds = '0'
)
# Native failures are data to inspect, not shell exceptions. Script scope only.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$code = 50
try {
    $repo = [IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot, '..'))
    $engine = [IO.Path]::Combine($repo, 'terminan', 'r2_harness.py')
    $root = if ([IO.Path]::IsPathRooted($EvidenceRoot)) { [IO.Path]::GetFullPath($EvidenceRoot) } else { [IO.Path]::GetFullPath([IO.Path]::Combine($repo, $EvidenceRoot)) }
    $runId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $arguments = @($engine, '--expected-sha', $ExpectedSha, '--evidence-root', $root, '--review-seconds', $ReviewSeconds, '--run-id', $runId, '--shell-version', $PSVersionTable.PSVersion.ToString())
    if ($OpenBrowser) { $arguments += '--open-browser' }
    & $Python @arguments 2>$null
    $nativeCode = $LASTEXITCODE # Capture before ANY other native command.
    $final = [IO.Path]::Combine($root, $runId)
    if (-not [IO.File]::Exists([IO.Path]::Combine($final, 'summary.json')) -or -not [IO.File]::Exists([IO.Path]::Combine($final, 'manifest.json'))) {
        [Console]::WriteLine('R2 launcher failure_stage=evidence_finalize error_class=EVIDENCE_UNAVAILABLE exit_code=50')
    } else {
        & $Python $engine --inspect-run --expected-sha $ExpectedSha --evidence-root $root --run-id $runId 2>$null
        $evidenceCode = $LASTEXITCODE
        $allowed = @(0,10,20,30,31,32,33,40,50)
        if ($allowed -contains $nativeCode -and $nativeCode -eq $evidenceCode) {
            $code = [int]$nativeCode
        } else {
            [Console]::WriteLine('R2 launcher failure_stage=evidence_finalize error_class=EXIT_CODE_MISMATCH exit_code=50')
        }
    }
} catch {
    # Never emit ErrorRecord, exception message, executable/path or raw stderr.
    $code = 50
    [Console]::WriteLine('R2 launcher failure_stage=preflight error_class=LAUNCHER_ERROR exit_code=50')
}
$global:LASTEXITCODE = $code
exit $code
