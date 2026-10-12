"""Conservative comparison gates for research runs; no implicit trading approval."""


def compare_runs(left, right):
    """Allow descriptive metric comparison only on an identical, explicit dataset.

    Strategy versions may differ (that is often the purpose of a comparison),
    but the distinction is always disclosed. A dataset match alone does not
    establish equivalent fees, slippage, strategy settings or simulation rules.
    """
    a = left.get("dataset") or {}
    b = right.get("dataset") or {}
    af = a.get("fingerprint")
    bf = b.get("fingerprint")
    if not isinstance(af, str) or not af.strip() or not isinstance(bf, str) or not bf.strip():
        state, reason = "BLOCKED", "DATASET_IDENTITY_MISSING"
    elif af != bf:
        state, reason = "BLOCKED", "DATASET_MISMATCH"
    else:
        state, reason = "CONDITIONAL", "EXECUTION_ASSUMPTIONS_UNVERIFIED"
    return {
        "state": state,
        "reason": reason,
        "same_strategy": left.get("strategy") == right.get("strategy") and bool(left.get("strategy")),
        "same_strategy_version": left.get("version") == right.get("version") and bool(left.get("version")),
        "same_dataset": bool(af and bf and af == bf),
        "execution_assumptions": "UNVERIFIED",
        "statistical_significance": "NOT_EVALUATED",
        "live_validation": "NOT_VERIFIED",
        "trading_authority": "NONE",
    }
