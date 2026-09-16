from collections import deque
from dataclasses import dataclass
from math import isfinite
from typing import ClassVar

from ..data.data_loader import Bar
from .base import BaseStrategy


@dataclass(frozen=True)
class DonchianConfig:
    window: int = 20
    target_size: float = 0.2

    def __post_init__(self) -> None:
        if type(self.window) is not int or self.window <= 0:
            raise ValueError("窗口大小应为正整数")
        if not isfinite(self.target_size):
            raise ValueError("目标仓位大小应为有限数")
        if not 0 < self.target_size <= 1:
            raise ValueError("目标仓位大小应在 0 到 1.0 之间")


class DonchianStrategy(BaseStrategy):
    name: ClassVar[str] = "Donchian Channel"
    config: DonchianConfig
    last_maximums: deque[tuple[int, float]]
    last_minimums: deque[tuple[int, float]]

    def __init__(self, config: DonchianConfig | None = None) -> None:
        self.config = config if config is not None else DonchianConfig()
        self.last_maximums = deque()
        self.last_minimums = deque()

    def generate_signal(self, index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None

        while self.last_maximums and index - self.last_maximums[0][0] > self.config.window:
            self.last_maximums.popleft()
        while self.last_minimums and index - self.last_minimums[0][0] > self.config.window:
            self.last_minimums.popleft()
        highest_previous = self.last_maximums[0][1] if self.last_maximums else None
        lowest_previous = self.last_minimums[0][1] if self.last_minimums else None

        while self.last_maximums and self.last_maximums[-1][1] < previous_bar.high:
            self.last_maximums.pop()
        self.last_maximums.append((index, previous_bar.high))
        while self.last_minimums and self.last_minimums[-1][1] > previous_bar.low:
            self.last_minimums.pop()
        self.last_minimums.append((index, previous_bar.low))

        if index <= self.config.window:
            return None
        if highest_previous is not None and previous_bar.close > highest_previous:
            return self.config.target_size
        if lowest_previous is not None and previous_bar.close < lowest_previous:
            return -self.config.target_size
        return None

    def reset(self) -> None:
        self.last_maximums = deque()
        self.last_minimums = deque()
