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
        fieldnames = ["side", "entry_time", "exit_time", "entry_price", "exit_price", "quantity", "commission", "pnl"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        day_interval: bool = True if interval is not None and interval.total_seconds() % 86400 == 0 else False
        for trade in log:
            writer.writerow({
                "side": trade.side.value,
                "entry_time": ohlcv[trade.entry_index].timestamp.strftime("%Y-%m-%d") if day_interval else ohlcv[trade.entry_index].timestamp,
                "exit_time": ohlcv[trade.exit_index].timestamp.strftime("%Y-%m-%d") if day_interval else ohlcv[trade.exit_index].timestamp,
                "entry_price": f"{trade.entry_price:.2f}",
                "exit_price": f"{trade.exit_price:.2f}",
                "quantity": f"{trade.quantity:.4f}",
                "commission": f"{trade.commission:.2f}",
                "pnl": f"{trade.pnl:.2f}",
            })    
    return out_path