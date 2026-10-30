# Unified visual QA

Base PR63 exact c08de12dbee5bcb64efe91641438efcdf9e96796. Independent isolated branch; no upstream branch changes.

Baseline:362Python PASS.108Chromium states (DPR1/1.5/2 × real browser zoom1/1.5/2 × viewport1280x720/1920x1080 × six pages) had no global overflow/offscreen form controls with default demo data. Real tab zoom is chrome.tabs.setZoom/getZoom in an isolated ephemeral extension/profile; innerWidth and effective DPR independently verified. Never CSS zoom/pinch or user profile changes. Sources: https://developer.chrome.com/docs/extensions/reference/api/tabs#method-setZoom and https://playwright.dev/docs/chrome-extensions.

Adversarial valid128character unbroken node IDs revealed overflow (1941px vs1280,1514px vs640), overlapping cards and inaccessible button labels. Infrastructure also contains U+FFFD text and incorrectly reports SOURCE_NOT_CONFIGURED for admitted unverified snapshots. Only local monitor wrapping, separator and safe reason token require correction; financial/canvas/SVG palette stays untouched.

Plan: retain baseline screenshots+metrics; add actual browser matrix with valid long-token fixture, selected-node details, real zoom self-check, palette parity with/without shared theme, error states and retained terminal/Saved/lab state; add Python reason/encoding regressions; RED then minimal fix; exact-head Python/JS/browser verification, screenshots and manifests, independent review, separate Draft PR. Synthetic snapshots/temporary cache only; no real sources or trading changes.

Geometry scope: content viewport dimensions at100% zoom, genuine browser zoom afterward. Headless Chromium screenshots omit native browser chrome. Windows OS scaling and human physical acceptance require manual LS-5 checks; DPR emulation is not an OS display-settings change. Horizontal scrolling inside explicitly bounded data tables/footprint and graph pan is permitted; page-level overflow or unreachable controls is not.

Pixel comparison uses exact premultiplied RGBA8 hashes within the same rendered scene, plus explicit semantic CSS/SVG colors and shapes. Raw unpremultiplied Canvas readback was observed to change47semi-transparent pixels by1RGB unit with unchanged geometry/draw count; diagnostic PNGs retained. No opaque-color tolerance or runtime rendering changes are introduced. R4 existing backing-DPR cap3 remains; effective4 (DPR2×zoom2) is composited from3. Saved canvas uses full effective DPR.


## Windows LS-5

Use a clean exact checkout of this Draft PR, Python3.12, Node24. Browser tests use an isolated profile/extension and new temporary synthetic snapshots/cache. No native Chrome user profile or OS display setting is modified.

```powershell
npm ci --ignore-scripts
node node_modules/@playwright/test/cli.js install chromium
$sha=(git rev-parse HEAD).Trim()
$out=Join-Path $env:TEMP ('terminan-visual-'+[guid]::NewGuid().ToString('N'))
powershell.exe -NoProfile -File .\scripts\Invoke-VisualQA.ps1 -ExpectedSha $sha -EvidenceRoot $out
$native=$LASTEXITCODE
$s=Get-Content -Raw (Join-Path $out 'summary.json') | ConvertFrom-Json
if ($native -ne 0 -or $s.exit_code -ne 0 -or $s.result -ne 'AUTOMATED_VISUAL_PASS' -or $s.matrix_cases -ne 108 -or $s.screenshots_verified -ne 114) { throw 'VISUAL_QA_FAIL' }
foreach ($f in @(Get-Content -Raw (Join-Path $out 'manifest.json') | ConvertFrom-Json)) {
 if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $out $f.path)).Hash.ToLowerInvariant() -ne $f.sha256) { throw 'HASH_FAIL' }
}
(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $out 'manifest.json')).Hash
```

Do not reuse evidence directories. A missing/malformed/stale report, wrong invocation/SHA/tree, missing DPR identity, skipped/interrupted/retried test, incomplete matrix or missing/invalid PNG refuses PASS. Summary exits50source/evidence,31browser,130cancel; PS host propagates native exit. All manifests exclude themselves, record manifestSHA separately. CLI color-environment warnings are preserved; app page errors and unexpected console errors must be zero. Disabled Math catalogue HTTP400/BRIDGE_DISABLED and deliberate invalid history HTTP422 are verified and recorded as expected error states, not connectivity PASS.

Manual review:

```powershell
powershell.exe -NoProfile -File .\scripts\Invoke-Terminan.ps1 -ExpectedSha $sha -Demo -Port 0
```

Open the printed loopback URL. Check all six tabs, focus and tooltips, vertical scrolling to all panels, bounded table/footprint scrolling, root ASK above BID and POC/delta, history fact versus past/future forecast markers. Compare100/150/200% in Chromium menu, resize browser content to1280x720/1920x1080; note native browser chrome reduces usable content. Test zoom/pan, Play/Step, return to Saved and laboratory graph. Source/API authority remains SYNTHETIC/HISTORICAL/UNVERIFIED. Enter stops the owner. If using8765, first close its prior owner normally; never kill an unknown listener. Record human observations with exactSHA/invocation/manifest separately. Automated screenshots do not declare PHYSICAL PASS.

## Rollback

Stop this owner normally. Use a separate clean PR63 checkout pinned `c08de12dbee5bcb64efe91641438efcdf9e96796` and its original launcher. No migration/cache/source write occurs in this change. Baseline preserves the known long-node clipping/encoding/reason defects.

```powershell
$rb=Join-Path $env:TEMP ('terminan-visual-rollback-'+[guid]::NewGuid().ToString('N'))
git clone --no-checkout https://github.com/YehorBabenko88/Terminan.git $rb
git -C $rb checkout --detach c08de12dbee5bcb64efe91641438efcdf9e96796
powershell.exe -NoProfile -File (Join-Path $rb 'scripts/Invoke-Terminan.ps1') -ExpectedSha c08de12dbee5bcb64efe91641438efcdf9e96796 -Demo -Port 0
```
