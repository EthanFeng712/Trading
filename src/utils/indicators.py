from typing import List, Optional


def simple_moving_average(values: List[float], window: int) -> List[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    sma: List[float | None] = [None] * len(values)
    running_sum = 0.0
    for i, value in enumerate(values):
        running_sum += value
        if i >= window:
            running_sum -= values[i - window]
        if i >= window - 1:
            sma[i] = running_sum / window
    return sma
