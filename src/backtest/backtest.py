from pathlib import Path

from ..data.data_loader import CsvDataLoader
from ..data.data_loader import Bar
from ..reports.equity import generate_equity_curve_plot
from ..reports.trade_log import generate_trade_log_csv
from ..strategies.base import BaseStrategy
from ..strategies.buy_and_hold import BuyAndHoldStrategy
from ..strategies.sma_cross import SmaCrossStrategy
from ..reports.metrics import calculate_metrics
from ..reports.metrics import Metrics
from .engine import SimpleBacktestEngine


def build_strategy(name: str, param: tuple[int, int] | None = None) -> BaseStrategy:
    if name == "buy_and_hold":
        if param is not None:
            raise ValueError("BuyAndHoldStrategy does not accept parameters")
        return BuyAndHoldStrategy()
    if name == "sma_cross":
        if param is None:
            return SmaCrossStrategy()
        if len(param) != 2:
            raise ValueError("SmaCrossStrategy requires fast and slow windows")
        fast_window, slow_window = param
        return SmaCrossStrategy(fast_window=fast_window, slow_window=slow_window)
    raise ValueError(f"未知策略名: {name}")


def demo(
    csv_path: str | Path | None = None,
    strategy_name: str = "sma_cross",
    param: tuple[int, int] | None = None,
) -> None:
    if csv_path is None:
        csv_path = Path(__file__).resolve().parents[2] / "data" / "sample.csv"
    else:
        csv_path = Path(csv_path)

    loader = CsvDataLoader(csv_path)
    ohlcv: list[Bar] = loader.load_ohlcv()

    strategy = build_strategy(strategy_name, param)
    cash = float(input("请输入初始资金（默认为 10000）: ") or 10000.0)
    commission_rate = float(input("请输入手续费率（默认为 0.001）: ") or 0.001)
    slippage_rate = float(input("请输入滑点率（默认为 0.0005）: ") or 0.0005)
    maintenance_margin_rate = float(input("请输入维持保证金率（默认为 0.1）: ") or 0.1)
    engine = SimpleBacktestEngine(
        initial_cash=cash,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        maintenance_margin_rate=maintenance_margin_rate,
    )
    result = engine.run(ohlcv, strategy)

    print("策略回测演示")
    print("数据文件:", csv_path)
    print("初始资金:", result.initial_cash)
    print("最终资金:", round(result.final_cash, 2))
    metrics: Metrics = calculate_metrics(result)
    print("总盈亏:", round(metrics.total_pnl, 2))
    print("总收益率:", round(metrics.total_return * 100, 2), "%")
    print("年化收益率:", round(metrics.annualized_return * 100, 2), "%")
    print("最大回撤:", round(metrics.max_drawdown * 100, 2), "%")
    print("交易次数:", metrics.trade_count)
    print("胜率:", round(metrics.win_rate * 100, 2), "%")
    print("平均每笔盈亏:", round(metrics.average_pnl, 2))
    print("回测结束原因:", "维持保证金不足，强制平仓" if result.liquidated else "正常结束")

    if strategy_name != "buy_and_hold":
        benchmark_result = engine.run(ohlcv, BuyAndHoldStrategy())
        benchmark_metrics = calculate_metrics(benchmark_result)
        print("买入并持有策略最终资金:", round(benchmark_result.final_cash, 2))
        print("买入持有基准年化收益率:", round(benchmark_metrics.annualized_return * 100, 2), "%")
        print("买入持有基准最大回撤:", round(benchmark_metrics.max_drawdown * 100, 2), "%")
        print(
            "年化超额收益:",
            round((metrics.annualized_return - benchmark_metrics.annualized_return) * 100, 2),
            "%",
        )

    interval = loader.get_interval(ohlcv)
    output_path = generate_equity_curve_plot(result.equity_curve)
    log_path = generate_trade_log_csv(log=result.trades, ohlcv=ohlcv, interval=interval)
    print("收益曲线已保存到:", output_path)
    print("交易日志已保存到:", log_path)
