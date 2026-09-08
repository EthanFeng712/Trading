import csv
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from collections.abc import Iterator
from math import isfinite


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


class CsvDataLoader:
    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def _iter_rows(self) -> Iterator[dict[str, str | None]]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV 文件不存在: {self.file_path}")

        with self.file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield row

    def load_closes(self) -> list[float]:
        closes: list[float] = []
        for row in self._iter_rows():
            close_price = row.get("close") or row.get("Close")
            if close_price is not None:
                closes.append(float(close_price))
        if not closes:
            raise ValueError(f"没有收盘数据: {self.file_path}")
        return closes

    def get_interval(self, bars: list[Bar]) -> timedelta:
        timestamps: list[datetime] = []
        counts: dict[timedelta, int] = {}
        for bar in bars:
            timestamp = bar.timestamp
            timestamps.append(timestamp)
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i - 1]
            counts[interval] = counts.get(interval, 0) + 1
        if not counts:
            raise ValueError("无法确定时间间隔，因为没有足够的时间戳数据。")
        else:
            most_common_interval = max(counts, key=counts.get)
        return most_common_interval

    def check_bar(self, index: int, bar: Bar) -> None:
        if not all(isfinite(value) for value in [bar.open, bar.high, bar.low, bar.close, bar.volume]):
            raise ValueError(f"第 {index} 行数据有误: 价格和成交量必须为有限数")
        if min(bar.open, bar.high, bar.low, bar.close) <= 0:
            raise ValueError(f"第 {index} 行数据有误: 价格必须为正数")
        if bar.volume < 0:
            raise ValueError(f"第 {index} 行数据有误: 成交量不能为负数")
        if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
            raise ValueError(f"第 {index} 行数据有误: 开盘价、收盘价必须在最高价和最低价之间")

    def load_ohlcv(self) -> list[Bar]:
        rows: list[Bar] = []
        for i, row in enumerate(self._iter_rows(), 1):
            open_price = row.get("open") or row.get("Open")
            high_price = row.get("high") or row.get("High")
            low_price = row.get("low") or row.get("Low")
            close_price = row.get("close") or row.get("Close")
            volume = row.get("volume") or row.get("Volume") or "0"
            timestamp_text = row.get("timestamp") or row.get("Timestamp")
            if not all([open_price, high_price, low_price, close_price]):
                raise ValueError(f"第 {i} 行数据有误: OHLC 数据不能为空")
            if timestamp_text is None:
                raise ValueError(f"第 {i} 行数据有误: 时间戳不能为空")
            bar = Bar(
                    open=float(open_price),
                    high=float(high_price),
                    low=float(low_price),
                    close=float(close_price),
                    volume=float(volume),
                    timestamp=datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
                )
            self.check_bar(i, bar)
            rows.append(bar)
        rows.sort(key=lambda bar: bar.timestamp)
        for i in range(1, len(rows)):
            if rows[i].timestamp == rows[i - 1].timestamp:
                raise ValueError(f"时间戳重复: {rows[i].timestamp} in {self.file_path}")
        if not rows:
            raise ValueError(f"没有数据: {self.file_path}")
        return rows
