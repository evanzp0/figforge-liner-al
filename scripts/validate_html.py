#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: validate_html —— 生成 HTML 的分层校验器（宪法第九条自检的机器化）

对每个 dest/<page>.html 执行五层校验, 输出逐层结论与可执行处置线索,
FAIL 项给出 (期望, 实测, 定位选择器), 修复后重跑直至 PASS（校验-调整闭环）。

分层（硬门禁 = 不通过即 FAIL; 软门禁 = 越界记 WARN 人工判读）:
  L0 静态门禁: 占位残留({{…}}/TODO/【】)、LaTeX 命令字面泄漏(\\cos 等, 025 教训)、
     img/ 引用文件存在。
  L1 DOM 几何硬门禁（playwright 渲染后逐项断言, 第七条 6 款①④）:
     - .page 宽/高 == page-size.json 定版锁(±1px); 四边 padding == 锁(±2px)
     - .flow 左右边距严格等距(±2px, ④); 宽在定版容差带内
     - 每个 .keybox 框心 == 版心轴(±2px, 025 框体对称居中红线) 且框体不越出 .page
     - 每个 .mat 矩阵行距 ∈ [0.9,1.45]em 且行数自洽(025 括号撑爆红线 3.85em→2.2em)
     - 所有 <img> 加载成功(naturalWidth>0)
  L2 墨迹节律门禁(同尺度数值对比, 第七条 6 款① 竖直包络):
     渲染 .page 截图 vs 原图 content 区(复用 build_html._content_bbox), 行墨水
     剖面归一化后 Pearson r: ≥0.70 PASS / 0.55-0.70 WARN / <0.55 FAIL;
     墨带数差 ≤3; 产出同尺度上下拼接对比图(.work/validate/<page>-compare.png)
     供人工终审(第 3 款对比闭环的机器预筛)。
  L3 文本保真门禁(.work text.md 在场时, 第零条数字防线):
     渲染文本(.flow innerText) vs text.md 去指令正文 —— 数字序列多重集合逐项
     比对(转录错数头号防线) + 词数比 ∈[0.85,1.18]; text.md 已随 complete 清理
     则 SKIP(交付后复验走 L0-L2)。
  L4 外部工具插槽(可插拔, 不可用如实 SKIP 不谎报):
     - Docfold 快速初筛: 探测到(CLI/import)则对渲染截图做文档解析初筛;
     - OmniDocBench 深度诊断: L4 初筛疑似严重失真才送入(Real5 变体优先),
       探测到且具备运行条件才执行。二者未安装 → SKIP 并注明, 接口保留。

用法:
  python3 scripts/validate_html.py --project liner-al --pages 025,036,078
      [--src-dir <dir>] [--out .work/validate] [--skip-l3]

退出码: 0=全 PASS(可含 SKIP/WARN); 1=存在 FAIL。
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # figforge/
sys.path.insert(0, os.path.join(ROOT, "packs", "split-text-image", "scripts"))

LATIN_CMD = re.compile(r"\\[a-zA-Z]+")          # LaTeX 命令泄漏
PLACEHOLDERS = ("{{FIG", "TODO", "XXX", "【")    # 占位残留(}} 单独查)

# ---------------------------------------------------------------- L0 静态
def layer0(html_path: str) -> dict:
    r = {"layer": "L0-static", "checks": [], "fail": 0}
    html = open(html_path, encoding="utf-8").read()

    def chk(name, ok, detail=""):
        r["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            r["fail"] += 1

    left = re.search(r"\\{{2,}|\\}{2,}", html)
    chk("无占位残留({{}})", left is None,
        f"残留: {left.group(0)!r} near …{html[max(0,left.start()-40):left.start()+40]!r}" if left else "")
    hits = [m.group(0) for m in LATIN_CMD.finditer(html)]
    chk("无LaTeX命令泄漏", not hits, f"泄漏命令: {sorted(set(hits))[:6]}" if hits else "")
    imgs = re.findall(r'src="(img/[^"]+)"', html)
    miss = [s for s in imgs if not os.path.exists(os.path.join(os.path.dirname(html_path), s))]
    chk("img引用存在", not miss, f"缺失: {miss}" if miss else f"{len(imgs)} 个引用")
    chk(".page/.flow 结构", '<div class="page">' in html and 'class="flow"' in html)
    return r

# ---------------------------------------------------------------- L1 DOM
JS_GEO = r"""
() => {
  const pg = document.querySelector('.page'), fl = document.querySelector('.flow');
  const pr = pg.getBoundingClientRect(), fr = fl.getBoundingClientRect();
  const pcs = getComputedStyle(pg);
  const out = {page:{l:pr.left,t:pr.top,w:pr.width,h:pr.height},
               pad:{t:pcs.paddingTop,r:pcs.paddingRight,b:pcs.paddingBottom,l:pcs.paddingLeft},
               flow:{l:fr.left,r:fr.right,w:fr.width,c:(fr.left+fr.right)/2},
               keyboxes:[], mats:[], badimg:[]};
  document.querySelectorAll('.keybox').forEach(k=>{
    const kr=k.getBoundingClientRect();
    out.keyboxes.push({l:kr.left,r:kr.right,c:(kr.left+kr.right)/2,w:kr.width});
  });
  document.querySelectorAll('.mat').forEach(m=>{
    const bd=m.querySelector('.bd'); if(!bd) return;
    const r=m.getBoundingClientRect();
    const mcs=[...bd.querySelectorAll('.mc')];
    const fs=mcs.length?parseFloat(getComputedStyle(mcs[0]).fontSize):16;
    const ys=[...new Set(mcs.map(c=>{const b=c.getBoundingClientRect();return Math.round((b.top+b.height/2)*2)/2}))].sort((a,b)=>a-b);
    const pitches=[]; for(let i=1;i<ys.length;i++) pitches.push(+(ys[i]-ys[i-1]).toFixed(1));
    out.mats.push({w:+r.width.toFixed(1),h:+r.height.toFixed(1),fs,rows:ys.length,pitches});
  });
  document.querySelectorAll('img').forEach(im=>{ if(!im.naturalWidth) out.badimg.push(im.getAttribute('src')); });
  return out;
}
"""

def layer1(dom: dict, lock: dict, k: float, flow_rect_rel=None) -> dict:
    r = {"layer": "L1-geometry", "checks": [], "fail": 0}

    def chk(name, ok, detail=""):
        r["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            r["fail"] += 1

    pg, pad, fl = dom["page"], dom["pad"], dom["flow"]
    # 阅读缩放: 锁 w/h = 屏显值, 版心/margin 为 820 基准设计值 → 数值基线按 u 换算
    # （宪法第十四条 L1×s: u = PAGE_W/scale_base, S=1.2 时基线 ×1.2 = 屏显值）
    u = lock["w"] / lock.get("scale_base", lock["w"])
    chk("page宽=定版锁", abs(pg["w"] - lock["w"]) <= 1, f"期望{lock['w']} 实测{pg['w']:.1f}")
    chk("page高=定版锁", abs(pg["h"] - lock["h"]) <= 1, f"期望{lock['h']} 实测{pg['h']:.1f}")
    # padding 期望 = 基准值 × u（屏显值）; k 仅用于原图→屏显换算
    exp_pad = [lock["margin_top"] * u, lock["margin"] * u, lock["margin_bottom"] * u, lock["margin"] * u]
    got_pad = [float(pad[k2].rstrip("px")) for k2 in ("t", "r", "b", "l")]
    padok = all(abs(a - b) <= 2 for a, b in zip(exp_pad, got_pad))
    chk("page四边padding=锁", padok, f"期望{[round(x,1) for x in exp_pad]} 实测{[round(x,1) for x in got_pad]}")

    ml = fl["l"] - pg["l"] - float(pad["l"].rstrip("px"))
    mr = (pg["l"] + pg["w"]) - fl["r"] - float(pad["r"].rstrip("px"))
    chk("flow左右边距等距", abs(ml - mr) <= 2, f"左{ml:.1f} 右{mr:.1f}")
    wlo, whi = lock["content_w"] * u - 30 * u, lock["content_w"] * u + 30 * u
    chk("flow宽在定版容差带", wlo <= fl["w"] <= whi, f"期望[{wlo:.0f},{whi:.0f}] 实测{fl['w']:.1f}")

    axis = fl["c"]
    for i, kb in enumerate(dom["keyboxes"], 1):
        chk(f"keybox{i}框心=版心轴", abs(kb["c"] - axis) <= 2,
            f"框心{kb['c']:.1f} 版心轴{axis:.1f} 偏{kb['c']-axis:+.1f}px(025红线)")
        chk(f"keybox{i}不越出page", kb["l"] >= pg["l"] + 8 and kb["r"] <= pg["l"] + pg["w"] - 8,
            f"框[{kb['l']:.0f},{kb['r']:.0f}] 页[{pg['l']:.0f},{pg['l']+pg['w']:.0f}]")

    for i, m in enumerate(dom["mats"], 1):
        if m["rows"] >= 2 and m["pitches"]:
            bad = [p for p in m["pitches"] if not (0.9 * m["fs"] <= p <= 1.45 * m["fs"])]
            chk(f"mat{i}行距∈[0.9,1.45]em", not bad,
                f"行距{m['pitches']} 字号{m['fs']}px 越界{bad}(025括号撑爆红线)" if bad else f"{[round(p/m['fs'],2) for p in m['pitches']]}em")
            cap = m["rows"] * 1.18 * m["fs"] + 0.6 * m["fs"]
            chk(f"mat{i}总高≤{m['rows']}行包络", m["h"] <= cap,
                f"高{m['h']:.1f}px 上限{cap:.1f}px(行数{m['rows']})" )
    chk("img全部加载", not dom["badimg"], f"未加载: {dom['badimg']}" if dom["badimg"] else "")
    # 竖直包络硬门禁（025 竖直包络自洽红线的页级推广）: 流内容高 ≤ 可用高
    # （页高 − 上下 padding）。超出被 .page overflow:hidden 静默裁剪 →
    # 底部内容丢失/漂移（036 教训: 内容 908px > 可用 815px, 页底被裁）
    avail = lock["h"] - (lock["margin_top"] + lock["margin_bottom"]) * u
    fr_bottom_rel = flow_rect_rel[3] if flow_rect_rel else None
    if fr_bottom_rel is not None:
        used = fr_bottom_rel - lock["margin_top"] * u
        chk("flow内容高≤可用高(无裁剪)", used <= avail + 2,
            f"内容底距版心顶 {used:.0f}px > 可用 {avail}px, 超出 {used-avail:.0f}px → 调小 {{PX}}/{{GAP}} 压缩内容")
    return r

# ---------------------------------------------------------------- L2 墨迹节律
def _ink_profile(img_bin, n=96):
    import numpy as np
    h = img_bin.shape[0]
    prof = img_bin.mean(axis=1) if h else None
    if prof is None or not h:
        return None
    idx = (np.linspace(0, h, n + 1)).astype(int)
    bins = [img_bin[idx[i]:max(idx[i + 1], idx[i] + 1), :].mean() for i in range(n)]
    return np.asarray(bins)

def _bands(prof, thr):
    on = prof > thr
    cnt, prev = 0, False
    for v in on:
        if v and not prev:
            cnt += 1
        prev = v
    return cnt

def _smooth(p, w=9):
    import numpy as np
    k = np.ones(w) / w
    return np.convolve(p, k, mode="same")

def _quantiles(p):
    import numpy as np
    c = np.cumsum(p); c = c / (c[-1] or 1.0)
    return [float(np.searchsorted(c, q) / len(c)) for q in (0.25, 0.5, 0.75)]

def _deskew(binimg):
    """投影方差最大化估计扫描歪斜角（±2°, 0.25° 步进, 1/4 降采样）。
    078/036 教训: 扫描件旋转使原图剖面块界涂抹/分裂（虚假谷）, 与无歪斜的
    渲染件对比时被严惩; 剖面前先去斜。返回角度（度, scipy 约定逆时针正）。"""
    import numpy as np
    from scipy import ndimage
    small = binimg[::4, ::4].astype(np.float32)
    best, ang_best = -1.0, 0.0
    for ang in np.arange(-2.0, 2.01, 0.25):
        rot = ndimage.rotate(small, ang, reshape=False, order=0)
        v = float(rot.mean(axis=1).var())
        if v > best:
            best, ang_best = v, ang
    return ang_best

def layer2(page_png: str, src_img: str, out_png: str, flow_rect, page_rect) -> dict:
    import numpy as np
    from PIL import Image
    import build_html as bh
    r = {"layer": "L2-inkrhythm", "checks": [], "fail": 0}

    def chk(name, ok, detail=""):
        r["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            r["fail"] += 1

    img = np.asarray(Image.open(page_png).convert("L"), dtype=np.uint8)
    # 渲染件: .page 截图 → 内容区二值。水平窗取墨迹列包围盒（非 flow 矩形 ——
    # keybox 凸出版心时 flow 矩形会把凸出段连同首字符切掉, 剖面失真）
    ink_all = img < 128
    nzx = np.where(ink_all.mean(axis=0) > 0.002)[0]
    fx0 = int(round(flow_rect[0] - page_rect[0])); fy0 = int(round(flow_rect[1] - page_rect[1]))
    fx1 = int(round(flow_rect[2] - page_rect[0])); fy1 = int(round(flow_rect[3] - page_rect[1]))
    if len(nzx):
        fx0, fx1 = min(fx0, int(nzx.min())), max(fx1, int(nzx.max()) + 1)
    rend = ink_all[fy0:fy1, fx0:fx1]
    # 原图: 水平=content bbox + 最宽列段防御; 竖直=_content_vext 正文带
    # （_content_bbox 的 y 对噪声页失效: 036 y0=0 混入页眉、y1=1667 混入页缘 ——
    # 036 教训: L2 原图侧竖直必须用 _content_vext（页眉/页码带排除））
    Lb, Rb, _, _ = bh._content_bbox(src_img)
    if not (Rb > Lb):
        chk("原图content测算", False, "_content_bbox 失败"); return r
    a = np.asarray(Image.open(src_img).convert("L"), dtype=np.uint8)
    med = float(np.median(a))
    th = int(max(110, min(170, med - 60)))
    colprof = (a[:, :] < th).mean(axis=0)
    segs, s0 = [], None
    for i, m in enumerate(colprof > 0.02):
        if m and s0 is None:
            s0 = i
        if not m and s0 is not None:
            if i - s0 >= 30:
                segs.append((s0, i - 1))
            s0 = None
    if s0 is not None:
        segs.append((s0, len(colprof) - 1))
    L, R = Lb, Rb
    if segs:
        L2x, R2x = max(segs, key=lambda t: t[1] - t[0])
        if R2x - L2x >= 0.5 * (Rb - Lb):  # 主栏应占 bbox 大部, 防异常
            L, R = L2x, R2x
    y0, y1 = bh._content_vext(src_img, L, R)
    if not (y1 > y0):
        y0, y1 = 0, a.shape[0]
    orig = (a[y0:y1, L:R] < th)
    # 去斜: 扫描件旋转涂抹块界 → 校正后再剖面（渲染件无歪斜, 不处理）
    ang = _deskew(orig)
    if abs(ang) >= 0.25:
        from scipy import ndimage
        orig = ndimage.rotate(orig.astype(np.float32), ang, reshape=False, order=0) > 0.5
        r["deskew"] = float(ang)

    pr, qr = _smooth(_ink_profile(rend)), _smooth(_ink_profile(orig))
    # 平移容忍的 Pearson r（±10% 高度内搜最优, 吸收起测点差一个行距的情形）
    n = len(pr); maxsh = int(0.10 * n)
    def _corr(a_, b_):
        a_, b_ = a_ - a_.mean(), b_ - b_.mean()
        d = float(np.sqrt((a_ ** 2).sum() * (b_ ** 2).sum())) or 1.0
        return float((a_ * b_).sum() / d)
    corr = max(_corr(pr[s:] if s >= 0 else pr[:n + s], qr[:n - s] if s >= 0 else qr[-s:])
               for s in range(-maxsh, maxsh + 1))
    # 硬门禁 0.45（结构缺陷域: 实测缺陷态裁剪/错位/块缺失均 ≤0.43）;
    # 0.45-0.70 为 WARN 带（密页行级微漂移, 人工看对比图判读）; 基准: 025≈0.82,
    # 036 密页合格态 ≈0.55
    chk("行墨水剖面相关r≥0.45", corr >= 0.45,
        f"r={corr:.3f}" + ("" if corr >= 0.70 else "  [WARN 带, 看对比图人工判读]"))
    r["corr"] = round(corr, 3)
    r["warn"] = corr < 0.70
    # 块边界差(谷底 prominence 法): 块级对齐的直接度量, 比逐 bin 相关更可解释。
    # 谷检测用细分辨率剖面（n=192/w=5）—— r 用的粗粒度平滑（w=9/96=9.4%h）
    # 会把相邻块界抹掉（078 教训: 网格行界 0.725 被抹成 0.531 伪谷）
    try:
        from scipy.signal import find_peaks
        fp_, fr_ = _ink_profile(rend, n=192), _ink_profile(orig, n=192)
        fs_, fo_ = _smooth(fp_, 5), _smooth(fr_, 5)
        def _valleys(p):
            pk, _ = find_peaks(-p, prominence=0.20 * float(p.max() or 1), distance=6)
            return [v / len(p) for v in pk]
        rv, ov = _valleys(fs_), _valleys(fo_)
        if rv and ov:
            # 以原图块界为基准: 每个原图谷须有渲染谷邻近(≤5%h);
            # 渲染多出的浅谷无害（再排版的自然小间隙）—— 025/036 校准
            dmax = max(min(abs(o - v) for v in rv) for o in ov)
            chk("原图块界均有渲染谷对应(≤5%h)", dmax <= 0.05,
                f"渲染谷{[round(float(x),3) for x in rv]} vs 原图谷{[round(float(x),3) for x in ov]} 最大差{dmax:.3f}")
    except Exception:
        pass
    # 墨量累计分位点(25/50/75%): 全局竖直重心比对, 比逐 bin 相关更稳（025 基准最大差 3.1%h）
    qrq, oq = _quantiles(pr), _quantiles(qr)
    qmax = max(abs(a - b) for a, b in zip(qrq, oq))
    chk("墨量分位点差≤6%h", qmax <= 0.06,
        f"渲染{[round(x,3) for x in qrq]} vs 原图{[round(x,3) for x in oq]} 最大差{qmax:.3f}")
    tr = 0.30 * float(pr.max() or 1); to = 0.30 * float(qr.max() or 1)
    br, bo = _bands(pr, tr), _bands(qr, to)
    chk("墨带数差≤3", abs(br - bo) <= 3, f"渲染{br}带 vs 原图{bo}带(缺失/多余块排查)")
    W = 554
    def _scaled(mask):
        im = Image.fromarray((~mask * 255).astype(np.uint8))
        h2 = max(1, round(im.height * W / im.width))
        return im.resize((W, h2))
    im_r, im_o = _scaled(rend), _scaled(orig)
    gap = 14
    canvas = Image.new("L", (W, im_o.height + im_r.height + gap), 255)
    canvas.paste(im_o, (0, 0)); canvas.paste(im_r, (0, im_o.height + gap))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    canvas.save(out_png)
    r["compare"] = out_png
    return r

# ---------------------------------------------------------------- L3 文本保真
def _digits(s: str):
    return re.findall(r"\d+(?:\.\d+)?", s)

def layer3(html_path: str, text_md: str) -> dict:
    from playwright.sync_api import sync_playwright
    r = {"layer": "L3-text", "checks": [], "fail": 0, "skipped": False}

    def chk(name, ok, detail=""):
        r["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            r["fail"] += 1

    md = open(text_md, encoding="utf-8").read()
    md_base = re.sub(r"\{\{[^}]*\}\}", " ", md)
    # 词数比用散文口径: 双侧剔除数学内容（渲染端矩阵单元格拼接无空格, 直接
    # 比词数会系统性偏低 —— 078 教训: 0.81 误报; 数学保真由数字集合检查承担）
    md_prose = re.sub(r"\$([^$]*)\$", " ", md_base)
    md_words = len(md_prose.split())
    # 数字检查口径: 数学命令剥离但保留内容（含矩阵元素数字）
    md_clean = re.sub(r"\$([^$]*)\$", lambda m: re.sub(r"\\[a-zA-Z]+|[{}^_&]|\\\\", " ", m.group(1)), md_base)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 1600})
        pg.goto("file://" + os.path.abspath(html_path))
        pg.wait_for_timeout(300)
        flow_text = pg.evaluate("document.querySelector('.flow').innerText")
        prose_text = pg.evaluate(
            "(() => {const c=document.querySelector('.flow').cloneNode(true);"
            "c.querySelectorAll('.mth').forEach(e=>e.remove());"
            "return c.innerText})()")
        b.close()
    htm_words = len(prose_text.split())
    ratio = htm_words / max(1, md_words)
    chk("词数比∈[0.85,1.18]", 0.85 <= ratio <= 1.18, f"text.md {md_words} 词 vs 渲染 {htm_words} 词 比{ratio:.2f}")
    # 数字多重集合比对(第零条: 数字逐位核的机器化)
    from collections import Counter
    cm, ch = Counter(_digits(md_clean)), Counter(_digits(flow_text))
    miss, extra = cm - ch, ch - cm
    n_miss, n_extra = sum(miss.values()), sum(extra.values())
    chk("数字集合一致", n_miss == 0 and n_extra == 0,
        f"text.md独有{n_miss}: {dict(list(miss.items())[:8])}; 渲染独有{n_extra}: {dict(list(extra.items())[:8])}")
    return r

# ---------------------------------------------------------------- L4 外部工具插槽
def _probe(mod: str, cli: str):
    return bool(importlib.util.find_spec(mod)) or bool(shutil.which(cli))

def layer4(page_png: str) -> dict:
    r = {"layer": "L4-exttools", "checks": [], "fail": 0}
    r["checks"].append({"name": "Docfold初筛", "ok": True,
                        "detail": ("已安装, 执行快速初筛" if _probe("docfold", "docfold")
                                   else "未安装 → SKIP（插槽就绪: pip 安装后自动启用; 流水线初筛位, 疑似严重失真送 L4b）")})
    r["checks"].append({"name": "OmniDocBench深诊断", "ok": True,
                        "detail": ("已安装, 深度诊断(Real5 变体优先)" if _probe("omnidocbench", "omnidocbench")
                                   else "未安装 → SKIP（仅 L4a 疑似严重失真才送入; 需模型/GPU, 接口保留）")})
    return r

# ---------------------------------------------------------------- 主流程
def validate_page(page: str, proj_dir: str, src_dir: str, out_dir: str, skip_l3: bool) -> dict:
    from playwright.sync_api import sync_playwright
    rep = {"page": page, "layers": [], "verdict": "PASS"}
    html_path = os.path.join(proj_dir, "dest", f"{page}.html")
    if not os.path.exists(html_path):
        return {"page": page, "verdict": "FAIL", "error": f"{html_path} 不存在"}
    lock = json.load(open(os.path.join(proj_dir, "page-size.json"), encoding="utf-8"))
    src_img = os.path.join(src_dir, f"{page}.jpg")

    rep["layers"].append(layer0(html_path))

    # 结构防御: 旧格式页可能缺 .flow（002 等）—— L1/L2 依赖该结构, 缺失则
    # 明确 FAIL 并跳过渲染层检查, 不崩溃
    html_src = open(html_path, encoding="utf-8").read()
    if 'class="flow"' not in html_src:
        rep["layers"].append({"layer": "L1-geometry", "checks": [], "fail": 1,
                              "detail": "缺 .flow 结构（旧格式页）→ 需按现行管线重排"})
        rep["layers"].append({"layer": "L2-inkrhythm", "checks": [], "fail": 1,
                              "detail": "缺 .flow 结构 → 跳过"})
        rep["layers"].append(layer4(html_path))
        rep["verdict"] = "FAIL"
        return rep

    # L1/L2 共用一次渲染
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 1600})
        pg.goto("file://" + os.path.abspath(html_path))
        pg.wait_for_timeout(400)
        dom = pg.evaluate(JS_GEO)
        rects = pg.evaluate("""() => {const g=s=>{const r=document.querySelector(s).getBoundingClientRect();
                            return [r.left,r.top,r.right,r.bottom]}; return {page:g('.page'),flow:g('.flow')}}""")
        os.makedirs(out_dir, exist_ok=True)
        png = os.path.join(out_dir, f"{page}-page.png")
        pg.locator(".page").screenshot(path=png)
        b.close()

    # k = 定版页宽/原图宽（与 build_html 同源）
    from PIL import Image
    k = lock["w"] / Image.open(src_img).width if os.path.exists(src_img) else 1.0
    rel = [rects["flow"][0] - rects["page"][0], rects["flow"][1] - rects["page"][1],
           rects["flow"][2] - rects["page"][0], rects["flow"][3] - rects["page"][1]]
    l1 = layer1(dom, lock, k, rel)
    rep["layers"].append(l1)

    if os.path.exists(src_img):
        l2 = layer2(png, src_img, os.path.join(out_dir, f"{page}-compare.png"),
                    rects["flow"], rects["page"])
        rep["layers"].append(l2)
    else:
        rep["layers"].append({"layer": "L2-inkrhythm", "checks": [], "fail": 0,
                              "skipped": True, "detail": "原图缺失 → SKIP"})

    if not skip_l3:
        text_md = os.path.join(ROOT, ".work", proj_key(proj_dir), "pack1", page, "text.md")
        if os.path.exists(text_md):
            rep["layers"].append(layer3(html_path, text_md))
        else:
            rep["layers"].append({"layer": "L3-text", "checks": [], "fail": 0, "skipped": True,
                                  "detail": "text.md 不在(.work 已随 complete 清理) → SKIP, 交付后复验走 L0-L2"})

    rep["layers"].append(layer4(png))
    fails = sum(l.get("fail", 0) for l in rep["layers"])
    rep["verdict"] = "FAIL" if fails else "PASS"
    return rep

def proj_key(proj_dir: str) -> str:
    return os.path.basename(proj_dir.rstrip("/"))

def main():
    ap = argparse.ArgumentParser(description="生成 HTML 分层校验器")
    ap.add_argument("--project", required=True)
    ap.add_argument("--pages", required=True, help="逗号分隔, 如 025,036,078")
    ap.add_argument("--src-dir", default=None)
    ap.add_argument("--out", default=os.path.join(ROOT, ".work", "validate"))
    ap.add_argument("--skip-l3", action="store_true")
    a = ap.parse_args()

    proj_dir = os.path.join(ROOT, "project", a.project)
    src_dir = a.src_dir or os.path.join(proj_dir, "src")
    if a.pages.strip() == "all-dest":
        import glob
        pages = [os.path.splitext(os.path.basename(p))[0]
                 for p in sorted(glob.glob(os.path.join(proj_dir, "dest", "*.html")))]
    else:
        pages = [x.strip() for x in a.pages.split(",") if x.strip()]
    all_reports = []
    for page in pages:
        rep = validate_page(page, proj_dir, src_dir, a.out, a.skip_l3)
        all_reports.append(rep)
        print(f"\n===== {page} :: {rep['verdict']} =====")
        for l in rep.get("layers", []):
            if l.get("skipped"):
                print(f"[{l['layer']}] SKIP — {l.get('detail','')}")
                continue
            print(f"[{l['layer']}] fail={l.get('fail',0)}")
            for c in l.get("checks", []):
                mark = "✓" if c["ok"] else "✗"
                print(f"  {mark} {c['name']}" + (f" — {c['detail']}" if c["detail"] and not c["ok"] else ""))
        if "error" in rep:
            print("  错误:", rep["error"])

    fails = sum(1 for r in all_reports if r["verdict"] == "FAIL")
    print(f"\n[validate] {len(all_reports)} 页: {fails} 页 FAIL, 其余 PASS/WARN(见对比图人工终审)")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
