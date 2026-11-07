# Gateway metadata implementation plan

Goal: implement the direction-ACKed metadata-only parser/text renderer; chart and endpoint admission remain independent gates.
Architecture: dependency-free UMD module, strict bounded JSON decoder, closed metadata validation, frozen detached DTO, inert textContent renderer. Node builtins and isolated Chromium tests only.
Spec: DESIGN-PROPOSAL-v1.md. Owner directionACK permits local implementation; shared DTO/endpoint ACK absent.

1. RED: tests/gateway_artifacts/test_metadata.cjs asserts absent/malformed/duplicate/oversize/depth/unknown/version/type/date/unit/URI/digest/status rejection, detached frozen metadata, truthful qualifiers, reset, no IO/HTML/effects. Run node --test and retain RED outside source.
2. GREEN: implement terminan/gateway_artifacts.js only. No existing module imports or Sync changes. Fixed error codes; no input logging. UTC calendar/range validation; opaque ASCII IDs; bounded textual units; strict TEST_ONLY/LOCAL_UNVERIFIED qualifiers. Run all tests.
3. Add source-bound CI bootstrap in tests/gateway_artifacts/qualification.cjs and owned workflow, pinned actions, no dependencies/cache, raw Git before/after inventories, exact mandatory test IDs. Retain local receipt; hosted is separate.
4. Isolated browser stand under owned tests verifies native collapsed metadata details and no links/effects/network, captures screenshots outside source. Metadata fixtures contain reference literals only, no fabricated scientific values.
5. Independent review; commit/push own branch/DraftPR, exact HEAD/tree and proposal hash. Request shared series schema/readcapability separately; chart only after exact ACK and owner-computed immutable bytes.

Review focus: advertised digest never verified; development metadata never runtime authority; unknown fields cannot introduce series/URLs; invalid input clears previous model; bounded parsing precedes Number conversion/object materialization. No runtime/physical/real-order acceptance.
