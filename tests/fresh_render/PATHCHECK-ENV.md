# Read-only PowerShell child environment successor

Source-only follow-up from immutable7b861f3/PR76. Root requested explicit environment
custody for checkPaths PowerShell children. No observed global filesystem write is
claimed or inferred from the earlier env-only-SystemRoot source. NoProfile alone
does not establish cache/profile location.

After the SAME bootstrap GO (and therefore after Root's retained-HANDLE own-Job
admission), path checks pass ONLY required SystemRoot, WINDIR, TEMP, TMP,
LOCALAPPDATA, APPDATA, USERPROFILE and optional TMPDIR from Root-selected process
environment. Values must be present, nonempty, canonical absolute local paths
<=2048 characters. Missing/invalid required values fail closed; no inherited global
profile fallback. Helper does not forward PATH, HOME, credentials, PSModulePath,
arbitrary flags or the rest of process.env. Root must establish directory custody,
existing canonical paths/no reparse and private writable locations before GO;
environment strings are NOT proof of ownership, ACL isolation or permission.

Child PSModuleAnalysisCachePath is always the literal NUL, overriding any inherited
cache location. Microsoft's Windows PowerShell5.1 documentation describes this as
process-only file-cache disable, set before child startup:
https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_windows_powershell_5.1
No registry, global environment, policy, ExecutionPolicy or bypass flags change.
The existing fixed read-only script and every before/after ReparsePoint check are
retained. This is not a filesystem write audit or a claim that every Windows API
honors environment overrides; Root must observe actual disposable behavior.

Root's direct ordinary Node parent must supply these private TEMP/profile variables
at launch. Early post-GO prepare/tooling checks use those parent-selected private
directories. Once harness creates its new run/temp directory, it temporarily points
TEMP/TMP/TMPDIR/LOCALAPPDATA/APPDATA/USERPROFILE there, restores original values in
finally, and browser's explicit sanitized environment also includes own APPDATA.
No PS is started before GO. SDK guard, exact dependency pins, renderer and nonce
protocol remain unchanged. Do NOT launch the ordinary harness CLI in place of the
Root-supervised bootstrap for the physical pilot.

Budgets are NOT increased: existing45000ms cooperative harness budget,5000ms SDK
close timeout and10000ms per-path-check child timeout remain exact. Root's stricter
20s work/10s cleanup/10s USER CPU limits are externally enforced and take precedence;
this source does not qualify those limits or silently extend/retry them. Many PS
startups may exceed Root's actual pilot budget. Collect timeout/failure, then change
source through commit/review; do not skip checks or relabel timeout PASS.

Unit setup uses Root-selected disposable location directories and an explicit
FRESH_UNIT_BROWSER_EXE only in retained test configuration so relocating LOCALAPPDATA
does not redirect tests to a nonexistent browser. Runtime tooling still consumes
the passed private module/executable args; it has no original-install path change.
Tests verify exact allowlist, required/optional fields, no ambient secret forwarding,
NUL override and actual read-only PS environment observation. No SDK/browser/Job or
physical smoke is executed. Overall runtime/physical NO-GO pending Root/A8 review.
