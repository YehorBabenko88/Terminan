# G0 read-only Windows smoke; PowerShell 5.1/7. No production adapters.
[CmdletBinding()]
param([ValidateSet(8765,8766)][int]$Port=8766,[string]$EvidenceDir="",[switch]$Browser)
$ErrorActionPreference='Stop'
$code=1
$child=$null
$start=Get-Date
if(-not $EvidenceDir){$EvidenceDir=Join-Path ([IO.Path]::GetTempPath()) ("terminan-g0-"+[guid]::NewGuid().ToString('N'))}
New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null
$checks=New-Object System.Collections.ArrayList
function Record($name,$status,$detail){[void]$checks.Add([ordered]@{name=$name;status=$status;detail=$detail})}
try {
  $root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
  $sha=(& git -C $root rev-parse HEAD 2>$null)
  if($LASTEXITCODE -ne 0 -or $sha -notmatch '^[a-f0-9]{40}$'){throw 'Git HEAD unavailable'}
  Record 'source_sha' 'PASS' $sha
  $py=& python -c "import sys;print('.'.join(map(str,sys.version_info[:3])));sys.exit(0 if sys.version_info[:2]>=(3,11) else 1)" 2>$null
  if($LASTEXITCODE -ne 0){throw 'Python 3.11+ required'}
  Record 'python' 'PASS' $py
  $listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
  if($listeners.Count -gt 0){throw "Port $Port already in use; will not stop another process"}
  Record 'port_preflight' 'PASS' ("port "+$Port+" free")
  $psi=New-Object Diagnostics.ProcessStartInfo
  $psi.FileName='python';$psi.Arguments='-m terminan'
  $psi.WorkingDirectory=$root
  $psi.UseShellExecute=$false
  $psi.CreateNoWindow=$true
  $psi.EnvironmentVariables['TERMINAN_HOST']='127.0.0.1'
  $psi.EnvironmentVariables['TERMINAN_PORT']=[string]$Port
  foreach($k in @('TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB','TERMINAN_GRID_DSN')){$psi.EnvironmentVariables.Remove($k)}
  $child=[Diagnostics.Process]::Start($psi)
  $ready=$false
  for($i=0;$i -lt 40;$i++){
    Start-Sleep -Milliseconds 250
    if($child.HasExited){throw 'Terminan exited before readiness'}
    try {
      $r=Invoke-WebRequest -Uri ("http://127.0.0.1:"+$Port+"/") -UseBasicParsing -TimeoutSec 2
      if($r.StatusCode -eq 200){$ready=$true;break}
    }catch{}
  }
  if(-not $ready){throw 'HTTP readiness timeout'}
  Record 'http_root' 'PASS' 'HTTP 200 (body not recorded)'
  $listeners=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop)
  if($listeners.Count -eq 0){throw 'No listener after readiness'}
  foreach($l in $listeners){
    if($l.OwningProcess -ne $child.Id){throw 'Listener not owned by harness child'}
    if($l.LocalAddress -notin @('127.0.0.1','::1')){throw 'Non-loopback listener detected'}
  }
  Record 'loopback_binding' 'PASS' 'owned listener restricted to loopback'
  if($Browser){Start-Process ("http://127.0.0.1:"+$Port+"/");Record 'browser_visual' 'NOT_RUN' 'manual screenshots and console review required'}
  else{Record 'browser_visual' 'NOT_RUN' 'manual browser acceptance required'}
  $code=0
}catch{
  Record 'harness' 'FAIL' 'Preflight, startup or HTTP verification failed; details withheld to avoid secret leakage'
  $code=2
}finally{
  if($null -ne $child -and -not $child.HasExited){
    try{$child.Kill();$child.WaitForExit(5000)|Out-Null;Record 'shutdown' 'PASS' 'harness-owned child stopped'}catch{Record 'shutdown' 'FAIL' 'child shutdown failed';$code=3}
  }
  $manifest=[ordered]@{schema='terminan-g0-v1';classification='PHYSICAL_EVIDENCE_PENDING_REVIEW';utc=$start.ToUniversalTime().ToString('o');port=$Port;pwsh=$PSVersionTable.PSVersion.ToString();checks=@($checks);exit_code=$code;sha256=@{}}
  $path=Join-Path $EvidenceDir 'manifest.json'
  $manifest|ConvertTo-Json -Depth 8|Set-Content -Path $path -Encoding UTF8
  $hash=(Get-FileHash -Algorithm SHA256 $path).Hash.ToLowerInvariant()
  Set-Content -Path (Join-Path $EvidenceDir 'manifest.sha256') -Value ($hash+'  manifest.json') -Encoding Ascii
  Write-Host ('G0 exit='+$code+' evidence='+$EvidenceDir)
}
exit $code
