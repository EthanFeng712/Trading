from collections import deque
from dataclasses import dataclass
from typing import ClassVar

from ..data.data_loader import Bar
from ..utils.indicators import RollingSMA
from .base import BaseStrategy


@dataclass(frozen=True)
class SmaCrossConfig:
    fast_window: int = 25
    slow_window: int = 99
    target_size: float = 0.2

    def __post_init__(self) -> None:
        if (
            type(self.fast_window) is not int
            or self.fast_window <= 0
            or type(self.slow_window) is not int
            or self.slow_window <= 0
        ):
            raise ValueError("SMA 窗口必须为正整数")
        if self.fast_window >= self.slow_window:
            raise ValueError("快线窗口必须小于慢线窗口")
        if not 0 < self.target_size <= 1:
            raise ValueError("目标仓位大小应该处于 0 到 1 之间")


class SmaCrossStrategy(BaseStrategy):
    name: ClassVar[str] = "SMA Cross"
    config: SmaCrossConfig

    def __init__(self, config: SmaCrossConfig | None = None) -> None:
        self.config = config if config is not None else SmaCrossConfig()
        self.fast = RollingSMA(self.config.fast_window)
        self.slow = RollingSMA(self.config.slow_window)
        self.fast_sma: deque[float | None] = deque(maxlen=2)
        self.slow_sma: deque[float | None] = deque(maxlen=2)

    def generate_signal(self, index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None

        self.fast_sma.append(self.fast.update(previous_bar.close))
        self.slow_sma.append(self.slow.update(previous_bar.close))

        if len(self.fast_sma) < 2 or len(self.slow_sma) < 2:
            return None

        if self.fast_sma[-2] is None or self.slow_sma[-2] is None or self.fast_sma[-1] is None or self.slow_sma[-1] is None:
            return None

        buy_signal = self.fast_sma[-2] <= self.slow_sma[-2] and self.fast_sma[-1] > self.slow_sma[-1]
        sell_signal = self.fast_sma[-2] >= self.slow_sma[-2] and self.fast_sma[-1] < self.slow_sma[-1]
        if buy_signal:
            return self.config.target_size
        if sell_signal:
            return -self.config.target_size
        return None

    def reset(self) -> None:
        self.fast = RollingSMA(self.config.fast_window)
        self.slow = RollingSMA(self.config.slow_window)
        self.fast_sma = deque(maxlen=2)
        self.slow_sma = deque(maxlen=2)
