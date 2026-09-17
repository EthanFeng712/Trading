import datetime
import unittest

from src.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from src.data.data_loader import Bar


def bar(close: float, i: int = 0) -> Bar:
    t = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
    return Bar(float(close), float(close), float(close), float(close), 1.0, t)


def feed(strategy: MeanReversionStrategy, closes: list[float]) -> float | None:
    """按引擎约定逐根喂入收盘价，返回最后一根 K 线产生的信号。"""
    prev: Bar | None = None
    last: float | None = None
    for i, c in enumerate(closes):
        b = bar(c, i + 1)
        last = strategy.generate_signal(i, prev)
        prev = b
    return last


class TestMeanReversionConfig(unittest.TestCase):
    def test_defaults(self):
        c = MeanReversionConfig()
        self.assertEqual(c.window, 20)
        self.assertEqual(c.entry_z, 2.0)
        self.assertEqual(c.exit_z, 0.5)
        self.assertEqual(c.target_size, 0.2)
        self.assertEqual(c.trend_window, 90)

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            MeanReversionConfig(window=1)

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            MeanReversionConfig(entry_z=0)
        with self.assertRaises(ValueError):
            MeanReversionConfig(exit_z=2.0, entry_z=2.0)
        with self.assertRaises(ValueError):
            MeanReversionConfig(exit_z=3.0, entry_z=2.0)

    def test_invalid_trend_window(self):
        # 负数非法
        with self.assertRaises(ValueError):
            MeanReversionConfig(trend_window=-1)
        # 开启时须大于均值窗口
        with self.assertRaises(ValueError):
            MeanReversionConfig(window=20, trend_window=20)
        with self.assertRaises(ValueError):
            MeanReversionConfig(window=20, trend_window=10)


class TestMeanReversionZScore(unittest.TestCase):
    """纯 z-score 逻辑（关闭趋势过滤，trend_window=0）保持原有行为。"""

    def _cfg(self, **kw):
        kw.setdefault("window", 10)
        kw.setdefault("entry_z", 2.0)
        kw.setdefault("exit_z", 0.5)
        kw["trend_window"] = 0  # 关闭过滤
        return MeanReversionConfig(**kw)

    def test_warmup_none(self):
        s = MeanReversionStrategy(self._cfg())
        for i in range(1, 10):
            self.assertIsNone(s.generate_signal(i, bar(100 + i, i)))

    def test_flat_market_no_signal(self):
        s = MeanReversionStrategy(self._cfg())
        for i in range(1, 12):
            self.assertIsNone(s.generate_signal(i, bar(100, i)))

    def test_extreme_high_short(self):
        s = MeanReversionStrategy(self._cfg())
        for i in range(1, 11):
            s.generate_signal(i, bar(100, i))
        sig = s.generate_signal(11, bar(200, 11))
        self.assertEqual(sig, -0.2)

    def test_extreme_low_long(self):
        s = MeanReversionStrategy(self._cfg())
        for i in range(1, 11):
            s.generate_signal(i, bar(100, i))
        sig = s.generate_signal(11, bar(50, 11))
        self.assertEqual(sig, 0.2)

    def test_near_mean_flat(self):
        s = MeanReversionStrategy(self._cfg())
        vals = [100, 102, 98, 104, 96, 100, 101, 99, 103, 97]
        for i, v in enumerate(vals, start=1):
            s.generate_signal(i, bar(v, i))
        sig = s.generate_signal(11, bar(100, 11))
        self.assertEqual(sig, 0.0)

    def test_reset(self):
        s = MeanReversionStrategy(self._cfg(window=5))
        for i in range(1, 7):
            s.generate_signal(i, bar(100 + (i % 2) * 30, i))
        s.reset()
        self.assertIsNone(s.generate_signal(7, bar(100, 7)))
        self.assertIsNone(s.trend_sma)


class TestMeanReversionTrendGate(unittest.TestCase):
    """趋势状态过滤（默认开启）：仅在趋势方向与反向信号一致时开仓。

    feed() 按引擎语义（第 i 根信号基于第 i-1 根已收盘价）返回最后一根的评估结果；
    因此每个场景把"信号棒"放在倒数第二根，并追加一根相同的后续棒（不会被评估，
    仅占位以满足循环长度）。
    """

    def _cfg(self, **kw):
        kw.setdefault("window", 10)
        kw.setdefault("entry_z", 2.0)
        kw.setdefault("exit_z", 0.5)
        kw.setdefault("trend_window", 60)
        return MeanReversionConfig(**kw)

    def _warm_up(self, n: int, start: int, step: int) -> list[float]:
        return [start + i * step for i in range(n)]

    def test_blocks_short_in_uptrend(self):
        # 上行趋势中即便出现超买极值，也不允许做空（逆趋势阻断）。
        s = MeanReversionStrategy(self._cfg())
        closes = self._warm_up(80, 100, 1) + [300, 300]
        self.assertIsNone(feed(s, closes))

    def test_blocks_long_in_downtrend(self):
        # 下行趋势中即便出现超卖极值，也不允许做多（逆趋势阻断）。
        s = MeanReversionStrategy(self._cfg())
        closes = self._warm_up(80, 179, -1) + [0, 0]
        self.assertIsNone(feed(s, closes))

    def test_allows_long_in_uptrend(self):
        # 上行趋势中的回撤（超卖）允许做多。
        s = MeanReversionStrategy(self._cfg())
        closes = self._warm_up(80, 100, 1) + [155, 155]
        self.assertEqual(feed(s, closes), 0.2)

    def test_allows_short_in_downtrend(self):
        # 下行趋势中的反弹（超买）允许做空。
        s = MeanReversionStrategy(self._cfg())
        closes = self._warm_up(80, 179, -1) + [115, 115]
        self.assertEqual(feed(s, closes), -0.2)

    def test_reset_rebuilds_trend_sma(self):
        s = MeanReversionStrategy(self._cfg())
        self.assertIsNotNone(s.trend_sma)
        feed(s, self._warm_up(80, 100, 1))
        self.assertIsNotNone(s.trend_sma.sma)
        s.reset()
        self.assertIsNotNone(s.trend_sma)
        self.assertIsNone(s.trend_sma.sma)
        self.assertIsNone(s._long_ma)


if __name__ == "__main__":
    unittest.main()
