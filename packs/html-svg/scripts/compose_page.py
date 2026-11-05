#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: pack-3 html-svg —— 单页编排: 原页图 → 书页 HTML + 内嵌 SVG（项目化）

路径全部由项目工作区约定推导（batch.py 逐页串行调用 —— 宪法第三条）;
dest 只放最终件, 中间件一律在 .work/<名>/（宪法第十一条）:
  <project>/src/<page>.*                                       原页图（自动识别扩展名）
  figforge/.work/<名>/pack1/<page>/                             pack-1 中间件
      figures.json  text.md  figure-map.json  crops/
  figforge/.work/<名>/pack2/specs/<page>-fig<i>.spec.json       pack-2 spec
  figforge/.work/<名>/pack2/svg/                                pack-2 四件套 + 对比图
  <project>/dest/img/<page>.svg                                 pack-2 发布的重绘主档（多图页 -fig<i>）
  <project>/dest/img/<page>.jpg                                 pack-1 插图裁剪最终件
  <project>/dest/<page>.html                                    最终书页 HTML（插图相对引用 img/）
  figforge/.work/<名>/pack3/<page>.manifest.json                中间件: 每图状态

单页流程（串行）:
  1. 插图框: 复用 pack-1 detect_figures.py（已有 figures.json 不再调 vision, 省配额;
     退出码 43 = 429 风暴, 原样上抛 —— 宪法第六条）
  2. 重绘:   spec 存在 → 调 pack-2 mpl_redraw.py（crop 作 --original 出对比图, 宪法第七条;
     --publish 发布主档到 dest/img/）; 缺 spec → JPG 裁剪发布 dest/img/ 占位, manifest 登记 redraw_todo
  3. 合成:   pack-1 build_html.py + figure-map（重绘 SVG / 裁剪 JPG 均相对引用 img/）→ dest/<page>.html
  4. 清单:   manifest 写 .work/<名>/pack3/, 记录每图状态; redraw_todo 为空才算整页完成（第九条）

用法:
  compose_page.py --project <名或路径> --page 0107 [--no-detect] [--skip-redraw]
                  [--title "..."] [--page-no 107]
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # figforge/
PACKS = os.path.join(ROOT, "packs")
P1 = os.path.join(PACKS, "split-text-image", "scripts")
P2 = os.path.join(PACKS, "px2svg", "scripts")
PAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


def run(cmd):
    print("[compose]", " ".join(cmd), flush=True)
    p = subprocess.run(cmd)
    if p.returncode == 43:  # 429 风暴: 原样上抛, 由 batch/runner 熔断（宪法第六条）
        sys.exit(43)
    if p.returncode != 0:
        sys.exit(p.returncode)


def find_src_image(project, page):
    for ext in PAGE_EXTS:
        f = os.path.join(project, "src", page + ext)
        if os.path.exists(f):
            return f
    raise SystemExit(f"compose_page: src 下找不到 {page}.*（{project}/src/）")


def main():
    ap = argparse.ArgumentParser(description="pack-3: 单页 HTML + SVG 编排（项目化）")
    ap.add_argument("--project", required=True, help="项目名或项目目录绝对路径")
    ap.add_argument("--page", required=True)
    ap.add_argument("--no-detect", action="store_true", help="复用已有 figures.json")
    ap.add_argument("--skip-redraw", action="store_true", help="跳过重绘（只占位排版）")
    ap.add_argument("--title", default="")
    ap.add_argument("--page-no", default="")
    a = ap.parse_args()

    proj = a.project if os.path.isabs(a.project) else os.path.join(ROOT, "project", a.project)
    if not os.path.isdir(proj):
        raise SystemExit(f"compose_page: 项目目录不存在: {proj}")
    page = a.page

    src_img = find_src_image(proj, page)
    work = os.path.join(ROOT, ".work", os.path.basename(os.path.normpath(proj)))
    p1_dir = os.path.join(work, "pack1", page)
    specs_dir = os.path.join(work, "pack2", "specs")
    svg_out = os.path.join(work, "pack2", "svg")
    manifest_dir = os.path.join(work, "pack3")
    publish_dir = os.path.join(proj, "dest", "img")
    out_html = os.path.join(proj, "dest", f"{page}.html")
    os.makedirs(p1_dir, exist_ok=True)
    os.makedirs(manifest_dir, exist_ok=True)

    figmap_path = os.path.join(p1_dir, "figure-map.json")

    # ---- 1) 插图框（pack-1; 幂等: 已有 figures.json 不再调 vision, 省配额） ----
    figures_json = os.path.join(p1_dir, "figures.json")
    if a.no_detect or os.path.exists(figures_json):
        if not a.no_detect:
            print("[compose] figures.json 已存在, 跳过重复检测（--no-detect 语义自动生效）")
    else:
        run([sys.executable, os.path.join(P1, "detect_figures.py"),
             "--page", page, "--image", src_img, "--out", p1_dir])
    if not os.path.exists(figures_json):
        raise SystemExit(f"compose_page: 缺 {figures_json}（先跑 pack-1 检测或去掉 --no-detect）")
    meta = json.load(open(figures_json, encoding="utf-8"))
    n_figs = meta.get("count", len(meta.get("figures", [])))

    # ---- 2) 逐图重绘（pack-2; 主档发布 dest/img/: 单图页 <page>.svg 多图页 <page>-fig<i>.svg） ----
    figmap = {}
    todo = []
    if os.path.exists(figmap_path):  # 保留既有映射（重跑时 svg 已生成）
        figmap = json.load(open(figmap_path, encoding="utf-8"))
    for i in range(1, n_figs + 1):
        spec = os.path.join(specs_dir, f"{page}-fig{i}.spec.json")
        publish_stem = page if n_figs == 1 else f"{page}-fig{i}"
        if a.skip_redraw:
            pass
        elif os.path.exists(spec):
            os.makedirs(svg_out, exist_ok=True)
            crop = os.path.join(p1_dir, "crops", f"fig{i}.jpg")
            cmd = [sys.executable, os.path.join(P2, "mpl_redraw.py"),
                   "--spec", spec, "--out", svg_out,
                   "--publish", publish_dir, "--publish-name", publish_stem]
            if os.path.exists(crop):
                cmd += ["--original", crop]
            run(cmd)
            sp = json.load(open(spec, encoding="utf-8"))
            spec_name = sp.get("name", f"{page}-fig{i}")
            cmp_img = os.path.join(svg_out, f"compare-{spec_name}.png")
            if not os.path.exists(cmp_img):
                cmp_img = ""
            figmap[str(i)] = {"kind": "svg",
                              "path": os.path.join(publish_dir, publish_stem + ".svg"),
                              "compare": cmp_img, "spec": spec}
        else:
            todo.append(i)
            if str(i) not in figmap:  # 已有映射则尊重之
                figmap[str(i)] = {"kind": "jpg",
                                  "path": os.path.join(p1_dir, "crops", f"fig{i}.jpg")}
    json.dump(figmap, open(figmap_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 3) 合成最终件 HTML（pack-1 build_html.py） ----
    text_md = os.path.join(p1_dir, "text.md")
    if not os.path.exists(text_md):
        raise SystemExit(f"compose_page: 缺 {text_md}（transcriber 先按 pack-1 workflow 产出）")
    run([sys.executable, os.path.join(P1, "build_html.py"),
         "--page", page, "--text", text_md,
         "--figures", figures_json, "--figure-map", figmap_path,
         "--workdir", p1_dir,
         "--out", out_html,
         "--title", a.title, "--page-no", a.page_no])

    # ---- 4) manifest（中间件 → .work/<名>/pack3/） ----
    manifest = {
        "page": page,
        "figures": [{"idx": i, **figmap.get(str(i), {})} for i in range(1, n_figs + 1)],
        "redraw_todo": todo,
        "complete": len(todo) == 0,
    }
    mpath = os.path.join(manifest_dir, f"{page}.manifest.json")
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    state = "完成" if not todo else f"完成排版, {len(todo)} 图待重绘: {todo}"
    print(f"[compose_page] {page}: {state} → {out_html} | manifest → {mpath}")


if __name__ == "__main__":
    main()
