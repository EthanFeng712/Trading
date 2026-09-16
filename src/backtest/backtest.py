from pathlib import Path

from ..data.data_loader import CsvDataLoader
from ..data.data_loader import Bar
from ..reports.equity import generate_equity_curve_plot
from ..reports.trade_log import generate_trade_log_csv
from ..reports.html_report import generate_html_report
from ..reports.console import comparison_report
from ..reports.console import print_report
from ..strategies.base import BaseStrategy
from ..strategies.buy_and_hold import BuyAndHoldStrategy
from ..strategies.sma_cross import SmaCrossStrategy, SmaCrossConfig
from ..strategies.donchian import DonchianConfig, DonchianStrategy
from ..strategies.momentum import MomentumConfig, MomentumStrategy
from ..strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from ..strategies.regime import RegimeConfig, RegimeFilteredStrategy
from .engine import SimpleBacktestEngine
from .engine import BacktestResult
from .config import BacktestConfig


def build_strategy(
    name: str,
    strategy_config: object | None = None,
    regime_config: object | None = None,
) -> BaseStrategy:
    if name == "Buy_and_Hold":
        if strategy_config is not None:
            raise ValueError("BuyAndHoldStrategy 不接受策略配置")
        base: BaseStrategy = BuyAndHoldStrategy()
    elif name == "SMA_Cross":
        if strategy_config is None:
            base = SmaCrossStrategy()
        elif not isinstance(strategy_config, SmaCrossConfig):
            raise TypeError("SMA_Cross 需要 SmaCrossConfig")
        else:
            base = SmaCrossStrategy(config=strategy_config)
    elif name == "Donchian_Channel":
        if strategy_config is None:
            base = DonchianStrategy()
        elif not isinstance(strategy_config, DonchianConfig):
            raise TypeError("Donchian_Channel 需要 DonchianConfig")
        else:
            base = DonchianStrategy(config=strategy_config)
    elif name == "Momentum":
        if strategy_config is None:
            base = MomentumStrategy()
        elif not isinstance(strategy_config, MomentumConfig):
            raise TypeError("Momentum 需要 MomentumConfig")
        else:
            base = MomentumStrategy(config=strategy_config)
    elif name == "Mean_Reversion":
        if strategy_config is None:
            base = MeanReversionStrategy()
        elif not isinstance(strategy_config, MeanReversionConfig):
            raise TypeError("Mean_Reversion 需要 MeanReversionConfig")
        else:
            base = MeanReversionStrategy(config=strategy_config)
    else:
        raise ValueError(f"未知策略名: {name}")

    # 状态过滤仅包裹趋势类策略；Buy_and_Hold 不包裹。
    if regime_config is not None and name != "Buy_and_Hold":
        if not isinstance(regime_config, RegimeConfig):
            raise TypeError("regime_config 需要 RegimeConfig")
        return RegimeFilteredStrategy(base, regime_config)
    return base


def run_backtest(
    ohlcv: list[Bar],
    strategy_name: str = "Buy_and_Hold",
    strategy_config: object | None = None,
    config: BacktestConfig | None = None,
    regime_config: object | None = None,
) -> BacktestResult:
    """在给定 K 线上执行回测并返回完整结果。

    纯函数：无交互输入、无文件输出，可直接用于参数扫描、批量对比与自动化测试。
    regime_config 非 None 时会用状态过滤器包裹趋势策略。
    """
    strategy = build_strategy(strategy_name, strategy_config, regime_config)
    engine = SimpleBacktestEngine(config=config)
    return engine.run(ohlcv, strategy)


def demo(
    csv_path: str | Path | None = None,
    strategy_name: str = "Buy_and_Hold",
    strategy_config: object | None = None,
    regime_config: object | None = None,
    stop_loss_rate: float | None = None,
    vol_target_annual: float | None = None,
) -> BacktestResult:
    """交互式回测演示：读取参数、跑回测、打印报告并落盘产物。

    需要程序化调用（无 stdin）时请改用 run_backtest。
    新增可选参数 regime_config / stop_loss_rate / vol_target_annual 用于启用
    优化栈（状态过滤 + 对称止损 + 波动率目标化仓位）；默认均为关闭。
    """
    if csv_path is None:
        csv_path = Path(__file__).resolve().parents[2] / "data" / "sample.csv"
    else:
        csv_path = Path(csv_path)

    loader = CsvDataLoader(csv_path)
    ohlcv: list[Bar] = loader.load_ohlcv()

    cash = float(input("请输入初始资金（默认为 10000）: ") or 10000.0)
    commission_rate = float(input("请输入手续费率（默认为 0.001）: ") or 0.001)
    slippage_rate = float(input("请输入滑点率（默认为 0.0005）: ") or 0.0005)
    maintenance_margin_rate = float(input("请输入维持保证金率（默认为 0.1）: ") or 0.1)
    config = BacktestConfig(
        initial_cash=cash,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        maintenance_margin_rate=maintenance_margin_rate,
        stop_loss_rate=stop_loss_rate,
        vol_target_annual=vol_target_annual,
    )

    result = run_backtest(ohlcv, strategy_name, strategy_config, config, regime_config=regime_config)
    benchmark = None
    if strategy_name == "Buy_and_Hold":
        print_report(strategy_name, result)
    else:
        benchmark = run_backtest(ohlcv, "Buy_and_Hold", None, config)
        comparison_report(strategy_name, result, benchmark)

    interval = loader.get_interval(ohlcv)
    output_path = generate_equity_curve_plot(result.equity_curve)
    log_path = generate_trade_log_csv(log=result.trades, ohlcv=ohlcv, interval=interval)
    report_path = generate_html_report(
        result,
        config=config,
        strategy_name=strategy_name,
        source_path=csv_path,
        benchmark_result=benchmark,
        interval=interval,
    )
    print("收益曲线已保存到:", output_path)
    print("交易日志已保存到:", log_path)
    print("回测报告已保存到:", report_path)

    return result
