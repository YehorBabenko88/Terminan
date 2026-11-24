# Canonical scaled-limit execution

The existing sole PaperEngine owns the event model; scale_execution defines typed contracts and detached admission only. Math owns all allocation, sizing, weighted basis, cost, fees and PnL arithmetic. There is no second simulator, legacy alias or active Data import.

The direct typed API is execute_scale_plan. Strategy discovery and CLI/replay surfaces remain unchanged; no unwired strategy is advertised. This transfer initially covers the three original direct scale-execution test roles. It does not claim scale-report persistence, live execution, source/PIT authenticity or full legacy simulator equivalence.

The explicit conservative model applies stop first, one target per bar, and close proof for targets after intrabar entries. The last target closes the exact entire remainder and cancels unfilled entries. Break-even stop changes take effect on the following bar. Tiny EOD quantities are not discarded. The Math execution-entry basis stays unchanged on partial exits, separately from rounded accounting cost. All effects are staged before the sole engine commit.

Original immutable source bytes and the old→new map are retained in SOURCE.json and raw/. Canonical installed coverage preserves all324 prior IDs and appends17 unique cases. Local actual threads, HTTP processes, native/SourceFence and provider calls remain held.

The final workflow pins public Math9379384606492af33619bc9168d259917da296a0 (34 required CI jobs accepted) and Data30ef77cefe5e5b9d8af8dafc6da24e587711f897 (14 current CI jobs accepted). The functional source and actual Terminan wheel are unchanged from a87e08d73c16dec5a91564e4598dbef4188d0303. Independent acceptance of this Terminan candidate and its fresh exact-head hosted CI remain required. Current statusNO_GO,516 legacy obligations remain until actual old caller/code retirement.
