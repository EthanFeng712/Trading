import datetime
import unittest

from src.backtest.config import BacktestConfig
from src.backtest.engine import SimpleBacktestEngine
from src.strategies.base import BaseStrategy
from src.data.data_loader import Bar


def bar(close: float, i: int = 0, low: float | None = None, high: float | None = None) -> Bar:
    t = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
    return Bar(
        float(close), float(high if high is not None else close),
        float(low if low is not None else close), float(close), 1.0, t,
    )


class OnceLong(BaseStrategy):
    """首日开多后一直持有（返回 None），用于测试止损。"""

    def __init__(self) -> None:
        self._done = False

    def generate_signal(self, _index: int, _previous_bar: Bar | None) -> float | None:
        if not self._done:
            self._done = True
            return 0.2
        return None

    def reset(self) -> None:
        self._done = False


class DelayedLong(BaseStrategy):
    """前 warmup 根返回 None，之后恒定做多，用于测试波动率目标缩放。"""

    def __init__(self, warmup: int) -> None:
        self._warmup = warmup
        self._i = 0

    def generate_signal(self, _index: int, _previous_bar: Bar | None) -> float | None:
        self._i += 1
        if self._i <= self._warmup:
            return None
        return 0.2

    def reset(self) -> None:
        self._i = 0


class TestRiskConfigValidation(unittest.TestCase):
    def test_stop_loss_validation(self):
        with self.assertRaises(ValueError):
            BacktestConfig(stop_loss_rate=-0.1)
        with self.assertRaises(ValueError):
            BacktestConfig(stop_loss_rate=0.0)

    def test_vol_target_validation(self):
        with self.assertRaises(ValueError):
            BacktestConfig(vol_target_annual=-0.1)

    def test_vol_lookback_validation(self):
        with self.assertRaises(ValueError):
            BacktestConfig(vol_lookback=1)
        with self.assertRaises(ValueError):
            BacktestConfig(vol_lookback=0)


class TestStopLoss(unittest.TestCase):
    def test_long_stop_triggered(self):
        ohlcv = [bar(100.0, 1)]
        for i in range(2, 7):
            ohlcv.append(bar(100.0, i))          # 横盘，不触发
        ohlcv.append(bar(100.0, 7, low=84.0))    # 低点击穿 100*(1-0.15)=85 -> 止损
        for i in range(8, 12):
            ohlcv.append(bar(100.0, i))

        cfg = BacktestConfig(stop_loss_rate=0.15)
        res = SimpleBacktestEngine(cfg).run(ohlcv, OnceLong())
        # 止损价 ~85，应产生一笔在该价位附近平仓的交易
        self.assertTrue(any(t.average_exit_price <= 86.0 for t in res.trades))
        self.assertFalse(res.liquidated)

    def test_stop_off_keeps_position(self):
        ohlcv = [bar(100.0, 1)]
        for i in range(2, 7):
            ohlcv.append(bar(100.0, i))
        ohlcv.append(bar(100.0, 7, low=84.0))
        for i in range(8, 12):
            ohlcv.append(bar(100.0, i))

        res = SimpleBacktestEngine(BacktestConfig()).run(ohlcv, OnceLong())
        # 未启用止损：不会出现 ~85 的止损平仓价
        self.assertFalse(any(t.average_exit_price <= 86.0 for t in res.trades))


class TestVolTarget(unittest.TestCase):
    def test_high_vol_scales_down_position(self):
        # 高波动收盘价序列（大幅摆动），前 10 根不入场以积累波动率样本
        ohlcv = []
        for i in range(1, 16):
            swing = 100.0 + (60.0 if i % 2 == 0 else -60.0)
            ohlcv.append(bar(swing, i))

        off = SimpleBacktestEngine(BacktestConfig()).run(ohlcv, DelayedLong(warmup=10))
        on = SimpleBacktestEngine(BacktestConfig(vol_target_annual=0.4, vol_lookback=5)).run(
            ohlcv, DelayedLong(warmup=10)
        )
        qty_off = off.trades[0].cumulative_quantity
        qty_on = on.trades[0].cumulative_quantity
        self.assertLess(qty_on, qty_off)


if __name__ == "__main__":
    unittest.main()
