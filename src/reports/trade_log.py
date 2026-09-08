import csv
from pathlib import Path
from datetime import timedelta

from ..data.data_loader import Bar
from ..backtest.engine import Trade

def generate_trade_log_csv(log: list[Trade], ohlcv: list[Bar], out_path: str | Path | None = None, interval: timedelta | None = None) -> Path:
    if out_path is None:
        out_path = Path(__file__).resolve().parents[2] / "output" / "trade_log.csv"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8-sig", newline="") as csvfile:
        fieldnames = ["side", "entry_time", "exit_time", "average_entry_price", "average_exit_price", "cumulative_quantity", "max_quantity", "count", "commission", "gross_pnl", "net_pnl"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        day_interval: bool = True if interval is not None and interval.total_seconds() % 86400 == 0 else False
        for trade in log:
            writer.writerow({
                "side": trade.side.value,
                "entry_time": trade.entry_time.strftime("%Y-%m-%d") if day_interval else trade.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": trade.exit_time.strftime("%Y-%m-%d") if day_interval else trade.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "average_entry_price": round(trade.average_entry_price, 8),
                "average_exit_price": round(trade.average_exit_price, 8),
                "cumulative_quantity": round(trade.cumulative_quantity, 8),
                "max_quantity": round(trade.max_quantity, 8),
                "count": trade.count,
                "commission": round(trade.commission, 8),
                "gross_pnl": round(trade.gross_pnl, 8),
                "net_pnl": round(trade.net_pnl, 8)
            })
    return out_path