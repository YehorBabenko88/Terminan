# Independent cache audit / LS-5 physical instructions

Audited PR46 exact `dae98726caca4d939e34a4ff16e3ebaee2ade69f` in a separate branch. PR46 is not modified. No Grid/Strattester startup, source DB connection, PostgreSQL change, merge or deployment.

## Findings and changes

P1 fixes, reproduced by regressions before patching:

- `open_cache` uses autocommit. Python `with con` did not make submit/retention atomic: concurrent identical submissions could raise UNIQUE errors; failed insert could leave expired entries deleted. Explicit BEGIN IMMEDIATE/savepoints now cover each operation and rollback all related changes.
- An expired third claim remained RUNNING forever. The next claim pass marks it FAILED/LEASE_EXHAUSTED, clears its capability and reports the terminal state. A replacement token fences the dead worker; publication checks the stored full claim identity/key as well as state/token/deadline. `submit --retry` explicitly starts a fresh bounded attempt cycle for FAILED jobs. Ordinary duplicate submit remains idempotent. READY entries whose data/view is missing/expired/corrupt can be rebuilt. Reusing a revision with different snapshot content is rejected.
- Completeness previously examined only existing groups: a wholly absent5m period could disappear while `complete=true`. V2 requires the exact inclusive minute-start range and every complete period. It rejects duplicate `(minute,price)` records, checks per-minute footprint buy/sell conservation, finite positive prices/OHLC ordering, aggregate volume/delta and deterministic POC. Sparse zero activity is not inferred from missing records: optional `zero_trade_minutes` must explicitly attest zero-volume minutes. Empty-volume periods have no POC.
- Filter-before-LIMIT in PR46 still scanned all READY JSON identities. An explicit partial expression index covers revision/symbol/timeframe/range/algorithm and job order. HTTP refuses a missing/non-searchable index rather than falling back to a scan. Status ordering is indexed too. Index construction is an explicit cache-writer initialization, never an HTTP migration.
- Exact lookup previously used one connection for matching and another for result retrieval, allowing changed range/identity between reads. One WAL read transaction now binds selection, job identity and preview. Parameters/algorithm/key and returned UTC range are verified; ambiguous variants remain AMBIGUOUS.
- UI compared40-character source code SHA to64-character cache revision, so normal data could never match. Matching now uses data `epoch`64. Source/timeframe changes clear results, abort obsolete requests and fence late lookup/inspection responses. Manual job inspection remains an explicitly historical view. Previews longer than64 bars are labeled as shown/total rather than falsely treated as complete displayed history.

P2 review fixes: timeframe-only change now invalidates/requeries cache; zero-volume absence requires explicit coverage, not default zeros. Legacy test fixtures that called a single `{close:100}` candle a complete15m history were corrected to real complete OHLC/footprint data; no integrity assertion was weakened.

## Integrity and HTTP scope

`saved-mtf-cache-v2` deliberately rejects legacy v1 identities; do not reuse their cache claims. Keep original evidence and build a new isolated cache or explicitly regenerate with a v2 identity. Existing v1 payloads are not silently certified under the corrected algorithm.

Worker computation/validation/full SHA256 occurs outside the claim write lock. Full entry, bounded materialized preview and READY state publish in one transaction. The compact preview carries its own SHA256, full-result digest, full identity/range, TTL, total count and explicit truncation. Entry payload/hash/identity/revision/key/expiry updates or deletion invalidate its preview transactionally; LRU touches do not. Readers use `mode=ro`, query_only and a WAL snapshot. No immutable=1 shortcut that would ignore the WAL.

Normal HTTP hits read at most32KiB/64 projected candles, verify preview SHA/identity/coverage/TTL and perform indexed selection. They do not read the raw cache blob, source JSON, initialize a queue, aggregate MTF or invoke a worker. SQLite read operations have250ms lock/progress limits; OS/filesystem I/O itself is not a hard real-time guarantee. Raw full-cache SHA is checked by offline `saved_cache get`, not reread/decoded on every HTTP request. The response explicitly declares `PREVIEW_SHA256_WORKER_VALIDATED_FULL_DIGEST`; it does not claim continuous full-disk-bitrot scrubbing or authentication against a malicious DB editor who can rewrite data and hashes.

## Measurement

`scripts/audit_cache.py` creates only temporary SQLite corpora and measures1k/10k/100k jobs **and** entries/previews. Both indexed HIT/MISS include connection, snapshot, integrity checks and result projection. The comparison removes the expression index and measures the linear JSON-filter SQL (not a complete old HTTP pipeline). It records index-build cost and EXPLAIN plans. Samples20 by default; nearest-rank p50/p95/p99 (p99=max at this sample size), CPU mean, machine OS/Python/SQLite and exact source SHA are retained. Local audit target: HIT/MISS p95<50ms, not an exchange/display SLA. No timing result or failure is suppressed.

The archival corpus intentionally bypasses normal queue128/cache256 retention to stress read scaling. It is **not** a claim that production enqueue accepts100k jobs. Corpus source JSON is omitted for unrelated completed fixture jobs; all read-view/hash/identity records are synthetic and generated locally. Batches500 bound seeding memory. Source revision is an operator/export pin, not independently attested upstream data.

## Windows PowerShell5.1 / Python3.12 physical repro

Use a NEW evidence root. The shell wrapper must run in its own `-File` process; it uses fail-closed native exit propagation and never terminates an interactive parent shell. No elevation or service changes.

```powershell
# From the exact audit checkout; replace with its published40-character HEAD.
$sha='<AUDIT_HEAD>'
$root=Join-Path $env:TEMP ('terminan-cache-audit-'+[guid]::NewGuid().ToString('N'))
powershell.exe -NoProfile -File .\scripts\Invoke-CacheAudit.ps1 -ExpectedSha $sha -EvidenceRoot $root
$native=$LASTEXITCODE
Write-Host "CACHE_AUDIT_CALLER_EXIT=$native"
$summary=Get-Content -Raw -LiteralPath (Join-Path $root 'summary.json') | ConvertFrom-Json
if ($native -ne 0 -or $summary.exit_code -ne 0 -or $summary.candidate_sha -ne $sha) { throw 'AUDIT_FAIL' }
@($summary.checks) | Format-Table
$manifest=@(Get-Content -Raw -LiteralPath (Join-Path $root 'manifest.json') | ConvertFrom-Json)
foreach ($item in $manifest) {
  $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root $item.path)).Hash.ToLowerInvariant()
  if ($actual -ne $item.sha256) { throw 'EVIDENCE_SHA_MISMATCH' }
}
(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'manifest.json')).Hash
```

Requires Python3.12 (`py -3.12`) and Node (project target24); `-Python <explicit python.exe>` is available. Run once in PS5.1, optionally once in PS7 with a separate root. The Python audit verifies clean/exact source, runs cache regressions/Node races, then the bounded benchmark. Native/evidence0 means AUTOMATED_AUDIT_PASS only; physical/manual acceptance remains PENDING until LS-5 evidence and observations are reviewed.

The crash regression launches and kills **only its own child PID**, verifies an uncommitted writer is invisible to a WAL reader, then reclaims with a new token. Lease-expiry clocks are injected deterministically (no two-minute sleep); real elapsed120s expiry and clock-skew testing are not claimed. Concurrent tests use separate connections; never share a sqlite3 connection across threads. Retain any FAIL/CANCELLED evidence and use a new root for retry.

Optional manual UI fixture, still no real sources:

```powershell
$demo=Join-Path $env:TEMP ('terminan-cache-ui-'+[guid]::NewGuid().ToString('N'))
py -3.12 scripts/audit_cache.py --sha $sha --prepare-preview $demo
if ($LASTEXITCODE -ne 0) { throw 'PREVIEW_PREPARE_FAIL' }
py -3.12 -m terminan.saved_runner --config (Join-Path $demo 'sources.json') --cache-db (Join-Path $demo 'cache.sqlite') --port 0
$native=$LASTEXITCODE
Write-Host "CACHE_PREVIEW_NATIVE_EXIT=$native"
```

Open printed URL. Select5m: the generated5-minute snapshot should give EXACT CACHE HIT (volume15/delta5);1m should MISS, with no old5m rows retained. Switch symbol/timeframe/source and inspect manual job history; old requests must not overwrite the active view. Modifying the synthetic snapshot changes its data epoch and must MISS until a new cache is generated. Press Enter in owner console to stop normally; observe SESSION_ENDED. All files are fresh synthetic data; no existing production cache or source is used.

To verify the raw blob independently before/after UI, use `py -3.12 -m terminan.saved_cache --db <demo/cache.sqlite> --identity <demo/identity.json> get`; HIT verifies full SHA and complete payload. This offline command touches LRU in that explicit local cache; HTTP readers never do. The application projection read is bounded32KiB; underlying SQLite/filesystem page I/O is not claimed to be exactly32KiB.

## Remaining limitations / rollback

- Hard120s lease, no heartbeat/chunked cancellation; work exceeding it is rejected and ultimately FAILED. Explicit manual retry resets an attempt cycle; this is not durable per-attempt history.
- No indefinite worker stress, power-loss filesystem testing, adversarial clock rollback, malicious DB authentication or upstream-revision attestation. Historical snapshots are offline-only, never live authority.
- Freshly upgraded cache metadata is not a backfill of old results; v1/missing views require regeneration. Normal capacities remain128 jobs/256entries; rotate a NEW isolated cache when necessary, preserve evidence.
- Standalone cache monitor remains opt-in loopback; Terminan uses its existing bounded HTTP workers. No HTTP method starts computation or writes/installs a worker.
- Rollback: separate clean PR46 checkout at dae98726caca4d939e34a4ff16e3ebaee2ade69f and the original/new isolated cache, not a reset of another branch. Do not reuse a v2 qualification as proof of v1 correctness.
