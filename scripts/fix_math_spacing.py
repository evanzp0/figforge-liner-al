#!/usr/bin/env python3
# figforge :: fix_math_spacing.py —— 数学运算符空格幂等修复与复扫（宪法第零条第 4 款）
#
# 规则: 二元运算符（· × ÷ ± + − = ≤ ≥）两侧各留一个空格; 一元负号与阶码紧排
# （矩阵负数、坐标分量、e−x 类阶码）。判据 = 看运算符**紧邻左字符**（原始流紧邻
# 字符, 标签边界 >/​< 与空白都视为"非操作数"）:
#   左邻为操作数（数字/变量/右括号/竖线等）→ 二元 → 两侧空格;
#   左邻为开括号/逗号/空白/标签边界/行首/另一运算符 → 一元 → 紧排。
#   sup/sub 内的 − 视为阶码符号, 一律紧排。
#
# 教训锚点（001/010 误伤复盘中钉死）: 矩阵单元格/独立 mth span 段首的 −1/−5,
# 紧邻左字符是标签边界 '>' 或空白 → 一元 → 保持紧排; 禁止跨标签回溯找"最近
# 可见字符"当左邻（会把隔壁单元格的操作数误判为左邻 → −1 被拆成 − 1）。
#
# 只处理元素文本（<style>/<title>/<script>/HTML 注释与一切标签属性不动）;
# 幂等: 已合规文本再跑零改动; --check 复扫不改文件（有待修处退出码 1, clean=0）。
#
# 用法:
#   python3 scripts/fix_math_spacing.py --project <名>                 # 就地修复
#   python3 scripts/fix_math_spacing.py --project <名> --pages 025,036 # 指定页
#   python3 scripts/fix_math_spacing.py --project <名> --check         # 复扫(验收锚)
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BINARY_OPS = set("·×÷±=≤≥")          # 恒二元
MINUS = "−"                            # U+2212 二元/一元由紧邻左字符判定
WS = set(" \t\n\r\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u202f\u3000")
UNARY_LEFT = set("([{,;:'\"") | BINARY_OPS | {MINUS}   # 这些左邻 → 一元/紧排
SKIP_TAGS = ("style", "script", "title")


def _is_operand(c: str) -> bool:
    """紧邻左字符是否为操作数（→ 二元）。"""
    return c is not None and (c.isalnum() or c in ")]}.%|°′″")


def tokenize(html: str):
    """→ [(kind, text)]; kind ∈ {'tag','text','skip'}; skip = 注释与 style/script/title 内文本。"""
    parts = re.split(r"(<[^>]*>|<!--.*?-->)", html, flags=re.S)
    toks, skip_until = [], None
    for t in parts:
        if not t:
            continue
        if t.startswith("<!--"):
            toks.append(("skip", t))
            continue
        if t.startswith("<"):
            m = re.match(r"</?\s*([a-zA-Z][a-zA-Z0-9-]*)", t)
            name = m.group(1).lower() if m else ""
            if skip_until:
                toks.append(("skip", t))
                if name == skip_until and t.startswith("</"):
                    skip_until = None
            else:
                toks.append(("tag", t))
                if name in SKIP_TAGS and not t.startswith("</") and not t.endswith("/>"):
                    skip_until = name
        else:
            toks.append(("skip" if skip_until else "text", t))
    return toks


def fix_html(html: str):
    """→ (new_html, n_fix)。判据只用原始流紧邻字符, 插入/删除都落在文本 token 内。"""
    toks = tokenize(html)
    # 可见字符流（仅 text token; sup/sub 阶码标记）
    chars = []            # (tok_idx, pos, ch)
    supsub = [False] * len(toks)
    depth = 0
    for ti, (kind, t) in enumerate(toks):
        if kind == "tag":
            low = t.lower()
            if re.match(r"<(sup|sub)\b", low):
                depth += 1
            elif re.match(r"</(sup|sub)\s*>", low):
                depth = max(0, depth - 1)
            supsub[ti] = depth > 0
        elif kind == "text":
            supsub[ti] = depth > 0
            for pos, ch in enumerate(t):
                chars.append((ti, pos, ch))

    def raw_prev(ti, pos):
        """紧邻左字符（原始流; 标签边界 → '>', 流首 → None）。"""
        if pos > 0:
            return toks[ti][1][pos - 1]
        if ti > 0:
            k, t = toks[ti - 1]
            if k == "text":
                return t[-1] if t else None
            return ">"                       # tag/skip 边界
        return None

    # 减号判据终版（001/010/016/036 四起误伤复盘钉死）:
    #   紧邻左字符 = 操作数 → 二元 → 两侧补空格（仅插入, 不删除）;
    #   其余（空白/标签边界/开括号/逗号/运算符/行首）→ 一元/阶码 → 零改动。
    # 两侧已有空格的减号（"w − w"、"column 2 − column 3"）永不触碰;
    # 禁止跨 token 回溯找"可见左邻"（隔壁单元格的操作数不是左邻）;
    # 禁止删除式紧排（"= − 1" 与 "a − b" 局部不可分辨, 宁可不动）。

    def raw_next(ti, pos):
        """紧邻右字符（原始流; 标签边界 → '<', 流尾 → None）。→ (char, tok_idx, pos_in_tok)"""
        t = toks[ti][1]
        if pos < len(t) - 1:
            return t[pos + 1], ti, pos + 1
        if ti + 1 < len(toks):
            k, t2 = toks[ti + 1]
            if k == "text" and t2:
                return t2[0], ti + 1, 0
            return "<", None, None           # tag/skip 边界
        return None, None, None

    fixes = []   # (tok_idx, pos, insert_str) 插入; (tok_idx, pos, "", 1) 删除
    n_fix = 0
    for ti, pos, ch in chars:
        if ch not in BINARY_OPS and ch != MINUS:
            continue
        cprev = raw_prev(ti, pos)
        cnext, _, _ = raw_next(ti, pos)
        if ch == MINUS and not _is_operand(cprev):
            continue                          # 一元负号/阶码 → 紧排, 零改动
        if _is_operand(cprev):
            fixes.append((ti, pos, " ", 0))
            n_fix += 1
        if cnext is not None and cnext not in WS and cnext not in "<>":
            fixes.append((ti, pos + 1, " ", 0))
            n_fix += 1

    if not fixes:
        return html, 0
    by_tok = {}
    for f in fixes:
        by_tok.setdefault(f[0], []).append(f[1:])
    for ti, ops in by_tok.items():
        s = toks[ti][1]
        for pos, ins, dell in sorted(ops, key=lambda x: -x[0]):
            if dell:
                s = s[:pos] + s[pos + 1:]
            else:
                s = s[:pos] + ins + s[pos:]
        toks[ti] = ("text", s)
    return "".join(t for _, t in toks), n_fix


def main():
    ap = argparse.ArgumentParser(description="数学运算符空格幂等修复与复扫（宪法第零条第 4 款）")
    ap.add_argument("--project", required=True, help="项目名或路径")
    ap.add_argument("--pages", default=None, help="逗号分隔页 id（默认 dest/ 全部 html）")
    ap.add_argument("--check", action="store_true", help="复扫: 不改文件, 有待修处退出码 1")
    a = ap.parse_args()

    proj = a.project if os.path.isdir(a.project) else \
        os.path.join(ROOT, "project", a.project)
    dest = os.path.join(proj, "dest")
    if not os.path.isdir(dest):
        raise SystemExit(f"fix_math_spacing: dest/ 不存在: {dest}")
    if a.pages:
        pages = [x.strip() for x in a.pages.split(",") if x.strip()]
        files = [os.path.join(dest, p + ".html") for p in pages]
    else:
        files = sorted(os.path.join(dest, f) for f in os.listdir(dest) if f.endswith(".html"))

    total, dirty = 0, []
    for fp in files:
        if not os.path.exists(fp):
            print(f"[fix-math] ✗ 缺文件: {fp}")
            dirty.append(fp)
            continue
        html = open(fp, encoding="utf-8").read()
        new, n = fix_html(html)
        name = os.path.basename(fp)
        if n:
            total += n
            dirty.append(fp)
            if a.check:
                print(f"[fix-math] △ {name}: 待修 {n} 处")
            else:
                open(fp, "w", encoding="utf-8").write(new)
                print(f"[fix-math] ✓ {name}: 修复 {n} 处")
        else:
            print(f"[fix-math] ✓ {name}: clean")
    if a.check:
        if dirty:
            print(f"[fix-math] 复扫结果: {len(dirty)} 页共 {total} 处待修 → 未达 clean（退出码 1）")
            sys.exit(1)
        print("[fix-math] 复扫结果: 全部 clean（幂等验收锚达成）")
    else:
        print(f"[fix-math] 完成: 共修复 {total} 处; 再跑 --check 应为 clean")


if __name__ == "__main__":
    main()
