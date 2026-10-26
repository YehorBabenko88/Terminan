# Windows G0 browser evidence (synthetic, not physical acceptance)

This tool is a read-only, headless smoke test for a **separately started** Terminan on loopback. It does not start services, install dependencies, access Grid/Strattester databases, or claim LIVE L2 or physical PASS.

## Run from an unprivileged PowerShell session

Use a pinned integration candidate containing the validated port override (PR #5); **main does not necessarily support this override**. Verify `git rev-parse HEAD` and `git status --porcelain` before testing. Do not set source DB/DSN variables. With an approved candidate only:

```powershell
$env:TERMINAN_PORT = '18765'
Remove-Item Env:TERMINAN_GRID_DSN -ErrorAction SilentlyContinue
Remove-Item Env:TERMINAN_STRATTESTER_DB -ErrorAction SilentlyContinue
Remove-Item Env:TERMINAN_RESULTS_DB -ErrorAction SilentlyContinue
python -m terminan
```

In a **second** terminal, after confirming `http://127.0.0.1:18765/` serves the expected candidate:

```powershell
python -m pip install playwright
python -m playwright install chromium
python tools/windows_browser_g0.py --browser chromium --url http://127.0.0.1:18765/ --output evidence-chrome
python tools/windows_browser_g0.py --browser msedge --url http://127.0.0.1:18765/ --output evidence-edge
Get-FileHash evidence-chrome/manifest.json -Algorithm SHA256
Get-FileHash evidence-edge/manifest.json -Algorithm SHA256
```

Do not overwrite existing evidence directories. Keep source DBs disconnected. Browser download/install is a preparation step, not part of the read-only G0 execution. Use an already installed browser where required by local policy. No trading, DB writes, ACL changes, deployment or G1 cleanup.

## Manual physical checklist (Chrome and Edge separately)

Record browser version, Windows version, exact candidate commit/tree SHA, timestamp and anonymized screenshots. Verify startup and no blank screen; select two symbols quickly while throttling responses and ensure older results never overwrite newer; change each supported timeframe; refresh repeatedly; resize 800x600/1280x800/1920x1080; test Windows display scaling 100/150/200%; inspect browser console and network panel for errors and unexpected external requests. Capture rendering latency distribution, FPS, CPU and RAM from browser performance tools. Test offline, STALE, GAP and reconnect **only with an approved isolated synthetic fixture**, never by disturbing a production feed. Check graceful shutdown and port conflicts. Redact usernames, tokens, DSNs, account IDs, hostnames, local paths and research records before publication.

## Interpretation

`SYNTHETIC_SMOKE_PASS` means only that a headless browser loaded the loopback UI with expected controls, screenshots, reload and no captured JS console errors. It does not establish physical Windows PASS, performance targets, correct symbol switching, LIVE market data or integration readiness. `FAIL` is a blocker; missing evidence remains `NOT_RUN`. The manifest hashes PNG evidence and prints its own SHA256. Store manifest SHA256 separately to avoid recursive hashing.
