from collections import deque

class RollingSMA:
    def __init__(self, window: int):
        if type(window) is not int or window <= 0:
            raise ValueError("SMA 窗口必须为正整数")
        self.window = window
        self.sma: float | None = None
        self.closes: deque[float] = deque()

    def update(self, close: float) -> float | None:
        self.closes.append(close)
        if len(self.closes) < self.window:
            return None
        elif len(self.closes) == self.window:
            self.sma = sum(self.closes) / self.window
        else:
            self.sma = self.sma + (close - self.closes.popleft()) / self.window
        return self.sma

def simple_moving_average(values: list[float], window: int) -> list[float | None]:
    if type(window) is not int or window <= 0:
        raise ValueError("window must be a positive integer")
    sma: list[float | None] = [None] * len(values)
    running_sum = 0.0
    for i, value in enumerate(values):
        running_sum += value
        if i >= window:
            running_sum -= values[i - window]
        if i >= window - 1:
            sma[i] = running_sum / window
    return sma
