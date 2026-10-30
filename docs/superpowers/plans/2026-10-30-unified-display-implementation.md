# Approved P1 implementation ledger

User approved implementation, contract-only local tests and own Draft PRs.
This supersedes the preparation-only execution restriction, not the Math hosted gate.

- Control bases remain #59 eafdc32 / #66 c951b3f, both exact remote heads rechecked.
- Prepared patch matches the separate readiness branch; 11 original probes/oracle tests passed before changes.
- Producer: preserve actual market/model/units/source/splits; publication is caller-declared and bounded, never guessed from input availability. Missing publication withholds OOS for backward compatibility.
- New inert envelope: `terminan.unified-display.v1`, `contract_only:true`, `qualification:NOT_QUALIFIED`; original joint request/result and independently pinned receipt, legacy history handoff, and explicit joint publication time. No numerical execution, fitting or scoring in exporter/consumer.
- Consumer: opt-in `TERMINAN_UNIFIED_CONTRACT_IMPORT=1`, unchanged active Math locks. Validate receipts/prefix/source/runtime identity and original clocks, separate price series, frozen forecasts, scalar/non-price diagnostics and published OOS. New results require actual decision/publication <= display asOf, not merely old source availability.
- Legacy delayed availability: require event and availability <= request.asOf, retain original axes. Existing instantaneous sources remain a subset. New engine pin remains denied through legacy import.
- Test sequence: producer RED/GREEN; adapter RED/GREEN; opt-in browser contract fixtures (explicitly no engine run); backward compatibility/new negatives; independent review; own Draft PRs and exact-head SHA evidence.
- Final Unified numerical E2E, runtime pin update, ADMINIT, production DB/trading, merge/deployment remain forbidden until hosted gate; do not auto-promote a local contract PASS.
- RED/GREEN: metadata/publication export, original request capture, delayed HTTP/editor/protocol, receipt/provenance/prefix mutations, forecast feature clocks and late publication slider. Independent review found two P2 boundaries (feature-clock comparison, slider publication domain); both reproduced and fixed. Returned source manifest is detached from mutable client guard state.
