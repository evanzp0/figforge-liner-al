#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: pack-1 split-text-image —— 转录文本 → 书页 HTML（最终件, 公式已渲染）

用法:
  build_html.py --page 0107 --text .work/<名>/pack1/0107/text.md \
      [--figures .../figures.json] [--figure-map .../figure-map.json] \
      [--out project/<名>/dest/0107.html] [--title "Section 3.2"] [--page-no 107]

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
TEXT_W_SRC = 840.0  # 源图正文栏宽 px（aside 图列宽换算基准; 058 实测 330..1170）


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
                 figs_meta: list, out_dir: str) -> tuple:
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
            return f'<img src="img/{href}" alt="figure {n}">', _img_size(path)
    crop = None
    if ent and ent.get("kind") != "svg" and ent.get("path") and os.path.exists(ent["path"]):
        crop = ent["path"]  # compose 场景: figure-map 直接给 crop 路径
    elif fig and os.path.exists(os.path.join(workdir, f"crops/fig{n}.jpg")):
        crop = os.path.join(workdir, f"crops/fig{n}.jpg")
    if crop:
        if _publish_crop(crop, out_dir, stem):
            return f'<img src="img/{stem}.jpg" alt="figure {n}">', _img_size(crop)
        return _embed_img(crop, n), _img_size(crop)  # 发布失败 → base64 兜底
    return None, 0


def render_fig_slot(n: int, page: str, workdir: str, fmap: dict,
                    figs_meta: list, out_dir: str) -> str:
    """单图块: 居中 <figure>（无并排/混排语义的槽）。"""
    fig = next((f for f in figs_meta if f.get("idx") == n), None)
    img_html, _ = _fig_img_tag(n, page, workdir, fmap, figs_meta, out_dir)
    if img_html is None:
        return f'<!-- missing figure {n} for page {page} -->'
    return f'<figure class="fig">{img_html}{_cap_html(fig)}</figure>'


def render_fig_row(slots: list, page: str, workdir: str, fmap: dict,
                   figs_meta: list, out_dir: str) -> str:
    """相邻 {{FIG:n}} 槽 → 并排图行 .figrow（原图两图并排版式, 宪法第七条）。
    每图 flex-grow 比例 = 裁剪实际像素宽, 图注随图左对齐。"""
    cells = []
    for m in slots:
        n = int(m.group(1))
        fig = next((f for f in figs_meta if f.get("idx") == n), None)
        img_html, w = _fig_img_tag(n, page, workdir, fmap, figs_meta, out_dir)
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
                     figs_meta: list, out_dir: str, text_w: float = TEXT_W_SRC) -> str:
    """{{FIG:n|aside}} → 图文混排 .figaside（左图右文, 原版式）。
    图列宽占正文栏比 = 裁剪实际像素宽 / 源图正文栏宽（--text-width）;
    右侧文字列排 aside_ps 各段; 图注在整块下方。无文字段则退化为单图块。"""
    fig = next((f for f in figs_meta if f.get("idx") == n), None)
    img_html, w = _fig_img_tag(n, page, workdir, fmap, figs_meta, out_dir)
    if img_html is None:
        return f'<!-- missing figure {n} for page {page} -->'
    ps_html = "".join(f"<p>{inline(p)}</p>" for p in aside_ps)
    if not ps_html:
        return render_fig_slot(n, page, workdir, fmap, figs_meta, out_dir)
    pct = min(66.0, max(30.0, 100.0 * (w or 0.55 * text_w) / max(text_w, 1.0)))
    return (f'<figure class="figaside"><div class="aside-row">'
            f'<span class="figimg" style="flex:0 0 {pct:.1f}%">{img_html}</span>'
            f'<div class="asidetext">{ps_html}</div></div>{_cap_html(fig)}</figure>')


def md_to_body(md: str, page: str, workdir: str, fmap: dict,
               figs_meta: list, out_dir: str, text_w: float = TEXT_W_SRC) -> str:
    out, para, in_eq = [], [], False
    eq_buf = []
    lines = md.splitlines()
    STRUCT = re.compile(r"^(#{1,3}\s+|[-*]\s+|\$\$)")  # 结构行: 标题/列表/公式

    def flush_para():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
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
                    k = j + 1
                    while k < len(lines):
                        s3 = lines[k].strip()
                        if not s3 or FIG_LINE.match(s3) or STRUCT.match(s3):
                            break
                        buf.append(s3)
                        k += 1
                    aside_ps.append(" ".join(buf))
                    j = k
                out.append(render_fig_aside(int(m.group(1)), aside_ps, page, workdir,
                                            fmap, figs_meta, out_dir, text_w))
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
                out.append(render_fig_row(slots, page, workdir, fmap, figs_meta, out_dir))
                i = j
                continue
            out.append(render_fig_slot(int(m.group(1)), page, workdir, fmap,
                                       figs_meta, out_dir))
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
            out.append(f"<h{lvl}>{inline(h.group(2))}</h{lvl}>")
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
    return body


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
    a = ap.parse_args()

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
    body = md_to_body(md, a.page, workdir, fmap, figs_meta, out_dir, a.text_width)
    if FIG_TOKEN.search(body):
        print("[build_html] 警告: 仍有未解析的 {{FIG:n}} 槽（宪法第九条自检不通过）", file=sys.stderr)

    tpl = open(TEMPLATE, encoding="utf-8").read()
    page_html = (tpl
                 .replace("{{TITLE}}", html.escape(a.title or f"Page {a.page}", quote=False))
                 .replace("{{PAGE_NO}}", html.escape(str(a.page_no or a.page), quote=False))
                 .replace("{{BODY}}", body))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(page_html)
    print(f"[build_html] {a.text} → {out}")


if __name__ == "__main__":
    import sys
    main()
