from pathlib import Path

import matplotlib

# 无头环境（服务器 / CI / 容器）下没有 GUI 后端，必须显式指定，否则 savefig 可能失败。
matplotlib.use("Agg")

from matplotlib import dates as mdates  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from ..backtest.engine import EquityPoint  # noqa: E402


def generate_equity_curve_plot(equity_curve: list[EquityPoint], output_path: str | Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).resolve().parents[2] / "output" / "equity_curve.png"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    timestamps = [point.timestamp for point in equity_curve]
    equities = [point.equity for point in equity_curve]

    figure, axis = plt.subplots(figsize=(8, 4))
    try:
        if timestamps and all(timestamp is not None for timestamp in timestamps):
            axis.plot(timestamps, equities, linewidth=1.5)
            axis.xaxis.set_major_locator(mdates.AutoDateLocator())
            axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(axis.xaxis.get_major_locator()))
            axis.set_xlabel("Date (UTC)")
        else:
            axis.plot(equities, linewidth=1.5)
            axis.set_xlabel("Bar Index")

        axis.set_title("Equity Curve")
        axis.set_ylabel("Equity")
        axis.grid(True, alpha=0.3)
        figure.tight_layout()
        figure.savefig(output_path)
    finally:
        # 绘制过程中若抛异常，也必须释放 figure，否则长循环下会累积内存泄漏。
        plt.close(figure)
    return output_path
