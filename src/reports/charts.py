# -*- coding: utf-8 -*-
"""纯标准库的内联 SVG 图表助手，供回测报告使用（无 matplotlib / 无外部依赖）。

配色遵循 A 股惯例：盈利(正)→红、亏损(负)→绿；做多→蓝、做空→橙。
"""
import html

C_PROFIT = "#d64545"
C_LOSS = "#2e9e5b"
C_LONG = "#3b6fb5"
C_SHORT = "#e0902b"
C_GRID = "#e6eaef"
C_AXIS = "#9aa6b2"
C_TEXT = "#33404d"
C_SUB = "#7a8794"


def _esc(s):
    return html.escape(str(s))


def svg_line(
    ys,
    *,
    xlabels=None,
    w=760,
    h=360,
    title="",
    ylabel="",
    line_color=C_LONG,
    area=True,
    fmt_y=lambda v: f"{v:,.0f}",
    zero=True,
    series2=None,
    series2_color=C_SHORT,
    legend=None,
):
    """折线图。series2 为可选的第二组数据（与 ys 等长），用于叠加基准曲线。"""
    pad_l, pad_r, pad_t, pad_b = 64, 24, 46, 54
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    n = len(ys)
    if n == 0:
        return ""
    vals = list(ys)
    if series2:
        vals += list(series2)
    if zero:
        vals = vals + [0]
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
        grid += (f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" '
                 f'stroke="{C_GRID}" stroke-width="1"/>')
        grid += f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{C_SUB}">{_esc(fmt_y(val))}</text>'
    if zero and ymin < 0 < ymax:
        yz = sy(0)
        grid += f'<line x1="{pad_l}" y1="{yz:.1f}" x2="{w - pad_r}" y2="{yz:.1f}" stroke="{C_AXIS}" stroke-width="1.2"/>'

    def path(series):
        pts = [(sx(i), sy(series[i])) for i in range(n)]
        return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), pts

    d1, pts1 = path(ys)
    area_d = d1 + f" L {pts1[-1][0]:.1f},{sy(ymin):.1f} L {pts1[0][0]:.1f},{sy(ymin):.1f} Z" if area else ""
    area_svg = f'<path d="{area_d}" fill="{line_color}" fill-opacity="0.10"/>' if area else ""
    line1 = f'<path d="{d1}" fill="none" stroke="{line_color}" stroke-width="2.2" stroke-linejoin="round"/>'
    extra = ""
    if series2:
        d2, _ = path(series2)
        extra = f'<path d="{d2}" fill="none" stroke="{series2_color}" stroke-width="1.8" stroke-dasharray="5 3" stroke-linejoin="round"/>'

    xlab = ""
    if xlabels:
        step = max(1, n // 8)
        for i in range(0, n, step):
            xlab += f'<text x="{sx(i):.1f}" y="{h - pad_b + 18:.1f}" text-anchor="middle" font-size="10" fill="{C_SUB}">{_esc(xlabels[i])}</text>'

    title_svg = f'<text x="{pad_l}" y="24" font-size="14" font-weight="600" fill="{C_TEXT}">{_esc(title)}</text>'
    leg = ""
    if legend:
        lx = w - pad_r - (len(legend) * 130)
        for lab, col in legend:
            leg += f'<rect x="{lx}" y="16" width="14" height="4" rx="2" fill="{col}"/>'
            leg += f'<text x="{lx + 19}" y="22" font-size="11" fill="{C_TEXT}">{_esc(lab)}</text>'
            lx += 130
    yl = ""
    if ylabel:
        yc = pad_t + plot_h / 2
        yl = f'<text x="16" y="{yc:.0f}" font-size="11" fill="{C_SUB}" transform="rotate(-90 16 {yc:.0f})" text-anchor="middle">{_esc(ylabel)}</text>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet">'
            f'{grid}{area_svg}{line1}{extra}{xlab}{leg}{title_svg}{yl}</svg>')


def svg_bar(values, *, labels=None, colors=None, w=760, h=360, title="", ylabel="",
            fmt_y=lambda v: f"{v:,.0f}", zero=True, bar_gap=0.28):
    """柱状图。bar_gap 控制柱间留白（0=紧贴）。"""
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

    bw = plot_w / n * (1 - bar_gap)
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
    if not groups:
        return ""
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
