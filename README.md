# Trading v2.0

一个基于本地 CSV 历史数据的量化回测学习项目。项目不依赖交易所 API，也不会发送真实订单。

项目支持行情数据校验、目标仓位、多空交易、加减仓和反手，并计入手续费、滑点、资金约束与做空爆仓。回测完成后可查看策略指标、Buy-and-Hold 基准对比、权益曲线、HTML 回测报告与交易日志可视化仪表盘。v2.0 将回测参数与策略参数分别放入配置对象，并内置 SMA 交叉、Donchian 通道、买入持有、动量趋势跟踪与均值回归五类策略。

## 快速开始

需要 Python 3.10 或更高版本。克隆仓库后，在仓库根目录执行：

```bash
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

后续命令均在 `Quant.py` 所在的仓库根目录执行。安装依赖并运行：

```bash
python -m pip install -r requirements.txt
python Quant.py
```

- `1`：SMA 快慢均线交叉策略，可设置窗口（默认 `25` 和 `99`）及目标仓位（默认 `0.2`）
- `2`：Donchian Channel 策略，可设置窗口（默认 `20`）及目标仓位（默认 `0.2`）
- `3`：满仓买入并持有策略
- `4`：动量趋势跟踪策略（Momentum），可设置动量窗口（默认 `20`）、触发阈值（默认 `0.0`）及目标仓位（默认 `0.2`）
- `5`：均值回归策略（Mean Reversion），可设置均值窗口（默认 `20`）、入场 z 阈值（默认 `2.0`）、平仓 z 阈值（默认 `0.5`）及目标仓位（默认 `0.2`）；默认启用长周期趋势门控（trend_window=90），仅在趋势方向上逆势开仓，以降低均值回归在单边市中的亏损

## 文件结构

```text
Trading/
├── .gitignore
├── __init__.py
├── __main__.py               # 支持 python -m Trading
├── Quant.py                  # 命令行入口
├── README.md
├── requirements.txt          # 第三方依赖
├── visualize_trades.py       # 解析 trade_log.csv 生成交易日志可视化仪表盘（内联 SVG）
├── data/
│   └── sample.csv            # Binance BTCUSDT 现货日线示例数据
├── output/
│   └──                       # 运行时自动创建；内容不会提交
├── src/
│   ├── __init__.py
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── backtest.py       # 组装并运行回测
│   │   ├── config.py         # 不可变回测参数及范围校验
│   │   └── engine.py         # 账户、持仓、成交、滑点和爆仓处理
│   ├── data/
│   │   ├── __init__.py
│   │   └── data_loader.py    # CSV 校验、排序、周期推断和 Bar 模型
│   ├── reports/
│   │   ├── charts.py         # 内联 SVG 图表助手（折线/柱状/堆叠/环形），零依赖
│   │   ├── console.py        # 输出控制台回测报告
│   │   ├── equity.py         # 绘制权益曲线
│   │   ├── html_report.py    # 自包含 HTML 回测报告
│   │   ├── metrics.py        # 收益、回撤和交易指标
│   │   └── trade_log.py      # 导出交易日志 CSV
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py           # 策略抽象接口
│   │   ├── buy_and_hold.py   # 买入并持有策略
│   │   ├── donchian.py       # Donchian Channel 策略与配置
│   │   ├── mean_reversion.py # 均值回归策略与配置（含长周期趋势门控）
│   │   ├── momentum.py       # 动量趋势跟踪策略与配置
│   │   └── sma_cross.py      # SMA 均线交叉策略与配置
│   └── utils/
│       └── indicators.py     # 批量与滚动 SMA 等技术指标
└── tests/
    ├── test_backtest.py      # 策略工厂与参数装配
    ├── test_buy_and_hold.py  # 买入并持有策略
    ├── test_charts.py        # 内联 SVG 图表助手
    ├── test_config.py        # 回测配置默认值、边界与非法值
    ├── test_console.py       # 控制台指标比较与颜色判断
    ├── test_data_loader.py   # CSV 与时间戳处理
    ├── test_donchian.py      # Donchian 策略
    ├── test_engine.py        # 多空、加减仓、反手和手续费
    ├── test_html_report.py   # HTML 报告端到端渲染
    ├── test_indicators.py    # SMA 指标
    ├── test_mean_reversion.py# 均值回归（z 计分与趋势门控）
    ├── test_metrics.py       # 回测指标
    ├── test_momentum.py      # 动量趋势跟踪策略
    ├── test_risk_controls.py # 止损与波动率目标风控
    ├── test_sma_cross.py     # SMA 策略
    ├── test_trade_log.py     # 交易日志精度
    └── test_visualize.py     # 交易日志可视化仪表盘
```

## 数据与回测规则

CSV 必须包含以下列：

```text
timestamp,open,high,low,close,volume
```

`data/sample.csv` 会随仓库提交，既可直接运行演示，也可作为 CSV 加载逻辑的参考数据。数据来自 Binance 公开历史数据归档（`data.binance.vision`）的 BTCUSDT 现货日线，覆盖 2020 至 2025 年；项目运行时只读取本地 CSV，不会请求 Binance API。加载器会解析 UTC 时间戳、按时间排序、拒绝重复时间戳，并推断 K 线周期。

```text
上一根已收盘 K 线 -> 策略给出目标仓位 -> 当前 K 线 open 成交 -> 当前 K 线 close 估值
```

策略返回目标仓位：`1.0` 为全多，`0.2` 为 20% 仓位做多，`0.0` 为空仓，负数为做空，`None` 表示保持当前仓位。回测结束仍有持仓时，按最后一根 K 线的 `close` 结算。

成交会计入手续费和固定比例滑点，买入价更高、卖出价更低。目标仓位的微小偏差不会重复下单；做多不能使用超过现金的资金。空头权益低于维持保证金时会爆仓，随后停止交易，并以剩余现金补齐权益曲线。

交互输入使用小数形式，例如 `0.001` 表示 `0.1%`，`0.0005` 表示 `0.05%`。

引擎只遍历一次行情数据，策略自行保存所需状态。

输出文件：

- `output/equity_curve.png`：账户权益曲线。
- `output/trade_log.csv`：每笔完整交易的方向、时间、均价、累计数量、手续费和盈亏。
- `output/backtest_report.html`：每次回测结束自动生成的自包含 HTML 报告（内联 SVG，离线可用），含 KPI、权益曲线、逐笔盈亏、多空对比、持仓周期分布与交易明细。
- `output/trade_dashboard.html`：由 `visualize_trades.py` 解析 `trade_log.csv` 生成的可视化仪表盘（内联 SVG，离线可用），含累计净盈亏曲线、逐笔盈亏、多空占比环形图、年度多空分布、持仓周期分布与交易明细。

所有图表配色遵循 A 股惯例：**盈利（红）/ 亏损（绿）**，与控制台输出（盈利为红、亏损为绿）保持一致。

每次运行会覆盖上一次生成的同名输出文件。

控制台会输出总收益率、年化收益率、最大回撤、交易次数、胜率、平均单笔盈亏和回测结束原因。SMA Cross 与 Donchian Channel 报告还会展示相对满仓 Buy-and-Hold 的指标对比和年化超额收益。

## 测试

项目使用标准库 `unittest`：

```bash
# 在 Trading 仓库根目录执行
python -m unittest discover -s tests -v
```

测试覆盖 CSV 校验、非法行情数据、配置校验（含风控边界）、指标与策略信号、策略状态重置、目标仓位边界、多空交易、加减仓、反手、资金约束、滑点、爆仓、回测结束结算、回测指标、控制台指标比较、交易日志精度、内联 SVG 图表助手、HTML 报告端到端渲染、交易日志可视化仪表盘、动量趋势跟踪、均值回归（z 计分与趋势门控）以及止损与波动率目标风控。

## 当前局限

- 仅支持单一标的和本地 CSV 数据，不连接交易所或实盘账户。
- 订单按下一根 K 线 `open` 完全成交；滑点为固定比例，尚未模拟订单簿、买卖价差、部分成交和限价单。
- 做空采用简化的现货借币模型，尚未计算借币利息、分级保证金和额外爆仓费用。
- 目标仓位限制在 `-1.0` 到 `1.0`，尚未支持杠杆。
- 当前策略使用可配置但固定的目标仓位，尚未加入动态仓位管理。
- 尚未支持多标的组合、样本外检验、参数优化、无风险利率比较和夏普比率。
