from collections import deque
from dataclasses import dataclass
from math import isfinite

from .base import BaseStrategy
from ..data.data_loader import Bar


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
    """趋势跟踪：基于价格动量（过去 lookback 根 K 线的累计收益率）判断趋势方向。

    接口约定
    --------
    输入 : generate_signal(index, previous_bar)
           previous_bar 为「已收盘」的 K 线（Bar），提供 open/high/low/close/volume/timestamp。
           本策略仅使用 previous_bar.close 与内部维护的滚动收盘价序列。
    输出 : float，表示目标仓位，约束于 [-1.0, 1.0]；返回 None 表示维持当前仓位。

    信号生成规则
    ------------
        momentum = close_now / close_{now-lookback} - 1
        momentum >  +threshold  -> 做多 (+target_size)   上行趋势
        momentum <  -threshold  -> 做空 (-target_size)   下行趋势
        |momentum| <= threshold -> 维持现状 (None)        死区内保持已有仓位
    """

    config: MomentumConfig
    closes: deque[float]

    def __init__(self, config: MomentumConfig | None = None) -> None:
        self.config = config if config is not None else MomentumConfig()
        self.closes = deque(maxlen=self.config.lookback + 1)

    def generate_signal(self, _index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None

        self.closes.append(previous_bar.close)
        if len(self.closes) <= self.config.lookback:
            return None

        past_close = self.closes[0]
        if past_close <= 0:
            return None
        momentum = previous_bar.close / past_close - 1.0

        if momentum > self.config.threshold:
            return self.config.target_size
        if momentum < -self.config.threshold:
            return -self.config.target_size
        return None

    def reset(self) -> None:
        self.closes = deque(maxlen=self.config.lookback + 1)
