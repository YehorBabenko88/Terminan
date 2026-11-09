# Target Adapter result renderer — inventory and harness preparation

Date: 2026-11-09. Status: WAIT_EXACT_ROOT_OUTPUT_SCHEMA.
No renderer, parser, DTO, endpoint or passing target-result tests exist in this slice.

## Immutable base and ownership ACK

Terminan source base b70725220eed43e371a3c08f1c87fcabd984a45d,
tree fb1859899a41a6976f39023ff1caeb4323b519bb; existing source worktree clean.
Separate branch feature/target-adapter-result-20261109.
Separate worktree work/terminan-target-result-20261109.
All allocated new paths were absent in the base Git tree:
- terminan/target_adapter_result.js
- tests/target_adapter_result/**
- docs/gateway/target-adapter/**
- .github/workflows/target-adapter-result.yml (selected dedicated workflow name)

Do not modify gateway_artifacts.js, existing gateway tests/workflow, Sync, or any
ROOT/producer file. Prior b707 tests/browser/audit evidence remains historical,
not target-adapter qualification. No physical, network or service changes.

## Available reusable test techniques (not shared product dependencies)

Existing owned local components demonstrate dependency-free Node tests, strict
raw-source before/after receipts, independent exact test-ID inventory, pinned
Windows/Ubuntu workflows and isolated loopback Chromium with CSP connect-src none.
Use those techniques in NEW target-specific files after the schema is available;
do not import a hidden provider, adapt v1/v2 wire contracts or alter their behavior.
No new dependency installation or setup is needed for preparation.

## Harness plan, blocked on schema

After exact ROOT schema/source pins and actual immutable target output arrive:
1. Check schema identity/hash, bytes/size/type boundaries and actual producer packet
   preimages; agree the local consumer mapping before implementing behavior.
2. Write RED target-specific cases for malformed/missing/version/extra/oversize
   input, truthful experiment/capability/dataset/params/result/units/status/provenance/
   limits display and input reset; use field names/types ONLY from ROOT schema.
3. Test textContent-only rendering, no URLs/imported HTML/effects/logs/providers,
   detached bounded model, explicit unavailable states and LOCAL_UNATTESTED labels.
   Declared hashes/capabilities/status never grant execution/authentication.
4. If the exact API needs async verification, test stale success/failure/reset
   with per-root UI bookkeeping only. No authority generation or lease substitute.
5. Execute actual owner-produced synthetic output only; no model-generated result
   values, production fallback fixtures, inferred units or financial zero defaults.
6. Add new source-bound CI and isolated real browser screenshots after implementation;
   distinguish Node/model/browser/hosted/Windows-runtime/physical evidence.

## Pending owner inputs

Exact versioned ROOT output schema and immutable commit/tree/hash; local entrypoint
input/return/error specification; strict byte/depth/member/array/string limits;
actual pure target source identity + output bytes/digest + provenance/units/status
semantics. These are dependencies, not an invented replacement contract.

RUNTIME_ENDPOINT: NONE IN THIS SCOPE.
IMPLEMENTATION: NOT_STARTED_WAIT_SCHEMA.
TARGET_TESTS/BROWSER/WINDOWS_CI/PHYSICAL: NOT_RUN.
GO_NO_GO: NO-GO.
