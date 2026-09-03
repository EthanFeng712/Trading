from dataclasses import dataclass

from ..utils.indicators import RollingSMA
from .base import BaseStrategy
from ..data.data_loader import Bar


@dataclass
class SmaCrossStrategy(BaseStrategy):
    fast_window: int = 10
    slow_window: int = 30

    def __init__(self, fast_window: int = 10, slow_window: int = 30):
        if fast_window <= 0 or slow_window <= 0:
            raise ValueError("SMA 窗口必须为正数")
        if fast_window >= slow_window:
            raise ValueError("快线窗口必须小于慢线窗口")
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.fast = RollingSMA(fast_window)
        self.slow = RollingSMA(slow_window)
        self.fast_sma: list[float | None] = []
        self.slow_sma: list[float | None] = []

    def generate_signal(self, _index: int, previous_bar: Bar | None) -> float | None:
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
            return 0.2
        if sell_signal:
            return -0.2
        return None

    def reset(self) -> None:
        self.fast = RollingSMA(self.fast_window)
        self.slow = RollingSMA(self.slow_window)
        self.fast_sma = []
        self.slow_sma = []
