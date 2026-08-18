# Trading v1.2

一个使用本地 CSV 历史数据的量化策略回测学习项目。它不依赖交易所 API，也不会发送真实订单。

v1.2 在可配置策略与自动化测试的基础上，加入收益、风险和交易表现指标。

## 运行

在项目上一级目录运行：

```bash
python -m Trading
```

或直接运行：

```bash
python Trading/Quant.py
```

- `1`：SMA 快慢均线交叉策略，可设置快慢均线窗口，默认 `10` 和 `30`
- `2`：买入并持有策略

生成收益曲线需要 `matplotlib`：

```bash
pip install matplotlib
```

## 文件结构

```text
Trading/
├── __main__.py               # 支持 python -m Trading
├── Quant.py                  # 命令行入口
├── .gitignore                # 忽略缓存、环境变量和生成的输出文件
├── README.md
├── data/
│   └── sample.csv            # BTCUSDT 现货日线，2020-2025，UTC 时间戳
├── output/
│   └── .gitkeep              # 保留目录；生成文件不会提交
├── src/
│   ├── data/
│   │   └── data_loader.py    # CSV 校验、排序、周期推断和 Bar 模型
│   ├── strategies/
│   │   ├── base.py           # BaseStrategy 和 Signal
│   │   ├── sma_cross.py      # SMA 均线交叉策略
│   │   └── buy_and_hold.py   # 买入并持有策略
│   ├── backtest/
│   │   ├── engine.py         # 账户、仓位、成交、手续费和交易记录
│   │   └── backtest.py       # 组装并运行回测
│   ├── reports/
│   │   ├── equity.py         # 绘制权益曲线
│   │   ├── metrics.py        # 计算收益、回撤和交易指标
│   │   └── trade_log.py      # 导出交易日志 CSV
│   └── utils/
│       └── indicators.py     # SMA 等技术指标
└── tests/
    ├── test_backtest.py      # 策略工厂与参数装配测试
    ├── test_data_loader.py   # CSV 排序、周期和重复时间戳测试
    ├── test_engine.py        # 引擎成交、仓位与手续费规则测试
    ├── test_indicators.py    # SMA 指标计算测试
    ├── test_metrics.py       # 回测指标计算测试
    └── test_sma_cross.py     # SMA 策略信号测试
```

## 数据与时间

CSV 必须包含：

```text
timestamp,open,high,low,close,volume
```

加载器会解析 UTC 时间戳、按时间排序，并拒绝缺失 OHLC、缺失时间戳和重复时间戳的数据。它从相邻 K 线最常见的正时间间隔推断数据周期；交易日志据此在日线时显示日期，在更短周期时保留完整时间。

## 回测规则

```text
已收盘的历史 K 线 -> 策略信号 -> 下一根 K 线 open 成交 -> 当前 close 估值
```

- 策略输出 `BUY`、`SELL` 或 `NONE`。
- 当前只支持做多，且同一时间只允许一个仓位，不加仓。
- `position_size` 控制每次开仓使用的现金比例，默认值为 `0.2`。
- 买入数量已包含买入手续费，买入与卖出手续费都会计入交易 PnL。
- 回测结束仍有仓位时，按最后一根 K 线的 `close` 强制平仓。

输出文件：

- `output/equity_curve.png`：按市场时间绘制的账户权益曲线。
- `output/trade_log.csv`：方向、买卖时间、价格、数量、手续费和单笔 PnL。

`output/` 目录会提交到仓库，但其中回测生成的文件会被 `.gitignore` 忽略。

控制台还会输出总收益率、最大回撤、交易次数、胜率和平均单笔盈亏。

## 测试

项目使用 Python 标准库 `unittest`：

```bash
python -m unittest discover -s Trading/tests -v
```

测试覆盖 CSV 排序与时间戳校验、SMA 指标和交叉信号、策略参数装配、成交时点、仓位限制、手续费、收益指标和非法账户配置。

## 当前边界

v1.2 是学习用的最小回测框架，尚未支持做空、加减仓、滑点、价差、限价单、多标的和夏普比率。
