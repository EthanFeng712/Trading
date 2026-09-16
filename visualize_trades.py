# -*- coding: utf-8 -*-
"""
读取 D:\\trading\\output\\trade_log.csv，解析交易数据并以内联 SVG 仪表盘形式可视化。

零第三方依赖（仅标准库），输出单一 HTML 文件，完全离线、可直接在浏览器/预览面板打开。

配色遵循 A 股惯例：盈利(正)→红，亏损(负)→绿。
"""
import csv
import html
import math
import pathlib
import statistics
from collections import defaultdict
from datetime import date

CSV_PATH = pathlib.Path(r"D:\trading\output\trade_log.csv")
OUT_PATH = pathlib.Path(r"D:\trading\output\trade_dashboard.html")

# 调色板
C_PROFIT = "#d64545"   # 盈利 → 红
C_LOSS = "#2e9e5b"     # 亏损 → 绿
C_LONG = "#3b6fb5"     # 做多
C_SHORT = "#e0902b"    # 做空
C_GRID = "#e6eaef"
C_AXIS = "#9aa6b2"
C_TEXT = "#33404d"
C_SUB = "#7a8794"


# --------------------------------------------------------------------------- #
# 数据解析
# --------------------------------------------------------------------------- #
def load_trades(path: pathlib.Path):
    trades = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            et = date.fromisoformat(row["entry_time"])
            xt = date.fromisoformat(row["exit_time"])
            trades.append(
                {
                    "side": row["side"],
                    "entry": et,
                    "exit": xt,
                    "entry_price": float(row["average_entry_price"]),
                    "exit_price": float(row["average_exit_price"]),
                    "cum_qty": float(row["cumulative_quantity"]),
                    "max_qty": float(row["max_quantity"]),
                    "count": int(row["count"]),
                    "commission": float(row["commission"]),
                    "gross": float(row["gross_pnl"]),
                    "net": float(row["net_pnl"]),
                    "holding": (xt - et).days,
                }
            )
    return trades


# --------------------------------------------------------------------------- #
# SVG 绘图助手（纯字符串，无外部依赖）
# --------------------------------------------------------------------------- #
def _esc(s):
    return html.escape(str(s))


def svg_line(ys, *, xlabels=None, w=760, h=360, title="", ylabel="",
             line_color=C_LONG, area=True, fmt_y=lambda v: f"{v:,.0f}", zero=True):
    pad_l, pad_r, pad_t, pad_b = 64, 24, 46, 54
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    n = len(ys)
    if n == 0:
        return ""
    vals = list(ys) + ([0] if zero else [])
    ymin, ymax = min(vals), max(vals)
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    span = ymax - ymin
    ymax += span * 0.08
    ymin -= span * 0.08

    def sx(i):
        return pad_l + (plot_w * (i / (n - 1)) if n > 1 else plot_w / 2)

    def sy(v):
        return pad_t + plot_h * (1 - (v - ymin) / (ymax - ymin))

    grid = ""
    for k in range(6):
        val = ymin + (ymax - ymin) * k / 6
        y = sy(val)
        grid += f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" stroke="{C_GRID}" stroke-width="1"/>'
        grid += f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{C_SUB}">{_esc(fmt_y(val))}</text>'
    if zero and ymin < 0 < ymax:
        yz = sy(0)
        grid += f'<line x1="{pad_l}" y1="{yz:.1f}" x2="{w - pad_r}" y2="{yz:.1f}" stroke="{C_AXIS}" stroke-width="1.2"/>'

    pts = [(sx(i), sy(ys[i])) for i in range(n)]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area_d = d + f" L {pts[-1][0]:.1f},{sy(ymin):.1f} L {pts[0][0]:.1f},{sy(ymin):.1f} Z" if area else ""
    area_svg = f'<path d="{area_d}" fill="{line_color}" fill-opacity="0.10"/>' if area else ""
    line_svg = f'<path d="{d}" fill="none" stroke="{line_color}" stroke-width="2.2" stroke-linejoin="round"/>'

    xlab = ""
    if xlabels:
        step = max(1, n // 8)
        for i in range(0, n, step):
            xlab += f'<text x="{sx(i):.1f}" y="{h - pad_b + 18:.1f}" text-anchor="middle" font-size="10" fill="{C_SUB}">{_esc(xlabels[i])}</text>'

    title_svg = f'<text x="{pad_l}" y="24" font-size="14" font-weight="600" fill="{C_TEXT}">{_esc(title)}</text>'
    yl = ""
    if ylabel:
        yc = pad_t + plot_h / 2
        yl = f'<text x="16" y="{yc:.0f}" font-size="11" fill="{C_SUB}" transform="rotate(-90 16 {yc:.0f})" text-anchor="middle">{_esc(ylabel)}</text>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet">'
            f'{grid}{area_svg}{line_svg}{xlab}{title_svg}{yl}</svg>')


def svg_bar(values, *, labels=None, colors=None, w=760, h=360, title="", ylabel="",
            fmt_y=lambda v: f"{v:,.0f}", zero=True):
    pad_l, pad_r, pad_t, pad_b = 64, 24, 46, 54
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    n = len(values)
    if n == 0:
        return ""
    vals = list(values) + ([0] if zero else [])
    ymin, ymax = min(vals), max(vals)
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    span = ymax - ymin
    ymax += span * 0.08
    ymin -= span * 0.08

    def sy(v):
        return pad_t + plot_h * (1 - (v - ymin) / (ymax - ymin))

    grid = ""
    for k in range(6):
        val = ymin + (ymax - ymin) * k / 6
        y = sy(val)
        grid += f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" stroke="{C_GRID}" stroke-width="1"/>'
        grid += f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{C_SUB}">{_esc(fmt_y(val))}</text>'
    if zero and ymin < 0 < ymax:
        yz = sy(0)
        grid += f'<line x1="{pad_l}" y1="{yz:.1f}" x2="{w - pad_r}" y2="{yz:.1f}" stroke="{C_AXIS}" stroke-width="1.2"/>'

    bw = plot_w / n * 0.72
    gap = plot_w / n
    bars = ""
    step = max(1, n // 12)
    for i, v in enumerate(values):
        x = pad_l + gap * i + (gap - bw) / 2
        y0 = sy(0)
        y1 = sy(v)
        ytop = min(y0, y1)
        bh = abs(y0 - y1)
        c = colors[i] if colors else C_LONG
        bars += f'<rect x="{x:.1f}" y="{ytop:.1f}" width="{bw:.1f}" height="{max(bh, 0):.1f}" fill="{c}" rx="1.5"/>'
        if labels and i % step == 0:
            bars += f'<text x="{x + bw / 2:.1f}" y="{h - pad_b + 18:.1f}" text-anchor="middle" font-size="10" fill="{C_SUB}">{_esc(labels[i])}</text>'

    title_svg = f'<text x="{pad_l}" y="24" font-size="14" font-weight="600" fill="{C_TEXT}">{_esc(title)}</text>'
    yl = ""
    if ylabel:
        yc = pad_t + plot_h / 2
        yl = f'<text x="16" y="{yc:.0f}" font-size="11" fill="{C_SUB}" transform="rotate(-90 16 {yc:.0f})" text-anchor="middle">{_esc(ylabel)}</text>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet">'
            f'{grid}{bars}{title_svg}{yl}</svg>')


def svg_stacked(groups, *, w=760, h=360, title="", ylabel="",
                seg_colors=(C_LONG, C_SHORT), seg_labels=("做多", "做空")):
    pad_l, pad_r, pad_t, pad_b = 64, 24, 52, 54
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    n = len(groups)
    totals = [sum(g[1]) for g in groups]
    ymax = max(totals) if totals else 1
    ymax = ymax * 1.12 if ymax else 1

    def sy(v):
        return pad_t + plot_h * (1 - v / ymax)

    grid = ""
    for k in range(6):
        val = ymax * k / 6
        y = sy(val)
        grid += f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" stroke="{C_GRID}" stroke-width="1"/>'
        grid += f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{C_SUB}">{val:,.0f}</text>'

    bw = plot_w / n * 0.6
    gap = plot_w / n
    bars = ""
    for i, (lab, vals) in enumerate(groups):
        x = pad_l + gap * i + (gap - bw) / 2
        ybase = sy(0)
        for j, v in enumerate(vals):
            hgt = plot_h * (v / ymax)
            ytop = ybase - hgt
            bars += f'<rect x="{x:.1f}" y="{ytop:.1f}" width="{bw:.1f}" height="{max(hgt, 0):.1f}" fill="{seg_colors[j]}"/>'
            ybase = ytop
        bars += f'<text x="{x + bw / 2:.1f}" y="{h - pad_b + 18:.1f}" text-anchor="middle" font-size="10" fill="{C_SUB}">{_esc(lab)}</text>'

    legend = ""
    lx = pad_l
    for j, lab in enumerate(seg_labels):
        legend += f'<rect x="{lx}" y="34" width="11" height="11" fill="{seg_colors[j]}"/>'
        legend += f'<text x="{lx + 15}" y="44" font-size="11" fill="{C_TEXT}">{_esc(lab)}</text>'
        lx += 15 + len(lab) * 12 + 16
    title_svg = f'<text x="{pad_l}" y="20" font-size="14" font-weight="600" fill="{C_TEXT}">{_esc(title)}</text>'
    yl = ""
    if ylabel:
        yc = pad_t + plot_h / 2
        yl = f'<text x="16" y="{yc:.0f}" font-size="11" fill="{C_SUB}" transform="rotate(-90 16 {yc:.0f})" text-anchor="middle">{_esc(ylabel)}</text>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet">'
            f'{grid}{bars}{legend}{title_svg}{yl}</svg>')


def svg_donut(segments, *, w=380, h=300, title="", center_text=None):
    total = sum(s[1] for s in segments)
    cx, cy, r = w / 2, h / 2 - 4, 92
    if total <= 0:
        return ""
    a0 = -90.0
    arcs = ""
    for _lab, val, c in segments:
        frac = val / total
        a1 = a0 + frac * 360
        large = 1 if (a1 - a0) > 180 else 0
        x0 = cx + r * math.cos(math.radians(a0))
        y0 = cy + r * math.sin(math.radians(a0))
        x1 = cx + r * math.cos(math.radians(a1))
        y1 = cy + r * math.sin(math.radians(a1))
        arcs += (f'<path d="M {cx:.1f},{cy:.1f} L {x0:.1f},{y0:.1f} '
                 f'A {r},{r} 0 {large} 1 {x1:.1f},{y1:.1f} Z" fill="{c}"/>')
        a0 = a1
    leg = ""
    lx, ly = 14, h - 30
    for lab, val, c in segments:
        pct = val / total * 100
        leg += f'<rect x="{lx}" y="{ly}" width="12" height="12" fill="{c}"/>'
        leg += f'<text x="{lx + 17}" y="{ly + 11}" font-size="11" fill="{C_TEXT}">{_esc(lab)} {val:.0f} ({pct:.0f}%)</text>'
        ly += 18
    title_svg = f'<text x="{w / 2}" y="20" font-size="14" font-weight="600" fill="{C_TEXT}" text-anchor="middle">{_esc(title)}</text>'
    ct = (f'<text x="{cx}" y="{cy + 6}" font-size="20" font-weight="700" fill="{C_TEXT}" text-anchor="middle">{_esc(center_text)}</text>'
          if center_text else "")
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet">'
            f'{arcs}{ct}{leg}{title_svg}</svg>')


# --------------------------------------------------------------------------- #
# 指标计算
# --------------------------------------------------------------------------- #
def build_metrics(trades):
    n = len(trades)
    wins = sum(1 for t in trades if t["net"] > 0)
    losses = sum(1 for t in trades if t["net"] < 0)
    total_net = sum(t["net"] for t in trades)
    total_gross = sum(t["gross"] for t in trades)
    total_comm = sum(t["commission"] for t in trades)
    avg_holding = statistics.mean(t["holding"] for t in trades) if n else 0
    longs = [t for t in trades if t["side"] == "LONG"]
    shorts = [t for t in trades if t["side"] == "SHORT"]
    long_net = sum(t["net"] for t in longs)
    short_net = sum(t["net"] for t in shorts)
    cum = 0.0
    cum_series = []
    for t in trades:
        cum += t["net"]
        cum_series.append(cum)
    date_min = min(t["entry"] for t in trades)
    date_max = max(t["exit"] for t in trades)

    # 年度分组（按入场年）
    by_year = defaultdict(lambda: [0, 0])
    for t in trades:
        y = t["entry"].year
        idx = 0 if t["side"] == "LONG" else 1
        by_year[y][idx] += 1
    years = sorted(by_year)
    year_groups = [(str(y), by_year[y]) for y in years]

    # 持仓周期分箱 (天)
    bins = [(0, 30), (30, 60), (60, 90), (90, 180), (180, 360), (360, 10 ** 9)]
    hist_labels = []
    hist_vals = []
    for lo, hi in bins:
        if hi >= 10 ** 9:
            label = f"{lo}+"
            cnt = sum(1 for t in trades if t["holding"] >= lo)
        else:
            label = f"{lo}-{hi}"
            cnt = sum(1 for t in trades if lo <= t["holding"] < hi)
        hist_labels.append(label)
        hist_vals.append(cnt)

    return dict(
        n=n, wins=wins, losses=losses,
        win_rate=wins / n if n else 0,
        total_net=total_net, total_gross=total_gross, total_comm=total_comm,
        avg_holding=avg_holding,
        long_count=len(longs), short_count=len(shorts),
        long_net=long_net, short_net=short_net,
        cum_series=cum_series,
        date_min=date_min, date_max=date_max,
        year_groups=year_groups,
        hist_labels=hist_labels, hist_vals=hist_vals,
    )


# --------------------------------------------------------------------------- #
# HTML 组装
# --------------------------------------------------------------------------- #
def build_html(trades, m):
    fmt_money = lambda v: f"¥{v:,.0f}"
    fmt_signed = lambda v: f"{'+' if v >= 0 else '−'}¥{abs(v):,.0f}"

    # 逐笔净盈亏配色（盈红亏绿）
    net_colors = [C_PROFIT if t["net"] >= 0 else C_LOSS for t in trades]
    net_labels = [t["entry"].strftime("%y-%m") for t in trades]
    cum_labels = [t["entry"].strftime("%y-%m") for t in trades]
    cum_color = C_PROFIT if m["cum_series"][-1] >= 0 else C_LOSS

    line_chart = svg_line(m["cum_series"], xlabels=cum_labels, title="累计净盈亏曲线",
                          ylabel="累计净盈亏", line_color=cum_color, fmt_y=fmt_money)
    bar_chart = svg_bar([t["net"] for t in trades], labels=net_labels, colors=net_colors,
                        title="逐笔净盈亏", ylabel="净盈亏", fmt_y=fmt_signed)
    year_chart = svg_stacked(m["year_groups"], title="年度交易次数（多空分布）",
                             ylabel="交易笔数")
    hist_chart = svg_bar(m["hist_vals"], labels=m["hist_labels"],
                         title="持仓周期分布", ylabel="交易笔数", fmt_y=lambda v: f"{v:.0f}", zero=False)
    donut = svg_donut([("做多", m["long_count"], C_LONG), ("做空", m["short_count"], C_SHORT)],
                      title="多空交易笔数占比", center_text=str(m["n"]))

    # 多空净盈亏对比（小柱状）
    cmp_chart = svg_bar([m["long_net"], m["short_net"]],
                        labels=["做多", "做空"],
                        colors=[C_LONG, C_SHORT],
                        title="多空累计净盈亏对比", ylabel="净盈亏",
                        fmt_y=fmt_signed, zero=True)

    kpis = [
        ("总交易笔数", str(m["n"]), ""),
        ("胜率", f"{m['win_rate']:.1%}", f"盈利 {m['wins']} / 亏损 {m['losses']}"),
        ("累计净盈亏", fmt_signed(m["total_net"]), f"毛利 {fmt_money(m['total_gross'])}"),
        ("总手续费", fmt_money(m["total_comm"]), "成本支出"),
        ("平均持仓天数", f"{m['avg_holding']:.0f}", "天"),
        ("多/空笔数", f"{m['long_count']} / {m['short_count']}", ""),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{v}</div><div class="kpi-l">{l}</div><div class="kpi-s">{s}</div></div>'
        for l, v, s in kpis
    )

    # 明细表
    rows = ""
    for i, t in enumerate(trades, 1):
        cls = "pos" if t["net"] >= 0 else "neg"
        side_cls = "long" if t["side"] == "LONG" else "short"
        rows += (
            f"<tr><td>{i}</td>"
            f'<td><span class="tag {side_cls}">{t["side"]}</span></td>'
            f'<td>{t["entry"]}</td><td>{t["exit"]}</td>'
            f'<td class="num">{t["entry_price"]:,.2f}</td>'
            f'<td class="num">{t["exit_price"]:,.2f}</td>'
            f'<td class="num">{t["cum_qty"]:.4f}</td>'
            f'<td class="num">{t["holding"]}</td>'
            f'<td class="num">{t["count"]}</td>'
            f'<td class="num">{t["commission"]:,.2f}</td>'
            f'<td class="num {cls}">{t["net"]:,.2f}</td></tr>'
        )

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
    .kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin-bottom:22px;}
    .kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 14px;
      box-shadow:0 1px 3px rgba(20,30,50,.04);}
    .kpi-v{font-size:22px;font-weight:700;line-height:1.1;}
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
    .table-scroll{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:8px;}
    footer{max-width:1180px;margin:24px auto 0;color:var(--sub);font-size:11px;line-height:1.6;}
    @media(max-width:900px){.kpis{grid-template-columns:repeat(3,1fr);}.grid{grid-template-columns:1fr;}}
    """

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>交易日志可视化仪表盘</title>
<style>{css}</style>
</head>
<body>
<header>
  <h1>交易日志可视化仪表盘</h1>
  <p>数据源：D:\\trading\\output\\trade_log.csv ｜ 交易区间 {m['date_min']} ~ {m['date_max']} ｜ 共 {m['n']} 笔交易
     ｜ 配色遵循 A 股惯例：<span style="color:var(--red)">盈利(红)</span> / <span style="color:var(--green)">亏损(绿)</span></p>
</header>
<div class="wrap">
  <div class="kpis">{kpi_html}</div>
  <div class="grid">
    <div class="card full">{line_chart}</div>
    <div class="card"><h3>逐笔净盈亏</h3><div class="hint">单笔交易盈亏，红涨绿跌</div>{bar_chart}</div>
    <div class="card"><h3>多空交易笔数占比</h3><div class="hint">做多 vs 做空</div>{donut}</div>
    <div class="card"><h3>年度交易次数（多空分布）</h3><div class="hint">按入场年份统计</div>{year_chart}</div>
    <div class="card"><h3>多空累计净盈亏对比</h3><div class="hint">做多 vs 做空总盈亏</div>{cmp_chart}</div>
    <div class="card full"><h3>持仓周期分布</h3><div class="hint">平仓与开仓间隔天数</div>{hist_chart}</div>
  </div>
  <div class="card full" style="margin-top:18px;">
    <h3>交易明细</h3>
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th>#</th><th>方向</th><th>开仓日</th><th>平仓日</th><th class="num">开仓均价</th>
          <th class="num">平仓均价</th><th class="num">累计数量</th><th class="num">持仓(天)</th>
          <th class="num">成交次数</th><th class="num">手续费</th><th class="num">净盈亏</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
</div>
<footer>
  说明：本仪表盘由 visualize_trades.py 解析 trade_log.csv 生成，仅依赖 Python 标准库，图表为内联 SVG（离线可用）。
  净盈亏 = 毛利 − 手续费；胜率 = 净盈亏为正的笔数 / 总笔数。
</footer>
</body>
</html>
"""
    return html_doc


def main():
    trades = load_trades(CSV_PATH)
    if not trades:
        raise SystemExit("未解析到任何交易记录，请确认 CSV 路径与格式。")
    m = build_metrics(trades)
    doc = build_html(trades, m)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(doc, encoding="utf-8")
    print(f"已生成仪表盘：{OUT_PATH}")
    print(f"交易笔数={m['n']}  胜率={m['win_rate']:.1%}  累计净盈亏={m['total_net']:,.2f}  "
          f"多/空={m['long_count']}/{m['short_count']}  平均持仓={m['avg_holding']:.0f}天")


if __name__ == "__main__":
    main()
