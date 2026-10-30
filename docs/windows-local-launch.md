# Windows LS-5 local launch — integration checkpoint

This launcher starts **only** the original main terminal at 127.0.0.1:8765.
It is not a combined /saved + cache + science launcher yet: those components
remain on separate draft branches and require a compatibility review.

## Preflight (safe, no listener)

From an exact clean checkout of this PR:

```powershell
powershell.exe -NoProfile -NonInteractive -File .\scripts\Start-TerminanLocal.ps1 -ExpectedSha '<exact PR head>' -PreflightOnly
$rc = $LASTEXITCODE
"LOCAL_PREFLIGHT_EXIT=$rc"
```

The preflight verifies HEAD, clean Git status, Python 3.12, compilation and
the full Python unittest discovery suite. It does not start Grid, Strattester,
PostgreSQL, cache workers or a server.

## Launch

```powershell
powershell.exe -NoProfile -File .\scripts\Start-TerminanLocal.ps1 -ExpectedSha '<exact PR head>'
$rc = $LASTEXITCODE
"LOCAL_TERMINAN_EXIT=$rc"
```

Open http://127.0.0.1:8765/ and http://127.0.0.1:8765/monitor
manually. Stop with Ctrl+C in the owner console. A port collision fails
closed. Existing source adapters remain optional, and their availability is
not implied by this launcher.

## Scope / rollback

No install, deployment, Windows service, task scheduler, DB schema mutation
or merge. Rollback: stop the owner console and return to the previous
detached SHA. Keep old physical evidence intact.

Next: independently compare PR47 cache, /saved and scientific workstream
branches, then add one tested orchestration layer. Do not silently transplant
an old cache schema or bypass source publication/fencing.
