from dataclasses import dataclass

from ..data.data_loader import Bar
from .base import BaseStrategy
from .base import Signal


@dataclass
class BuyAndHoldStrategy(BaseStrategy):
    has_bought: bool = False
    
    def reset(self) -> None:
        self.has_bought = False

    def generate_signal(self, ohlcv: list[Bar]) -> Signal:
        if not self.has_bought:
            self.has_bought = True
            return Signal.BUY
        return Signal.NONE
