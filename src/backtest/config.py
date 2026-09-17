from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    maintenance_margin_rate: float = 0.1
    rebalance_tolerance: float = 0.001
    # 以下三项为可选风险控件，默认关闭（None / 0）。仅在显式设置后激活，
    # 因此不影响任何既有的默认回测路径与测试基线。
    stop_loss_rate: float | None = None
    vol_target_annual: float | None = None
    vol_lookback: int = 20

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

        if self.stop_loss_rate is not None:
            if not isfinite(self.stop_loss_rate) or self.stop_loss_rate <= 0.0:
                raise ValueError("止损率必须为正数")
            if self.stop_loss_rate > 0.9:
                raise ValueError("止损率应不超过 0.9（90%）")
        if self.vol_target_annual is not None:
            if not isfinite(self.vol_target_annual) or self.vol_target_annual <= 0.0:
                raise ValueError("波动率目标必须为正数")
            if self.vol_target_annual > 2.0:
                raise ValueError("波动率目标应不超过 2.0（200%）")
        if type(self.vol_lookback) is not int or self.vol_lookback <= 1:
            raise ValueError("波动率回看窗口必须为大于 1 的整数")
