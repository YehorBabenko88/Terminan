# Windows G0 isolated read-only smoke. PowerShell 5.1 / 7.
[CmdletBinding()]
param(
  [ValidateSet(8765,8766)][int]$Port=8766,
  [string]$EvidenceDir='',
  [string]$PythonExe='python',
  [switch]$Browser
)
$ErrorActionPreference='Stop'
$exitCode=2
$child=$null
$started=[DateTime]::UtcNow
$checks=New-Object System.Collections.ArrayList
function Add-Check([string]$Name,[string]$Status,[string]$Detail) {
  [void]$checks.Add([ordered]@{name=$Name;status=$Status;detail=$Detail})
}
if(-not $EvidenceDir) {
  $EvidenceDir=Join-Path ([IO.Path]::GetTempPath()) ('terminan-g0-'+[guid]::NewGuid().ToString('N'))
}
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
try {
  $root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
  $sha=(& git -C $root rev-parse HEAD 2>$null)
  if($LASTEXITCODE -ne 0 -or $sha -notmatch '^[a-f0-9]{40}$'){throw 'git_sha'}
  Add-Check 'source_sha' 'PASS' $sha
  # Python bytecode cache is excluded via .gitignore; all other changes block.
  $dirty=@(& git -C $root status --porcelain --untracked-files=all)
  if($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0){throw 'dirty_checkout'}
  Add-Check 'clean_checkout' 'PASS' 'tracked and non-cache untracked files clean'
  $version=& $PythonExe -c "import sys; print('.'.join(map(str,sys.version_info[:3])));sys.exit(0 if sys.version_info[:2]>=(3,11) else 1)" 2>$null
  if($LASTEXITCODE -ne 0){throw 'python_version'}
  Add-Check 'python' 'PASS' ([string]$version)
  $existing=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
  if($existing.Count -ne 0){throw 'port_in_use'}
  Add-Check 'port_preflight' 'PASS' 'free'
  $psi=New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName=$PythonExe
  $psi.Arguments='-m terminan'
  $psi.WorkingDirectory=$root
  $psi.UseShellExecute=$false
  $psi.CreateNoWindow=$true
  $psi.EnvironmentVariables['TERMINAN_HOST']='127.0.0.1'
  $psi.EnvironmentVariables['TERMINAN_PORT']=[string]$Port
  foreach($k in @('TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB','TERMINAN_GRID_DSN')){
    [void]$psi.EnvironmentVariables.Remove($k)
  }
  $child=[Diagnostics.Process]::Start($psi)
  if($null -eq $child){throw 'child_start'}
  $base='http://127.0.0.1:'+$Port
  $ready=$false
  for($i=0;$i -lt 30;$i++){
    if($child.HasExited){throw 'child_exited'}
    try{
      $r=Invoke-WebRequest -Uri ($base+'/') -UseBasicParsing -TimeoutSec 2
      if($r.StatusCode -eq 200){$ready=$true;break}
    }catch{}
    Start-Sleep -Milliseconds 250
  }
  if(-not $ready){throw 'readiness_timeout'}
  $listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop)
  if($listeners.Count -ne 1){throw 'listener_count'}
  if($listeners[0].LocalAddress -ne '127.0.0.1' -or $listeners[0].OwningProcess -ne $child.Id){throw 'listener_identity'}
  Add-Check 'loopback_owned_listener' 'PASS' '127.0.0.1 only; owned by child'
  foreach($endpoint in @('/','/api/status','/api/instruments','/api/candles?symbol=BTCUSDT&timeframe=1m','/api/grid/footprint?symbol=BTCUSDT')){
    $r=Invoke-WebRequest -Uri ($base+$endpoint) -UseBasicParsing -TimeoutSec 5
    if($r.StatusCode -ne 200){throw 'http_status'}
    Add-Check ('GET '+$endpoint) 'PASS' 'HTTP 200; body not retained'
  }
  $status=Invoke-RestMethod -Uri ($base+'/api/status') -TimeoutSec 5
  if($status.mode -ne 'READ_ONLY' -or $status.grid -ne $false -or $status.strattester -ne $false -or $status.research -ne $false){throw 'source_isolation'}
  Add-Check 'source_isolation' 'PASS' 'READ_ONLY; all source adapters disabled'
  if($Browser){
    Start-Process ($base+'/')
    Add-Check 'browser_visual' 'NOT_RUN' 'Manual inspection required; screenshot not collected'
    Write-Host 'Browser opened. Inspect UI/console, then press Enter to stop the isolated child.'
    [void](Read-Host)
  }else{
    Add-Check 'browser_visual' 'NOT_RUN' 'Manual inspection required'
  }
  $exitCode=0
}catch{
  # No raw exception: may include private paths, environment or endpoint data.
  Add-Check 'g0_smoke' 'FAIL' 'A gate failed; raw errors intentionally redacted'
  $exitCode=2
}finally{
  if($null -ne $child){
    if(-not $child.HasExited){
      try{
        $listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
        if($listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $child.Id -or $listeners[0].LocalAddress -ne '127.0.0.1'){throw 'ownership_changed'}
        # Forced stop only. Never claim graceful shutdown.
        $child.Kill()
        if(-not $child.WaitForExit(5000)){throw 'shutdown_timeout'}
        Add-Check 'controlled_forced_shutdown' 'PASS' 'Owned child exited; NOT graceful'
      }catch{
        Add-Check 'controlled_forced_shutdown' 'FAIL' 'Ownership or exit verification failed'
        $exitCode=3
      }
    }else{Add-Check 'controlled_forced_shutdown' 'NOT_RUN' 'Child exited independently'}
  }
  $remaining=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
  if($remaining.Count -eq 0){Add-Check 'port_released' 'PASS' 'No listener'}
  else{Add-Check 'port_released' 'FAIL' 'Listener remains';$exitCode=3}
  $manifest=[ordered]@{
    schema='terminan-g0-v2'
    classification='PHYSICAL_EVIDENCE_PENDING_INDEPENDENT_REVIEW'
    started_utc=$started.ToString('o')
    finished_utc=[DateTime]::UtcNow.ToString('o')
    port=$Port
    powershell=$PSVersionTable.PSVersion.ToString()
    checks=@($checks)
    exit_code=$exitCode
    graceful_shutdown='NOT_RUN'
    production_integration='NOT_RUN'
  }
  $path=Join-Path $EvidenceDir 'manifest.json'
  $manifest|ConvertTo-Json -Depth 8|Set-Content -Path $path -Encoding UTF8
  $hash=(Get-FileHash -Algorithm SHA256 $path).Hash.ToLowerInvariant()
  Set-Content -Path (Join-Path $EvidenceDir 'manifest.sha256') -Encoding Ascii -Value ($hash+'  manifest.json')
  Write-Host ('G0 exit='+$exitCode+' evidence='+$EvidenceDir)
}
exit $exitCode
