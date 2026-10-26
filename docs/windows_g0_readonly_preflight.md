# Windows G0 — read-only Terminan preflight (2026-10-26)

The integrated executable harness and current acceptance/rollback procedure are
in [physical-g0-release.md](physical-g0-release.md). The original manual procedure
below is retained for PR #8 provenance; use the integrated harness for PR #9.

This procedure is **physical evidence collection**, not production commissioning. It does not execute G1, install software, change services, change ACLs, connect databases or enable trading. Use only an isolated checkout of a pinned commit. All reported results are **NOT_RUN** until executed on the real Windows PC.

## Initial preflight (Windows PowerShell 5.1 / 7)

Open an **ordinary non-administrator** PowerShell terminal. Run from a clean checkout of the chosen immutable release-candidate SHA, not a mutable branch name.

```powershell
$ErrorActionPreference = 'Stop'
$ExpectedSha = '<FULL_40_CHARACTER_CANDIDATE_SHA>'
$ActualSha = (git rev-parse HEAD).Trim()
if ($ActualSha -cne $ExpectedSha) { throw 'STOP: HEAD does not match expected immutable SHA' }
if ((git status --porcelain).Count -ne 0) { throw 'STOP: worktree is not clean' }
$Py = python -c "import sys; print(sys.version_info.major, sys.version_info.minor)"
if ($LASTEXITCODE -ne 0 -or $Py -notmatch '^3 (1[1-9]|[2-9][0-9])$') { throw 'STOP: Python 3.11+ required' }
$PSVersionTable.PSVersion.ToString()
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'STOP: offline unit tests failed' }
```

Do not copy DSNs, tokens, process command lines, usernames or environment-variable values into public evidence. On PC4/LS5, make sure no services or production database paths are touched.

## Isolated UI-only smoke

Unset inherited source paths and DSNs **in the test process environment only**; do not modify machine-wide variables. On an unused loopback port, run a pinned candidate that already implements `TERMINAN_PORT` (PR #5 or a verified descendant).

```powershell
$env:TERMINAN_HOST = '127.0.0.1'
$env:TERMINAN_PORT = '18765'
Remove-Item Env:TERMINAN_GRID_DSN -ErrorAction SilentlyContinue
Remove-Item Env:TERMINAN_STRATTESTER_DB -ErrorAction SilentlyContinue
Remove-Item Env:TERMINAN_RESULTS_DB -ErrorAction SilentlyContinue
$Existing = Get-NetTCPConnection -LocalPort 18765 -State Listen -ErrorAction SilentlyContinue
if ($Existing) { throw 'STOP: test port 18765 already occupied' }
python -m terminan
```

Open a **second** non-administrator PowerShell window (same machine) to validate the local HTTP surface:

```powershell
$Base = 'http://127.0.0.1:18765'
foreach ($Path in @('/', '/monitor', '/api/status', '/api/instruments', '/api/candles?symbol=BTCUSDT&timeframe=1m', '/api/grid/footprint?symbol=BTCUSDT', '/api/research?symbol=BTCUSDT')) {
  $Response = Invoke-WebRequest -Uri ($Base + $Path) -UseBasicParsing -TimeoutSec 5
  '{0} {1}' -f $Response.StatusCode, $Path
}
```

Expected: HTML for `/` and `/monitor`, bounded JSON for API routes, `READ_ONLY` for status and empty source lists while all source configuration is absent. Verify locally that listening addresses are loopback-only. Do not declare LIVE market data or working Grid/Strattester integration when disconnected.

Check in Edge/Chrome: UI renders, `/monitor` renders, selection and refresh are not broken, no credential output in devtools/network, and SOURCE_NOT_CONNECTED is clear. Any blank page, 5xx, non-loopback listener or unexpected source access is a BLOCK.

Stop the foreground Python process using Ctrl+C; confirm the listener is gone. Do not kill unrelated processes.

## Evidence checklist

Record manually in a private folder: UTC timestamp, exact SHA for Terminan/Grid/Strattester, OS and PowerShell/Python versions (without username/hostname), local listener test, individual endpoint status codes, test command and exit code, screenshots with privacy masking, startup/shutdown results, and SHA256 hashes of sanitized evidence. Before uploading verify no DSN, tokens, local paths, credentials, computer name, PID or personal data are present.

`PHYSICAL_PASS` requires evidence from an actual Windows system; standalone unit tests and hosted Actions are not equivalent. No merge or deployment is authorized by this procedure.
