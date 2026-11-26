"""Read-only custody of unimplemented historical Strattester hypotheses.

This is NOT a strategy implementation, runtime registry, Math kernel,
historical data attestation or trading permission. The eight separately
migrated scalp hypotheses remain in strategy_catalog.py. The twenty
additional spec-only records below are original parameter metadata, retained
under their original unique names and source Git blobs.

Original repository: YehorBabenko88/strattester
Original pinned tree: 37ff7e9d12a4d2dccd788fc493c28557dbe8bcea
"""
from dataclasses import dataclass, field
from types import MappingProxyType


_SOURCE_COMMIT = "37ff7e9d12a4d2dccd788fc493c28557dbe8bcea"
_SOURCE_PATH = "strattester/strategies/builtin/"
_SOURCE_BLOBS = MappingProxyType({
    "research_levels.py": "ba5a60c867fc0fc6f715a966b1a6ccfbb2ed19d5",
    "research_poc.py": "e1ceb266f1c342504e21a87bad0b267127f63e90",
    "research_volatility.py": "f28ef49806456f6e79481559b1a70c74f08d41d8",
    "research_smc.py": "ddaa04c19a3e4aa703fdb8fafc6ef8034d199ac2",
})


@dataclass(frozen=True, slots=True)
class HistoricalResearchSpecification:
    name: str
    family: str
    params: MappingProxyType
    control: bool
    source_path: str
    source_git_blob: str
    execution_status: str = field(default="SPEC_ONLY", init=False)
    signal_generator: None = field(default=None, init=False)
    source_commit: str = field(default=_SOURCE_COMMIT, init=False)
    source_authentication: str = field(default="NOT_EVALUATED", init=False)
    execution_authority: bool = field(default=False, init=False)
    trading_authorized: bool = field(default=False, init=False)


# Immutable literal metadata, not original executable imports. Preserve the
# literal parameter spellings/tuple order and source-defined control fields.
# Only the canonical Terminan PaperEngine can simulate trades, separately
# subject to source and execution checks. Nothing here invokes a generator.
_ITEMS = (
    ("LEVEL_BASE", "levels", (), True, "research_levels.py"),
    ("LEVEL_VOLUME", "levels", (("confirm", "volume"),), False, "research_levels.py"),
    ("LEVEL_OI", "levels", (("confirm", "open_interest"),), False, "research_levels.py"),
    ("LEVEL_POC", "levels", (("confirm", "poc"),), False, "research_levels.py"),
    ("LEVEL_BREAKOUT_RETEST", "levels", (("setup", "breakout_retest"),), False, "research_levels.py"),

    ("POC_MEAN_REVERSION", "poc", (("setup", "mean_reversion"),), False, "research_poc.py"),
    ("POC_BREAKOUT_RETEST", "poc", (("setup", "breakout_retest"),), False, "research_poc.py"),
    ("POC_VAH_VAL_REJECTION", "poc", (("setup", "value_area_rejection"),), False, "research_poc.py"),
    ("POC_MIGRATION", "poc", (("setup", "poc_migration"),), False, "research_poc.py"),

    ("VOL_COMPRESSION_EXPANSION", "volatility", (("setup", "compression_expansion"),), False, "research_volatility.py"),
    ("VOL_EXPANSION_CONTINUATION", "volatility", (("setup", "expansion_continuation"),), False, "research_volatility.py"),
    ("VOL_EXHAUSTION", "volatility", (("setup", "exhaustion"),), False, "research_volatility.py"),

    ("SMC_CONTROL_MOMENTUM", "smc", (("setup", "momentum"),), True, "research_smc.py"),
    ("SMC_OB", "smc", (("setup", "order_block"),), False, "research_smc.py"),
    ("SMC_OB_FVG", "smc", (("setup", "order_block"), ("confirm", "fvg")), False, "research_smc.py"),
    ("SMC_OB_BOS", "smc", (("setup", "order_block"), ("confirm", "bos")), False, "research_smc.py"),
    ("SMC_SWEEP_BOS", "smc", (("setup", "liquidity_sweep"), ("confirm", "bos")), False, "research_smc.py"),
    ("SMC_HTF_BIAS_LTF_SWEEP", "smc", (
        ("bias_timeframes", ("4h", "1h")), ("entry_timeframes", ("15m", "5m", "1m")),
        ("setup", "liquidity_sweep")), False, "research_smc.py"),

    ("ORDERFLOW_ABSORPTION_PROXY", "orderflow", (
        ("setup", "absorption"), ("mode", "ABSORPTION_PROXY"),
        ("entry_parts", (0.5, 0.5)), ("tp_parts", (0.6, 0.4)),
        ("requires", ("public_trade_aggregates", "level", "cvd", "aggression_decay"))),
        False, "research_smc.py"),
    ("ORDERFLOW_SWEEP_REVERSAL", "orderflow", (
        ("setup", "liquidity_sweep_reversal"),
        ("requires", ("level", "public_trade_aggregates", "cvd")),
        ("return_inside_required", True)), False, "research_smc.py"),
)


def historical_research_specifications():
    """Return fresh immutable archival descriptors (20 SPEC_ONLY, zero grants).

    Metadata transfer is separate from executable research; no synthetic
    implied exchange/OI/L2 source, source attestation, or PaperEngine enabling.
    """
    return tuple(
        HistoricalResearchSpecification(name, family, MappingProxyType(dict(pairs)),
                                        control, _SOURCE_PATH + filename,
                                        _SOURCE_BLOBS[filename])
        for name, family, pairs, control, filename in _ITEMS
    )


def historical_research_specification(name):
    """Resolve one original name; a lookup cannot invoke old code."""
    if type(name) is not str or not 1 <= len(name) <= 128 or not name.isascii():
        raise ValueError("HISTORICAL_HYPOTHESIS_LITERAL_NAME_REQUIRED")
    for record in historical_research_specifications():
        if record.name == name:
            return record
    raise ValueError("HISTORICAL_HYPOTHESIS_UNKNOWN_NAME")


def historical_research_family(family):
    """List original hypotheses from one explicitly named source family."""
    if type(family) is not str or family not in (
        "levels", "poc", "volatility", "smc", "orderflow"
    ):
        raise ValueError("HISTORICAL_HYPOTHESIS_KNOWN_FAMILY_REQUIRED")
    return tuple(item for item in historical_research_specifications()
                 if item.family == family)
