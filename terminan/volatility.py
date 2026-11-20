"""Typed causal volatility observations; every numerical formula belongs to Math."""
from dataclasses import dataclass,field
from enum import Enum
class VolatilityRegime(str,Enum):
    VERY_LOW='VERY_LOW'
    LOW='LOW'
    NORMAL='NORMAL'
    HIGH='HIGH'
    EXTREME='EXTREME'
@dataclass(frozen=True)
class VolatilityMetrics:
    event_start_ms:int
    available_at_ms:int
    atr_fraction:float
    realized_volatility:float
    parkinson_volatility:float
    range_fraction:float
    volume_ratio:float
    turnover_ratio:float
    atr_percentile:float
    regime:VolatilityRegime
    version:str
    availability_basis:str=field(default='CALLER_DECLARED_PREFIX_MAX',init=False)
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)
@dataclass(frozen=True)
class VolatilityAnalyzer:
    window:int=20
    percentile_lookback:int=252
    version:str='volatility.v1'
    def __post_init__(self):
        if type(self.version) is not str or not 1<=len(self.version)<=128 or not self.version.isascii():raise ValueError('VOLATILITY_VERSION_REQUIRED')
    def analyze(self,candles,*,bar_duration_ms):
        from market_compute_api import VOLATILITY_ABI,causal_volatility_metrics
        if VOLATILITY_ABI!='math.market.volatility.binary64.v2':raise RuntimeError('UNSUPPORTED_VOLATILITY_ABI')
        rows=causal_volatility_metrics(candles,window=self.window,percentile_lookback=self.percentile_lookback,bar_duration_ms=bar_duration_ms)
        regimes=tuple(VolatilityRegime)
        return tuple(VolatilityMetrics(*row[:-1],regimes[row[-1]],self.version) for row in rows)
