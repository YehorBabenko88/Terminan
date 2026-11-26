# ROUND17 — narrow legacy grid executable transfer and explicit refusals

Original Strattester \`strattester/strategies/builtin/legacy_grid.py\` from
pinned \`37ff7e9d12a4d2dccd788fc493c28557dbe8bcea\`, original Git
blob \`87a7ea0fa5b66b2faeb2e8be45efa183cbc16ccd\`.

The archived **original BacktestEngine** is loaded solely in tests from
selected original AST class nodes after checking its complete Git blob.
Production never imports it and does not recreate it. An extremely narrow
research proposal \`propose_legacy_level_base\` reuses ONLY the existing
Math \`paper_stop_price\` for the historical default 0.005 entry distance,
0.01 stop fraction and 0.015 target fraction. The default historical HIGH
level is long and LOW level is short. It returns the existing canonical
\`ResearchSignal\` for optional **offline** PaperEngine use.

**Equivalence scope:** the first eligible one-minute bar's *open must equal
the exact historical trigger* and the entry bar must not touch SL/TP. This
prevents mislabeling historical level-trigger STOP-like entries as favorable
LIMIT fills, which the unique Terminan PaperEngine models differently.
An original short/long end-to-end historical BacktestEngine comparison is
done in dynamic tests (signal, entry, target, stop, fees, gross/net, exit).
Any gap, opening mismatch, ambiguous same-bar path, partial candle, unknown
clock or unsupported variant fails closed.

This is **NOT full 28-variant legacy-grid strategy migration**, and does not
promote the 20 historical LEVEL/POC/SMC specifications to executable status.
No competing engine, no second numerical kernel, no source authenticity,
no exchange orderbook, and no real trading. Spread and nonzero slippage
cannot be asserted historically equivalent because old engine does not
model those quotes; keep a separate actual spread/fee/slippage test matrix.

Only a qualified historical research candidate is returned, with
\`NOT_EVALUATED\`, \`execution_authority=False\`,
\`trading_authorized=False\`. Full order parity remains blocked.

CODE NO_GO / PRODUCTION NO_GO.
