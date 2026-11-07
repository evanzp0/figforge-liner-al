#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: calibrate.py —— 项目布局参数定版（宪法第七条第 6 款③, 开工前置红线）

开工（转换任何原图之前）必须先定版: 检查 handoff.md 交接文件——若不存在、或
其中未写明转换后 HTML 的页面宽/高、上下左右边距等内容布局参数, 则**随机选取
x 张原图**（x 默认 5; 用户建项目时 `forge.sh new <pack> <名> --samples x` 设定,
存 project/<名>/config.json）进行试测, **版心优先**策略:

  * 逐张测算**版心（有效内容区, 除去留白）的宽 × 高**: 水平 = _content_bbox
    （顶部页眉/底部页码带排除 + 页缘噪声列清洗, 扫描件装订阴影/透印鲁棒 ——
    宪法④）; 竖直 = _content_vext（内容列带内行墨水率 + 页缘 2% 截除,
    页角阴影/歪斜鲁棒）;
  * 概率统计（抗差中位数）: 各样本 版心占宽比（content_w/img_w）与
    版心高宽比（content_h/content_w）→ 合并为**项目级统一版心**（屏显宽 × 高）;
  * 人体工程学（**不使用原图留白测算 padding**）: 页宽 = 820 舒适阅读宽;
    左右 padding = (页宽 − 版心宽)/2 **严格等距**（宪法④）;
    上下 padding = 0.75 × 左右 padding（Tschichold 版心比例 top:outer ≈ 3:4,
    视觉舒适）; 页高 = 版心屏显高 + 上/下 padding, 高/宽比夹紧 [1.05, 1.60]。

结果覆盖写入 handoff.md「定版参数」段（非日志, 附录; send 永不删除该段）+
project/<名>/page-size.json 机器锁（build_html 自动读锁复用）。此后本项目
**所有页面**转换一律使用该套参数; 已定版禁止重复测算; 改定版须整项目重排。

batch.py 开工自动调用 ensure() 执行本检查（split-text-image / html-svg 流程）。

用法:
  calibrate.py check --project <名>              # 检查是否已定版（退出码 0=已定版, 3=未定版）
  calibrate.py --project <名> [--samples 5] [--seed N]   # 未定版则随机抽样测算定版
  （calibrate.py ensure --project <名>           # 供 batch.py 调用: 已定版跳过, 未定版自动测算）
"""
import argparse
import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "packs", "split-text-image", "scripts"))

import handoff as handoff_mod                     # noqa: E402
from build_html import _content_bbox, _content_vext, _src_page_size, \
    PAGE_W_ERGO, ASPECT_MIN, ASPECT_MAX, PAD_V_RATIO   # noqa: E402

DEFAULT_SAMPLES = 5
PAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


def page_size_path(proj: str) -> str:
    return os.path.join(proj, "page-size.json")


def samples_config(proj: str) -> int:
    """样本数 x: project/<名>/config.json 的 layout_samples（forge.sh new --samples 写入）,
    缺省 5（宪法第七条第 6 款③）。"""
    try:
        v = json.load(open(os.path.join(proj, "config.json"),
                           encoding="utf-8")).get("layout_samples", DEFAULT_SAMPLES)
        return max(1, int(v))
    except Exception:
        return DEFAULT_SAMPLES


def scan_src(proj: str):
    """返回 [(page_id, image_path)], 按 id 排序（与 batch.scan_src 同口径）。"""
    import glob
    out = []
    for ext in PAGE_EXTS:
        for f in glob.glob(os.path.join(proj, "src", f"*{ext}")):
            out.append((os.path.splitext(os.path.basename(f))[0], os.path.abspath(f)))
    seen, uniq = set(), []
    for pid, p in sorted(out):
        if pid not in seen:
            seen.add(pid)
            uniq.append((pid, p))
    return uniq


def measure(path: str):
    """单样本测算（版心优先, 宪法第七条第 6 款③）: 返回 dict(page_id, img_w, img_h,
    content_ratio, content_aspect); 版心（有效内容区, 除去留白）: 水平 = _content_bbox,
    竖直 = _content_vext（页缘失真鲁棒）; 测算失败返回 None。"""
    w, h = _src_page_size(path)
    if not (w and h):
        return None
    L, R, _y0, _y1 = _content_bbox(path)
    if R <= L:
        return None
    yt, yb = _content_vext(path, L, R)
    if yb <= yt:
        return None
    cw, ch = R - L + 1, yb - yt
    return {
        "img_w": w, "img_h": h,
        "content_ratio": cw / w,        # 版心宽占原图宽比
        "content_aspect": ch / cw,      # 版心高宽比（有效内容区, 除去留白）
    }


def calibrate(proj: str, x: int, seed=None, only_pages=None) -> dict:
    """随机抽 x 张原图测**版心**（除去留白的有效内容区宽×高）→ 中位数合并为项目级
    统一版心 → 人体工程学 padding（不取原图留白）→ 定版参数。
    only_pages = 显式样本 id 列表（--pages, 复现/重算同一样本集用, 不再随机）。
    写 handoff.md「定版参数」段 + page-size.json 机器锁, 返回锁 dict。"""
    pages = scan_src(proj)
    if not pages:
        raise SystemExit(f"calibrate: src/ 下没有原图（{os.path.join(proj, 'src')}）")
    if only_pages:
        want = [str(p) for p in only_pages]
        by_id = {pid: p for pid, p in pages}
        miss = [p for p in want if p not in by_id]
        if miss:
            raise SystemExit(f"calibrate: --pages 指定的样本不存在: {','.join(miss)}")
        picks = [(pid, by_id[pid]) for pid in want]
        x = len(picks)
    else:
        if len(pages) < x:
            print(f"[calibrate] 警告: 原图 {len(pages)} 张少于样本数 x={x}, 按全部原图测算")
            x = len(pages)
        if seed is not None:
            random.seed(seed)
        picks = random.sample(pages, x)
    ms = []
    for pid, p in picks:
        m = measure(p)
        if m:
            m["page_id"] = pid
            ms.append(m)
        else:
            print(f"[calibrate] 警告: 样本 {pid} 版心测算失败, 跳过")
    if len(ms) < 2:
        raise SystemExit("calibrate: 有效样本不足 2 张, 无法统计定版（检查原图可读性）")

    ids = [m["page_id"] for m in ms]
    ratio_med = statistics.median(m["content_ratio"] for m in ms)
    ca_med = statistics.median(m["content_aspect"] for m in ms)

    # ---- 版心优先（宪法③）: 样本中位数 → 项目级统一版心（屏显） ----
    page_w = int(round(PAGE_W_ERGO))                     # 宽 = 820 舒适阅读宽
    content_w = int(round(page_w * ratio_med))
    content_h = int(round(content_w * ca_med))
    # ---- 人体工程学 padding（宪法③, 不取原图留白） ----
    margin = int(round((page_w - content_w) / 2.0))       # 左右严格等距（宪法④）
    pad_v = int(round(PAD_V_RATIO * margin))              # 上下 = 0.75 × 左右
    page_h = int(round(content_h + 2 * pad_v))            # 高 = 版心高 + 上/下 padding
    aspect_f = page_h / page_w
    if not (ASPECT_MIN <= aspect_f <= ASPECT_MAX):
        page_h = int(round(page_w * min(max(aspect_f, ASPECT_MIN), ASPECT_MAX)))

    lock = {
        "w": page_w, "h": page_h,
        "rule": "constitution-7-6-③: content-box-first (版心优先) + ergonomic padding (不取原图留白) + equal-margin",
        "from": f"calibrate x={x}: {','.join(ids)}",
        "content_w": content_w, "content_h": content_h,
        "margin": margin, "margin_top": pad_v, "margin_bottom": pad_v,
        "stats": {
            "samples": ids,
            "content_ratio_median": round(ratio_med, 4),
            "content_aspect_median": round(ca_med, 4),
            "content_aspect_min": round(min(m["content_aspect"] for m in ms), 4),
            "content_aspect_max": round(max(m["content_aspect"] for m in ms), 4),
        },
    }
    json.dump(lock, open(page_size_path(proj), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    lines = [
        f"- page_w x page_h: **{page_w}x{page_h}px**（宽=820 人体工程学阅读宽; 高=版心高 {content_h} + 上下 padding {pad_v}×2, 高/宽比 {aspect_f:.3f} 夹紧区间 [{ASPECT_MIN},{ASPECT_MAX}]）",
        f"- 版心（有效内容区, 除去留白）: **{content_w} x {content_h}px**（占宽比中位数 {ratio_med:.3f} × 版心高宽比中位数 {ca_med:.3f}, 随机样本合并）",
        f"- 页面 padding: 左右 **{margin}px 严格等距**（(page_w−版心宽)/2, 宪法④）; 上下 **{pad_v}px**（= 0.75 × 左右, Tschichold top:outer ≈ 3:4 人体工程学, **不取原图留白**）",
        f"- 竖直节奏: 版心内由转录 {{{{GAP}}}} 表达; 上边距为定版页框参数, 禁止 {{{{VOFF}}}} 复刻扫描件页顶留白",
        f"- 依据: 随机样本 x={x} 页 [{', '.join(ids)}] 版心测算, 中位数统计（概率统计+人体工程学, 第七条第 6 款③）",
        "- 机器锁: page-size.json（build_html 自动读锁复用）; 全项目所有页面一律遵守本套参数, 改定版须整项目重排",
    ]
    ns = argparse.Namespace(project=proj, line=lines)
    handoff_mod.params_set(ns)
    print(f"[calibrate] 定版完成: page {page_w}x{page_h}, 版心 {content_w}x{content_h}, "
          f"padding 左右 {margin} / 上下 {pad_v}（样本 x={x}: {','.join(ids)}）")
    print(f"[calibrate] 写入: {page_size_path(proj)} + handoff.md 定版参数段")
    return lock


def is_locked(proj: str) -> bool:
    """已定版 = handoff.md 有定版参数段 且 page-size.json 机器锁存在且可读。"""
    if not handoff_mod.params_lines(proj):
        return False
    try:
        lock = json.load(open(page_size_path(proj), encoding="utf-8"))
        return bool(lock.get("w") and lock.get("h"))
    except Exception:
        return False


def ensure(proj: str):
    """开工前置检查（batch.py 自动调用）: 已定版→打印参数直接放行;
    未定版→按 config.json 的 x（默认 5）随机抽样测算定版。"""
    if is_locked(proj):
        pl = handoff_mod.params_lines(proj)
        print("[calibrate] 已定版（宪法第七条第 6 款③）, 复用项目统一参数:")
        for l in pl:
            print("  " + l)
        return
    print("[calibrate] 未定版（handoff.md 无定版参数段或 page-size.json 缺失）→ "
          "开工前置定版（第七条第 6 款③）")
    calibrate(proj, samples_config(proj))


def rescale(proj: str, scale: float) -> dict:
    """阅读缩放定版（宪法第七条第 6 款③）—— 改定版页宽/高的唯一合法通道。
    锁的页框基准值（版心/四边 padding 的 820 基准设计值）不变, w/h = 基准 × S,
    scale/scale_base 入锁, handoff「定版参数」段覆盖写。存量现行格式页随后用
    scripts/rescale_html.py 真参数重定标 + validate_html 复验;
    禁止 CSS zoom/transform 冒充阅读缩放。"""
    psp = page_size_path(proj)
    try:
        lock = json.load(open(psp, encoding="utf-8"))
    except Exception:
        raise SystemExit("calibrate rescale: page-size.json 缺失/不可读 —— 先完成 ⓪ 定版")
    if not handoff_mod.params_lines(proj):
        raise SystemExit("calibrate rescale: handoff.md 无定版参数段 —— 先完成 ⓪ 定版")
    if lock.get("scale_base") and lock.get("scale"):
        base_w = int(lock["scale_base"])
        base_h = int(round(lock["h"] / lock["scale"]))
    else:
        base_w, base_h = int(lock["w"]), int(lock["h"])
    new_w = int(round(base_w * scale))
    new_h = int(round(base_h * scale))
    aspect_f = new_h / new_w
    if not (ASPECT_MIN <= aspect_f <= ASPECT_MAX):
        new_h = int(round(new_w * min(max(aspect_f, ASPECT_MIN), ASPECT_MAX)))
    lock["w"], lock["h"] = new_w, new_h
    lock["scale"], lock["scale_base"] = scale, base_w
    lock["rule"] = ("constitution-7-6-③: content-box-first (版心优先) + ergonomic padding "
                    "(不取原图留白) + equal-margin; 阅读缩放定版 S={:g}: 本锁 w/h=屏显值"
                    "({} 基准×S), content_w/content_h/margin/margin_top/margin_bottom 为 "
                    "{} 基准设计值(渲染乘 --u = w/scale_base), 改定版唯一合法通道 "
                    "calibrate rescale".format(scale, base_w, base_w))
    json.dump(lock, open(psp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cw, ch = lock.get("content_w"), lock.get("content_h")
    mg, mt = lock.get("margin"), lock.get("margin_top")
    lines = [
        f"- page_w x page_h: **{new_w}x{new_h}px**（= {base_w} 基准 × 阅读缩放 S={scale:g}; "
        f"高/宽比 {aspect_f:.3f} 夹紧区间 [{ASPECT_MIN},{ASPECT_MAX}]）; --u = {scale:g}, "
        "模板铬件与页框随 --u 等比",
        f"- 版心（有效内容区, 除去留白）: {base_w} 基准 **{cw} x {ch}px** → 屏显 "
        f"{cw*scale:g} x {ch*scale:g}px（占宽比中位数 × 版心高宽比中位数, 随机样本合并）",
        f"- 页面 padding: {base_w} 基准 左右 **{mg} 严格等距** → 屏显 {mg*scale:g}px（宪法④）; "
        f"上下基准 **{mt}** → 屏显 {mt*scale:g}px（= 0.75 × 左右, Tschichold top:outer ≈ 3:4, "
        "**不取原图留白**）",
        "- 竖直节奏: 版心内由转录 {{GAP}} 表达; 上边距为定版页框参数, 禁止 {{VOFF}} 复刻扫描件页顶留白",
        f"- 阅读缩放定版: `calibrate.py rescale --scale {scale:g}`（页框锁值为 {base_w} 基准设计值, "
        "渲染乘 --u）; 存量现行格式页真参数重定标 `scripts/rescale_html.py`（真字号/真边距, "
        "禁止 CSS zoom/transform 渲染层缩放）+ validate_html 复验; 改 S 须全项目重定标/重排",
        "- 机器锁: page-size.json（build_html 自动读锁复用）; 全项目所有页面一律遵守本套参数, 改定版须整项目重排",
    ]
    ns = argparse.Namespace(project=proj, line=lines)
    handoff_mod.params_set(ns)
    print(f"[calibrate] 阅读缩放定版完成: page {new_w}x{new_h}（{base_w} 基准 × S={scale:g}）, "
          f"基准页框值不变（版心 {cw}x{ch}, margin 左右 {mg} / 上下 {mt}）")
    print(f"[calibrate] 写入: {psp} + handoff.md 定版参数段（覆盖写）")
    print(f"[calibrate] 下一步: python3 scripts/rescale_html.py --project <名> --scale {scale:g} "
          "存量页重定标 + validate_html 复验")
    return lock


def main():
    ap = argparse.ArgumentParser(
        description="项目布局参数定版（随机 x 样本统计 + 人体工程学, 宪法第七条第 6 款③）")
    sub = ap.add_subparsers(dest="verb")
    p_check = sub.add_parser("check", help="检查是否已定版（退出码 0/3）")
    p_check.add_argument("--project", required=True)
    p_ens = sub.add_parser("ensure", help="开工前置检查: 未定版则自动测算（batch.py 用）")
    p_ens.add_argument("--project", required=True)
    p_res = sub.add_parser("rescale", help="阅读缩放定版: 改定版页宽/高唯一合法通道 "
                                          "（锁=820 基准设计值 × S, 第七条第 6 款③）")
    p_res.add_argument("--project", required=True)
    p_res.add_argument("--scale", type=float, required=True, help="阅读缩放倍率 S（如 1.2 = 120%）")

    ap.add_argument("--project", help="项目名或路径")
    ap.add_argument("--samples", type=int, default=None,
                    help="随机样本数 x（默认取 config.json 的 layout_samples, 再默认 5）")
    ap.add_argument("--pages", default=None,
                    help="显式样本 id 列表（逗号分隔, 如 113,297,309,159,191）—— "
                         "复现/重算同一样本集, 不再随机")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（复现用, 默认真随机）")
    a = ap.parse_args()

    if a.verb in ("check", "ensure"):
        proj = a.project if os.path.isdir(a.project) else \
            os.path.join(os.path.dirname(HERE), "project", a.project)
        if not os.path.isdir(proj):
            raise SystemExit(f"calibrate: 项目目录不存在: {proj}")
        if a.verb == "check":
            if is_locked(proj):
                print("[calibrate] 已定版:")
                for l in handoff_mod.params_lines(proj):
                    print("  " + l)
            else:
                print("[calibrate] 未定版 —— 先运行: python3 scripts/calibrate.py "
                      f"--project {os.path.basename(proj)}")
                raise SystemExit(3)
        else:
            ensure(proj)
        return

    if a.verb == "rescale":
        proj = a.project if os.path.isdir(a.project) else \
            os.path.join(os.path.dirname(HERE), "project", a.project)
        if not os.path.isdir(proj):
            raise SystemExit(f"calibrate: 项目目录不存在: {proj}")
        rescale(proj, a.scale)
        return

    if not a.project:
        ap.error("必须给 --project（或使用 check/ensure 子命令）")
    proj = a.project if os.path.isdir(a.project) else \
        os.path.join(os.path.dirname(HERE), "project", a.project)
    if not os.path.isdir(proj):
        raise SystemExit(f"calibrate: 项目目录不存在: {proj}")
    x = a.samples if a.samples else samples_config(proj)
    only = [s.strip() for s in a.pages.split(",") if s.strip()] if a.pages else None
    calibrate(proj, x, a.seed, only_pages=only)


if __name__ == "__main__":
    main()
