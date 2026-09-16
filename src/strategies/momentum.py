from collections import deque
from dataclasses import dataclass
from math import isfinite

from .base import BaseStrategy
from ..data.data_loader import Bar

# 内部派生超参：趋势判定窗口与中性带。
# 不暴露为配置字段，以保证 MomentumConfig 的参数框架（lookback/threshold/target_size）不变；
# 趋势窗口需显著长于动量窗口，才能可靠区分「趋势」与「短期噪声」。
def _default_trend_window(lookback: int) -> int:
    return max(lookback * 4, 60)


_TREND_BAND = 0.0  # 收盘价须严格高于/低于长均线才判定为趋势方向（无缓冲带）


@dataclass(frozen=True)
class MomentumConfig:
    """动量趋势跟踪策略的可配置参数。

    lookback   : 动量计算周期（根 K 线）。用当前收盘价与 lookback 根之前的收盘价
                 计算累计收益率，作为趋势强度代理。
    threshold  : 触发阈值（绝对收益率，>=0）。动量超过 +threshold 视为上行趋势、
                 低于 -threshold 视为下行趋势；落入 [-threshold, +threshold] 死区则
                 维持现状。设为 0 即「纯符号」趋势判断。
    target_size: 触发时的目标仓位绝对值，约束于 (0, 1]。
    """

    lookback: int = 20
    threshold: float = 0.0
    target_size: float = 0.2

    def __post_init__(self) -> None:
        if type(self.lookback) is not int or self.lookback <= 0:
            raise ValueError("动量窗口必须为正整数")
        if not isfinite(self.threshold):
            raise ValueError("触发阈值应为有限数")
        if self.threshold < 0:
            raise ValueError("触发阈值应不小于 0")
        if not 0 < self.target_size <= 1:
            raise ValueError("目标仓位大小应在 0 到 1.0 之间")


class MomentumStrategy(BaseStrategy):
    """趋势跟踪：基于价格动量 + 长周期趋势状态门控判断趋势方向。

    接口约定
    --------
    输入 : generate_signal(index, previous_bar)
           previous_bar 为「已收盘」的 K 线（Bar），提供 open/high/low/close/volume/timestamp。
           本策略仅使用 previous_bar.close 与内部维护的滚动收盘价序列。
    输出 : float，表示目标仓位，约束于 [-1.0, 1.0]；返回 None 表示维持当前仓位。

    信号生成规则（就地优化版）
    --------------------------
    1. 动量代理：momentum = close_now / close_{now-lookback} - 1
       momentum >  +threshold  -> 期望做多 (+target_size)   上行动量
       momentum <  -threshold  -> 期望做空 (-target_size)   下行动量
       |momentum| <= threshold -> 死区，维持现状 (None)

    2. 趋势状态门控（稳健性核心，固有逻辑，非可切换模块）：
       以更长周期（默认 max(lookback*4, 60) 根）的滚动均线为基准，判断市场所处状态：
         收盘价 >  MA*(1+band) -> 上行趋势：仅放行做多期望
         收盘价 <  MA*(1-band) -> 下行趋势：仅放行做空期望
         其余（均线附近/中性带内）-> 震荡：所有方向期望均被抑制为 None（强制空仓）
       即「动量看多但不在上行趋势」或「动量看空但不在下行趋势」均不开仓，
       从信号源头消除震荡市逆势追涨杀跌——这是诊断中近期持续亏损的根本诱因。

    3. 预热与数值稳健：
       - 动量窗口或趋势窗口样本不足时返回 None，避免短历史噪声误判；
       - 收盘价非有限或历史基准价 <= 0 时返回 None，杜绝除零/NaN 传播。

    效率
    ----
    趋势均线通过滚动和（running sum）在 O(1) 内更新，避免每根 K 线重新求和，
    长序列回测的均线计算开销由 O(N·W) 降至 O(N)。
    """

    config: MomentumConfig
    closes: deque[float]
    trend_closes: deque[float]
    _trend_sum: float
    _trend_window: int

    def __init__(self, config: MomentumConfig | None = None) -> None:
        self.config = config if config is not None else MomentumConfig()
        self._trend_window = _default_trend_window(self.config.lookback)
        self.closes = deque(maxlen=self.config.lookback + 1)
        self.trend_closes = deque(maxlen=self._trend_window)
        self._trend_sum = 0.0

    def _push_trend(self, close: float) -> None:
        """O(1) 维护趋势窗口的滚动和：挤出最旧值、纳入新值。"""
        if len(self.trend_closes) == self._trend_window:
            self._trend_sum -= self.trend_closes[0]
        self.trend_closes.append(close)
        self._trend_sum += close

    def _regime(self, close: float) -> int:
        """返回 1=上行趋势，-1=下行趋势，0=震荡/未知（含预热期）。"""
        if len(self.trend_closes) < self._trend_window:
            return 0
        sma = self._trend_sum / self._trend_window
        if sma <= 0:
            return 0
        upper = sma * (1.0 + _TREND_BAND)
        lower = sma * (1.0 - _TREND_BAND)
        if close > upper:
            return 1
        if close < lower:
            return -1
        return 0

    def generate_signal(self, _index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None
        close = previous_bar.close
        if not isfinite(close):
            return None

        self.closes.append(close)
        self._push_trend(close)

        # 预热：动量窗口与长趋势窗口均需足够样本，否则返回 None
        if len(self.closes) <= self.config.lookback:
            return None
        if len(self.trend_closes) < self._trend_window:
            return None

        past_close = self.closes[0]
        if past_close <= 0 or not isfinite(past_close):
            return None
        momentum = close / past_close - 1.0

        if momentum > self.config.threshold:
            raw = self.config.target_size
        elif momentum < -self.config.threshold:
            raw = -self.config.target_size
        else:
            return None  # 死区维持现状

        # 趋势状态门控：仅当期望方向与所处趋势同向时才开仓
        regime = self._regime(close)
        if raw > 0 and regime == 1:
            return raw
        if raw < 0 and regime == -1:
            return raw
        return None

    def reset(self) -> None:
        self.closes = deque(maxlen=self.config.lookback + 1)
        self.trend_closes = deque(maxlen=self._trend_window)
        self._trend_sum = 0.0
