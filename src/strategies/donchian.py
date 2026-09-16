from collections import deque
from dataclasses import dataclass
from math import isfinite

from .base import BaseStrategy
from ..data.data_loader import Bar


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

        # 用 while 而非 if：引擎恒以 index 递增 1 调用，两者等价；但一旦出现跳号，
        # if 每次只淘汰一个过期元素，会让通道混入早已失效的 K 线。
        while len(self.last_maximums) > 0 and index - self.last_maximums[0][0] > self.config.window:
            self.last_maximums.popleft()
        while len(self.last_minimums) > 0 and index - self.last_minimums[0][0] > self.config.window:
            self.last_minimums.popleft()
        highest_previous = self.last_maximums[0][1] if len(self.last_maximums) > 0 else None
        lowest_previous = self.last_minimums[0][1] if len(self.last_minimums) > 0 else None

        while len(self.last_maximums) > 0 and self.last_maximums[-1][1] < previous_bar.high:
            self.last_maximums.pop()
        self.last_maximums.append((index, previous_bar.high))
        while len(self.last_minimums) > 0 and self.last_minimums[-1][1] > previous_bar.low:
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
