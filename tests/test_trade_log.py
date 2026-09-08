import csv
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.backtest.engine import PositionSide
from src.backtest.engine import Trade
from src.reports.trade_log import generate_trade_log_csv


class TradeLogTests(unittest.TestCase):
    def test_small_quantities_keep_eight_decimal_places(self) -> None:
        cumulative_quantity = 1 / 810
        max_quantity = 8 / 810
        trade = Trade(
            side=PositionSide.LONG,
            entry_time=datetime(2024, 1, 1),
            exit_time=datetime(2024, 1, 2),
            average_entry_price=42_000,
            average_exit_price=43_000,
            cumulative_quantity=cumulative_quantity,
            max_quantity=max_quantity,
            count=2,
            gross_pnl=1,
            commission=0.1,
            net_pnl=0.9,
        )

        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "trade_log.csv"
            generate_trade_log_csv(
                log=[trade],
                ohlcv=[],
                out_path=output_path,
                interval=timedelta(days=1),
            )

            with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))

        self.assertEqual(float(row["cumulative_quantity"]), round(cumulative_quantity, 8))
        self.assertEqual(float(row["max_quantity"]), round(max_quantity, 8))


if __name__ == "__main__":
    unittest.main()
