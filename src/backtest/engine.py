from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .config import BacktestConfig
from ..data.data_loader import Bar
from ..strategies.base import BaseStrategy


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


@dataclass
class Position:
    side: PositionSide = PositionSide.NONE
    quantity: float = 0.0  # 持仓数量
    entry_timestamp: datetime | None = None
    total_entry_price: float = 0.0  # 累计开仓成交额
    total_entry_quantity: float = 0.0  # 累计开仓数量
    total_exit_price: float = 0.0
    max_quantity: float = 0.0
    equity_when_entry: float = 0.0
    commission: float = 0.0
    count: int = 0


@dataclass
class Trade:
    side: PositionSide
    entry_time: datetime
    exit_time: datetime
    average_entry_price: float
    average_exit_price: float
    cumulative_quantity: float
    max_quantity: float
    count: int
    gross_pnl: float
    commission: float
    net_pnl: float


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    equity: float


@dataclass(frozen=True)
class BacktestResult:
    initial_cash: float
    final_cash: float
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    liquidated: bool = False


class SimpleBacktestEngine:
    cash: float
    config: BacktestConfig
    position: Position
    trades: list[Trade]
    liquidated: bool

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config if config is not None else BacktestConfig()
        self.cash = self.config.initial_cash
        self.position = Position()
        self.trades = []
        self.liquidated = False

    def check_liquidate(self, price: float) -> bool:
        if self.position.quantity < 0:
            equity = self.cash + self.position.quantity * price
            maintenance_margin = (
                abs(self.position.quantity)
                * price
                * self.config.maintenance_margin_rate
            )
            if equity <= maintenance_margin:
                return True
        return False

    def liquidate(self, bar: Bar, price: float) -> None:
        quantity = -self.position.quantity
        if quantity > 0:
            fill_price = price * (1 + self.config.slippage_rate)
        else:
            fill_price = price * (1 - self.config.slippage_rate)
        self.opt(bar, quantity, fill_price)


    def opt(self, bar: Bar, quantity: float, fill_price: float) -> None:
        if abs(quantity) < 1e-8 or self.liquidated:
            return

        closes_position = (
            (self.position.quantity + quantity) * self.position.quantity <= 0
            or abs(self.position.quantity + quantity) < 1e-8
        )
        if abs(self.position.quantity) > 1e-8 and closes_position:
            self.cash += (
                fill_price * self.position.quantity
                - fill_price
                * self.config.commission_rate
                * abs(self.position.quantity)
            )
            self.position.commission += (
                fill_price
                * self.config.commission_rate
                * abs(self.position.quantity)
            )
            self.position.total_exit_price += fill_price * abs(self.position.quantity)
            pnl = self.cash - self.position.equity_when_entry
            entry_timestamp = self.position.entry_timestamp
            if entry_timestamp is None:
                raise RuntimeError("持仓缺少开仓时间")
            self.trades.append(Trade(
                side=self.position.side,
                entry_time=entry_timestamp,
                exit_time=bar.timestamp,
                average_entry_price=self.position.total_entry_price / self.position.total_entry_quantity if self.position.total_entry_quantity != 0 else 0.0,
                average_exit_price=self.position.total_exit_price / self.position.total_entry_quantity if self.position.total_entry_quantity != 0 else 0.0,
                cumulative_quantity=self.position.total_entry_quantity,
                max_quantity=self.position.max_quantity,
                count=self.position.count + 1,
                gross_pnl=pnl + self.position.commission,
                commission=self.position.commission,
                net_pnl=pnl
            ))
            quantity += self.position.quantity
            self.position = Position()

        required_cash = (
            fill_price * quantity
            + fill_price * self.config.commission_rate * abs(quantity)
        )
        if (
            quantity > 1e-8
            and self.position.quantity >= 0
            and self.cash < required_cash
        ):
            quantity = self.cash / (fill_price * (1 + self.config.commission_rate))
        if abs(quantity) < 1e-8:
            return

        if self.position.quantity == 0:  # 创建新持仓
            self.position.side = (
                PositionSide.LONG if quantity > 0 else PositionSide.SHORT
            )
            self.position.entry_timestamp = bar.timestamp
            self.position.equity_when_entry = self.cash
        self.position.quantity += quantity
        if quantity * self.position.quantity > 0:
            self.position.total_entry_quantity += abs(quantity)
            self.position.total_entry_price += fill_price * abs(quantity)
            self.position.max_quantity = max(
                self.position.max_quantity,
                abs(self.position.quantity),
            )
        if quantity * self.position.quantity < 0:
            self.position.total_exit_price += fill_price * abs(quantity)
        self.position.commission += (
            fill_price * self.config.commission_rate * abs(quantity)
        )
        self.cash -= (
            fill_price * quantity
            + fill_price * self.config.commission_rate * abs(quantity)
        )
        self.position.count += 1

    def run(self, ohlcv: list[Bar], strategy: BaseStrategy) -> BacktestResult:
        self.cash = self.config.initial_cash
        self.position = Position()
        self.trades = []
        self.liquidated = False
        strategy.reset()
        equity_curve: list[EquityPoint] = []
        previous_bar: Bar | None = None

        for i, bar in enumerate(ohlcv):
            if self.liquidated:
                equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
                continue

            flag = self.check_liquidate(bar.open)
            if flag:
                self.liquidate(bar, bar.open)
                equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
                self.liquidated = True
                continue

            target_position: float | None = strategy.generate_signal(i, previous_bar)
            if target_position is not None:
                price = bar.open
                if not -1.0 <= target_position <= 1.0:
                    raise ValueError(f"目标仓位应处于 -1 到 1 之间，策略{strategy.__class__.__name__}返回了{target_position}")
                position_size = self.position.quantity * price / (self.cash + self.position.quantity * price)
                equity = self.cash + self.position.quantity * price
                delta_position = target_position - position_size
                quantity = equity * delta_position / price
                if quantity > 0:
                    fill_price = price * (1 + self.config.slippage_rate)
                else:
                    fill_price = price * (1 - self.config.slippage_rate)
                if abs(delta_position) > self.config.rebalance_tolerance:
                    self.opt(bar, quantity, fill_price)
                    flag = self.check_liquidate(bar.open)
                    if flag:
                        self.liquidate(bar, bar.open)
                        equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
                        self.liquidated = True
                        continue

            if self.position.quantity < 0:
                liquidation_price = self.cash / (abs(self.position.quantity) * (1 + self.config.maintenance_margin_rate))
                if bar.high >= liquidation_price:
                    self.liquidate(bar, liquidation_price)
                    equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
                    self.liquidated = True
                    continue

            equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash + self.position.quantity * bar.close))
            previous_bar = bar

        if self.position.quantity != 0:
            last_price = ohlcv[-1].close
            quantity = -self.position.quantity
            if quantity > 0:
                fill_price = last_price * (1 + self.config.slippage_rate)
            else:
                fill_price = last_price * (1 - self.config.slippage_rate)

            self.opt(ohlcv[-1], quantity, fill_price)
            equity_curve[-1] = EquityPoint(timestamp=ohlcv[-1].timestamp, equity=self.cash)

        return BacktestResult(
            initial_cash=self.config.initial_cash,
            final_cash=self.cash,
            equity_curve=equity_curve,
            trades=self.trades,
            liquidated=self.liquidated
        )
