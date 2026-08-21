# Trading v1.4

一个基于本地 CSV 历史数据的量化回测学习项目。项目不依赖交易所 API，也不会发送真实订单。

v1.4 将策略接口升级为“目标仓位”：引擎现在支持做多、做空、加仓、减仓、平仓和反手，并记录完整持仓生命周期的交易数据。

## 快速开始

需要 Python 3.10 或更高版本。克隆仓库后，在仓库根目录执行：

```bash
git clone <仓库地址>
cd Trading

# 创建虚拟环境
python -m venv .venv
```

激活虚拟环境：

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

安装依赖并运行：

```bash
python -m pip install -r requirements.txt
python Quant.py
```

- `1`：SMA 快慢均线交叉策略，可设置快慢均线窗口，默认 `10` 和 `30`
- `2`：买入并持有策略

也可以在仓库上一级目录以模块方式运行：

```bash
python -m Trading
```

## 文件结构

```text
Trading/
├── __init__.py
├── __main__.py               # 支持 python -m Trading
├── Quant.py                  # 命令行入口
├── .gitignore
├── README.md
├── requirements.txt          # 第三方依赖
├── data/
│   └── sample.csv            # Binance BTCUSDT 现货日线示例数据
├── output/
│   └──                       # 运行时自动创建；内容不会提交
├── src/
│   ├── __init__.py
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── backtest.py       # 组装并运行回测
│   │   └── engine.py         # 账户、持仓、成交和 Trade 生命周期
│   ├── data/
│   │   ├── __init__.py
│   │   └── data_loader.py    # CSV 校验、排序、周期推断和 Bar 模型
│   ├── reports/
│   │   ├── equity.py         # 绘制权益曲线
│   │   ├── metrics.py        # 收益、回撤和交易指标
│   │   └── trade_log.py      # 导出交易日志 CSV
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py           # 策略抽象接口
│   │   ├── buy_and_hold.py   # 买入并持有策略
│   │   └── sma_cross.py      # SMA 均线交叉策略
│   └── utils/
│       └── indicators.py     # SMA 等技术指标
└── tests/
    ├── test_backtest.py      # 策略工厂与参数装配
    ├── test_data_loader.py   # CSV 与时间戳处理
    ├── test_engine.py        # 多空、加减仓、反手和手续费
    ├── test_indicators.py    # SMA 指标
    ├── test_metrics.py       # 回测指标
    └── test_sma_cross.py     # SMA 策略
```

## 数据与回测规则

CSV 必须包含以下列：

```text
timestamp,open,high,low,close,volume
```

`data/sample.csv` 会随仓库提交，既可直接运行演示，也可作为 CSV 加载逻辑的参考数据。数据来自 Binance 公开历史数据归档（`data.binance.vision`）的 BTCUSDT 现货日线，覆盖 2020 至 2025 年；项目运行时只读取本地 CSV，不会请求 Binance API。加载器会解析 UTC 时间戳、按时间排序、拒绝重复时间戳，并推断 K 线周期。

```text
已收盘历史 K 线 -> 策略给出目标仓位 -> 下一根 K 线 open 成交 -> 当前 close 估值
```

策略返回目标仓位：`1.0` 为全多，`0.2` 为 20% 多仓，`0.0` 为空仓，负数为做空，`None` 表示保持当前仓位。回测结束仍有持仓时，按最后一根 K 线的 `close` 强制平仓。

输出文件：

- `output/equity_curve.png`：账户权益曲线。
- `output/trade_log.csv`：每笔完整交易的方向、时间、均价、累计数量、手续费和盈亏。

控制台会输出总收益率、年化收益率、最大回撤、交易次数、胜率、平均单笔盈亏，以及相对 Buy-and-Hold 的年化超额收益。

## 测试

项目使用标准库 `unittest`：

```bash
# 在 Trading 的上一级目录执行
python -m unittest discover -s Trading/tests -v
```

测试覆盖 CSV 校验、指标、策略、目标仓位、多空交易、加减仓、反手、强制平仓、手续费和回测指标。

## 当前局限

- 仅支持单一标的和本地 CSV 数据，不连接交易所或实盘账户。
- 订单按下一根 K 线 `open` 完全成交，尚未模拟滑点、买卖价差、部分成交和限价单。
- 做空没有保证金、资金费率或爆仓规则。
- 不支持杠杆交易。
- 目标仓位为 `1.0` 时，手续费可能使现金暂时为负；资金约束尚未建模。
- SMA Cross 目前使用固定目标仓位，尚未加入基于波动率、趋势强弱或风险预算的动态仓位管理。
- 尚未支持多标的组合、样本外检验、参数优化、无风险利率比较和夏普比率。
