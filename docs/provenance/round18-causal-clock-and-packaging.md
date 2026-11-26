# ROUND18 D — post-close retrospective parity, not causal execution

The historical Strattester \`legacy_grid.BacktestEngine\` (pinned Git blob
\`87a7ea0fa5b66b2faeb2e8be45efa183cbc16ccd\`) considers
the entry candle's high/low while deciding whether the entry occurred at
that candle's open. A candidate built from a **closed** entry bar cannot
issue an executable signal for that bar's opening without look-ahead.

Round17's \`LegacyLevelBaseProposal.signal\` originally contained an
earlier \`ResearchSignal.decision_ms\` despite using full future bar high/low.
Round18 removes that \`ResearchSignal\` from production entirely. The
\`LegacyLevelBaseObservation\` now carries the first known
\`observed_at_ms=entry_bar.start_ms+bar_ms\`, explicit
\`FULL_ENTRY_BAR_CLOSE_DECLARED_NOT_AUTHENTICATED\` availability, original
entry/stop/target geometry and \`execution_authority=False\`.
This is an exact-open **RETROSPECTIVE** comparison, not a causal
strategy nor a historical live trade. It cannot be silently converted into
an order request by an API claiming earlier knowledge.

The existing Round17 differential test still executes the exact historical
BacktestEngine and the single canonical PaperEngine side-by-side, but
constructs a **hypothetical pre-open ResearchSignal only inside tests**.
Historical long/short price, stop, target, fee and PnL consistency in these
two fixed simulations must never be promoted as real causal execution parity.
No default strategy registry is modified and all 20 history descriptors
remain SPEC_ONLY.

Packaging: wheel Git bytes previously verified (Round17). Added
\`tests/check_archive_artifact_exclusion.py\`, called after building both
the wheel and sdist in existing wheel-install CI, to exclude original archived
Python test fixtures from either distribution. The check uses actual member
names; manifest text alone is not proof. Runtime package remains the
existing fixed \`terminan\` package and sole Math SDK.

Remaining: prove full exact historical semantics or keep SPEC_ONLY; source,
coverage, spread/L2, slippage, intrabar order and native integration not
proven. CODE NO_GO / PRODUCTION NO_GO.
