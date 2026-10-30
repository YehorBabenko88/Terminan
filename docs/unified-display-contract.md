# Unified display contract (unqualified, opt-in)

This Draft extends #59 without changing its branch or its active Math lock. It
implements display contracts only; the numerical Grid -> Unified Math -> replay
E2E and Math #105 pin admission remain blocked by the hosted qualification gate.

## Producer and consumer

Strattester's own Draft on #66 preserves market separately from source identity,
model/version, units, split bounds and original receipts. Recorded publication
is retained through review/export; conflicting overrides fail. If publication
is absent, no OOS availability timestamp is invented. The existing CLI adds
optional `--published-at-ms` and keeps exclusive output creation.

New producer API `joint_display_packet(history,request,result,expected_receipt,
joint_published_at_ms=...)` and `scripts/export_joint_display.py` wrap the
original history packet, joint request/result and separately supplied joint
receipt pin. The 8 MiB envelope is `terminan.unified-display.v1` with
`contract_only:true`, `qualification:NOT_QUALIFIED`, SYNTHETIC/UNATTESTED and false
execution/training/trading flags. This is not a Math runtime admission mechanism.

Terminan requires explicit `TERMINAN_UNIFIED_CONTRACT_IMPORT=1`; default import
rejects this new schema. Legacy files keep their 2 MiB limit and existing pins;
opt-in Unified envelopes have an 8 MiB limit. The adapter performs only schema,
receipt, source/prefix, manifest, units and clock validation. It never executes
Math, fits a model, regenerates forecasts or scores OOS.

Original `joint_request.history` must bind exactly to returned provenance and
the full stored historical prefix, including observed values/availability and
watermarks. Python canonical receipts bind request/history/result/envelope;
the browser separately verifies Math's JS canonical scientific request,
definition and output-port digests. A checked digest establishes internal
consistency, not authenticated source/engine execution or correct mathematics.

The producer's replay model has a Python manifest; joint.math_source has the
larger Python/JS manifest. The former must be a matching subset with the same
commit/tree/Python runtime; Node runtime remains explicit. Unknown/incorrect
models, unsafe clocks, invalid original source event ranges, revision hashes,
nonfinite OHLCV, future training rows and elapsed horizons fail closed.

## Four distinct display meanings

- Frozen historical forecasts retain original feature, first availability,
  decision, target, value and request digest. Past targets remain predictions;
  forward mode only removes past predictions, not known facts.
- Historical scientific price-unit series are independent colored layers.
  Event/availableAt remain separate and can satisfy event < availableAt. Results
  require original event/availability <= asOf AND declared joint publication
  (at least the original decision) <= asOf. They cannot retroactively appear
  merely because their input samples were available earlier.
- Scalar and non-price outputs retain their values/units/axes in separate
  DESCRIPTIVE_NOT_OOS diagnostics. They never become forecast skill, profit or
  a price series. They have the same result-publication gate.
- OOS belongs to Strattester's replay/test split only. Scores appear after
  explicit publication >= test end, observation availability and decisions;
  absent clocks withhold them. No source/model metadata carries outcome values.

The HTTP bridge and editor/protocol now independently require timestamps and
availability <= request.asOf. They no longer reject legitimate delayed
publication simply because availability exceeds event time. All old instant
series remain valid. The pinned old engine may still reject new delayed input;
these validator changes do not silently replace that engine or its pin.

## Contract evidence only

`tests/fixtures/unified-contract.v1.json` is a literal synthetic wire fixture
wrapped by the actual producer helper. Its b/c source IDs and arithmetic values
are inert test records, not an executed/qualified Math #105 outcome. The source
and SHA256 are recorded in CI. `scripts/unified_contract_test_server.py` only
enables the inert import in a disposable loopback server and clears all other
TERMINAN_* settings. New browser tests launch no Math or database.

```text
python -m unittest tests.test_unified_display_adapter tests.test_unified_delayed_contract tests.test_history_overlay_admission tests.test_history_overlay_route tests.test_unified_bundle_oracle -v
node --test tests/test_delayed_protocol.cjs tests/test_history_overlay_script.cjs
npx playwright test -c playwright.unified-contract.config.cjs
```

The new hosted workflow checks these contracts with Chromium and Firefox; it
does not check out or execute Math #105. Existing legacy numerical tests retain
their own older pins and do not substitute for final Unified qualification.
Neither local nor hosted contract PASS upgrades NOT_QUALIFIED to qualified.
