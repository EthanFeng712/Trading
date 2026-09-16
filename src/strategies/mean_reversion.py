from collections import deque
from dataclasses import dataclass
from math import isfinite, sqrt

from .base import BaseStrategy
from ..data.data_loader import Bar
from ..utils.indicators import RollingSMA


@dataclass(frozen=True)
class MeanReversionConfig:
    """均值回归策略的可配置参数。

    window   : 均值与标准差的计算周期（根 K 线），须 > 1。
    entry_z  : 入场阈值（z-score 绝对值）。价格偏离均值超过 +entry_z 视为超买、
               低于 -entry_z 视为超卖，触发反向信号。须 > 0。
    exit_z   : 平仓阈值（z-score 绝对值）。偏离回落到 [-exit_z, +exit_z] 内时平仓。
               须满足 0 <= exit_z < entry_z。
    target_size: 触发时的目标仓位绝对值，约束于 (0, 1]。
    """

    window: int = 20
    entry_z: float = 2.0
    exit_z: float = 0.5
    target_size: float = 0.2

    def __post_init__(self) -> None:
        if type(self.window) is not int or self.window <= 1:
            raise ValueError("均值窗口必须为大于 1 的整数")
        if not isfinite(self.entry_z) or self.entry_z <= 0:
            raise ValueError("入场阈值 entry_z 应为正数")
        if not isfinite(self.exit_z) or self.exit_z < 0:
            raise ValueError("平仓阈值 exit_z 应不小于 0")
        if self.exit_z >= self.entry_z:
            raise ValueError("平仓阈值 exit_z 应小于入场阈值 entry_z")
        if not 0 < self.target_size <= 1:
            raise ValueError("目标仓位大小应在 0 到 1.0 之间")


class MeanReversionStrategy(BaseStrategy):
    """均值回归：衡量价格相对滚动均值的 z-score 偏离，在极端偏离时反向开仓。

    接口约定
    --------
    输入 : generate_signal(index, previous_bar)
           previous_bar 为「已收盘」的 K 线（Bar）。本策略仅使用 previous_bar.close
           与内部维护的滚动收盘价窗口。
    输出 : float，表示目标仓位，约束于 [-1.0, 1.0]；返回 None 表示维持当前仓位。

    信号生成规则
    ------------
        z = (close - mean) / std      # std 为 window 内总体标准差
        z >  +entry_z -> 做空 (-target_size)   价格远高于均值，预期回落
        z <  -entry_z -> 做多 (+target_size)   价格远低于均值，预期反弹
        |z| <= exit_z -> 平仓 (0.0)           已回归均值
        其余          -> 维持现状 (None)        介于双阈值之间，保持仓位
    """

    config: MeanReversionConfig
    closes: deque[float]
    sma: RollingSMA

    def __init__(self, config: MeanReversionConfig | None = None) -> None:
        self.config = config if config is not None else MeanReversionConfig()
        self.closes = deque(maxlen=self.config.window)
        self.sma = RollingSMA(self.config.window)

    def generate_signal(self, _index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None

        self.closes.append(previous_bar.close)
        mean = self.sma.update(previous_bar.close)
        if mean is None or len(self.closes) < self.config.window:
            return None

        var = sum((c - mean) ** 2 for c in self.closes) / self.config.window
        std = sqrt(var)
        if std <= 1e-12:
            return None

        z = (previous_bar.close - mean) / std
        if z > self.config.entry_z:
            return -self.config.target_size
        if z < -self.config.entry_z:
            return self.config.target_size
        if abs(z) <= self.config.exit_z:
            return 0.0
        return None

    def reset(self) -> None:
        self.closes = deque(maxlen=self.config.window)
        self.sma = RollingSMA(self.config.window)
