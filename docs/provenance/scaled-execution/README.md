# Canonical scaled-limit execution

The existing sole PaperEngine owns the event model; scale_execution defines typed contracts and detached admission only. Math owns all allocation, sizing, weighted basis, cost, fees and PnL arithmetic. There is no second simulator, legacy alias or active Data import.

The direct typed API is execute_scale_plan. Strategy discovery and CLI/replay surfaces remain unchanged; no unwired strategy is advertised. This transfer initially covers the three original direct scale-execution test roles. It does not claim scale-report persistence, live execution, source/PIT authenticity or full legacy simulator equivalence.

The explicit conservative model applies stop first, one target per bar, and close proof for targets after intrabar entries. The last target closes the exact entire remainder and cancels unfilled entries. Break-even stop changes take effect on the following bar. Tiny EOD quantities are not discarded. The Math execution-entry basis stays unchanged on partial exits, separately from rounded accounting cost. All effects are staged before the sole engine commit.

Original immutable source bytes and the old→new map are retained in SOURCE.json and raw/. Canonical installed coverage preserves all324 prior IDs and appends17 unique cases. Local actual threads, HTTP processes, native/SourceFence and provider calls remain held.

Math dependency9379384606492af33619bc9168d259917da296a0 has passed independent source/wheel QA and is published; fresh required CI is pending. The workflow intentionally retains earlier public1b until final qualified dependency pin update; this candidate must not be published prematurely. Current statusNO_GO,516 legacy obligations remain until actual old caller/code retirement.
