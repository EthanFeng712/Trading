from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..data.data_loader import Bar
from ..strategies.base import BaseStrategy
from ..strategies.base import Signal


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Trade:
    side: PositionSide
    entry_index: int
    entry_price: float
    quantity: float # 持仓数量
    buy_fee: float # 买入每股手续费
    
    exit_index: int | None = None
    exit_price: float | None = None
    commission: float | None = None # 总手续费
    pnl: float | None = None # 本单盈亏


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


class SimpleBacktestEngine:
    def __init__(self, initial_cash: float = 10000.0, commission_rate: float = 0.001, position_size: float = 0.2) -> None:
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.position_size = position_size
        if self.initial_cash <= 0.0:
            raise ValueError("初始资金应大于 0")
        if self.position_size > 1.0 or self.position_size <= 0.0:
            raise ValueError("仓位应处于 0 到 1 之间")
        if self.commission_rate < 0.0:
            raise ValueError("手续费应大于等于 0")

    def run(self, ohlcv: list[Bar], strategy: BaseStrategy) -> BacktestResult:
        strategy.reset()
        cash = self.initial_cash
        position: Trade | None = None
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []

        for i, bar in enumerate(ohlcv):
            history = ohlcv[: i]
            signal = strategy.generate_signal(history)
            price = bar.open

            if signal is Signal.BUY and position is None and cash > 0.0:
                buy_fee_ = price * self.commission_rate
                position = Trade(
                    side=PositionSide.LONG,
                    entry_index=i,
                    entry_price=price,
                    quantity=(self.position_size * cash) / (price + buy_fee_),
                    buy_fee=buy_fee_,
                )
                cash -= (price + position.buy_fee) * position.quantity
            elif signal is Signal.SELL and position is not None:
                position.exit_index = i
                position.exit_price = price
                sell_fee = price * self.commission_rate
                position.commission = (position.buy_fee + sell_fee) * position.quantity
                cash += (price - sell_fee) * position.quantity
                position.pnl = (price - position.entry_price) * position.quantity - position.commission
                trades.append(position)
                position = None

            equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=cash + (position.quantity if position is not None else 0) * bar.close))

        if position is not None:
            last_price = ohlcv[-1].close
            position.exit_index = len(ohlcv) - 1
            position.exit_price = last_price
            sell_fee = last_price * self.commission_rate
            position.commission = (position.buy_fee + sell_fee) * position.quantity
            cash += (last_price - sell_fee) * position.quantity
            position.pnl = (last_price - position.entry_price) * position.quantity - position.commission
            trades.append(position)
            equity_curve[-1] = EquityPoint(timestamp=ohlcv[-1].timestamp, equity=cash)

        return BacktestResult(
            initial_cash=self.initial_cash,
            final_cash=cash,
            equity_curve=equity_curve,
            trades=trades,
        )
