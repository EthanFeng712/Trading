from dataclasses import dataclass

from ..utils.indicators import simple_moving_average
from .base import BaseStrategy
from .base import Signal
from ..data.data_loader import Bar


@dataclass
class SmaCrossStrategy(BaseStrategy):
    fast_window: int = 10
    slow_window: int = 30

    def generate_signal(self, ohlcv: list[Bar]) -> Signal:
        closes = [bar.close for bar in ohlcv]
        if not closes:
            return Signal.NONE

        fast_sma = simple_moving_average(closes, self.fast_window)
        slow_sma = simple_moving_average(closes, self.slow_window)

        if len(fast_sma) < 2 or len(slow_sma) < 2:
            return Signal.NONE

        if fast_sma[-2] is None or slow_sma[-2] is None or fast_sma[-1] is None or slow_sma[-1] is None:
            return Signal.NONE

        buy_signal = fast_sma[-2] <= slow_sma[-2] and fast_sma[-1] > slow_sma[-1]
        sell_signal = fast_sma[-2] >= slow_sma[-2] and fast_sma[-1] < slow_sma[-1]
        if buy_signal:
            return Signal.BUY
        if sell_signal:
            return Signal.SELL
        return Signal.NONE
