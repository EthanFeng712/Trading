import datetime
import unittest

from src.strategies.regime import RegimeConfig, RegimeFilteredStrategy
from src.strategies.base import BaseStrategy
from src.data.data_loader import Bar


def bar(close: float, i: int = 0) -> Bar:
    t = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
    return Bar(float(close), float(close), float(close), float(close), 1.0, t)


class StubStrategy(BaseStrategy):
    """返回固定信号的桩策略，用于隔离测试状态过滤门控逻辑。"""

    def __init__(self, signal: float | None) -> None:
        self.signal = signal

    def generate_signal(self, _index: int, _previous_bar: Bar | None) -> float | None:
        return self.signal

    def reset(self) -> None:
        pass


class TestRegimeConfig(unittest.TestCase):
    def test_defaults(self):
        c = RegimeConfig()
        self.assertEqual(c.ma_window, 100)
        self.assertEqual(c.band, 0.0)

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            RegimeConfig(ma_window=1)
        with self.assertRaises(ValueError):
            RegimeConfig(ma_window=-5)

    def test_invalid_band(self):
        with self.assertRaises(ValueError):
            RegimeConfig(band=-0.1)


class TestRegimeFilter(unittest.TestCase):
    def _feed(self, wrapper: RegimeFilteredStrategy, closes, start=1):
        outs = []
        for k, c in enumerate(closes):
            outs.append(wrapper.generate_signal(start + k, bar(c, start + k)))
        return outs

    def test_uptrend_passes_long_blocks_short(self):
        # 单调递增收盘价 -> 上行趋势：放行做多，阻断做空
        w = RegimeFilteredStrategy(StubStrategy(0.2), RegimeConfig(ma_window=5))
        # 预热（>=5 根）使其进入趋势判定
        self._feed(w, [100 + i for i in range(1, 8)])
        w.inner.signal = 0.2
        self.assertEqual(w.generate_signal(99, bar(108, 99)), 0.2)      # 做多放行
        w.inner.signal = -0.2
        self.assertEqual(w.generate_signal(100, bar(109, 100)), 0.0)    # 做空阻断

    def test_downtrend_passes_short_blocks_long(self):
        w = RegimeFilteredStrategy(StubStrategy(-0.2), RegimeConfig(ma_window=5))
        self._feed(w, [200 - i for i in range(1, 8)])
        w.inner.signal = -0.2
        self.assertEqual(w.generate_signal(99, bar(190, 99)), -0.2)     # 做空放行
        w.inner.signal = 0.2
        self.assertEqual(w.generate_signal(100, bar(189, 100)), 0.0)    # 做多阻断（空头/空仓时平仓）

    def test_ranging_forces_flat(self):
        w = RegimeFilteredStrategy(StubStrategy(0.2), RegimeConfig(ma_window=5))
        self._feed(w, [100] * 8)  # 横盘 -> 震荡，强制空仓
        self.assertEqual(w.generate_signal(99, bar(100, 99)), 0.0)

    def test_flips_flatten_counter_trend_position(self):
        # 上行趋势中建立多头后，状态翻转为下行时平掉多头
        w = RegimeFilteredStrategy(StubStrategy(0.2), RegimeConfig(ma_window=5))
        self._feed(w, [100 + i for i in range(1, 8)])   # 上行，开多，_pos=1
        last = w.generate_signal(99, bar(108, 99))
        self.assertEqual(last, 0.2)
        # 切换为下跌序列，使最近窗口转为下行趋势
        outs = self._feed(w, [200 - i for i in range(1, 12)])
        # 下跌趋势中 inner=+0.2 被阻断为平仓；且旧多头在翻转后被平掉
        self.assertIn(0.0, outs)

    def test_reset_clears_state_and_inner(self):
        inner = StubStrategy(0.2)
        w = RegimeFilteredStrategy(inner, RegimeConfig(ma_window=5))
        self._feed(w, [100 + i for i in range(1, 8)])
        w.reset()
        self.assertEqual(w._pos, 0)
        self.assertEqual(len(w.closes), 0)


if __name__ == "__main__":
    unittest.main()
