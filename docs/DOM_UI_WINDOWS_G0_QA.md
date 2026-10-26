# DOM/UI Windows G0 — read-only physical QA protocol

Scope: Terminan Draft PR #7. All test data are offline/synthetic unless a separately authorized source and independently verified provenance exist. Never interpret BookStatus.LIVE as evidence of live exchange L2. Do not trade, change ACLs, write production databases, or deploy.

## Preflight and provenance
1. On Windows, record `git rev-parse HEAD`, `git rev-parse HEAD^{tree}`, `python --version`, `node --version`, browser name/version, Windows build, display resolution, scaling and `$PSVersionTable.PSVersion`.
2. Checkout an immutable tested commit; do not run scripts downloaded from unreviewed branches. Confirm the source SHA matches the target PR HEAD.
3. Confirm loopback-only listener, local port ownership and that no Grid CONTROL listener is displaced. Never expose the server to the LAN.
4. Use a disposable offline fixture and a read-only source. Do not record DSNs, credentials, user profile paths, machine names, account IDs, cookies or raw environment dumps.

## Browser matrix
- Chrome and Edge (current installed versions); 100%, 125%, 150%, 175%, 200% Windows scaling; document actual DPR using browser devtools.
- 1280x720, 1920x1080, 2560x1440 (when supported); maximize/restore, repeated resize and zoom 80%, 100%, 125%.
- Cold start, initial empty state, API failure, slow response, malformed response, instrument switch BTCUSDT→ETHUSDT→BTCUSDT, timeframe switch and checkbox toggles.
- Simulate offline, latency and out-of-order responses in DevTools. Confirm older symbol responses never overwrite the latest selection. Check canvas clarity, clipped labels, scrollbars and absence of stale synthetic data presented as live.
- Inspect console errors, network failed requests, responsiveness, browser process CPU and private memory. Capture at least three 60-second sessions per browser at normal and high DPI; report p50/p95/p99 frame latency, dropped frames, peak RAM, CPU and whether the measurement includes startup. Record observed metrics without invented thresholds or PASS claims.

## Evidence collection
Store screenshots, console export, sanitized network summary, performance traces and test results under a fresh local evidence directory. Redact before hashing and uploading. In PowerShell 5.1/7:
```powershell
Get-ChildItem -LiteralPath .\evidence -File -Recurse |
  Sort-Object FullName |
  ForEach-Object {
    [pscustomobject]@{
      RelativePath = $_.FullName.Substring((Resolve-Path .\evidence).Path.Length + 1)
      Bytes = $_.Length
      SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
  } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 .\manifest.json
```
Include source commit/tree SHA, run ID/attempt/job ID, UTC timestamp, browser version, OS build, DPI, fixture identity, each command's exit code, observed results, and explicitly mark each gate SYNTHETIC_PASS, HOSTED_CI_PASS, PHYSICAL_PASS, FAIL or NOT_RUN. Do not hash a manifest into itself. Recompute hashes after redaction. Avoid uploading raw Chrome trace until inspected for URLs/tokens.

## Stop/rollback
On a wrong interface bind, leaked credential, non-read-only access, browser crash, runaway memory or unknown data provenance, stop the test, preserve redacted evidence and mark FAIL/UNKNOWN. Terminate only the test-owned process. Restore the previous known-good commit and port configuration; do not kill Grid processes, alter services, or perform G1 cleanup.

Physical acceptance is NOT_RUN until signed-off evidence from the user's actual Windows PC is inspected.
