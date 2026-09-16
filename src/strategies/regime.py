from collections import deque
from dataclasses import dataclass
from math import isfinite

from .base import BaseStrategy
from ..data.data_loader import Bar


@dataclass(frozen=True)
class RegimeConfig:
    """市场状态过滤器配置。

    仅当市场处于与信号同向的趋势状态时，才允许被包裹的趋势策略开仓；否则
    强制空仓。这是针对「趋势策略在震荡市无状态过滤、照常满仓」这一根本
    缺陷的修复。

    ma_window : 长周期均线窗口（根 K 线），用于判断趋势方向。默认 100。
    band      : 中性带（相对 MA 的比例）。收盘价位于 MA*(1±band) 之间视为
                震荡（RANGING），强制空仓；上穿上界视为上行趋势，下穿下界
                视为下行趋势。默认 0.0（即收盘价严格在 MA 上方才视为上行）。
    """

    ma_window: int = 100
    band: float = 0.0

    def __post_init__(self) -> None:
        if type(self.ma_window) is not int or self.ma_window <= 1:
            raise ValueError("均线窗口必须为大于 1 的整数")
        if not isfinite(self.band) or self.band < 0:
            raise ValueError("中性带 band 应不小于 0")


class RegimeFilteredStrategy(BaseStrategy):
    """状态过滤包装器：包裹任意策略，按市场状态门控其信号。

    门控规则（仅对趋势策略有意义，不建议包裹均值回归策略）：
        收盘价 > MA*(1+band)  -> 上行趋势：仅放行做多信号，做空/持空改为平仓(0.0)
        收盘价 < MA*(1-band)  -> 下行趋势：仅放行做空信号，做多/持多改为平仓(0.0)
        其余（中性带内）       -> 震荡：所有信号改为平仓(0.0)，强制空仓

    包装器内部跟踪自身给出的目标仓位符号，以正确处理「状态翻转时平掉逆势
    旧仓」的情形。reset() 会同时重置内部状态与被包裹策略。

    不持有仓位且信号为空时返回 None；需平仓时返回 0.0；否则透传内部信号。
    """

    config: RegimeConfig
    inner: BaseStrategy
    closes: deque[float]
    _pos: int

    def __init__(self, inner: BaseStrategy, config: RegimeConfig | None = None) -> None:
        self.inner = inner
        self.config = config if config is not None else RegimeConfig()
        self.closes = deque(maxlen=self.config.ma_window * 2)
        self._pos = 0

    def _regime(self, close: float) -> int:
        """返回 1=上行趋势，-1=下行趋势，0=震荡（含预热期）。"""
        if len(self.closes) < self.config.ma_window:
            return 0
        window = self.config.ma_window
        recent = list(self.closes)[-window:]
        sma = sum(recent) / window
        upper = sma * (1.0 + self.config.band)
        lower = sma * (1.0 - self.config.band)
        if close > upper:
            return 1
        if close < lower:
            return -1
        return 0

    def generate_signal(self, index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None

        self.closes.append(previous_bar.close)
        inner_sig = self.inner.generate_signal(index, previous_bar)
        regime = self._regime(previous_bar.close)

        if regime == 0:
            # 震荡：强制空仓（若本就空仓，0.0 与 None 等价，不产生交易）
            out: float | None = 0.0
        elif regime == 1:  # 上行趋势
            if inner_sig is not None and inner_sig > 0:
                out = inner_sig
            elif inner_sig is not None and inner_sig <= 0:
                out = 0.0
            else:  # inner_sig 为 None：保留多头、平掉逆势空头
                out = 0.0 if self._pos < 0 else None
        else:  # regime == -1 下行趋势
            if inner_sig is not None and inner_sig < 0:
                out = inner_sig
            elif inner_sig is not None and inner_sig >= 0:
                out = 0.0
            else:  # inner_sig 为 None：保留空头、平掉逆势多头
                out = 0.0 if self._pos > 0 else None

        if out is not None:
            if out > 0:
                self._pos = 1
            elif out < 0:
                self._pos = -1
            else:
                self._pos = 0
        return out

    def reset(self) -> None:
        self.closes = deque(maxlen=self.config.ma_window * 2)
        self._pos = 0
        self.inner.reset()
