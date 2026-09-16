import datetime
import unittest

from src.strategies.momentum import MomentumConfig, MomentumStrategy
from src.data.data_loader import Bar


def bar(close: float, i: int = 0) -> Bar:
    t = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
    return Bar(float(close), float(close), float(close), float(close), 1.0, t)


class TestMomentumConfig(unittest.TestCase):
    def test_defaults(self):
        c = MomentumConfig()
        self.assertEqual(c.lookback, 20)
        self.assertEqual(c.threshold, 0.0)
        self.assertEqual(c.target_size, 0.2)

    def test_invalid_lookback(self):
        with self.assertRaises(ValueError):
            MomentumConfig(lookback=0)
        with self.assertRaises(ValueError):
            MomentumConfig(lookback=-5)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            MomentumConfig(threshold=-0.1)

    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            MomentumConfig(target_size=0)
        with self.assertRaises(ValueError):
            MomentumConfig(target_size=1.5)


class TestMomentumStrategy(unittest.TestCase):
    def test_warmup_returns_none(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        for i in range(1, 6):
            self.assertIsNone(s.generate_signal(i, bar(100 + i, i)))

    def test_uptrend_allows_long(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        closes = [100.0 + i for i in range(1, 71)]  # 101..170 单调上行
        sig = None
        for idx, c in enumerate(closes, start=1):
            sig = s.generate_signal(idx, bar(c, idx))
        self.assertEqual(sig, 0.2)

    def test_downtrend_allows_short(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        closes = [200.0 - i for i in range(1, 71)]  # 199..130 单调下行
        sig = None
        for idx, c in enumerate(closes, start=1):
            sig = s.generate_signal(idx, bar(c, idx))
        self.assertEqual(sig, -0.2)

    def test_threshold_deadzone_hold(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.1))
        closes = [100.0] * 70  # 完全横盘，动量落入死区
        sig = None
        for idx, c in enumerate(closes, start=1):
            sig = s.generate_signal(idx, bar(c, idx))
        self.assertIsNone(sig)

    def test_downtrend_suppresses_countertrend_rebound(self):
        # 下行趋势末端出现短期反弹（动量>0），但所处趋势为下行 -> 抑制不开多
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        closes = []
        for i in range(1, 61):
            closes.append(200.0 - i)  # 199..140 下行，抬高 trend MA
        for i in range(61, 71):
            closes.append(140.0 + (i - 60))  # 141..150 反弹
        sig = None
        for idx, c in enumerate(closes, start=1):
            sig = s.generate_signal(idx, bar(c, idx))
        self.assertIsNone(sig)

    def test_uptrend_suppresses_countertrend_pullback(self):
        # 上行趋势末端出现短期回落（动量<0），但所处趋势为上行 -> 抑制不开空
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        closes = []
        for i in range(1, 61):
            closes.append(100.0 + i)  # 101..160 上行
        for i in range(61, 71):
            closes.append(160.0 - (i - 60))  # 159..150 回落
        sig = None
        for idx, c in enumerate(closes, start=1):
            sig = s.generate_signal(idx, bar(c, idx))
        self.assertIsNone(sig)

    def test_reset_clears_state(self):
        s = MomentumStrategy(MomentumConfig(lookback=3, threshold=0.0))
        for i in range(1, 5):
            s.generate_signal(i, bar(100 + i, i))
        s.reset()
        self.assertIsNone(s.generate_signal(5, bar(100, 5)))

    def test_nonfinite_close_safe(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        for i in range(1, 66):
            s.generate_signal(i, bar(100.0 + i, i))
        self.assertIsNone(s.generate_signal(66, bar(float("nan"), 66)))
        self.assertIsNone(s.generate_signal(67, bar(float("inf"), 67)))

    def test_long_series_runs_without_error(self):
        s = MomentumStrategy()
        closes = [100.0 * (1 + 0.001 * i + 0.01 * ((i % 7) - 3)) for i in range(1, 301)]
        sig = None
        for idx, c in enumerate(closes, start=1):
            sig = s.generate_signal(idx, bar(c, idx))
        self.assertIn(sig, (None, 0.2, -0.2))


if __name__ == "__main__":
    unittest.main()
