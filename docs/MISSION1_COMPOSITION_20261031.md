# Mission 1 Terminan source composition

The composition branch starts from visual QA `825c490`, which descends from
shared theme `c08de12`, browser navigation `3bc0954` and six-workspace runtime
`88161de`. All existing runtime, Saved, scientific Math, history overlay, theme
and visual QA files and assertions remain.

Focused existing-source additions:

- Infrastructure consumer and its tests from `d10cee6` (including nested claim
  rejection `988b299`, huge-integer bounds `a91ee10`, strict browser inventory).
  The visual QA `SOURCE_UNATTESTED` reason is retained explicitly.
- Causal display adapter, opt-in import, delayed result publication/diagnostics,
  scientific availability protocol and associated tests from `191ca3a`. Its
  sibling branch is not used wholesale because it lacks the unified runtime.
- Tamper browser expectation from `2a261aa` accepts either independently valid
  fail-closed integrity error while retaining zero experiment-history entries.

Legacy Grid/Strattester contract locks and Saved catalog hashes remain unchanged.
They refer to intentionally older source profiles; tests use disposable pinned
checkouts via GRID_REPO and STRATTESTER_REPO rather than changing those assertions
or replacing active development workspaces.

Development verification: 386 Python tests passed with local loopback permitted;
scientific JavaScript protocol/v2.1/delayed tests passed with MATH_REPO set to the
current composed Math workspace. System Chromium154 passed all 15 scientific Math
browser tests and four causal display tests. This is not pinned-browser or release
qualification. The six-workspace runtime browser test requires a clean committed
source tree and rejects the uncommitted composition at startup; rerun after review
and commit. No clean-source bypass was added.

Infrastructure lifecycle v1 remains the strict existing five-source observation
contract. The six UI workspaces are terminal, Saved, Math, history overlay,
infrastructure monitor and cache; they are not six module lifecycle identities.
No source admission, host changes or physical readiness is implied.

Independent review found an additional cross-module comparison decoder mismatch:
Math publishes scalar rmse/mae/bias at the maximum final event/input publication
clock, while the older decoder expected final event time alone. A real-engine
regression first reproduced TEMPORAL_PROPAGATION_MISMATCH, then passed after the
decoder adopted that exact causal maximum. Event timestamps remain unchanged.
The regression also rehashes forged premature publications for all three scalar
ports and requires temporal rejection, independently of digest validation.
