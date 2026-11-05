#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: pack-2 px2svg —— matplotlib 像素图重绘引擎

把"量测得到的 spec JSON"渲染成与原书逐像素可比的矢量图。

用法:
  mpl_redraw.py --spec spec.json --out .work/<名>/pack2/svg \
      [--original 源图.png] [--compare-height 540] \
      [--publish project/<名>/dest/img] [--publish-name <page>]

spec JSON（坐标系 = 源图像素, y 轴向下）:
{
  "name": "directed-graph",
  "canvas": {"width": 808, "height": 542, "dpi": 100, "background": "#ffffff"},
  "ink": "#1a1a1a",
  "line_width_px": 3.0,
  "font": {"family": "Liberation Serif", "fallbacks": ["Nimbus Roman","DejaVu Serif"], "math": "stix"},
  "elements": [
    {"type": "line",     "from": [104,76], "to": [676,82]},
    {"type": "polyline", "points": [[..]], "closed": false},
    {"type": "polygon",  "points": [[..]], "fill": "#ffffff", "join": "miter"},
    {"type": "dot",      "at": [104,76], "r": 10},
    {"type": "arrow",    "from": [104,76], "to": [676,82], "style": "stealth",
                         "length": 33, "width": 31, "notch": 12, "position": 0.5},
    {"type": "arc",      "center": [400,237], "w": 200, "h": 120, "theta1": 0, "theta2": 90},
    {"type": "label",    "text": "1", "x": 88, "y": 91, "size_px": 46,
                         "weight": "bold", "align": "right", "valign": "baseline"},
    {"type": "label",    "math": "\\boldsymbol{y}_1", "x": 385, "y": 41, "size_px": 46,
                         "align": "center", "valign": "center"}
  ]
}

输出（宪法第八条; 中间件在 --out, 最终主档发布到 --publish）:
  <out>/<name>.svg         主档, svg.fonttype="path"（字形转路径, 不依赖查看端字体）
  <out>/<name>_text.svg    可编辑版, svg.fonttype="none"
  <out>/<name>.png         300dpi
  <out>/compare-<name>.png --original 给定时: 原图 vs 重绘 并排对比（宪法第七条验收凭据）
  <publish>/<publish-name>.svg   --publish 给定时: 主档副本发布到 dest/img/
                           （dest 最终件命名: 单图页 <page>.svg, 多图页 <page>-fig<i>.svg;
                             仅 jpg→svg 重绘流程才有此文件, 裁剪 JPG 由 pack-1 发布 dest/img/<stem>.jpg）

宪法约束:
  * 第七条: 本引擎只负责渲染; spec 必须来自量测（见 references/redraw-playbook.md）,
    交付前必须人工查看 compare 图;
  * 第三条: 单页单图一进程, 批量由 runner.py 串行调度。
"""
import argparse
import json
import os
import re
import shutil
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Arc
from PIL import Image

ALIGN = {"left": "left", "center": "center", "right": "right"}
VALIGN = {"baseline": "baseline", "center": "center", "top": "top", "bottom": "bottom"}


def setup_fonts(spec):
    font = spec.get("font", {})
    fam = font.get("family", "Liberation Serif")
    fallbacks = font.get("fallbacks", ["Nimbus Roman", "DejaVu Serif"])
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = [fam] + fallbacks
    plt.rcParams["mathtext.fontset"] = font.get("math", "stix")
    # 字体落位自检: matplotlib 找不到首选字体会静默替换 —— 在此显式告警
    try:
        from matplotlib import font_manager as fm
        resolved = fm.findfont(fm.FontProperties(family=fam), fallback_to_default=False)
        print(f"[mpl_redraw] font '{fam}' -> {resolved}")
    except Exception:
        print(f"[mpl_redraw] 警告: 字体 {fam!r} 未安装, 将回退到 {fallbacks}", file=sys.stderr)


def stealth_triangle(mid, direction, L, Wd, notch):
    """燕尾形箭头（后缘内凹 stealth）: 顶点 = 中点 ± 方向 ± 法向。"""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    p = np.array([-d[1], d[0]])
    tip = mid + d * (L / 2)
    back = mid - d * (L / 2)
    barb_t = back + p * (Wd / 2)
    barb_b = back - p * (Wd / 2)
    rear = back + d * notch
    return np.array([tip, barb_t, rear, barb_b])


def draw_elements(ax, spec, PT):
    ink = spec.get("ink", "#1a1a1a")
    default_lw = spec.get("line_width_px", 3.0)

    def lw_of(el):
        return el.get("width_px", default_lw) * PT

    for el in spec.get("elements", []):
        t = el.get("type")
        if t == "line":
            (x1, y1), (x2, y2) = el["from"], el["to"]
            dash = el.get("dash")
            kw = dict(color=el.get("color", ink), lw=lw_of(el), zorder=2)
            kw["solid_capstyle" if not dash else "dash_capstyle"] = el.get("cap", "round")
            if dash:
                kw["dashes"] = [d * PT for d in dash]
            ax.plot([x1, x2], [y1, y2], **kw)
        elif t == "polyline":
            pts = np.asarray(el["points"], float)
            xs, ys = pts[:, 0], pts[:, 1]
            if el.get("closed"):
                xs = np.append(xs, xs[0]); ys = np.append(ys, ys[0])
            ax.plot(xs, ys, color=el.get("color", ink), lw=lw_of(el), zorder=2)
        elif t == "polygon":
            pts = np.asarray(el["points"], float)
            ax.add_patch(Polygon(pts, closed=True,
                                 facecolor=el.get("fill", "none"),
                                 edgecolor=el.get("color", ink), lw=lw_of(el),
                                 joinstyle=el.get("join", "miter"), zorder=el.get("z", 1)))
        elif t == "dot":
            ax.add_patch(Circle(tuple(el["at"]), el.get("r", 10),
                                facecolor=el.get("color", ink),
                                edgecolor="none", lw=0, zorder=4))
        elif t == "arrow":
            A = np.asarray(el["from"], float)
            B = np.asarray(el["to"], float)
            pos = el.get("position", 0.5)
            mid = A + (B - A) * pos
            if el.get("style", "stealth") == "triangle":   # 后缘平直的简单三角
                d = B - A; d = d / np.linalg.norm(d)
                p = np.array([-d[1], d[0]])
                L, Wd = el.get("length", 30), el.get("width", 30)
                tip, back = mid + d * (L / 2), mid - d * (L / 2)
                tri = np.array([tip, back + p * (Wd / 2), back - p * (Wd / 2)])
            else:                                          # stealth: 后缘内凹
                tri = stealth_triangle(mid, B - A, el.get("length", 33),
                                       el.get("width", 31), el.get("notch", 12))
            ax.add_patch(Polygon(tri, closed=True, facecolor=el.get("color", ink),
                                 edgecolor=el.get("color", ink), lw=0.5, zorder=3))
        elif t == "arc":
            cx, cy = el["center"]
            ax.add_patch(Arc((cx, cy), el["w"], el["h"],
                             theta1=el.get("theta1", 0), theta2=el.get("theta2", 360),
                             edgecolor=el.get("color", ink), lw=lw_of(el), zorder=2))
        elif t == "label":
            x, y = el["x"], el["y"]
            size = el.get("size_px", 40) * PT
            ha = ALIGN.get(el.get("align", "center"), "center")
            va = VALIGN.get(el.get("valign", "baseline"), "baseline")
            color = el.get("color", ink)
            z = el.get("z", 5)
            if el.get("math"):
                ax.text(x, y, f"${el['math']}$", fontsize=size, ha=ha, va=va,
                        color=color, zorder=z)
            else:
                ax.text(x, y, el.get("text", ""), fontsize=size, ha=ha, va=va,
                        color=color, zorder=z,
                        fontweight=el.get("weight", "normal"),
                        fontstyle=el.get("style", "normal"),
                        family="serif")
        else:
            raise SystemExit(f"mpl_redraw: 未知元素类型 {t!r}")


def fix_svg_size(path, w, h):
    """SVG 根元素 width/height 改为像素整数（与 viewBox 等比, 禁止变形 —— 宪法第八条）。"""
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', rf'\1 width="{w}"', txt, count=1)
    txt = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', rf'\1 height="{h}"', txt, count=1)
    open(path, "w", encoding="utf-8").write(txt)


def make_compare(spec_name, original, rebuilt_png, out_path, cmp_h):
    orig = Image.open(original).convert("RGB")
    reb = Image.open(rebuilt_png).convert("RGB")
    o = orig.resize((max(1, int(orig.width * cmp_h / orig.height)), cmp_h), Image.LANCZOS)
    r = reb.resize((max(1, int(reb.width * cmp_h / reb.height)), cmp_h), Image.LANCZOS)
    gap = 12
    cmp_img = Image.new("RGB", (o.width + r.width + gap, cmp_h), "#888888")
    cmp_img.paste(o, (0, 0))
    cmp_img.paste(r, (o.width + gap, 0))
    cmp_img.save(out_path)


def main():
    ap = argparse.ArgumentParser(description="pack-2: spec JSON → SVG/PNG/对比图")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--original", default=None, help="源图（出并排对比图, 宪法第七条）")
    ap.add_argument("--compare-height", type=int, default=540)
    ap.add_argument("--publish", default=None,
                    help="主档发布目录（dest/img/; 缺省不发布, 只落 --out）")
    ap.add_argument("--publish-name", default=None,
                    help="发布文件名 stem（默认 spec.name; 单图页 <page>, 多图页 <page>-fig<i>）")
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    name = spec.get("name") or os.path.splitext(os.path.basename(a.spec))[0]
    canvas = spec.get("canvas", {})
    W, H = int(canvas.get("width", 800)), int(canvas.get("height", 600))
    DPI = float(canvas.get("dpi", 100))
    PT = 72.0 / DPI
    os.makedirs(a.out, exist_ok=True)

    setup_fonts(spec)
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)          # y 轴向下, 与源图像素坐标一致（宪法第七条）
    ax.axis("off")
    bg = canvas.get("background", "#ffffff")
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)

    draw_elements(ax, spec, PT)

    png = os.path.join(a.out, f"{name}.png")
    # 主档: 字形转路径（不依赖查看端字体 —— 宪法第八条）
    matplotlib.rcParams["svg.fonttype"] = "path"
    svg_main = os.path.join(a.out, f"{name}.svg")
    fig.savefig(svg_main, dpi=DPI, facecolor=bg)
    fix_svg_size(svg_main, W, H)
    # 可编辑版: 保留 <text>（查看端需 Liberation Serif + STIX）
    matplotlib.rcParams["svg.fonttype"] = "none"
    svg_text = os.path.join(a.out, f"{name}_text.svg")
    fig.savefig(svg_text, dpi=DPI, facecolor=bg)
    fix_svg_size(svg_text, W, H)
    # 300dpi PNG
    fig.savefig(png, dpi=300, facecolor=bg)
    plt.close(fig)

    print(f"[mpl_redraw] {svg_main}")
    print(f"[mpl_redraw] {svg_text}")
    print(f"[mpl_redraw] {png}")

    if a.original:
        cmp_path = os.path.join(a.out, f"compare-{name}.png")
        make_compare(name, a.original, png, cmp_path, a.compare_height)
        print(f"[mpl_redraw] {cmp_path}  ← 宪法第七条: 交付前必须人工查看并核对")

    if a.publish:
        os.makedirs(a.publish, exist_ok=True)
        dst = os.path.join(a.publish, f"{a.publish_name or name}.svg")
        shutil.copyfile(svg_main, dst)
        print(f"[mpl_redraw] publish → {dst}")


if __name__ == "__main__":
    main()
