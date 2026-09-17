from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from math import sqrt

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
        self._recent_closes: deque[float] = deque(maxlen=self.config.vol_lookback + 1)
        # 年化波动率目标化所需的滚动收益：用运行和/平方和在 O(1) 内递推。
        self._vol_returns: deque[float] = deque(maxlen=self.config.vol_lookback)
        self._vol_sum: float = 0.0
        self._vol_sumsq: float = 0.0

    def check_liquidate(self, price: float) -> bool:
        if self.position.quantity < 0:
            equity = self.cash + self.position.quantity * price
            maintenance_margin = abs(self.position.quantity) * price * self.config.maintenance_margin_rate
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

    def _liquidate_and_record(self, bar: Bar, price: float, equity_curve: list[EquityPoint]) -> None:
        """按给定价格强制平仓，记录当前权益并标记爆仓。

        三条强平路径（开盘跳空、下单后即时触发、盘中触及）都必须执行同样的
        收尾动作，集中在此以免三处实现漂移。
        """
        self.liquidate(bar, price)
        equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
        self.liquidated = True

    def _check_stop_loss(self, bar: Bar) -> bool:
        """按 K 线高低价触发的对称单笔止损；命中则返回 True。

        多头：当 bar.low <= 入场均价*(1-sl) 时以止损价平仓；
        空头：当 bar.high >= 入场均价*(1+sl) 时以止损价平仓。
        多空一致处理，修复原引擎「仅空头有强平、多头不对称」的缺口。
        仅在 config.stop_loss_rate 非 None 时由 run() 调用。
        """
        if self.config.stop_loss_rate is None:
            return False
        if abs(self.position.quantity) < 1e-8:
            return False
        if self.position.total_entry_quantity == 0:
            return False
        avg_entry = self.position.total_entry_price / self.position.total_entry_quantity
        if avg_entry <= 0:
            return False

        sl = self.config.stop_loss_rate
        if self.position.quantity > 0:
            stop = avg_entry * (1.0 - sl)
            if bar.low <= stop:
                self.opt(bar, -self.position.quantity, stop)
                return True
        else:
            stop = avg_entry * (1.0 + sl)
            if bar.high >= stop:
                self.opt(bar, -self.position.quantity, stop)
                return True
        return False

    def _annualized_vol(self) -> float:
        """基于最近 vol_lookback 根 K 线的日收益标准差，年化（*sqrt(365)）。

        返回值由 run() 中递推维护的滚动收益和/平方和在 O(1) 内求得，
        不再每根 K 线重算 O(vol_lookback)。
        """
        n = len(self._vol_returns)
        if n < 2:
            return 0.0
        mean = self._vol_sum / n
        var = self._vol_sumsq / n - mean * mean
        if var <= 0.0:
            return 0.0
        return sqrt(var) * sqrt(365.0)


    def opt(self, bar: Bar, quantity: float, fill_price: float) -> None:
        if abs(quantity) < 1e-8 or self.liquidated:
            return

        if abs(self.position.quantity) > 1e-8 and ((self.position.quantity + quantity) * self.position.quantity <= 0 or abs(self.position.quantity + quantity) < 1e-8): # 平仓
            self.cash += fill_price * self.position.quantity - fill_price * self.config.commission_rate * abs(self.position.quantity)
            self.position.commission += fill_price * self.config.commission_rate * abs(self.position.quantity)
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
                count=self.position.count+1,
                gross_pnl=pnl+self.position.commission,
                commission=self.position.commission,
                net_pnl=pnl
            ))
            quantity += self.position.quantity
            self.position = Position()

        if quantity > 1e-8 and self.position.quantity >= 0 and self.cash < fill_price * quantity + fill_price * self.config.commission_rate * abs(quantity):
            quantity = self.cash / (fill_price * (1 + self.config.commission_rate))
        if abs(quantity) < 1e-8:
            return

        if self.position.quantity == 0: # 反开
            self.position.side = PositionSide.LONG if quantity > 0 else PositionSide.SHORT
            self.position.entry_timestamp = bar.timestamp
            self.position.equity_when_entry = self.cash
        self.position.quantity += quantity
        if quantity * self.position.quantity > 0:
            self.position.total_entry_quantity += abs(quantity)
            self.position.total_entry_price += fill_price * abs(quantity)
            self.position.max_quantity = max(self.position.max_quantity, abs(self.position.quantity))
        if quantity * self.position.quantity < 0:
            self.position.total_exit_price += fill_price * abs(quantity)
        self.position.commission += fill_price * self.config.commission_rate * abs(quantity)
        self.cash -= fill_price * quantity + fill_price * self.config.commission_rate * abs(quantity)
        self.position.count += 1

    def run(self, ohlcv: list[Bar], strategy: BaseStrategy) -> BacktestResult:
        self.cash = self.config.initial_cash
        self.position = Position()
        self.trades = []
        self.liquidated = False
        self._recent_closes = deque(maxlen=self.config.vol_lookback + 1)
        self._vol_returns = deque(maxlen=self.config.vol_lookback)
        self._vol_sum = 0.0
        self._vol_sumsq = 0.0
        strategy.reset()
        equity_curve: list[EquityPoint] = []
        previous_bar: Bar | None = None

        for i, bar in enumerate(ohlcv):
            if self.liquidated:
                equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
                continue

            self._recent_closes.append(bar.close)

            # 维护滚动日收益（O(1) 递推），供波动率目标化使用。
            if len(self._recent_closes) >= 2:
                prev_close = self._recent_closes[-2]
                if prev_close > 0:
                    ret = (self._recent_closes[-1] - prev_close) / prev_close
                    if len(self._vol_returns) == self._vol_returns.maxlen:
                        old = self._vol_returns[0]
                        self._vol_sum -= old
                        self._vol_sumsq -= old * old
                    self._vol_returns.append(ret)
                    self._vol_sum += ret
                    self._vol_sumsq += ret * ret

            if self.check_liquidate(bar.open):
                self._liquidate_and_record(bar, bar.open, equity_curve)
                continue

            if self.config.stop_loss_rate is not None and self._check_stop_loss(bar):
                equity_curve.append(EquityPoint(timestamp=bar.timestamp, equity=self.cash))
                previous_bar = bar
                continue

            target_position: float | None = strategy.generate_signal(i, previous_bar)
            if self.config.vol_target_annual is not None and target_position is not None:
                ann_vol = self._annualized_vol()
                if ann_vol > 1e-9:
                    scale = min(self.config.vol_target_annual / ann_vol, 1.5)
                    target_position = max(-1.0, min(1.0, target_position * scale))
            if target_position is not None:
                price = bar.open
                if not -1.0 <= target_position <= 1.0:
                    raise ValueError(f"目标仓位应处于 -1 到 1 之间，策略{strategy.__class__.__name__}返回了{target_position}")
                equity = self.cash + self.position.quantity * price
                position_size = self.position.quantity * price / equity
                delta_position = target_position - position_size
                quantity = equity * delta_position / price
                if quantity > 0:
                    fill_price = price * (1 + self.config.slippage_rate)
                else:
                    fill_price = price * (1 - self.config.slippage_rate)
                if abs(delta_position) > self.config.rebalance_tolerance:
                    self.opt(bar, quantity, fill_price)
                    if self.check_liquidate(bar.open):
                        self._liquidate_and_record(bar, bar.open, equity_curve)
                        continue

            if self.position.quantity < 0:
                liquidation_price = self.cash / (abs(self.position.quantity) * (1 + self.config.maintenance_margin_rate))
                if bar.high >= liquidation_price:
                    self._liquidate_and_record(bar, liquidation_price, equity_curve)
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
