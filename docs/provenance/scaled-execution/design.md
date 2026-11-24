{
  "base": "12d2ba4f7e2d1f5bfc521b42bac220614cc3ab0f",
  "worktree": "C:/Users/Administrator/Documents/Codex/2026-11-19/files-pasted-by-the-user-unified/work/terminan-scaled-execution20261124",
  "owner": "parent",
  "newModule": "terminan/scale_execution.py typed contracts/admission only",
  "onlySimulator": "terminan.paper.PaperEngine.execute_scale_plan",
  "typedNames": [
    "ScaleExecutionPlan",
    "ScaleEntryLeg",
    "ScaleExitTarget",
    "ScaleEntryFill",
    "ScaleExitFill",
    "ScaleExecution"
  ],
  "policy": "OHLC_SCALE_SL_FIRST_ONE_TARGET_PER_BAR_NO_TICK_ORDER_V1",
  "semantics": [
    "all graph detached before Math",
    "existing validate_signal_batch reused for shared OHLC and clock domain",
    "16entrylegs/16targets bounded",
    "limit eligibility strictly next aligned bar",
    "new intrabar entries require post-entry close proof for target under conservative model",
    "stop first, one target per bar, moved break-even stop takes effect next bar",
    "late entry updates remaining cost through sole Math helper",
    "fully closed position cancels all still pending entries",
    "EOD closes exact entire positive remainder, no epsilon drop",
    "stage all outcomes and derived metrics before sole engine commit",
    "final target closes exact remaining quantity; earlier targets use declared share of total opened"
  ],
  "mathAPI": "pending reviewed Math contract; all allocation/quantity/accounting math inMath",
  "strategyRegistry": "unchanged: typed execute_scale_plan method only until explicit replay/CLI consumer exists; no advertised unwired strategy",
  "oldScaleTests": 3,
  "legacyDeduction": 0,
  "publish": false,
  "release": "NO_GO"
}
