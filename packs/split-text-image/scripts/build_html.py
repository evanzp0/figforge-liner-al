#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: pack-1 split-text-image —— 转录文本 → 书页 HTML（最终件, 公式已渲染）

用法:
  build_html.py --page 0107 --text .work/<名>/pack1/0107/text.md \
      [--figures .../figures.json] [--figure-map .../figure-map.json] \
      [--src-image project/<名>/src/0107.png] \
      [--out project/<名>/dest/0107.html] [--title "Section 3.2"] [--page-no 107]

页面尺寸（宪法第七条第 6 款②③④, 强制红线）:
  页面尺寸 = 版心优先 + 人体工程学页框（禁止照搬原图像素尺寸与原图留白）且全项目统一:
  ② 宽度取 820px 舒适阅读宽（= 模板设计稿宽, --u=1）; 高度 = ③定版的项目统一版心高
    （屏显）+ 上/下 padding, 夹紧到高/宽 ∈ [1.05, 1.60]; 禁止按原图整页宽/高比导出
    （扫描件留白失真 —— 010 页顶拥挤教训）;
  ③ 项目级参数定版（版心优先 + 人体工程学 padding, 开工前置, 强制红线）: 转换任何
    原图之前必须先定版 —— 检查 handoff.md「定版参数」段 + project/<名>/page-size.json
    机器锁; 未定版先跑 scripts/calibrate.py（版心优先策略: 随机抽 x 张原图测有效
    内容区宽×高统计定版, x = config.json layout_samples, 默认 5, --pages 可显式复现;
    padding 由人体工程学计算、禁用原图留白: 左右 = (820−版心宽)/2 等距,
    上下 = 0.75×左右 Tschichold top:outer ≈ 3:4）; 全项目所有页面自动读锁复用同一套
    参数（--page-size-file, .page padding 字面一致）; 显式 --page-size 可覆盖
    （更新锁, 须整项目重排）。本文件"无锁时按②③单页推导"仅为兑底。
    上边距 = 定版 padding, {{VOFF}} 禁止复刻扫描件页顶留白（仅限光学微调）。
  ④ 左右边距等距（扫描件边距失真校正）: 原图页缘左右边距失真（装订阴影/透印/
    歪斜使页缘不可信）, 禁止照搬页缘定位内容——水平基准 = 原图**内容区域**
    （build_html 按 --src-image 自动测算: 顶部页眉/底部页码带排除 + 页缘噪声段
    排除）, 内容区域在 .page 上水平居中放置, 左右边距严格等距
    margin = (PAGE_W − content_w·k)/2; 正文流自动包 .flow 以 width + auto margin
    落位; 定版页测得的 content_w/margin 随 page-size.json 锁存, 后续页面同规则
    自动等距并对定版 margin 校验。{{HOFF}} 降级为相对等距基准的叠加微调
    （translateX 不会破坏 auto margin 居中）; {{FLOWW}} 仅覆盖版心宽（仍等距居中）。
  版式指令中的原图像素按 k = PAGE_W/原图宽 等比缩放落位（--src-image 必给）;
  模板铬件字号/间距按 --u = PAGE_W/820 缩放。

text.md 约定（极简 Markdown, 由转录员产出, 存 .work/<名>/pack1/<page>/ —— 第十一条）:
  # / ##        标题
  $$...$$       独立公式（math_render 渲染为纯 CSS HTML, 离线可开）
  $...$         行内公式（同上）
  **粗** *斜*   行内强调（***粗斜*** 亦支持）
  - 列表项
  {{FIG:n}}     插图槽: figure-map 主档(dest/img/<stem>.svg, 重绘流程)相对引用;
                否则把裁剪 JPG 发布为最终件 dest/img/<stem>.jpg 并相对引用。
                dest 交付单元 = <page>.html + img/（同仓自洽, 不引用 .work 中间件）
  版式（宪法第七条几何保真, 原样复刻纸面布局）:
    相邻多行 {{FIG:n}}（中间无空行）→ 并排图行 .figrow,
      各图列宽比例 = 裁剪实际像素宽, 图注随图左对齐;
    {{FIG:n|aside}} → 图文混排 .figaside（左图右文）, 紧随其后的连续段落
      进右侧文字列（至下一个结构行/EOF）, 图注在整块下方;
    图注样式 = 正文字号深色非斜体, 图号前缀 "Figure N.N:" 加粗。
  版式指令（宪法第七条第 6 款① 图文布局严格复刻; 都是版式指令, 不是正文内容;
  N 一律为原页图像素, 由 build_html 按 k = PAGE_W/原图宽 等比落位）:
    {{GAP:N}}    独立一行 → 竖直占位 N 原图像素（标题/段落块在原页的竖直位置;
                 N 可负 = 上提后续内容, 复刻大字号块的内生空隙）;
    {{PX:N}}     行尾追加 → 该标题/段落字号 = N 原图像素（同时锁 line-height（{{LH}} 页级,
                 默认 1.15）与 margin:0, 让竖直节奏完全由 {{GAP}} 控制）;
    {{CTR}}      行尾追加 → 该段落水平居中（标题 h1 本就居中, 无需此令）;
    {{R}}        行尾追加 → 该段落右对齐（原页右缘对齐的页眉/标题用）;
    {{IND}}      行尾追加 → 该段落首行缩进 2em（原页段首缩进复刻, 宪法第七条第 6 款①）;
    {{SX:F}}     行尾追加 → 该块 transform:scaleX(F)（F<1 复刻窄体 condensed 字面,
                原点 50% 50%, 居中块缩放后仍居中）;
    {{HOFF:N}}   独立一行 → 正文流相对等距基准水平微调 N 原图像素（N 可负;
                 宪法④: 版心水平位置由 build_html 自动等距落位, HOFF 仅作
                 原页版心特例的显式微调, 不再承担复刻失真偏移的职责）;
    {{VOFF:N}}   独立一行 → 正文流整体上移 N 原图像素（N 负则下移; 仅限原页印刷
                 区相对版心的光学微调。**禁止用于复刻扫描件页顶留白** —— 上边距
                 已由人体工程学定版, 与原图留白无关, 宪法第七条第 6 款③）;
    {{FLOWW:N}}  独立一行 → 覆盖版心宽 = N 原图像素（仍等距居中, 宪法④;
                 默认版心宽由内容区域自动测算）;
    {{COLROW}}/{{COL:f}}/{{ENDCOLROW}}
                 多栏文本行: COLROW 开行, COL:f 开新列（f = 列宽原图像素,
                 空列 = 占位对齐列缘）, ENDCOLROW 收行; 列内每行是一个段落,
                 支持 {{GAP:N}} 独立行、{{PX}}/{{CTR}}/{{SX}}/{{R}} 行尾指令与
                 {{FIG:n}} 插图槽（图文混排图行, 宪法第七条第 6 款①）;
    {{BOX}}/{{ENDBOX}}
                 重点框（原页圆角框条目组）: 开框/收框, 框内行走同一管道
                 （段落/公式/列表/GAP 均可用）; {{BOX:N}} 可选框宽 N 原图像素
                 （N = 原页框体外宽 border-box; 框心与版心轴对称 —— 框体凸出
                 版心时禁用 margin:auto 居中, 其在溢出时按 CSS 规范归零会
                 单侧错位, 025 教训）;
    {{EQBOX:N}}  公式框（原页矩形框公式）行首指令: N = 框左缩进原图像素,
                 行内其余为框内内容; 行尾 {{EQN:文本}} = 框外右侧编号（如 (1)）;
    {{FACE:sans}}独立一行 → 正文流改无衬线字体族（书名页等非 Times 版面用）。
    {{LH:F}}     独立一行 → 其后 {{PX}} 段行距 = F（line-height; 原页行距/字号比
                 复刻用, 如正文行距比 1.3 写 {{LH:1.3}}; 默认 1.15, 影响至文件尾或
                 下一个 {{LH}}）。

插图槽解析优先级: figure-map.json(重绘 SVG 主档, 相对引用) > figures.json
(裁剪 JPG → 发布 dest/img/<stem>.jpg + 相对引用; 发布失败才 base64 兜底) > 占位注释。
<stem> 命名: 单图页 <page>, 多图页 <page>-fig<i>（与 pack-2 主档命名一致）。
公式渲染走 math_render.py（技能 output-templates 同款纯 CSS, 第零条）；
全程 html.escape + Python 端字面替换（str.replace, 无 JS $ 序列之坑 —— 宪法第五条）。
输出即最终件: dest/<page>.html。
"""
import argparse
import base64
import html
import json
import mimetypes
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import math_render  # noqa: E402

TEMPLATE = os.path.join(HERE, "..", "templates", "page.html.tmpl")

FIG_TOKEN = re.compile(r"\{\{FIG:(\d+)(?:\|(\w+))?\}\}")
FIG_LINE = re.compile(r"^\{\{FIG:(\d+)(?:\|(\w+))?\}\}$")
FIG_LEAD = re.compile(r"^((?:Figure|Fig\.?)\s*\d+(?:\.\d+)?:)\s*")
GAP_LINE = re.compile(r"^\{\{GAP:(-?\d+)\}\}$")         # 竖直占位 N 原图像素(负值 = 上提后续内容)
PX_SUFFIX = re.compile(r"\s*\{\{PX:(\d+)\}\}\s*$")      # 行尾字号覆盖 N 原图像素
CTR_SUFFIX = re.compile(r"\s*\{\{CTR\}\}\s*$")          # 行尾居中指令
R_SUFFIX = re.compile(r"\s*\{\{R\}\}\s*$")              # 行尾右对齐指令
IND_SUFFIX = re.compile(r"\s*\{\{IND\}\}\s*$")          # 行尾段首缩进指令（text-indent: 2em）
IND_SUFFIX = re.compile(r"\s*\{\{IND\}\}\s*$")          # 行尾段首缩进指令（text-indent: 2em）
HOFF_LINE = re.compile(r"^\{\{HOFF:(-?\d+)\}\}$")       # 正文流水平平移 N 原图像素
VOFF_LINE = re.compile(r"^\{\{VOFF:(-?\d+)\}\}$")       # 正文流垂直上移 N 原图像素(负=下移)
FLOWW_LINE = re.compile(r"^\{\{FLOWW:(\d+)\}\}$")       # 正文流宽度 N 原图像素(右缘锚定)
COLROW_LINE = re.compile(r"^\{\{COLROW\}\}$")           # 多栏文本行开始
COL_LINE = re.compile(r"^\{\{COL:([\d.]+)\}\}$")        # 新列, f = 列宽原图像素(空列 = 占位)
ENDCOLROW_LINE = re.compile(r"^\{\{ENDCOLROW\}\}$")     # 多栏文本行结束
FACE_LINE = re.compile(r"^\{\{FACE:(\w+)\}\}$")         # 正文字体族覆盖（sans）
LH_LINE = re.compile(r"^\{\{LH:([\d.]+)\}\}$")          # 行距覆盖（PX 段 line-height, 默认 1.15）
BOXOPEN_LINE = re.compile(r"^\{\{BOX(?::(\d+))?\}\}$")   # 重点框（圆角框）开, 可选宽 N 原图像素(居中)
BOXCLOSE_LINE = re.compile(r"^\{\{ENDBOX\}\}$")          # 重点框收
EQBOX_LINE = re.compile(r"^\{\{EQBOX:(\d+)\}\}\s*(.*)$")  # 公式框（矩形框）行, N = 左缩进原图像素
EQN_TOKEN = re.compile(r"\s*\{\{EQN:([^}]*)\}\}\s*$")    # 行尾框外编号（如 (1)）
SX_SUFFIX = re.compile(r"\s*\{\{SX:([\d.]+)\}\}\s*$")    # 行尾横向缩放（窄体复刻）
FACE_SANS = "'Liberation Sans', Arial, Helvetica, sans-serif"
TEXT_W_SRC = 840.0  # 源图正文栏宽 px（aside 图列宽换算基准; 058 实测 330..1170）
PAGE_W_BASE = 820.0  # 模板设计稿宽度（--u = PAGE_W/PAGE_W_BASE 等比缩放基准）
PAGE_W_ERGO = 820.0   # 人体工程学阅读宽度（宪法第七条第 6 款②: .page 宽度基准）
ASPECT_MIN, ASPECT_MAX = 1.05, 1.60  # 舒适高/宽比夹紧区间（第七条第 6 款②）
PAD_V_RATIO = 0.75    # 上/下 padding = 0.75 × 左右 padding（人体工程学定版,
                      # Tschichold 版心比例 top:outer ≈ 3:4; 宪法第七条第 6 款③）


def inline(text: str) -> str:
    """行内渲染: 先提取 $数学$ 交给 math_render, 再转义+施加 Markdown 标记,
    最后字面替换回渲染结果（占位符不含正则特殊字符 —— 宪法第五条）。"""
    stash: list = []

    def _keep(m):
        stash.append(math_render.render(m.group(1)))
        return "\x00%d\x00" % (len(stash) - 1)

    s = re.sub(r"\$([^$\n]+?)\$", _keep, text)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*$\n]+?)\*(?!\*)", r"<em>\1</em>", s)
    for k, rendered in enumerate(stash):
        s = s.replace("\x00%d\x00" % k, f'<span class="mth">{rendered}</span>')
    return s


def _px_style(text: str, k: float = 1.0, tag: str = "p", lh: float = 1.15) -> tuple:
    """提取行尾版式指令 {{PX:N}}/{{CTR}}/{{SX:F}}/{{R}}/{{IND}}（任意顺序, 循环剥离行尾）→
    (去指令后的文本, style 属性串, 类名串)。
    PX 同时锁 line-height/margin, 竖直节奏完全由 {{GAP}} 控制（第七条第 6 款①）;
    N 为原图像素, 按 k = PAGE_W/原图宽 等比落位。tag='h' 时 PX 标题另加 nowrap。
    返回第三元为 class 名串（"ctr"/"indent" 可组合）。"""
    classes: list = []
    parts: list = []
    while True:
        m = CTR_SUFFIX.search(text)
        if m:
            classes.append("ctr")
            text = CTR_SUFFIX.sub("", text, count=1)
            continue
        m = IND_SUFFIX.search(text)
        if m:
            classes.append("indent")
            text = IND_SUFFIX.sub("", text, count=1)
            continue
        m = R_SUFFIX.search(text)
        if m:
            parts.append("text-align:right")
            text = R_SUFFIX.sub("", text, count=1)
            continue
        m = PX_SUFFIX.search(text)
        if m:
            parts.append(f"font-size:{round(int(m.group(1)) * k)}px; line-height:{lh}; margin:0")
            if tag == "h":
                # 版式精确复刻的标题 = 单行意图; 版心宽从原图内容区测算, 可能小于
                # 本地字体布局宽, nowrap 防字体度量差导致的意外换行（宪法④）
                parts.append("white-space:nowrap")
            text = PX_SUFFIX.sub("", text, count=1)
            continue
        m = SX_SUFFIX.search(text)
        if m:
            # {{SX}} = 字面宽度精确复刻（单行）: nowrap 保证不因版心宽/字体度量差异
            # 意外换行, transform 不改变布局宽, 视觉宽度由 SX 锁定
            parts.append("transform:scaleX(%s); transform-origin:50%% 50%%; white-space:nowrap" % m.group(1))
            text = SX_SUFFIX.sub("", text, count=1)
            continue
        break
    return text.strip(), "; ".join(parts), " ".join(classes)


def _content_vext(path: str, L: int, R: int) -> tuple:
    """版心竖直范围（第七条第 6 款③ 版心高测算, 扫描件页缘失真鲁棒）:
    在内容列带 [L,R] 内取行墨水率:
      ① 上下各 2.5% 页缘截除（页角阴影/歪斜/扫描边条不可信, 同宪法④哲学）;
      ② 平滑行墨水率阈值找有效行带（正文行 ≥10px 高, 零星斑点不成带）;
      ③ 顶部页眉带排除: 首带位于顶部 15% 内且其后空隙 ≥1.5% 页高（页眉与
         正文间距特征; 第零条: 页眉不属正文版心, HTML 不复刻）;
      ④ 底部页码/页脚带排除: 末带高 <2.5% 页高、前方空隙 ≥1.2% 页高、
         且位于底部 30% 内（页码特征）。
    返回 (y_top, y_bot) 原图像素; 失败 (0, 0)。"""
    try:
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    except Exception:
        return (0, 0)
    h, w = a.shape
    if not (h and w) or R <= L:
        return (0, 0)
    med = float(np.median(a))
    th = int(max(110, min(170, med - 60)))
    band = (a < th)[:, max(0, L):R + 1]
    lo, hi = int(0.025 * h), h - int(0.025 * h)
    if hi - lo < 10:
        return (0, 0)
    dens = band[lo:hi].mean(axis=1)
    smooth = np.convolve(dens, np.ones(3) / 3.0, "same")
    act = smooth > 0.006
    # 行带聚合（连续 active 段, ≤3px 小空隙并入同带 —— 行内子带粘合）
    idx = np.where(act)[0]
    if len(idx) == 0:
        return (0, 0)
    runs = []
    s = p = int(idx[0])
    for i in idx[1:]:
        i = int(i)
        if i - p <= 3:
            p = i
            continue
        runs.append((s, p))
        s = p = i
    runs.append((s, p))
    # ③ 顶部页眉带排除（首带矮 = 页眉字号特征 + 后随大空隙; 章标题等大字高带
    #    不满足"矮"条件, 不误杀 —— 191 教训: 章标题高 67px ≠ 页眉 ~20px）
    if len(runs) > 1 and (lo + runs[0][1]) < 0.15 * h \
            and (runs[0][1] - runs[0][0]) < 0.02 * h \
            and (runs[1][0] - runs[0][1]) >= 0.015 * h:
        runs = runs[1:]
    # ④ 底部页码/页脚带排除（矮末带 + 前方空隙 + 位于底部 30% 内）
    if len(runs) > 1:
        last = runs[-1]
        if (last[1] - last[0]) < 0.025 * h \
                and (last[0] - runs[-2][1]) >= 0.012 * h \
                and (lo + last[1]) > 0.70 * h:
            runs = runs[:-1]
    return (lo + runs[0][0], lo + runs[-1][1])


def _src_page_size(path: str) -> tuple:
    """原页图像素宽高（第七条第 6 款②: 定版高宽比推导 + k 缩放基准）; 失败返回 (0, 0)。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return (0, 0)


def _content_bbox(path: str) -> tuple:
    """原页内容区域水平 bbox（第七条第 6 款④ 等距边距基准）。
    原图是扫描件, 页缘左右边距失真（装订阴影/邻页透印/歪斜使页缘不可信）,
    禁止照搬页缘定位内容。鲁棒测算:
      ① 阈值自适应二值化（中位数灰度导出, 夹紧 [110,170] 滤掉淡透印）;
      ② 列噪声清洗: 贴缘 且（窄/墨水量小）的贯穿噪声列（透印文字列/装订阴影）
         先行置零 —— 否则它们让每一行的行墨水率都超阈值, 行带检测失效;
      ③ 顶部页眉/底部页码带排除（行墨水带 + 后随空隙的启发式; 第零条:
         页眉页码不属正文版心）;
      ④ 列墨水占比分段 → 段排除兜底。
    返回 (L, R, y0, y1) 原图像素（内容区左右缘 + 正文带上下缘）; 失败 (0,0,0,0)。"""
    try:
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    except Exception:
        return (0, 0, 0, 0)
    h, w = a.shape
    if not (h and w):
        return (0, 0, 0, 0)
    med = float(np.median(a))
    th = int(max(110, min(170, med - 60)))
    ink = a < th

    def _edge_noise_segs(band2d: "np.ndarray") -> list:
        """贴缘 且（宽 <10% 页宽 或 墨水量 <8%）的段 → 页缘噪声（透印/装订阴影）。"""
        col = band2d.mean(axis=0)
        segs, start = [], None
        for i, m in enumerate(col > 0.003):
            if m and start is None:
                start = i
            if (not m) and start is not None:
                segs.append((start, i - 1))
                start = None
        if start is not None:
            segs.append((start, band2d.shape[1] - 1))
        segs = [s for s in segs if s[1] - s[0] >= 3]
        if not segs:
            return []
        total = float(band2d.sum()) or 1.0
        noise = []
        for s in segs:
            near_edge = s[0] < 0.06 * w or s[1] > 0.94 * w
            narrow = (s[1] - s[0] + 1) < 0.10 * w
            small_ink = float(band2d[:, s[0]:s[1] + 1].sum()) / total < 0.08
            if near_edge and (narrow or small_ink):
                noise.append(s)
        return noise

    # ---- ② 列噪声清洗（全页口径）----
    noise_cols = np.zeros(w, dtype=bool)
    for s in _edge_noise_segs(ink):
        noise_cols[s[0]:s[1] + 1] = True
    ink2 = ink.copy()
    if noise_cols.any():
        ink2[:, noise_cols] = False
    row = ink2.mean(axis=1)

    # ---- ③ 顶部页眉 / 底部页码带排除 ----
    y0, y1 = 0, h
    active = row > 0.005
    if active.any():
        top = int(np.argmax(active))
        if top < 0.12 * h:
            i = top
            while i < h and row[i] > 0.0005:
                i += 1
            gap = i
            while gap < h and row[gap] <= 0.0005:
                gap += 1
            if (gap - i) >= 0.015 * h and gap < 0.30 * h:
                y0 = gap
        # 底部页码带: 末墨水带（高 <2.5% 页高, 页码特征）前有 ≥1.2% 页高空隙
        bot = h - 1 - int(np.argmax(active[::-1]))
        if bot > 0.90 * h:
            i = bot
            while i >= 0 and row[i] > 0.0005:
                i -= 1
            gap = i
            while gap >= 0 and row[gap] <= 0.0005:
                gap -= 1
            if (bot - i) < 0.025 * h and (bot - gap) >= 0.012 * h and gap > 0.70 * h:
                y1 = gap + 1

    # ---- ④ 水平内容段（窗口内, 噪声列已清洗; 段排除兜底）----
    band = ink2[y0:y1]
    segs, start = [], None
    col = band.mean(axis=0)
    for i, m in enumerate(col > 0.003):
        if m and start is None:
            start = i
        if (not m) and start is not None:
            segs.append((start, i - 1))
            start = None
    if start is not None:
        segs.append((start, w - 1))
    segs = [s for s in segs if s[1] - s[0] >= 3]
    if not segs:
        return (0, 0, 0, 0)
    total_ink = float(band.sum()) or 1.0
    keep = []
    for s in segs:
        near_edge = s[0] < 0.06 * w or s[1] > 0.94 * w
        narrow = (s[1] - s[0] + 1) < 0.15 * w
        small_ink = float(band[:, s[0]:s[1] + 1].sum()) / total_ink < 0.08
        if near_edge and (narrow or small_ink):
            continue
        keep.append(s)
    if not keep:
        keep = segs
    L, R = int(keep[0][0]), int(keep[-1][1])
    return (L, R, int(y0), int(y1))


def _publish_crop(crop: str, out_dir: str, stem: str) -> bool:
    """裁剪 JPG 发布为最终件 <out_dir>/img/<stem>.jpg（dest 交付单元的一部分）。
    成功返回 True; 失败（如只读盘）返回 False, 由调用方 base64 兜底。"""
    try:
        img_dir = os.path.join(out_dir, "img")
        os.makedirs(img_dir, exist_ok=True)
        shutil.copy2(crop, os.path.join(img_dir, stem + ".jpg"))
        return True
    except OSError:
        return False


def _embed_img(path: str, n: int) -> str:
    """兜底: 插图以 base64 内嵌（发布失败时仍保证 HTML 可离线看图）。只返回 <img>。"""
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    return f'<img src="data:{mime};base64,{b64}" alt="figure {n}">'


def _img_size(path: str) -> int:
    """插图实际像素宽（并排/混排列宽比例用）; 失败返回 0。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size[0]
    except Exception:
        return 0


def _cap_html(fig: dict | None) -> str:
    """图注: 正文字号深色非斜体（模板 CSS）, 图号前缀加粗 —— 原版式。"""
    caption = (fig.get("caption") or "") if fig else ""
    if not caption:
        return ""
    return f"<figcaption>{cap_inline(caption)}</figcaption>"


def cap_inline(caption: str) -> str:
    """图注转义 + "Figure N.N:" 图号前缀加粗（纸面原图如此）。"""
    s = html.escape(caption, quote=False)
    m = FIG_LEAD.match(s)
    if m:
        s = f"<strong>{m.group(1)}</strong> {s[m.end():].lstrip()}"
    return s


def _fig_img_tag(n: int, page: str, workdir: str, fmap: dict,
                 figs_meta: list, out_dir: str, k: float = 1.0) -> tuple:
    """插图槽解析 → (<img> HTML, 实际像素宽)。
    优先级: figure-map SVG 主档(相对引用) > 裁剪 JPG(发布 dest/img/<stem>.jpg)
    > base64 兜底。解析失败返回 (None, 0)。
    <stem> 命名与 pack-2 主档一致: 单图页 <page>, 多图页 <page>-fig<i>。"""
    fig = next((f for f in figs_meta if f.get("idx") == n), None)
    stem = page if len(figs_meta) <= 1 else f"{page}-fig{n}"
    ent = fmap.get(str(n)) or fmap.get(n)
    if ent:
        path = ent.get("path", "")
        if ent.get("kind") == "svg" and path and os.path.exists(path):
            # 重绘主档已发布 dest/img/ → 相对引用（不复制不内嵌, 主档更新即生效）
            href = html.escape(os.path.basename(path), quote=True)
            w = _img_size(path)
            st = f' style="width:{round(w * k)}px"' if (w and abs(k - 1.0) > 1e-9) else ""
            return f'<img src="img/{href}" alt="figure {n}"{st}>', w
    crop = None
    if ent and ent.get("kind") != "svg" and ent.get("path") and os.path.exists(ent["path"]):
        crop = ent["path"]  # compose 场景: figure-map 直接给 crop 路径
    elif fig and os.path.exists(os.path.join(workdir, f"crops/fig{n}.jpg")):
        crop = os.path.join(workdir, f"crops/fig{n}.jpg")
    if crop:
        if _publish_crop(crop, out_dir, stem):
            w = _img_size(crop)
            st = f' style="width:{round(w * k)}px"' if (w and abs(k - 1.0) > 1e-9) else ""
            return f'<img src="img/{stem}.jpg" alt="figure {n}"{st}>', w
        return _embed_img(crop, n), _img_size(crop)  # 发布失败 → base64 兜底
    return None, 0


def render_fig_slot(n: int, page: str, workdir: str, fmap: dict,
                    figs_meta: list, out_dir: str, k: float = 1.0) -> str:
    """单图块: 居中 <figure>（无并排/混排语义的槽）。"""
    fig = next((f for f in figs_meta if f.get("idx") == n), None)
    img_html, _ = _fig_img_tag(n, page, workdir, fmap, figs_meta, out_dir, k)
    if img_html is None:
        return f'<!-- missing figure {n} for page {page} -->'
    return f'<figure class="fig">{img_html}{_cap_html(fig)}</figure>'


def render_fig_row(slots: list, page: str, workdir: str, fmap: dict,
                   figs_meta: list, out_dir: str, k: float = 1.0) -> str:
    """相邻 {{FIG:n}} 槽 → 并排图行 .figrow（原图两图并排版式, 宪法第七条）。
    每图 flex-grow 比例 = 裁剪实际像素宽, 图注随图左对齐。"""
    cells = []
    for m in slots:
        n = int(m.group(1))
        fig = next((f for f in figs_meta if f.get("idx") == n), None)
        img_html, w = _fig_img_tag(n, page, workdir, fmap, figs_meta, out_dir, k)
        if img_html is None:
            continue
        flex = f' style="flex:{max(w, 1)} 1 0%"' if w else ""
        cells.append(f'<figure class="fig"{flex}>{img_html}{_cap_html(fig)}</figure>')
    if not cells:
        return ""
    if len(cells) == 1:
        return cells[0]
    return '<div class="figrow">' + "".join(cells) + "</div>"


def render_fig_aside(n: int, aside_ps: list, page: str, workdir: str, fmap: dict,
                     figs_meta: list, out_dir: str, text_w: float = TEXT_W_SRC,
                     k: float = 1.0) -> str:
    """{{FIG:n|aside}} → 图文混排 .figaside（左图右文, 原版式）。
    图列宽占正文栏比 = 裁剪实际像素宽 / 源图正文栏宽（--text-width）;
    右侧文字列排 aside_ps 各段; 图注在整块下方。无文字段则退化为单图块。"""
    fig = next((f for f in figs_meta if f.get("idx") == n), None)
    img_html, w = _fig_img_tag(n, page, workdir, fmap, figs_meta, out_dir, k)
    if img_html is None:
        return f'<!-- missing figure {n} for page {page} -->'
    ps_html = "".join(f"<p>{inline(p)}</p>" for p in aside_ps)
    if not ps_html:
        return render_fig_slot(n, page, workdir, fmap, figs_meta, out_dir, k)
    pct = min(66.0, max(30.0, 100.0 * (w or 0.55 * text_w) / max(text_w, 1.0)))
    return (f'<figure class="figaside"><div class="aside-row">'
            f'<span class="figimg" style="flex:0 0 {pct:.1f}%">{img_html}</span>'
            f'<div class="asidetext">{ps_html}</div></div>{_cap_html(fig)}</figure>')


def _col_lines_html(lines: list, k: float, lh: float = 1.15,
                    page: str = "", workdir: str = "", fmap: dict | None = None,
                    figs_meta: list | None = None, out_dir: str = "") -> str:
    """列内行 → HTML: 每非空行一个 <p>（支持 $数学$/粗斜体），
    {{GAP:N}} 独立行 → 竖直占位（k 等比），行尾 {{PX}}/{{CTR}}/{{SX}}/{{R}}/{{IND}} 生效；
    {{FIG:n}} 独立行 → 插图槽（图文混排图行, 宪法第七条第 6 款①）。"""
    out = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        m = GAP_LINE.match(s)
        if m:
            n = int(m.group(1))
            h_px = round(n * k)
            if n >= 0:
                out.append(f'<div class="vgap" style="height:{h_px}px"></div>')
            else:
                out.append(f'<div class="vgap" style="height:0;margin-top:{h_px}px"></div>')
            continue
        m = FIG_LINE.match(s)
        if m:
            out.append(render_fig_slot(int(m.group(1)), page, workdir,
                                       fmap or {}, figs_meta or [], out_dir, k))
            continue
        text, style, classes = _px_style(s, k, lh=lh)
        if not text:
            continue
        cls = f' class="{classes}"' if classes else ""
        if "ctr" in classes and "white-space:nowrap" in style:
            style += "; display:flex; justify-content:center"
        st = f' style="{style}"' if style else ""
        out.append(f"<p{cls}{st}>" + inline(text) + "</p>")
    return "\n".join(out)


def _render_colrow(col_specs: list, k: float, lh: float = 1.15,
                   page: str = "", workdir: str = "", fmap: dict | None = None,
                   figs_meta: list | None = None, out_dir: str = "") -> str:
    """{{COLROW}}/{{COL:f}}/{{ENDCOLROW}} → .colrow 多栏文本行（宪法第七条第 6 款①）。
    f = 列宽原图像素 → flex:0 0 {f*k}px 精确落位; 空列 = 占位（对齐原页列缘）;
    列顶对齐, 列内竖直节奏由 {{GAP}} 控制; 列内支持 {{FIG:n}} 插图槽。"""
    cells = []
    for w, lines in col_specs:
        body = _col_lines_html(lines, k, lh, page, workdir, fmap, figs_meta, out_dir)
        st = f' style="flex:0 0 {round(w * k)}px"' if w else ""
        cells.append(f'<div class="col"{st}>{body}</div>')
    return '<div class="colrow">' + "".join(cells) + "</div>"


def md_to_body(md: str, page: str, workdir: str, fmap: dict,
               figs_meta: list, out_dir: str, text_w: float = TEXT_W_SRC,
               k: float = 1.0) -> tuple:
    """返回 (body_html, flow_style) —— flow_style 为 {{HOFF}}/{{VOFF}}/{{FLOWW}}/{{FACE}} 页级版式串;
    k = PAGE_W/原图宽（版式指令原图像素 → 画布像素 等比系数, 第七条第 6 款②）。"""
    out, para, in_eq = [], [], False
    flow = []  # 页级版式: HOFF/VOFF/FLOWW/FACE
    lh = 1.15  # PX 段行距（{{LH:F}} 页级覆盖; 原页行距/字号比复刻用）
    # ---- 多栏文本行状态机（{{COLROW}}/{{COL:f}}/{{ENDCOLROW}}）----
    in_colrow = False
    col_specs: list = []   # [(列宽原图像素|None, [line, ...])]
    col_w = None
    col_lines: list = []
    eq_buf = []
    lines = md.splitlines()
    STRUCT = re.compile(r"^(#{1,3}\s+|[-*]\s+|\$\$)")  # 结构行: 标题/列表/公式

    def flush_para():
        if para:
            text, style, classes = _px_style(" ".join(para), k, lh=lh)
            if text:
                cls = f' class="{classes}"' if classes else ""
                # 居中 + nowrap 的溢出内容在 Chromium 会单侧右溢（左缘 clamp）,
                # 改 flex 双侧对称溢出保持视觉居中（宪法④ 等距基准）
                if "ctr" in classes and "white-space:nowrap" in style:
                    style += "; display:flex; justify-content:center"
                st = f' style="{style}"' if style else ""
                out.append(f"<p{cls}{st}>" + inline(text) + "</p>")
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        # ---- 多栏文本行（宪法第七条第 6 款① 版式复刻）----
        if in_colrow:
            m = COL_LINE.match(stripped)
            if m:
                if col_w is not None:  # 首个 {{COL}} 只初始化, 不产生幽灵空列（多耗一个 gap）
                    col_specs.append((col_w, col_lines))
                col_w, col_lines = float(m.group(1)), []
            elif ENDCOLROW_LINE.match(stripped):
                col_specs.append((col_w, col_lines))
                out.append(_render_colrow(col_specs, k, lh, page, workdir,
                                          fmap, figs_meta, out_dir))
                in_colrow, col_specs, col_w, col_lines = False, [], None, []
            else:
                col_lines.append(line)
            i += 1
            continue
        if COLROW_LINE.match(stripped):
            flush_para()
            in_colrow, col_specs, col_w, col_lines = True, [], None, []
            i += 1
            continue
        m = BOXOPEN_LINE.match(stripped)
        if m:
            # 重点框（圆角框条目组, 原版式）: 框内行递归走同一管道, 框宽可选
            # {{BOX:N}} N = 原页框体外宽（border-box, 含框线/内衬, 宪法第七条第 6 款①）。
            # 框心必须与版心轴对称（框体凸出文本版心两侧 = 原书版式）: margin:auto
            # 在框宽 > 版心时按 CSS 规范归零 → 单侧右错位（025 教训: 圆角框右移
            # 50px, 下方居中行/公式框轴心随之失准）—— 改 left:50% + translateX(-50%),
            # 溢出/容纳两态都严格对称居中（transform 百分比按框外宽解析, 无需知版心宽）
            flush_para()
            buf, j = [], i + 1
            while j < len(lines) and not BOXCLOSE_LINE.match(lines[j].strip()):
                buf.append(lines[j])
                j += 1
            inner, _fs = md_to_body("\n".join(buf), page, workdir, fmap, figs_meta,
                                    out_dir, text_w, k)
            wst = ""
            if m.group(1):
                w = round(int(m.group(1)) * k)
                wst = (f' style="width:{w}px; box-sizing:border-box;'
                       f' position:relative; left:50%; transform:translateX(-50%)"')
            out.append(f'<div class="keybox"{wst}>\n{inner}\n</div>')
            i = j + 1
            continue
        if BOXCLOSE_LINE.match(stripped):
            flush_para()
            print("[build_html] 警告: 游离 {{ENDBOX}}（无开框）, 已忽略", file=sys.stderr)
            i += 1
            continue
        m = EQBOX_LINE.match(stripped)
        if m:
            # 公式框（矩形框）行: N = 左缩进原图像素, 框外编号 {{EQN:...}}（原版式）;
            # 行内可再带 {{PX:N}} 字号（作用于框内与编号）
            flush_para()
            content = m.group(2).strip()
            eqnum, fs = "", ""
            while True:
                me = EQN_TOKEN.search(content)
                if me:
                    eqnum = me.group(1).strip()
                    content = content[:me.start()].strip()
                    continue
                mp = PX_SUFFIX.search(content)
                if mp:
                    fs = f"font-size:{round(int(mp.group(1)) * k)}px"
                    content = PX_SUFFIX.sub("", content, count=1)
                    continue
                break
            indent = round(int(m.group(1)) * k)
            ml = f"margin-left:{indent}px;" if indent else ""
            st = ml + (f"; {fs}" if fs else "")
            num = (f'<span class="eqnum"{f" style=\"{fs}\"" if fs else ""}>'
                   f'{html.escape(eqnum, quote=False)}</span>' if eqnum else "")
            out.append(f'<p class="eqbox" style="{st}">'
                       f'<span class="eqbox-in">{inline(content)}</span>{num}</p>')
            i += 1
            continue
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            flush_para()
            content = stripped[2:-2].strip()
            out.append('<div class="eq" role="math" aria-label="%s"><span class="mth">%s</span></div>'
                       % (html.escape(math_render.linearize(content), quote=True),
                          math_render.render(content)))
            i += 1
            continue
        if stripped == "$$":
            flush_para()
            if not in_eq:
                in_eq, eq_buf = True, []
            else:
                in_eq = False
                content = " ".join(eq_buf).strip()
                out.append('<div class="eq" role="math" aria-label="%s"><span class="mth">%s</span></div>'
                           % (html.escape(math_render.linearize(content), quote=True),
                              math_render.render(content)))
            i += 1
            continue
        if in_eq:
            eq_buf.append(line.strip())
            i += 1
            continue
        m = HOFF_LINE.match(stripped)
        if m:  # 版式指令: 正文流水平平移（第七条第 6 款①, 复刻扫描件印刷区偏移）
            flush_para()
            # 不直接发 transform —— 由收尾统一合成进对称居中 transform（calc）,
            # 避免 {{HOFF}} 覆盖 translateX(-50%) 基准
            flow.append(f"__HOFF__{round(int(m.group(1)) * k)}px__")
            i += 1
            continue
        m = VOFF_LINE.match(stripped)
        if m:  # 版式指令: 正文流垂直上移（第七条第 6 款①, 复刻印刷区顶部偏移）
            flush_para()
            flow.append(f"margin-top:{-round(int(m.group(1)) * k)}px")
            i += 1
            continue
        m = FLOWW_LINE.match(stripped)
        if m:  # 版式指令: 正文流宽度（第七条第 6 款①; 位置配 {{HOFF}} 平移）
            flush_para()
            flow.append(f"width:{round(int(m.group(1)) * k)}px")
            i += 1
            continue
        m = FACE_LINE.match(stripped)
        if m:  # 版式指令: 正文字体族覆盖（sans 等）
            flush_para()
            if m.group(1).lower() == "sans":
                flow.append(f"font-family:{FACE_SANS}")
            i += 1
            continue
        m = LH_LINE.match(stripped)
        if m:  # 版式指令: PX 段行距覆盖（原页行距/字号比复刻, 第七条第 6 款①）
            flush_para()
            lh = max(1.0, float(m.group(1)))
            i += 1
            continue
        m = GAP_LINE.match(stripped)
        if m:  # 版式指令: 竖直占位（宪法第七条第 6 款①, N 原图像素按 k 等比;
            #   负值 = 上提后续内容 —— 复刻大字号标题行盒内生空隙的负占位）
            flush_para()
            n = int(m.group(1))
            h_px = round(n * k)
            if n >= 0:
                out.append(f'<div class="vgap" style="height:{h_px}px"></div>')
            else:
                out.append(f'<div class="vgap" style="height:0;margin-top:{h_px}px"></div>')
            i += 1
            continue
        m = FIG_LINE.match(stripped)
        if m:
            flush_para()
            if (m.group(2) or "").lower() == "aside":
                # 图文混排: 收集紧随其后的连续段落进右侧文字列,
                # 直到下一个插图槽/结构行（标题/列表/公式）或 EOF
                aside_ps, j = [], i + 1
                while j < len(lines):
                    s2 = lines[j].strip()
                    if not s2:
                        j += 1
                        continue
                    if FIG_LINE.match(s2) or STRUCT.match(s2):
                        break
                    buf = [s2]
                    j2 = j + 1
                    while j2 < len(lines):
                        s3 = lines[j2].strip()
                        if not s3 or FIG_LINE.match(s3) or STRUCT.match(s3):
                            break
                        buf.append(s3)
                        j2 += 1
                    aside_ps.append(" ".join(buf))
                    j = j2
                out.append(render_fig_aside(int(m.group(1)), aside_ps, page, workdir,
                                            fmap, figs_meta, out_dir, text_w, k))
                i = j
                continue
            # 相邻多行 {{FIG:n}}（无修饰符）→ 并排图行 .figrow
            slots = [m]
            j = i + 1
            while j < len(lines):
                s2 = lines[j].strip()
                if not s2:
                    break
                m2 = FIG_LINE.match(s2)
                if not m2 or (m2.group(2) or ""):
                    break
                slots.append(m2)
                j += 1
            if len(slots) > 1:
                out.append(render_fig_row(slots, page, workdir, fmap, figs_meta, out_dir, k))
                i = j
                continue
            out.append(render_fig_slot(int(m.group(1)), page, workdir, fmap,
                                       figs_meta, out_dir, k))
            i += 1
            continue
        if not stripped:
            flush_para()
            i += 1
            continue
        h = re.match(r"^(#{1,3})\s+(.*)$", line)
        if h:
            flush_para()
            lvl = len(h.group(1))
            text, style, _cls = _px_style(h.group(2), k, tag="h", lh=lh)
            # h1 默认居中: nowrap 溢出改 flex 双侧对称（同 flush_para, 宪法④）
            if lvl == 1 and "white-space:nowrap" in style:
                style += "; display:flex; justify-content:center"
            st = f' style="{style}"' if style else ""
            out.append(f"<h{lvl}{st}>{inline(text)}</h{lvl}>")
            i += 1
            continue
        if re.match(r"^[-*]\s+", line):
            flush_para()
            out.append(f"<li>{inline(re.sub(r'^[-*]\s+', '', line))}</li>")
            i += 1
            continue
        para.append(line.strip())
        i += 1
    flush_para()
    body = "\n".join(out)
    # 连续 <li> 包 ul
    body = re.sub(r"(?:<li>.*?</li>\n?)+", lambda m: "<ul>" + m.group(0) + "</ul>", body)
    return body, "; ".join(flow)


def main():
    ap = argparse.ArgumentParser(description="pack-1: text.md → 书页 HTML")
    ap.add_argument("--page", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--figures", default=None, help="figures.json（提供 caption 与兜底槽）")
    ap.add_argument("--figure-map", default=None, help='figure-map.json: {"n":{"kind":"svg|jpg","path":...}}')
    ap.add_argument("--out", default=None,
                    help="最终件路径 dest/<page>.html（img/ 发布到其同目录下）")
    ap.add_argument("--title", default="")
    ap.add_argument("--page-no", default="")
    ap.add_argument("--workdir", default=None, help="解析 crops 相对路径的基准目录（默认 text 所在目录）")
    ap.add_argument("--text-width", type=float, default=TEXT_W_SRC,
                    help="源图正文栏宽 px（aside 图列宽换算基准）")
    ap.add_argument("--src-image", default=None,
                    help="原页图路径: 定版高宽比推导 + 版式指令 k 缩放基准"
                         "（宪法第七条第 6 款②, 批量必给）")
    ap.add_argument("--page-size", default=None,
                    help="WxH 显式覆盖页面尺寸（操作员决定; 若与定版不同会更新锁并要求整项目重排）")
    ap.add_argument("--page-size-file", default=None,
                    help="项目定版锁 project/<名>/page-size.json（第七条第 6 款③: 存在则"
                         "全项目复用其尺寸; 该锁由 calibrate.py 随机样本统计产出,"
                         " batch.py 开工自动检查; 不存在时本脚本按②推导写锁仅为兑底）")
    a = ap.parse_args()

    # ---- 原图尺寸（k 缩放基准, 第七条第 6 款②） ----
    src_w = src_h = 0
    if a.src_image:
        if not os.path.exists(a.src_image):
            raise SystemExit(f"build_html: --src-image 不存在: {a.src_image}")
        src_w, src_h = _src_page_size(a.src_image)
        if not (src_w and src_h):
            raise SystemExit(f"build_html: 无法读取原图尺寸: {a.src_image}")

    # ---- 内容区域自动测算（第七条第 6 款③版心 + ④等距边距: 扫描件边距失真校正）----
    bbox = _content_bbox(a.src_image) if a.src_image else (0, 0, 0, 0)
    vext = _content_vext(a.src_image, bbox[0], bbox[1]) if bbox[1] > bbox[0] else (0, 0)
    content_w = int(bbox[1] - bbox[0] + 1) if bbox[1] > bbox[0] else 0
    content_h_src = (vext[1] - vext[0]) if vext[1] > vext[0] else 0
    k_ergo = (PAGE_W_ERGO / src_w) if src_w else 0.0
    cw_ergo = content_w * k_ergo if content_w else 0.0
    ch_ergo = content_h_src * k_ergo if content_h_src else 0.0
    page_w = page_h = 0
    if a.page_size:
        ms = re.fullmatch(r"(\d+)[xX*](\d+)", a.page_size.strip())
        if not ms:
            raise SystemExit("build_html: --page-size 格式应为 WxH, 如 820x1042")
        page_w, page_h = int(ms.group(1)), int(ms.group(2))
    lock = None
    if a.page_size_file and os.path.exists(a.page_size_file):
        try:
            lock = json.load(open(a.page_size_file, encoding="utf-8"))
            page_w, page_h = int(lock["w"]), int(lock["h"])
        except Exception:
            print(f"[build_html] 警告: 定版文件损坏, 忽略: {a.page_size_file}", file=sys.stderr)
            lock, page_w, page_h = None, 0, 0
    if not (page_w and page_h) and src_w:
        # 兑底定版（第七条第 6 款②③）: 版心优先 + 人体工程学 padding ——
        # 宽 = 820 舒适阅读宽; 高 = 版心屏显高 + 上下 padding（0.75 × 左右 padding）,
        # 禁止用原图整页宽高比/留白推导（扫描件留白失真, 宪法③）
        page_w = int(round(PAGE_W_ERGO))
        if cw_ergo:
            pad_v = int(round(PAD_V_RATIO * (PAGE_W_ERGO - cw_ergo) / 2.0))
            page_h = int(round(ch_ergo + 2 * pad_v))
        else:
            aspect = min(max(src_h / src_w, ASPECT_MIN), ASPECT_MAX)
            page_h = int(round(page_w * aspect))
        aspect_f = page_h / page_w
        if not (ASPECT_MIN <= aspect_f <= ASPECT_MAX):
            page_h = int(round(page_w * min(max(aspect_f, ASPECT_MIN), ASPECT_MAX)))
    if not (page_w and page_h):
        raise SystemExit("build_html: 必须提供 --src-image 或 --page-size/--page-size-file"
                         " —— 宪法第七条第 6 款②③: 页面尺寸人体工程学 + 项目级定版锁")
    content_w = margin = 0
    if bbox[1] > bbox[0] and src_w:
        content_w = int(bbox[1] - bbox[0] + 1)
        cw_px = content_w * page_w / src_w
        margin = int(round((page_w - cw_px) / 2.0))
        print(f"[build_html] 内容区域测算: L={bbox[0]} R={bbox[1]} (版心竖直 y[{vext[0]}:{vext[1]}]"
              f" 原像素高 {content_h_src}) → content_w={content_w}px, k 缩放后版心宽 {round(cw_px)}px,"
              f" 等距边距 {margin}px (宪法③④ 版心优先+左右严格等距)")
    # ---- 页框 padding（第七条第 6 款③: 人体工程学定版, 不取原图留白）----
    if lock and lock.get("margin_top") and lock.get("margin_bottom"):
        pad_top, pad_bot = int(lock["margin_top"]), int(lock["margin_bottom"])
    elif margin:
        pad_top = pad_bot = int(round(PAD_V_RATIO * margin))
    else:
        pad_top = pad_bot = int(round(PAD_V_RATIO * 64))
    pad_h = margin if margin else 64
    if lock and lock.get("margin"):
        pad_h = int(lock["margin"])   # 定版锁优先: 全项目 .page 左右 padding 字面一致（宪法③）
    print(f"[build_html] 页框 padding: 上 {pad_top} / 左右 {pad_h} / 下 {pad_bot}px"
          " (宪法③ 人体工程学定版, 上下=0.75×左右, 与原图留白无关)")
    is_lock_source = (os.path.basename(a.src_image) == (lock or {}).get("from")) if a.src_image else False
    if a.page_size_file and not os.path.exists(a.page_size_file):
        # 兑底定版（第七条第 6 款③④）: 正常路径 = calibrate.py 开工前置随机样本定版;
        # 此分支仅在未定版直接调 build_html 时触发（batch.py 已接入 calibrate.ensure）
        os.makedirs(os.path.dirname(a.page_size_file) or ".", exist_ok=True)
        lock_data = {"w": page_w, "h": page_h,
                     "rule": "constitution-7-6: content-box-first + ergonomic padding + equal-margin",
                     "from": os.path.basename(a.src_image) if a.src_image else "manual"}
        if content_w:
            lock_data.update({"content_w": content_w, "margin": margin,
                              "margin_top": pad_top, "margin_bottom": pad_bot})
        json.dump(lock_data, open(a.page_size_file, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"[build_html] 项目页面尺寸定版（兑底）: {page_w}x{page_h} → {a.page_size_file}"
              " (宪法第③④条: 版心+人体工程学 padding+等距边距锁存; 正常路径请先跑 calibrate.py)")
    elif a.page_size and lock and (page_w, page_h) != (int(lock["w"]), int(lock["h"])):
        # 显式 --page-size 覆盖定版（操作员决定）: 更新锁, 整项目须重排
        lock_data = {"w": page_w, "h": page_h,
                     "rule": "constitution-7-6: manual --page-size override",
                     "from": os.path.basename(a.src_image) if a.src_image else "manual"}
        if content_w:
            lock_data.update({"content_w": content_w, "margin": margin,
                              "margin_top": pad_top, "margin_bottom": pad_bot})
        json.dump(lock_data, open(a.page_size_file, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"[build_html] 定版已按 --page-size 更新: {page_w}x{page_h}"
              " (宪法第七条第 6 款③: 改定版尺寸须整项目重排)")
    elif (a.page_size_file and lock and content_w
          and ("content_w" not in lock or "margin" not in lock)):
        if is_lock_source:
            # 定版锁缺④参数（旧格式）→ 由定版来源页测算补全（幂等升级）
            lock.update({"content_w": content_w, "margin": margin})
            json.dump(lock, open(a.page_size_file, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"[build_html] 定版锁补全④参数: content_w={content_w}, margin={margin}"
              " (宪法第七条第 6 款④ 等距边距锁存)")
        else:
            print(f"[build_html] 警告: 定版锁缺 content_w/margin（④）且本页非定版来源页,"
                  " 先重排定版页补全锁参数", file=sys.stderr)
    elif lock and "margin" in lock and margin:
        drift = abs(margin - int(lock["margin"]))
        tol = max(40, int(0.35 * int(lock["margin"])))
        if drift > tol:
            print(f"[build_html] 警告: 本页等距边距 {margin}px 与定版 {lock['margin']}px 偏差 {drift}px"
                  " 超容差 —— 版心与定版差异大（书名页/特殊版式属预期）, 人工核对"
                  "（宪法第七条第 6 款④）", file=sys.stderr)
    k = round(page_w / src_w, 4) if src_w else 1.0
    if src_w and content_h_src:
        need = content_h_src * (page_w / src_w) + pad_top + pad_bot
        if need > page_h + 4:
            print(f"[build_html] 警告: 本页版心按 k={k} 等比高 {round(content_h_src * page_w / src_w)}px"
                  f" + padding {pad_top}/{pad_bot} 超出定版页高 {page_h}px, 竖直流可能溢出, 人工核对"
                  "（宪法第七条第 6 款③）", file=sys.stderr)
    scale = round(page_w / PAGE_W_BASE, 4)

    workdir = a.workdir or os.path.dirname(os.path.abspath(a.text))
    md = open(a.text, encoding="utf-8").read()
    fmap = {}
    if a.figure_map and os.path.exists(a.figure_map):
        fmap = json.load(open(a.figure_map, encoding="utf-8"))
    figs_meta = []
    if a.figures and os.path.exists(a.figures):
        figs_meta = json.load(open(a.figures, encoding="utf-8")).get("figures", [])

    out = a.out or os.path.join(workdir, f"{a.page}.html")
    out_dir = os.path.dirname(os.path.abspath(out))
    body, flow_style = md_to_body(md, a.page, workdir, fmap, figs_meta, out_dir,
                                  a.text_width, k)
    if FIG_TOKEN.search(body):
        print("[build_html] 警告: 仍有未解析的 {{FIG:n}} 槽（宪法第九条自检不通过）", file=sys.stderr)
    # ---- 等距落位（宪法④）: 正文流自动包 .flow, width=版心宽 + 对称居中;
    # {{FLOWW}} 显式给宽则用之。居中不用 margin:auto —— 流宽 > 版心内容盒时
    # auto margin 按 CSS 规范归零 → 单侧左贴靠（025 框体同源陷阱; 036 教训:
    # FLOWW:928 → 559px > 554px 内容盒, 左贴靠右溢 5px）。改 left:50% +
    # translateX(-50%), 溢出/容纳两态都严格对称; {{HOFF}} 微调合成进同一
    # transform（calc）, 不互相覆盖 ----
    if content_w:
        cw_px = round(content_w * k)
        auto = "" if "width:" in flow_style else f"width:{cw_px}px;"
        hoff = ""
        m_h = re.search(r"__HOFF__(-?[\d.]+px)__", flow_style)
        if m_h:
            hoff = m_h.group(1)
            flow_style = flow_style.replace(m_h.group(0), "").strip("; ")
        base = "transform:translateX(-50%)"
        if hoff:
            base = f"transform:translateX(calc(-50% + {hoff}))"
        flow_style = f"{auto} position:relative; left:50%; {base}" + \
                     ("; " + flow_style if flow_style else "")
    if flow_style:
        body = f'<div class="flow" style="{flow_style}">\n{body}\n</div>'

    tpl = open(TEMPLATE, encoding="utf-8").read()
    title = a.title or ""
    page_no = str(a.page_no or "")
    # 页眉/页码为模板铬件（第零条: 禁止页码页眉复刻）——原页未印刷则不渲染
    tpl = tpl.replace("  <div class=\"runhead\">{{TITLE}}</div>\n",
                      f'  <div class="runhead">{html.escape(title, quote=False)}</div>\n' if title else "")
    tpl = tpl.replace("  <div class=\"pageno\">{{PAGE_NO}}</div>\n",
                      f'  <div class="pageno">{html.escape(page_no, quote=False)}</div>\n' if page_no else "")
    page_html = (tpl
                 .replace("{{TITLE}}", html.escape(title or f"Page {a.page}", quote=False))
                 .replace("{{PAGE_NO}}", html.escape(page_no or a.page, quote=False))
                 .replace("{{PAGE_W}}", str(page_w))
                 .replace("{{PAGE_H}}", str(page_h))
                 .replace("{{PAD_T}}", str(pad_top))
                 .replace("{{PAD_B}}", str(pad_bot))
                 .replace("{{PAD_H}}", str(pad_h))
                 .replace("{{SCALE}}", f"{scale:g}")
                 .replace("{{BODY}}", body))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(page_html)
    print(f"[build_html] {a.text} → {out} (页面 {page_w}x{page_h}px, padding"
          f" {pad_top}/{pad_h}/{pad_bot}, k={k}, --u={scale:g},"
          " 宪法第七条第 6 款②③④ 版心优先+人体工程学页框+项目定版+等距边距)")


if __name__ == "__main__":
    import sys
    main()
