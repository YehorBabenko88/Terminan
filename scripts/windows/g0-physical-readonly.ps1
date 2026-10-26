# G0 isolated Windows smoke. PS 5.1/7; no production source adapters.
[CmdletBinding()]
param([ValidateSet(8765,8766)][int]$Port=8766,
      [string]$EvidenceDir='',
      [string]$PythonExe='python',
      [switch]$Browser)
$ErrorActionPreference='Stop'
$stage='init'
$failure='NONE'
$cleanup='NOT_RUN'
$child=$null
$ownedPid=0
$started=[DateTime]::UtcNow
$checks=New-Object System.Collections.ArrayList
function Record([string]$Name,[string]$Status,[string]$Detail) {
  [void]$checks.Add([ordered]@{name=$Name;status=$Status;detail=$Detail})
}
function VerifiedOwner([int]$ListenerPid,[int]$RootPid,[DateTime]$StartedUtc) {
  $seen=@{}
  $pidNow=$ListenerPid
  for($depth=0;$depth -lt 6;$depth++){
    if($seen.ContainsKey([string]$pidNow)){return $false}
    $seen[[string]$pidNow]=$true
    $p=Get-CimInstance Win32_Process -Filter ("ProcessId="+$pidNow) -ErrorAction Stop
    if($null -eq $p -or $p.Name -ne 'python.exe'){return $false}
    if($p.CommandLine -notmatch '(^|\s)-m\s+terminan(\s|$)'){return $false}
    $created=([DateTime]$p.CreationDate).ToUniversalTime()
    if($created -lt $StartedUtc.AddSeconds(-5)){return $false}
    if($pidNow -eq $RootPid){return $true}
    $pidNow=[int]$p.ParentProcessId
  }
  return $false
}
function Listeners([int]$P) {
  @(Get-NetTCPConnection -State Listen -LocalPort $P -ErrorAction SilentlyContinue)
}
if(-not $EvidenceDir){$EvidenceDir=Join-Path ([IO.Path]::GetTempPath()) ('terminan-g0-'+[guid]::NewGuid().ToString('N'))}
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
try {
  $stage='git_sha'
  $root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
  $sha=(& git -C $root rev-parse HEAD 2>$null)
  if($LASTEXITCODE -ne 0 -or $sha -notmatch '^[a-f0-9]{40}$'){throw 'gate'}
  Record 'source_sha' 'PASS' $sha
  $stage='clean_checkout'
  $dirty=@(& git -C $root status --porcelain --untracked-files=all)
  if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){throw 'gate'}
  Record $stage 'PASS' 'clean'
  $stage='python_version'
  $version=& $PythonExe -c "import sys;print('.'.join(map(str,sys.version_info[:3])));sys.exit(0 if sys.version_info[:2]>=(3,11) else 1)" 2>$null
  if($LASTEXITCODE -ne 0){throw 'gate'}
  Record $stage 'PASS' ([string]$version)
  $stage='port_preflight'
  if((Listeners $Port).Count -ne 0){throw 'gate'}
  Record $stage 'PASS' 'free'
  $stage='start_child'
  $launchUtc=[DateTime]::UtcNow
  $psi=New-Object Diagnostics.ProcessStartInfo
  $psi.FileName=$PythonExe
  $psi.Arguments='-m terminan'
  $psi.WorkingDirectory=$root
  $psi.UseShellExecute=$false
  $psi.CreateNoWindow=$true
  $psi.EnvironmentVariables['TERMINAN_HOST']='127.0.0.1'
  $psi.EnvironmentVariables['TERMINAN_PORT']=[string]$Port
  $psi.EnvironmentVariables['PYTHONDONTWRITEBYTECODE']='1'
  foreach($key in @('TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB','TERMINAN_GRID_DSN')){[void]$psi.EnvironmentVariables.Remove($key)}
  $child=[Diagnostics.Process]::Start($psi)
  if($null -eq $child){throw 'gate'}
  $ownedPid=$child.Id
  Record $stage 'PASS' 'child created (PID redacted)'
  $stage='readiness'
  $base='http://127.0.0.1:'+$Port
  $ready=$false
  for($i=0;$i -lt 40;$i++){
    if($child.HasExited){throw 'gate'}
    try {
      $r=Invoke-WebRequest -Uri ($base+'/') -UseBasicParsing -TimeoutSec 2
      if($r.StatusCode -eq 200){$ready=$true;break}
    }catch{}
    Start-Sleep -Milliseconds 250
  }
  if(-not $ready){throw 'gate'}
  Record $stage 'PASS' 'HTTP 200'
  $stage='listener_identity'
  $listeners=@(Listeners $Port)
  if($listeners.Count -ne 1 -or $listeners[0].LocalAddress -ne '127.0.0.1' -or -not (VerifiedOwner ([int]$listeners[0].OwningProcess) $ownedPid $launchUtc)){throw 'gate'}
  $listenerPid=[int]$listeners[0].OwningProcess
  Record $stage 'PASS' 'verified descendant owns 127.0.0.1 listener'
  $stage='http_smoke'
  foreach($endpoint in @('/','/api/status','/api/instruments','/api/candles?symbol=BTCUSDT&timeframe=1m','/api/grid/footprint?symbol=BTCUSDT')){
    $r=Invoke-WebRequest -Uri ($base+$endpoint) -UseBasicParsing -TimeoutSec 5
    if($r.StatusCode -ne 200){throw 'gate'}
    Record ('GET '+$endpoint) 'PASS' 'HTTP 200; body omitted'
  }
  $stage='source_isolation'
  $status=Invoke-RestMethod -Uri ($base+'/api/status') -TimeoutSec 5
  if($status.mode -ne 'READ_ONLY' -or $status.grid -ne $false -or $status.strattester -ne $false -or $status.research -ne $false){throw 'gate'}
  Record $stage 'PASS' 'READ_ONLY; source adapters disabled'
  $stage='browser'
  if($Browser){
    Start-Process ($base+'/')
    Record $stage 'NOT_RUN' 'Manual UI and console evidence not captured'
    Write-Host 'Inspect browser; press Enter here to end G0 smoke.'
    [void](Read-Host)
  }else{Record $stage 'NOT_RUN' 'Manual UI and console evidence not captured'}
}catch{
  $failure=$stage
  Record $stage 'FAIL' 'Gate failed; raw exception omitted'
}finally{
  if($null -ne $child -and -not $child.HasExited){
    try {
      $stage='shutdown_identity'
      $listeners=@(Listeners $Port)
      $proc=Get-CimInstance Win32_Process -Filter ("ProcessId="+$ownedPid) -ErrorAction Stop
      if($null -eq $proc -or $proc.Name -ne 'python.exe' -or $proc.CommandLine -notmatch '(^|\s)-m\s+terminan(\s|$)'){throw 'identity'}
      if($listeners.Count -ne 1 -or $listeners[0].LocalAddress -ne '127.0.0.1'){throw 'listener'}
      $livePid=[int]$listeners[0].OwningProcess
      if(-not (VerifiedOwner $livePid $ownedPid $launchUtc)){throw 'provenance'}
      $stage='forced_shutdown'
      if($livePid -ne $ownedPid){
        Stop-Process -Id $livePid -ErrorAction Stop
      }
      if(-not $child.HasExited){$child.Kill()}
      if(-not $child.WaitForExit(5000)){throw 'timeout'}
      $cleanup='PASS'
      Record 'forced_shutdown' 'PASS' 'Verified child terminated; not graceful'
    }catch{
      $cleanup='FAIL'
      Record $stage 'FAIL' 'Cleanup gate failed; no other process touched'
    }
  }
  $remaining=@(Listeners $Port)
  if($remaining.Count -eq 0){Record 'port_released' 'PASS' 'No listener'}
  else{Record 'port_released' 'FAIL' 'Port still listening';$cleanup='FAIL'}
  $exitCode=0
  if($failure -ne 'NONE'){$exitCode=2}
  if($cleanup -eq 'FAIL'){$exitCode=3}
  $manifest=[ordered]@{
    schema='terminan-g0-v4'
    classification='PHYSICAL_EVIDENCE_PENDING_INDEPENDENT_REVIEW'
    started_utc=$started.ToString('o')
    finished_utc=[DateTime]::UtcNow.ToString('o')
    port=$Port
    powershell=$PSVersionTable.PSVersion.ToString()
    failure_stage=$failure
    cleanup_status=$cleanup
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
