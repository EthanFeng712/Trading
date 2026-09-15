from pathlib import Path

from ..data.data_loader import CsvDataLoader
from ..data.data_loader import Bar
from ..reports.equity import generate_equity_curve_plot
from ..reports.trade_log import generate_trade_log_csv
from ..reports.console import comparison_report
from ..reports.console import print_report
from ..strategies.base import BaseStrategy
from ..strategies.buy_and_hold import BuyAndHoldStrategy
from ..strategies.sma_cross import SmaCrossStrategy, SmaCrossConfig
from ..strategies.donchian import DonchianConfig, DonchianStrategy
from .engine import SimpleBacktestEngine
from .config import BacktestConfig


def build_strategy(name: str, strategy_config: object | None = None) -> BaseStrategy:
    if name == "Buy_and_Hold":
        if strategy_config is not None:
            raise ValueError("BuyAndHoldStrategy 不接受策略配置")
        return BuyAndHoldStrategy()
    if name == "SMA_Cross":
        if strategy_config is None:
            return SmaCrossStrategy()
        if not isinstance(strategy_config, SmaCrossConfig):
            raise TypeError("SMA_Cross 需要 SmaCrossConfig")
        return SmaCrossStrategy(config=strategy_config)
    if name == "Donchian_Channel":
        if strategy_config is None:
            return DonchianStrategy()
        if not isinstance(strategy_config, DonchianConfig):
            raise TypeError("Donchian_Channel 需要 DonchianConfig")
        return DonchianStrategy(config=strategy_config)

    raise ValueError(f"未知策略名: {name}")


def demo(
    csv_path: str | Path | None = None,
    strategy_name: str = "Buy_and_Hold",
    strategy_config: object | None = None,
) -> None:
    if csv_path is None:
        csv_path = Path(__file__).resolve().parents[2] / "data" / "sample.csv"
    else:
        csv_path = Path(csv_path)

    loader = CsvDataLoader(csv_path)
    ohlcv: list[Bar] = loader.load_ohlcv()

    strategy = build_strategy(strategy_name, strategy_config)
    cash = float(input("请输入初始资金（默认为 10000）: ") or 10000.0)
    commission_rate = float(input("请输入手续费率（默认为 0.001）: ") or 0.001)
    slippage_rate = float(input("请输入滑点率（默认为 0.0005）: ") or 0.0005)
    maintenance_margin_rate = float(input("请输入维持保证金率（默认为 0.1）: ") or 0.1)
    config = BacktestConfig(
        initial_cash=cash,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        maintenance_margin_rate=maintenance_margin_rate,
        rebalance_tolerance=0.001,
    )
    engine = SimpleBacktestEngine(config=config)
    result = engine.run(ohlcv, strategy)

    if strategy_name == "SMA_Cross":
        comparison_report(strategy_name, result, engine.run(ohlcv, BuyAndHoldStrategy()))
    elif strategy_name == "Donchian_Channel":
        comparison_report(strategy_name, result, engine.run(ohlcv, BuyAndHoldStrategy()))
    else:
        print_report(strategy_name, result)

    interval = loader.get_interval(ohlcv)
    output_path = generate_equity_curve_plot(result.equity_curve)
    log_path = generate_trade_log_csv(log=result.trades, ohlcv=ohlcv, interval=interval)
    print("收益曲线已保存到:", output_path)
    print("交易日志已保存到:", log_path)
