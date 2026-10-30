# Unified visual QA

Base PR63 exact c08de12dbee5bcb64efe91641438efcdf9e96796. Independent isolated branch; no upstream branch changes.

Baseline:362Python PASS.108Chromium states (DPR1/1.5/2 × real browser zoom1/1.5/2 × viewport1280x720/1920x1080 × six pages) had no global overflow/offscreen form controls with default demo data. Real tab zoom is chrome.tabs.setZoom/getZoom in an isolated ephemeral extension/profile; innerWidth and effective DPR independently verified. Never CSS zoom/pinch or user profile changes. Sources: https://developer.chrome.com/docs/extensions/reference/api/tabs#method-setZoom and https://playwright.dev/docs/chrome-extensions.

Adversarial valid128character unbroken node IDs revealed overflow (1941px vs1280,1514px vs640), overlapping cards and inaccessible button labels. Infrastructure also contains U+FFFD text and incorrectly reports SOURCE_NOT_CONFIGURED for admitted unverified snapshots. Only local monitor wrapping, separator and safe reason token require correction; financial/canvas/SVG palette stays untouched.

Plan: retain baseline screenshots+metrics; add actual browser matrix with valid long-token fixture, selected-node details, real zoom self-check, palette parity with/without shared theme, error states and retained terminal/Saved/lab state; add Python reason/encoding regressions; RED then minimal fix; exact-head Python/JS/browser verification, screenshots and manifests, independent review, separate Draft PR. Synthetic snapshots/temporary cache only; no real sources or trading changes.

Geometry scope: content viewport dimensions at100% zoom, genuine browser zoom afterward. Headless Chromium screenshots omit native browser chrome. Windows OS scaling and human physical acceptance require manual LS-5 checks; DPR emulation is not an OS display-settings change. Horizontal scrolling inside explicitly bounded data tables/footprint and graph pan is permitted; page-level overflow or unreachable controls is not.
