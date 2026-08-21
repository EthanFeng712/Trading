from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..data.data_loader import Bar
from ..strategies.base import BaseStrategy


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


@dataclass
class Position:
    side: PositionSide = PositionSide.NONE
    quantity: float = 0.0 # 持股数
    entry_timestamp: datetime | None = None
    total_entry_price: float = 0.0 # 累计购入股票价值
    total_entry_quantity: float = 0.0 # 累计购入股票数量
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


class SimpleBacktestEngine:
    initial_cash: float
    cash: float
    position: Position
    trades: list[Trade]
    commission_rate: float
    
    def __init__(self, initial_cash: float = 10000.0, commission_rate: float = 0.001) -> None:
        self.cash = self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.position = Position()
        self.trades = []
        if self.cash <= 0.0:
            raise ValueError("初始资金应大于 0")
        if self.commission_rate < 0.0:
            raise ValueError("手续费应大于等于 0")
        
    def opt(self, bar: Bar, quantity: float, price: float) -> None:
        if self.position.quantity != 0 and (self.position.quantity + quantity) * self.position.quantity <= 0: # 平仓
            self.cash += price * self.position.quantity - price * self.commission_rate * abs(self.position.quantity)
            self.position.commission += price * self.commission_rate * abs(self.position.quantity)
            self.position.total_exit_price += price * abs(self.position.quantity)
            pnl = self.cash - self.position.equity_when_entry
            self.trades.append(Trade(
                side=self.position.side,
                entry_time=self.position.entry_timestamp,
                exit_time=bar.timestamp,
                average_entry_price=self.position.total_entry_price / self.position.total_entry_quantity if self.position.total_entry_quantity != 0 else 0.0,
                average_exit_price=self.position.total_exit_price / self.position.total_entry_quantity if self.position.total_entry_quantity != 0 else 0.0,
                cumulative_quantity=self.position.total_entry_quantity,
                max_quantity=self.position.max_quantity,
                count=self.position.count+1,
                gross_pnl=pnl+self.position.commission,
                commission=self.position.commission,
                net_pnl=pnl
            ))
            quantity += self.position.quantity
            self.position = Position()
            if quantity == 0:
                return
        
        if self.position.quantity == 0: # 反开
            self.position.side = PositionSide.LONG if quantity > 0 else PositionSide.SHORT
            self.position.entry_timestamp = bar.timestamp
            self.position.equity_when_entry = self.cash - price * self.commission_rate * abs(self.position.quantity)
        self.position.quantity += quantity
        if quantity * self.position.quantity > 0:
            self.position.total_entry_quantity += abs(quantity)
            self.position.total_entry_price += price * abs(quantity)
            self.position.max_quantity = max(self.position.max_quantity, abs(self.position.quantity))
        if quantity * self.position.quantity < 0:
            self.position.total_exit_price += price * abs(quantity)
        self.position.commission += price * self.commission_rate * abs(quantity)
        self.cash -= price * quantity + price * self.commission_rate * abs(quantity)
        self.position.count += 1
            
    def run(self, ohlcv: list[Bar], strategy: BaseStrategy) -> BacktestResult:
        self.cash = self.initial_cash
        self.position = Position()
        self.trades = []
        strategy.reset()
        equity_curve: list[EquityPoint] = []

        for i, bar in enumerate(ohlcv):
            history = ohlcv[: i]
            target_position: float | None = strategy.generate_signal(history)
            if target_position is None:
                equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash + self.position.quantity * bar.close))
                continue
            price = bar.open
            position_size = self.position.quantity * price / (self.cash + self.position.quantity * price)
            if target_position > 1.0 or target_position < -1.0:
                raise ValueError(f"目标仓位应处于 -1 到 1 之间，策略{strategy.__class__.__name__}返回了{target_position}")
            
            equity = self.cash + self.position.quantity * price
            delta_position = target_position - position_size
            quantity = equity * delta_position / price
            self.opt(bar, quantity, price)

            equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash + self.position.quantity * bar.close))

        if self.position.quantity != 0:
            last_price = ohlcv[-1].close
            self.cash += last_price * self.position.quantity - last_price * self.commission_rate * abs(self.position.quantity)
            self.position.commission += last_price * self.commission_rate * abs(self.position.quantity)
            self.position.total_exit_price += last_price * abs(self.position.quantity)
            self.trades.append(Trade(
                side=self.position.side,
                entry_time=self.position.entry_timestamp,
                exit_time=ohlcv[-1].timestamp,
                average_entry_price=self.position.total_entry_price / self.position.total_entry_quantity if self.position.total_entry_quantity != 0 else 0.0,
                average_exit_price=self.position.total_exit_price / self.position.total_entry_quantity if self.position.total_entry_quantity != 0 else 0.0,
                cumulative_quantity=self.position.total_entry_quantity,
                max_quantity=self.position.max_quantity,
                count=self.position.count,
                gross_pnl=self.cash - self.position.equity_when_entry + self.position.commission,
                commission=self.position.commission,
                net_pnl=self.cash - self.position.equity_when_entry
            ))
            equity_curve[-1] = EquityPoint(timestamp=ohlcv[-1].timestamp, equity=self.cash)

        return BacktestResult(
            initial_cash=self.initial_cash,
            final_cash=self.cash,
            equity_curve=equity_curve,
            trades=self.trades,
        )
