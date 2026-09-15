from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    maintenance_margin_rate: float = 0.1
    rebalance_tolerance: float = 0.001

    def __post_init__(self) -> None:
        values = (
            self.initial_cash,
            self.commission_rate,
            self.slippage_rate,
            self.maintenance_margin_rate,
            self.rebalance_tolerance,
        )

        if not all(isfinite(value) for value in values):
            raise ValueError("回测配置必须是有限数")
        if self.initial_cash <= 0.0:
            raise ValueError("初始资金应大于 0")
        if self.commission_rate < 0.0:
            raise ValueError("手续费应大于等于 0")
        if not 0.0 <= self.slippage_rate <= 0.02:
            raise ValueError("滑点应处于 0 到 2% 之间")
        if not 0.0 <= self.maintenance_margin_rate <= 0.2:
            raise ValueError("维持保证金率应处于 0 到 20% 之间")
        if not 0.0 <= self.rebalance_tolerance < 1.0:
            raise ValueError("再平衡容差应处于 0 到 1 之间")
