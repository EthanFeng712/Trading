from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from Trading.src.data.data_loader import CsvDataLoader


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


if __name__ == "__main__":
    unittest.main()
