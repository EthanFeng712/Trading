from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import dates as mdates

from ..backtest.engine import EquityPoint


def generate_equity_curve_plot(equity_curve: list[EquityPoint], output_path: str | Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).resolve().parents[2] / "output" / "equity_curve.png"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    timestamps = [point.timestamp for point in equity_curve]
    equities = [point.equity for point in equity_curve]

    figure, axis = plt.subplots(figsize=(8, 4))
    if all(timestamp is not None for timestamp in timestamps):
        axis.plot(timestamps, equities, linewidth=1.5)
        axis.xaxis.set_major_locator(mdates.AutoDateLocator())
        axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(axis.xaxis.get_major_locator()))
        axis.set_xlabel("Date (UTC)")
    else:
        axis.plot(equities, linewidth=1.5)
        axis.set_xlabel("Bar Index")

    plt.title("Equity Curve")
    axis.set_ylabel("Equity")
    axis.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path
