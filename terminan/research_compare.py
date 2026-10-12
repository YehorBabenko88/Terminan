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
    # Compare explicitly persisted execution assumptions, not performance metrics.
    # A matching value means only that the recorded settings match, not that
    # their implementation was validated by the source service.
    fields = ("fee_rate", "slippage_bps", "execution_model", "simulation_config_hash")
    am = left.get("metrics") if isinstance(left.get("metrics"), dict) else {}
    bm = right.get("metrics") if isinstance(right.get("metrics"), dict) else {}
    assumptions = {}
    for field in fields:
        av, bv = am.get(field), bm.get(field)
        if av is None or bv is None or isinstance(av, bool) or isinstance(bv, bool):
            assumptions[field] = "UNVERIFIED"
        elif type(av) is not type(bv) or av != bv:
            assumptions[field] = "MISMATCH"
        else:
            assumptions[field] = "RECORDED_MATCH"
    # Coverage windows must be equal when both are explicitly provided.
    # A dataset fingerprint does not independently prove equal test windows.
    coverage_a = a.get("coverage")
    coverage_b = b.get("coverage")
    if (isinstance(coverage_a, str) and coverage_a != "UNSPECIFIED"
            and isinstance(coverage_b, str) and coverage_b != "UNSPECIFIED"):
        coverage_state = "RECORDED_MATCH" if coverage_a == coverage_b else "MISMATCH"
    else:
        coverage_state = "UNVERIFIED"
    # Only source-recorded quality indicators are considered. Missing
    # indicators never become an inferred pass from profitable metrics.
    quality_fields = ("missing_candles", "data_gap_count", "invalid_candle_count")
    quality = {}
    for field in quality_fields:
        av, bv = am.get(field), bm.get(field)
        if (type(av) is not int or type(bv) is not int or av < 0 or bv < 0):
            quality[field] = "UNVERIFIED"
        elif av > 0 or bv > 0:
            quality[field] = "DEFECT_RECORDED"
        else:
            quality[field] = "ZERO_RECORDED_NOT_VALIDATED"
    if state != "BLOCKED" and "DEFECT_RECORDED" in quality.values():
        state, reason = "BLOCKED", "DATA_QUALITY_DEFECT_RECORDED"
    if state != "BLOCKED" and coverage_state == "MISMATCH":
        state, reason = "BLOCKED", "COVERAGE_MISMATCH"
    if state != "BLOCKED" and "MISMATCH" in assumptions.values():
        state, reason = "BLOCKED", "EXECUTION_ASSUMPTIONS_MISMATCH"
    return {
        "state": state,
        "assumption_details": assumptions,
        "coverage_comparison": coverage_state,
        "data_quality": quality,
        "reason": reason,
        "same_strategy": left.get("strategy") == right.get("strategy") and bool(left.get("strategy")),
        "same_strategy_version": left.get("version") == right.get("version") and bool(left.get("version")),
        "same_dataset": bool(af and bf and af == bf),
        "execution_assumptions": "UNVERIFIED",
        "statistical_significance": "NOT_EVALUATED",
        "live_validation": "NOT_VERIFIED",
        "trading_authority": "NONE",
    }
