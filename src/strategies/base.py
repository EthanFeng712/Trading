from abc import ABC, abstractmethod

from ..data.data_loader import Bar

class BaseStrategy(ABC):
    """Base class for all strategies.

    generate_signal should return a float between -1.0 and 1.0 representing the desired position size
    """
    
    def reset(self) -> None:
        """Reset the strategy state."""
        pass

    @abstractmethod
    def generate_signal(self, ohlcv: list[Bar]) -> float | None:
        raise NotImplementedError
