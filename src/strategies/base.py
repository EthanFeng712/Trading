from abc import ABC, abstractmethod
from typing import ClassVar

from ..data.data_loader import Bar


class BaseStrategy(ABC):
    """Base class for all strategies.

    generate_signal should return a float between -1.0 and 1.0 representing the desired position size
    """

    name: ClassVar[str] = "Base Strategy"

    def reset(self) -> None:
        """Reset the strategy state."""
        pass

    @abstractmethod
    def generate_signal(self, index: int, previous_bar: Bar | None) -> float | None:
        raise NotImplementedError
