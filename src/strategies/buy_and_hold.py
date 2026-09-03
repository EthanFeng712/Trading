from dataclasses import dataclass

from ..data.data_loader import Bar
from .base import BaseStrategy


@dataclass
class BuyAndHoldStrategy(BaseStrategy):
    has_bought: bool = False
    
    def reset(self) -> None:
        self.has_bought = False

    def generate_signal(self, _index: int, _previous_bar: Bar | None) -> float | None:
        if not self.has_bought:
            self.has_bought = True
            return 0.2
        return None
