from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from ..backtest.engine import BacktestResult
from .metrics import Metrics
from .metrics import calculate_metrics

GOOD_COLOR = "green"
BAD_COLOR = "red"

def format_str(value: float, benchmark_value: float, format_spec: str, higher_better: bool = True) -> str:
    text = f"{value:{format_spec}}"

    is_better = value > benchmark_value if higher_better else value < benchmark_value

    if value == benchmark_value:
        return text
    return f"[{GOOD_COLOR}]{text}[/{GOOD_COLOR}]" if is_better else f"[{BAD_COLOR}]{text}[/{BAD_COLOR}]"

def comparison_report(strategy_name: str, strategy_report: BacktestResult, benchmark_report: BacktestResult) -> None:
    console = Console()
    strategy_metrics: Metrics = calculate_metrics(strategy_report)
    benchmark_metrics: Metrics = calculate_metrics(benchmark_report)

    table = Table(
        title="回测报告",
        title_style="bold",
        box=box.SIMPLE_HEAD,
        header_style="bold cyan",
        padding=(0, 2),
    )
    table.add_column("指标")
    table.add_column(strategy_name.replace("_", " "), justify="right")
    table.add_column("买入并持有", justify="right")

    table.add_row(
        "最终资金",
        format_str(strategy_report.final_cash, benchmark_report.final_cash, ",.2f"),
        f"{benchmark_report.final_cash:,.2f}",
    )
    table.add_row(
        "总盈亏",
        format_str(strategy_metrics.total_pnl, benchmark_metrics.total_pnl, ",.2f"),
        f"{benchmark_metrics.total_pnl:,.2f}",
    )
    table.add_row(
        "总收益率",
        format_str(strategy_metrics.total_return, benchmark_metrics.total_return, ".2%"),
        f"{benchmark_metrics.total_return:.2%}",
    )
    table.add_row(
        "年化收益率",
        format_str(strategy_metrics.annualized_return, benchmark_metrics.annualized_return, ".2%"),
        f"{benchmark_metrics.annualized_return:.2%}",
    )
    table.add_row(
        "最大回撤",
        format_str(strategy_metrics.max_drawdown, benchmark_metrics.max_drawdown, ".2%", False),
        f"{benchmark_metrics.max_drawdown:.2%}",
    )

    console.print(table)
    console.print("年化收益率超基准:", format_str(strategy_metrics.annualized_return - benchmark_metrics.annualized_return, 0, ",.2%"))

    stats = Table.grid(padding=(0, 2))
    stats.add_column(style="cyan")
    stats.add_column(justify="right")
    stats.add_column(style="cyan")
    stats.add_column(justify="right")
    stats.add_column(style="cyan")
    stats.add_column(justify="right")

    stats.add_row(
        "交易次数",
        str(strategy_metrics.trade_count),
        "胜率",
        f"{strategy_metrics.win_rate:.2%}",
        "平均盈亏",
        f"{strategy_metrics.average_pnl:,.2f}",
    )

    console.print(stats)

    if strategy_report.liquidated:
        console.print(
            Panel.fit(
                "[bold red]回测结束，策略在回测期间被强制平仓！[/bold red]",
                title="发生强平",
                border_style="red",
            )
        )
    else:
        console.print("\n[green]状态[/] 回测正常结束。\n")

def print_report(strategy_name: str, result: BacktestResult) -> None:
    console = Console()
    metrics: Metrics = calculate_metrics(result)

    table = Table(
        title=f"{strategy_name.replace('_', ' ')} 策略回测报告",
        title_style="bold",
        box=box.SIMPLE_HEAD,
        header_style="bold cyan",
        padding=(0, 2),
    )
    table.add_column("指标")
    table.add_column("数值", justify="right")

    table.add_row("最终资金", f"{result.final_cash:,.2f}")
    table.add_row("总盈亏", format_str(metrics.total_pnl, 0, ",.2f"))
    table.add_row("总收益率", format_str(metrics.total_return, 0, ".2%"))
    table.add_row("年化收益率", format_str(metrics.annualized_return, 0, ".2%"))
    table.add_row("最大回撤", f"{metrics.max_drawdown:.2%}")

    console.print(table)

    stats = Table.grid(padding=(0, 2))
    stats.add_column(style="cyan")
    stats.add_column(justify="right")
    stats.add_column(style="cyan")
    stats.add_column(justify="right")
    stats.add_column(style="cyan")
    stats.add_column(justify="right")

    stats.add_row(
        "交易次数",
        str(metrics.trade_count),
        "胜率",
        f"{metrics.win_rate:.2%}",
        "平均盈亏",
        f"{metrics.average_pnl:,.2f}",
    )

    console.print(stats)
    console.print("\n[green]状态[/] 回测正常结束。\n")