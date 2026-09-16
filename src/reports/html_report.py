# -*- coding: utf-8 -*-
"""生成自包含的回测 HTML 报告（内联 SVG，无外部依赖，离线可打开）。

每次 Quant 脚本运行结束都会调用 generate_html_report，落盘为
output/backtest_report.html（每次覆盖），无需人工干预。
"""
from datetime import datetime, timedelta
from pathlib import Path

from .charts import C_LOSS, C_LONG, C_PROFIT, C_SHORT, svg_bar, svg_line, svg_stacked
from .metrics import calculate_annualized_return, calculate_max_drawdown, calculate_metrics

STRATEGY_LABELS = {
    "Buy_and_Hold": "买入并持有 (Buy & Hold)",
    "SMA_Cross": "SMA 均线交叉",
    "Donchian_Channel": "唐奇安通道 (Donchian)",
}

OUTPUT_NAME = "backtest_report.html"


def _fmt_money(v: float) -> str:
    return f"¥{v:,.2f}"


def _fmt_signed(v: float) -> str:
    return f"{'+' if v >= 0 else '−'}¥{abs(v):,.2f}"


def _fmt_pct(v: float) -> str:
    return f"{v:.2%}"


def _interval_label(interval) -> str:
    if interval is None:
        return "未知"
    if isinstance(interval, timedelta):
        days = interval.total_seconds() / 86400
        if days == 1:
            return "日线"
        if days == 7:
            return "周线"
        return f"{days:.0f} 天"
    return str(interval)


def generate_html_report(
    result,
    *,
    config,
    strategy_name: str,
    source_path,
    benchmark_result=None,
    interval=None,
    output_dir: Path | None = None,
) -> Path:
    """根据回测结果生成自包含 HTML 报告并返回文件路径。"""
    output_dir = output_dir or (Path(__file__).resolve().parents[2] / "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / OUTPUT_NAME

    m = calculate_metrics(result)
    commission_total = sum(t.commission for t in result.trades)
    annual = calculate_annualized_return(result)
    mdd = calculate_max_drawdown(result.equity_curve)
    long_net = sum(t.net_pnl for t in result.trades if t.side.name == "LONG")
    short_net = sum(t.net_pnl for t in result.trades if t.side.name == "SHORT")

    eq = result.equity_curve
    start_ts = eq[0].timestamp if eq else datetime.now()
    end_ts = eq[-1].timestamp if eq else datetime.now()
    equity_series = [p.equity for p in eq]
    equity_labels = [p.timestamp.strftime("%Y-%m") for p in eq] if eq else []
    bench_series = [p.equity for p in benchmark_result.equity_curve] if benchmark_result else None

    # —— 逐笔净盈亏 —— #
    net_values = [t.net_pnl for t in result.trades]
    net_colors = [C_PROFIT if v >= 0 else C_LOSS for v in net_values]
    net_labels = [t.entry_time.strftime("%y-%m") for t in result.trades]

    # —— 持仓周期分布 —— #
    bins = [(0, 30), (30, 60), (60, 90), (90, 180), (180, 360), (360, 10 ** 9)]
    hist_labels, hist_vals = [], []
    for lo, hi in bins:
        if hi >= 10 ** 9:
            hist_labels.append(f"{lo}+")
            hist_vals.append(sum(1 for t in result.trades if (t.exit_time - t.entry_time).days >= lo))
        else:
            hist_labels.append(f"{lo}-{hi}")
            hist_vals.append(sum(1 for t in result.trades if lo <= (t.exit_time - t.entry_time).days < hi))

    # —— 图表 —— #
    equity_chart = svg_line(
        equity_series,
        xlabels=equity_labels,
        title="账户权益曲线",
        ylabel="权益",
        line_color=C_PROFIT if result.final_cash >= result.initial_cash else C_LOSS,
        fmt_y=_fmt_money,
        series2=bench_series,
        series2_color=C_SHORT,
        legend=([("策略", C_PROFIT), ("买入持有", C_SHORT)] if bench_series else None),
    )
    net_chart = svg_bar(
        net_values, labels=net_labels, colors=net_colors,
        title="逐笔交易净盈亏", ylabel="净盈亏", fmt_y=_fmt_signed,
    )
    compare_chart = svg_bar(
        [long_net, short_net], labels=["做多", "做空"], colors=[C_LONG, C_SHORT],
        title="多空累计净盈亏对比", ylabel="净盈亏", fmt_y=_fmt_signed,
    )
    hist_chart = svg_bar(
        hist_vals, labels=hist_labels, colors=[C_LONG] * len(hist_vals),
        title="持仓周期分布", ylabel="交易笔数", bar_gap=0.08, zero=False,
        fmt_y=lambda v: f"{v:.0f}",
    )

    # —— KPI —— #
    kpis = [
        ("初始资金", _fmt_money(result.initial_cash), ""),
        ("最终资金", _fmt_money(result.final_cash), "平仓后账户总额"),
        ("总收益率", _fmt_signed(result.final_cash - result.initial_cash), _fmt_pct(m.total_return)),
        ("年化收益", _fmt_pct(annual), "按 365.25 天折算"),
        ("最大回撤", _fmt_pct(mdd), "相对历史峰值"),
        ("交易笔数", str(m.trade_count), ""),
        ("胜率", _fmt_pct(m.win_rate), f"盈利 {sum(1 for t in result.trades if t.net_pnl > 0)} 笔"),
        ("手续费合计", _fmt_money(commission_total), "成本支出"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{v}</div><div class="kpi-l">{l}</div><div class="kpi-s">{s}</div></div>'
        for l, v, s in kpis
    )

    # —— 交易明细表 —— #
    rows = ""
    for i, t in enumerate(result.trades, 1):
        cls = "pos" if t.net_pnl >= 0 else "neg"
        side_cls = "long" if t.side.name == "LONG" else "short"
        rows += (
            f"<tr><td>{i}</td>"
            f'<td><span class="tag {side_cls}">{t.side.name}</span></td>'
            f'<td>{t.entry_time.date()}</td><td>{t.exit_time.date()}</td>'
            f'<td class="num">{t.average_entry_price:,.2f}</td>'
            f'<td class="num">{t.average_exit_price:,.2f}</td>'
            f'<td class="num">{t.cumulative_quantity:.4f}</td>'
            f'<td class="num">{(t.exit_time - t.entry_time).days}</td>'
            f'<td class="num">{t.count}</td>'
            f'<td class="num">{t.commission:,.2f}</td>'
            f'<td class="num">{t.gross_pnl:,.2f}</td>'
            f'<td class="num {cls}">{t.net_pnl:,.2f}</td></tr>'
        )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    liquidated_tag = ('<span class="warn">⚠ 回测期间发生强制平仓</span>'
                      if result.liquidated else '<span class="ok">正常结束</span>')

    css = """
    :root{
      --bg:#f4f6f9; --card:#ffffff; --line:#e3e8ee; --text:#33404d; --sub:#7a8794;
      --red:#d64545; --green:#2e9e5b; --blue:#3b6fb5; --orange:#e0902b;
    }
    *{box-sizing:border-box;}
    body{margin:0;background:var(--bg);color:var(--text);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
      padding:28px 32px 48px;}
    header{max-width:1180px;margin:0 auto 22px;}
    header h1{margin:0 0 6px;font-size:24px;font-weight:700;}
    header p{margin:0;color:var(--sub);font-size:13px;}
    .wrap{max-width:1180px;margin:0 auto;}
    .meta{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px;}
    .meta div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;}
    .meta .k{font-size:11px;color:var(--sub);}
    .meta .v{font-size:13px;font-weight:600;margin-top:3px;}
    .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px;}
    .kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 14px;
      box-shadow:0 1px 3px rgba(20,30,50,.04);}
    .kpi-v{font-size:20px;font-weight:700;line-height:1.1;}
    .kpi-l{font-size:12px;color:var(--text);margin-top:6px;}
    .kpi-s{font-size:11px;color:var(--sub);margin-top:2px;}
    .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;}
    .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px 18px;
      box-shadow:0 1px 3px rgba(20,30,50,.04);}
    .card.full{grid-column:1 / -1;}
    .card h3{margin:0 0 4px;font-size:15px;font-weight:600;}
    .card .hint{font-size:11px;color:var(--sub);margin:2px 0 6px;}
    table{width:100%;border-collapse:collapse;font-size:12px;}
    th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;}
    th{color:var(--sub);font-weight:600;position:sticky;top:0;background:var(--card);}
    td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
    .pos{color:var(--red);font-weight:600;}
    .neg{color:var(--green);font-weight:600;}
    .tag{display:inline-block;padding:1px 8px;border-radius:20px;font-size:11px;font-weight:600;}
    .tag.long{background:rgba(59,111,181,.12);color:var(--blue);}
    .tag.short{background:rgba(224,144,43,.14);color:var(--orange);}
    .table-scroll{max-height:440px;overflow:auto;border:1px solid var(--line);border-radius:8px;}
    .ok{color:var(--green);font-weight:600;}
    .warn{color:var(--red);font-weight:600;}
    footer{max-width:1180px;margin:24px auto 0;color:var(--sub);font-size:11px;line-height:1.6;}
    @media(max-width:900px){.kpis,.meta{grid-template-columns:repeat(2,1fr);}.grid{grid-template-columns:1fr;}}
    """

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>量化回测报告</title>
<style>{css}</style>
</head>
<body>
<header>
  <h1>量化回测报告</h1>
  <p>生成时间：{generated} ｜ 数据源：{Path(source_path).name} ｜ 状态：{liquidated_tag}</p>
</header>
<div class="wrap">
  <div class="meta">
    <div><div class="k">策略</div><div class="v">{STRATEGY_LABELS.get(strategy_name, strategy_name)}</div></div>
    <div><div class="k">数据区间</div><div class="v">{start_ts.date()} ~ {end_ts.date()}</div></div>
    <div><div class="k">K 线周期</div><div class="v">{_interval_label(interval)}</div></div>
    <div><div class="k">数据文件</div><div class="v">{Path(source_path).resolve()}</div></div>
    <div><div class="k">初始资金</div><div class="v">{_fmt_money(config.initial_cash)}</div></div>
    <div><div class="k">手续费率</div><div class="v">{config.commission_rate:.4f}</div></div>
    <div><div class="k">滑点率</div><div class="v">{config.slippage_rate:.4f}</div></div>
    <div><div class="k">维持保证金率</div><div class="v">{config.maintenance_margin_rate:.4f}</div></div>
  </div>
  <div class="kpis">{kpi_html}</div>
  <div class="grid">
    <div class="card full">{equity_chart}</div>
    <div class="card"><h3>逐笔交易净盈亏</h3><div class="hint">单笔盈亏，红涨绿跌</div>{net_chart}</div>
    <div class="card"><h3>多空累计净盈亏对比</h3><div class="hint">做多 vs 做空</div>{compare_chart}</div>
    <div class="card full"><h3>持仓周期分布</h3><div class="hint">平仓与开仓间隔天数</div>{hist_chart}</div>
  </div>
  <div class="card full" style="margin-top:18px;">
    <h3>交易明细</h3>
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th>#</th><th>方向</th><th>开仓时间</th><th>平仓时间</th><th class="num">开仓均价</th>
          <th class="num">平仓均价</th><th class="num">累计数量</th><th class="num">持仓(天)</th>
          <th class="num">成交次数</th><th class="num">手续费</th><th class="num">毛利</th><th class="num">净盈亏</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
</div>
<footer>
  本报告由量化回测脚本在每次运行结束时自动生成，为单一自包含 HTML 文件（内联 SVG，离线可用）。
  配色遵循 A 股惯例：盈利(红) / 亏损(绿)。净盈亏 = 毛利 − 手续费；胜率 = 净盈亏为正的笔数 / 总笔数；
  最大回撤 = 区间内权益相对历史峰值的最大跌幅。
</footer>
</body>
</html>
"""
    out_path.write_text(html_doc, encoding="utf-8")
    return out_path
