# Canonical scaled-limit execution

The existing sole PaperEngine owns the event model; scale_execution defines typed contracts and detached admission only. Math owns all allocation, sizing, weighted basis, cost, fees and PnL arithmetic. There is no second simulator, legacy alias or active Data import.

The direct typed API is execute_scale_plan. Strategy discovery and CLI/replay surfaces remain unchanged; no unwired strategy is advertised. This transfer initially covers the three original direct scale-execution test roles. It does not claim scale-report persistence, live execution, source/PIT authenticity or full legacy simulator equivalence.

The explicit conservative model applies stop first, one target per bar, and close proof for targets after intrabar entries. The last target closes the exact entire remainder and cancels unfilled entries. Break-even stop changes take effect on the following bar. Tiny EOD quantities are not discarded. The Math execution-entry basis stays unchanged on partial exits, separately from rounded accounting cost. All effects are staged before the sole engine commit.

Original immutable source bytes and the old→new map are retained in SOURCE.json and raw/. Canonical installed coverage preserves all324 prior IDs and appends17 unique cases. Local actual threads, HTTP processes, native/SourceFence and provider calls remain held.

The current workflow pins public Math 9379384606492af33619bc9168d259917da296a0 (34 required CI jobs accepted) and Data cef6365fb9241a62e9ffc3ddb610d2a8575fd6e3 (14 exact-head CI jobs accepted; outputs/hosted-data-cef-1795485808902/receipt.json). This metadata-only Data repin starts from public Terminan f5e3a0bacad7b1bec7b0ca3cb72a1d0a148caddd; its new enclosing-head Terminan CI is pending publication. The functional source and retained actual Terminan wheel remain based on a87e08d73c16dec5a91564e4598dbef4188d0303.

Historical repin anchors remain explicit: initial workflow repin 36f5317ae2c50e82b7e673cd06c414b1dfadea01 bound Math 9379/Data 30ef; previous repin f6f516252b230ef7f87cd58a1bdab920796cc904 started from 26af145a1c53d85f607fc18c4fd200f0a42b0f73 and bound Data da9e782470d1237122c99994c042c2834b026062 with its accepted 14-job evidence at outputs/hosted-datada9-1795482205614/receipt.json. The original Data104 source and frozen reporting counterpart proposal remain historical snapshots.

The accepted four-role event remains recorded as 35 accepted, 512 remaining and deduction 4 in outputs/qa-parent-data-eol-1795481603444/accepted-four-role-transition.json. Separately, the accepted two reporting roles update the current global original-547 counter to 37 accepted and 510 remaining, as recorded in outputs/qa-parent-data-fixture-1795485709205/accepted-reporting-two-transition.json. Neither event claims full legacy retirement. Current release status NO_GO.
