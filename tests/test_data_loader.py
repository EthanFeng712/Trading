from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.data.data_loader import CsvDataLoader


class CsvDataLoaderTests(unittest.TestCase):
    def write_csv(self, directory: str, rows: list[str]) -> Path:
        path = Path(directory) / "bars.csv"
        path.write_text(
            "timestamp,open,high,low,close,volume\n" + "\n".join(rows),
            encoding="utf-8",
        )
        return path

    def test_load_ohlcv_sorts_timestamps_and_infers_interval(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.write_csv(directory, [
                "2024-01-03T00:00:00Z,3,3,3,3,30",
                "2024-01-01T00:00:00Z,1,1,1,1,10",
                "2024-01-02T00:00:00Z,2,2,2,2,20",
            ])
            loader = CsvDataLoader(path)

            bars = loader.load_ohlcv()

            self.assertEqual([bar.close for bar in bars], [1, 2, 3])
            self.assertEqual(loader.get_interval(bars), timedelta(days=1))

    def test_duplicate_timestamps_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.write_csv(directory, [
                "2024-01-01T00:00:00Z,1,1,1,1,10",
                "2024-01-01T00:00:00Z,2,2,2,2,20",
            ])

            with self.assertRaises(ValueError):
                CsvDataLoader(path).load_ohlcv()

    def test_invalid_bars_are_rejected(self) -> None:
        invalid_rows = {
            "missing OHLC": "2024-01-01T00:00:00Z,,2,1,1.5,10",
            "missing timestamp": ",1,2,1,1.5,10",
            "zero price": "2024-01-01T00:00:00Z,0,2,1,1.5,10",
            "negative volume": "2024-01-01T00:00:00Z,1,2,1,1.5,-1",
            "non-finite value": "2024-01-01T00:00:00Z,1,inf,1,1.5,10",
            "invalid OHLC range": "2024-01-01T00:00:00Z,3,2,1,1.5,10",
        }

        for case, row in invalid_rows.items():
            with self.subTest(case=case), TemporaryDirectory() as directory:
                path = self.write_csv(directory, [row])

                with self.assertRaises(ValueError):
                    CsvDataLoader(path).load_ohlcv()


if __name__ == "__main__":
    unittest.main()
