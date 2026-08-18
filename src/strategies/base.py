from abc import ABC, abstractmethod
from enum import Enum

from ..data.data_loader import Bar

class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"

class BaseStrategy(ABC):
    """Base class for all strategies.

    generate_signal should return: Signal
    """
    
    def reset(self) -> None:
        """Reset the strategy state."""
        pass

    @abstractmethod
    def generate_signal(self, ohlcv: list[Bar]) -> Signal:
        raise NotImplementedError
