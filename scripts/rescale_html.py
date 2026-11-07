#!/usr/bin/env python3
# figforge :: rescale_html.py —— 存量现行格式页真参数重定标（宪法第七条第 6 款③）
#
# 阅读缩放 S 变更后, 存量 dest 页按新锁做**真参数**重定标（真字号/真边距/真间距）,
# 与按新锁重建数值等价; 禁止 CSS zoom/transform 渲染层缩放冒充（假真参数）。
# 幂等锚点: 页内 --u 已等于目标 u（= 锁 w/scale_base）→ clean/skip。
#
# 缩放范围（与 build_html 按 --u 渲染的分工一致）:
#   - <style> 块 .page 规则: width/height → 锁屏显值; --u → u_target
#     （padding 等 calc(...*var(--u)) 为基准设计值, 随 --u 自动缩放, 不改字面）
#   - 全部内联 style="..." 中的 <num>px → ×f（f = u_target/u_old; 字号/间距/图宽/
#     vgap 高等真值; %、em、unitless、calc 不动）
#   - <style> 块其余规则不动（模板铬件, 全部 calc(*var(--u)) 或百分比）
#
# 用法:
#   python3 scripts/rescale_html.py --project <名> --scale 1.2           # 就地重定标
#   python3 scripts/rescale_html.py --project <名> --scale 1.2 --check   # 复核
# 完成后必须 validate_html 复验（宪法第七条第 6 款③ / handoff 定版参数段）。
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _fmt(x: float) -> str:
    """数值格式化: 最多 2 位小数, 去尾零（12×1.2=14.4, 55×1.2=66, 1×1.2=1.2）。"""
    v = round(x + 1e-9, 2)
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _scale_style_block(style_src: str, lock: dict, u_old: float, u_new: float):
    """<style> 块内只改 .page 规则的 width/height/--u; 返回 (new, n)。"""
    n = 0

    def page_rule(m):
        nonlocal n
        rule = m.group(0)
        rule2, k = re.subn(r"(width:\s*)[\d.]+px", lambda mm: mm.group(1) + f"{lock['w']}px", rule)
        rule2, k2 = re.subn(r"(height:\s*)[\d.]+px", lambda mm: mm.group(1) + f"{lock['h']}px", rule2)
        n += k + k2
        return rule2

    s = re.sub(r"\.page\s*\{[^}]*\}", page_rule, style_src, count=1)
    s, k = re.subn(r"(--u:\s*)[\d.]+", lambda mm: mm.group(1) + f"{u_new:g}", s, count=1)
    return s, n + k


def rescale_html(html: str, lock: dict, u_old: float, u_new: float):
    """→ (new_html, n_changes)。"""
    f = u_new / u_old if u_old else u_new
    n = 0
    m = re.search(r"(<style[^>]*>)(.*?)(</style>)", html, flags=re.S)
    head, style_src, tail = m.group(1), m.group(2), m.group(3)
    style_new, k = _scale_style_block(style_src, lock, u_old, u_new)
    n += k
    html = html[:m.start()] + head + style_new + tail + html[m.end():]

    def inline(mm):
        nonlocal n
        attrs = mm.group(1)

        def px(mm2):
            nonlocal n
            n += 1
            return _fmt(float(mm2.group(1)) * f) + "px"

        attrs2 = re.sub(r"(\d+(?:\.\d+)?)px", px, attrs)
        attrs2, k2 = re.subn(r"(--u:\s*)[\d.]+", lambda mm3: mm3.group(1) + f"{u_new:g}", attrs2)
        n += k2
        return 'style="' + attrs2 + '"'

    # 只处理内联 style 属性（<style> 块已在上方还原, 此处正则不会匹配块内文本,
    # 因为块内容形如 "  .page { ... }" 无 style=" 前缀）
    html = re.sub(r'style="([^"]*)"', inline, html)
    return html, n


def main():
    ap = argparse.ArgumentParser(description="存量现行格式页真参数重定标（宪法第七条第 6 款③）")
    ap.add_argument("--project", required=True, help="项目名或路径")
    ap.add_argument("--scale", type=float, required=True, help="目标阅读缩放 S（如 1.2 = 120%）")
    ap.add_argument("--pages", default=None, help="逗号分隔页 id（默认 dest/ 全部 html）")
    ap.add_argument("--check", action="store_true", help="复核: 不改文件, 有待重定标页退出码 1")
    a = ap.parse_args()

    proj = a.project if os.path.isdir(a.project) else \
        os.path.join(ROOT, "project", a.project)
    lock_path = os.path.join(proj, "page-size.json")
    try:
        lock = json.load(open(lock_path, encoding="utf-8"))
    except Exception:
        raise SystemExit("rescale_html: page-size.json 缺失/不可读 —— 先 calibrate.py rescale 定版")
    u_target = lock["w"] / lock.get("scale_base", lock["w"])
    if abs(u_target - a.scale) > 1e-6:
        print(f"[rescale] 警告: 锁 u={u_target:g} 与 --scale {a.scale:g} 不一致, 以锁为准")

    dest = os.path.join(proj, "dest")
    if not os.path.isdir(dest):
        raise SystemExit(f"rescale_html: dest/ 不存在: {dest}")
    if a.pages:
        pages = [x.strip() for x in a.pages.split(",") if x.strip()]
        files = [os.path.join(dest, p + ".html") for p in pages]
    else:
        files = sorted(os.path.join(dest, f) for f in os.listdir(dest) if f.endswith(".html"))

    total, dirty = 0, []
    for fp in files:
        if not os.path.exists(fp):
            print(f"[rescale] ✗ 缺文件: {fp}")
            dirty.append(fp)
            continue
        html = open(fp, encoding="utf-8").read()
        name = os.path.basename(fp)
        mu = re.search(r"--u:\s*([\d.]+)", html)
        u_old = float(mu.group(1)) if mu else None
        # 现行格式判定（三条同时满足才可重定标）: ①有 --u 定义; ②.page 宽 ∈
        # {基准宽, 锁屏显宽}; ③.page 高 ∈ {基准高, 锁屏显高}。旧格式页（定版锁
        # 前构建: 995 画布/无 --u/字面 padding, 001-016）不在重定标范围 —— 随
        # 重转录自动继承新定版（handoff 定版参数段）。
        mr = re.search(r"\.page\s*\{([^}]*)\}", html, flags=re.S)
        rule = mr.group(1) if mr else ""
        mw = re.search(r"width:\s*([\d.]+)px", rule)
        mh = re.search(r"height:\s*([\d.]+)px", rule)
        page_w = float(mw.group(1)) if mw else None
        page_h = float(mh.group(1)) if mh else None
        base_w = lock.get("scale_base", lock["w"])
        base_h = int(round(lock["h"] / lock["scale"])) if lock.get("scale") else lock["h"]
        ok_w = page_w is not None and min(abs(page_w - base_w), abs(page_w - lock["w"])) <= 1
        ok_h = page_h is not None and min(abs(page_h - base_h), abs(page_h - lock["h"])) <= 1
        if u_old is None or not (ok_w and ok_h):
            why = [] 
            if u_old is None:
                why.append("无 --u 定义")
            if not ok_w:
                why.append(f"画布宽 {page_w if page_w is not None else '?'}")
            if not ok_h:
                why.append(f"画布高 {page_h if page_h is not None else '?'}")
            print(f"[rescale] ⊘ {name}: 旧格式页（{'/'.join(why)} ≠ 锁系 "
                  f"{base_w:g}x{base_h:g}/{lock['w']:g}x{lock['h']:g}）→ 不在重定标范围, "
                  "随重转录继承新定版")
            continue
        if abs(u_old - u_target) <= 1e-6:
            print(f"[rescale] ✓ {name}: 已是目标 u={u_target:g} → clean")
            continue
        new, n = rescale_html(html, lock, u_old or 1.0, u_target)
        total += n
        dirty.append(fp)
        if a.check:
            print(f"[rescale] △ {name}: 待重定标 {n} 处（u {u_old or 1.0:g} → {u_target:g}）")
        else:
            open(fp, "w", encoding="utf-8").write(new)
            print(f"[rescale] ✓ {name}: 重定标 {n} 处（u {u_old or 1.0:g} → {u_target:g}）")
    if a.check:
        if dirty:
            print(f"[rescale] 复核结果: {len(dirty)} 页待重定标（退出码 1）")
            raise SystemExit(1)
        print("[rescale] 复核结果: 全部 clean")
    else:
        print(f"[rescale] 完成: 共 {total} 处; 随后必须 validate_html 复验"
              f"（python3 scripts/validate_html.py --project <名> --pages ...）")


if __name__ == "__main__":
    main()
