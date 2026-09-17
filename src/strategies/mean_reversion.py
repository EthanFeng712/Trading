from collections import deque
from dataclasses import dataclass
from math import isfinite, sqrt

from .base import BaseStrategy
from ..data.data_loader import Bar
from ..utils.indicators import RollingSMA


@dataclass(frozen=True)
class MeanReversionConfig:
    """均值回归策略的可配置参数。

    window   : 均值与标准差的计算周期（根 K 线），须 > 1。
    entry_z  : 入场阈值（z-score 绝对值）。价格偏离均值超过 +entry_z 视为超买、
               低于 -entry_z 视为超卖，触发反向信号。须 > 0。
    exit_z   : 平仓阈值（z-score 绝对值）。偏离回落到 [-exit_z, +exit_z] 内时平仓。
               须满足 0 <= exit_z < entry_z。
    target_size: 触发时的目标仓位绝对值，约束于 (0, 1]。
    trend_window: 趋势过滤窗口（根 K 线）。仅当价格位于该长均线所界定的趋势方向一侧时
               才允许反向开仓：超卖开多需处于上行趋势（close > 长均线）、超买开空需处于
               下行趋势（close < 长均线），否则视为逆趋势而强制空仓。
               默认为 90（开启）；设为 0 可关闭过滤，恢复纯 z-score 行为。
               若开启，须大于 window。
    """

    window: int = 20
    entry_z: float = 2.0
    exit_z: float = 0.5
    target_size: float = 0.2
    trend_window: int = 90

    def __post_init__(self) -> None:
        if type(self.window) is not int or self.window <= 1:
            raise ValueError("均值窗口必须为大于 1 的整数")
        if not isfinite(self.entry_z) or self.entry_z <= 0:
            raise ValueError("入场阈值 entry_z 应为正数")
        if not isfinite(self.exit_z) or self.exit_z < 0:
            raise ValueError("平仓阈值 exit_z 应不小于 0")
        if self.exit_z >= self.entry_z:
            raise ValueError("平仓阈值 exit_z 应小于入场阈值 entry_z")
        if not 0 < self.target_size <= 1:
            raise ValueError("目标仓位大小应在 0 到 1.0 之间")
        if type(self.trend_window) is not int or self.trend_window < 0:
            raise ValueError("趋势过滤窗口必须为非负整数（0 表示关闭）")
        if self.trend_window != 0 and self.trend_window <= self.window:
            raise ValueError("趋势过滤窗口应大于均值窗口（或设为 0 关闭）")


class MeanReversionStrategy(BaseStrategy):
    """均值回归：衡量价格相对滚动均值的 z-score 偏离，在极端偏离时反向开仓。

    接口约定
    --------
    输入 : generate_signal(index, previous_bar)
           previous_bar 为「已收盘」的 K 线（Bar）。本策略仅使用 previous_bar.close
           与内部维护的滚动收盘价窗口。
    输出 : float，表示目标仓位，约束于 [-1.0, 1.0]；返回 None 表示维持当前仓位。

    信号生成规则
    ------------
        z = (close - mean) / std      # std 为 window 内总体标准差
        z >  +entry_z -> 做空 (-target_size)   价格远高于均值，预期回落
        z <  -entry_z -> 做多 (+target_size)   价格远低于均值，预期反弹
        |z| <= exit_z -> 平仓 (0.0)           已回归均值
        其余          -> 维持现状 (None)        介于双阈值之间，保持仓位

    趋势状态过滤（默认开启，trend_window=90）
    ---------------------------------------
        纯均值回归在强趋势中会反复"摸顶抄底"被碾轧。此处用一条更长的均线界定趋势：
        上行趋势（close > 长均线）只允许"超卖做多"（把回撤当回调）；
        下行趋势（close < 长均线）只允许"超买做空"（把反弹当回调）；
        趋势方向与信号相反或趋势不明时，一律返回 None（强制空仓），从信号源消除逆势交易。
    """

    config: MeanReversionConfig
    closes: deque[float]
    sma: RollingSMA
    trend_sma: RollingSMA | None
    _long_ma: float | None

    def __init__(self, config: MeanReversionConfig | None = None) -> None:
        self.config = config if config is not None else MeanReversionConfig()
        self.closes = deque(maxlen=self.config.window)
        self.sma = RollingSMA(self.config.window)
        self.trend_sma = (
            RollingSMA(self.config.trend_window)
            if self.config.trend_window > 0
            else None
        )
        self._long_ma = None

    def generate_signal(self, _index: int, previous_bar: Bar | None) -> float | None:
        if previous_bar is None:
            return None

        close = previous_bar.close
        self.closes.append(close)
        mean = self.sma.update(close)
        if mean is None or len(self.closes) < self.config.window:
            return None

        # 趋势状态过滤：仅在趋势方向与反向信号一致时开仓，避免逆趋势摸顶/抄底。
        # 使用「上一根已收盘价的滞后均线」作为趋势基准（不含当根），即 close 与
        # 其 trailing MA 比较；warmup 不足时不开仓。
        if self.trend_sma is not None:
            prev_long_ma = self._long_ma
            self._long_ma = self.trend_sma.update(close)
            if prev_long_ma is None:
                return None
            uptrend = close > prev_long_ma
            downtrend = close < prev_long_ma
        else:
            uptrend = downtrend = True  # 关闭过滤（trend_window=0）时不限方向

        var = sum((c - mean) ** 2 for c in self.closes) / self.config.window
        std = sqrt(var)
        if std <= 1e-12:
            return None

        z = (close - mean) / std
        if z > self.config.entry_z:
            # 超买 -> 做空，但仅允许在下行趋势（反弹视为回调），否则阻断。
            return -self.config.target_size if downtrend else None
        if z < -self.config.entry_z:
            # 超卖 -> 做多，但仅允许在上行趋势（回撤视为回调），否则阻断。
            return self.config.target_size if uptrend else None
        if abs(z) <= self.config.exit_z:
            return 0.0
        return None

    def reset(self) -> None:
        self.closes = deque(maxlen=self.config.window)
        self.sma = RollingSMA(self.config.window)
        self.trend_sma = (
            RollingSMA(self.config.trend_window)
            if self.config.trend_window > 0
            else None
        )
        self._long_ma = None
