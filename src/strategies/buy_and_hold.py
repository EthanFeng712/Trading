from dataclasses import dataclass
from typing import ClassVar

from ..data.data_loader import Bar
from .base import BaseStrategy


@dataclass
class BuyAndHoldStrategy(BaseStrategy):
    name: ClassVar[str] = "Buy and Hold"
    has_bought: bool = False

    def reset(self) -> None:
        self.has_bought = False

    def generate_signal(self, index: int, previous_bar: Bar | None) -> float | None:
        if not self.has_bought:
            self.has_bought = True
            return 1.0
        return None
