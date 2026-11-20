# Finite offline causal paper session

This library has no operational constructor. It accepts only an existing `CausalAccountJournal` whose policy is `SYNTHETIC_OFFLINE`. Its existing `require_current() is True` callback is a caller freshness boundary, **not permission, source authentication, kernel admission or a service grant**. Root must establish actual source/capsule/service custody before application imports or any future operational integration.

`CausalPaperSession(account, *, run_id, strategy_revision, planned_duration_ms, source_max_age_ms, clock_ms=None, min_history=8)` performs freshness, owned-account/recovery and capacity checks before constructing strategy instances. Clock callbacks return literal integer milliseconds; the default uses the local process wall clock. No provider, SQL selector, URL selector, credential or publisher callback is accepted.

- `accept_packet(packet, *, expected_request) -> tuple[SessionDescriptor]`: actual Data SDK validation and staged research; then causal risk/decision/quote/account transitions. An exact last-packet retry returns its same immutable descriptors without clock/action advancement. A conflict or account/source failure blocks further processing.
- `advance() -> tuple[SessionDescriptor]`: explicit clock/hold/expiry progression. Closing decisions are durable before later exit quotes; a predecision/prelatency sample cannot be relabelled as a fill.
- `finish() -> tuple[SessionDescriptor]`: idempotently ends the finite caller run. Unresolved reservations become RESTART uncertainty and retain collateral. It invents no closing fill or qualification.
- `status() -> dict`: fresh nonfinancial session-routing diagnostics; durable financial truth comes only from the owned verified artifact.
- `publication_artifact() -> SessionPublication`: immutable `artifact_json: bytes`, SHA256 and a small immutable descriptor. Family `terminan.paper.causal-ledger.v2` includes actual verified sole-engine receipts and Math balances, with `VERIFIED_LOCAL_READS_NOT_CROSS_DATABASE_ATOMIC`. It performs no publication.
- `publication_descriptor() -> SessionDescriptor`: the artifact descriptor only. `SessionDescriptor.decode()` returns a fresh copy; altering it changes no retained descriptor/state.

Root owns actual source polling, packet artifact retention, durable Journal/audit, artifact writer, presentation reader, provider/publication failure stop and protected operational admission. Descriptors bind source packet/row and risk/request/result digests, clocks and all evidence flags. Root must retain the canonical input packet artifacts to make those references replayable. Publication failure must stop the Root producer without retrying retained staging files.

Bounds: ten fixed symbols; history32/minimum4..32; duration<=1h; source-age>=account quote-age and<=1h; forecast<=200 completed results/512 decisions/4096 descriptors before factories; each descriptor<=64KiB; verified artifact<=4MiB. Existing account ledgers each have their independent2MiB cap. No new storage implementation exists.

Math135 `a5868944bf1bae813403a32b22d329c1da6f8238` supplies exact scaled funding clock conversion; nonintegral clocks are unavailable, never floored. Data packet pin `5bb26e2f469c407c16bd4165ba80844db6e4379d` supplies packet/field-use-time validation. The source request/as-of, original row/hash and funding observation clocks are never rewritten for processing delay.

The original16 composed roles are explicitly mapped in `causal-session-role-map.json`. Root writer/reader/provider/admission integration roles remain open until its actual composition tests pass. Old lab pipeline retirement is not authorized by library tests alone. Source authenticity/completeness are NOT_EVALUATED, point-in-time availability UNKNOWN, trading/execution authority false; actual native/process-crash/power-loss tests were not run.

## Pure canonical reader

`terminan.causal_artifacts.validate_causal_ledger_artifact(raw: bytes, *, expected_sha256: str) -> dict` performs no SQL, filesystem, network or publication actions. It rejects oversized bytes before hashing, duplicate/noncanonical/unknown JSON fields, oversized objects/rows and authority upgrades. Every completed receipt is replayed through the existing calculator at its original admitted_ms and compared as canonical bytes, including original request/result hashes. The returned dictionary is a fresh decode.

Required `balances_basis` is `PRODUCER_CLAIMED_LOCAL_ACCOUNT_SNAPSHOT_NOT_RECONSTRUCTABLE_FROM_RECEIPTS`: balances are bounded finite text but cannot be independently reconstructed from this receipt-only artifact. `consistency` remains `VERIFIED_LOCAL_READS_NOT_CROSS_DATABASE_ATOMIC`, a producer-local claim. A caller-selected digest verifies byte identity, not source authentication.

Owner verification:171 scoped pure cases passed on Python3.11 and3.12 against Math135 a5868944bf1bae813403a32b22d329c1da6f8238 and Data5bb26e2f469c407c16bd4165ba80844db6e4379d. Includes17 finite session roles and5 pure reader cases, with actual ten-symbol Data→Math→sole PaperEngine→ledger→reader composition. Actual Root Journal/writer/pinned-reader/provider-failure integration remains separate and required before old pipeline retirement.

Correction descendant: `causal-unknown-funding-and-json-bounds.md` records explicit latest-unknown invalidation before hold/close advancement and the raw structural/typed descriptor resource contract. These guards do not grant source authentication or operational permission.

All-visible funding descendant: `all-visible-funding-availability.md` requires Data105 e1ea525273aa2181e7357ca84a774ac2fb30ced0 and Math135 a5868944bf1bae813403a32b22d329c1da6f8238. It consumes canonical per-row assessments, latches all visible gaps before advancement and rejects pre-gap proof cache restoration.
