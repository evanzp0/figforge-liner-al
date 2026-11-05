#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: batch.py —— 目录驱动批量入口（宪法第二/三/六条 + 交接协议）

指定项目即可批量处理 src/ 下全部原图，而不是逐张指定:
  python3 scripts/batch.py --project mybook --pack split-text-image
  python3 scripts/batch.py --project mybook --pack px2svg
  python3 scripts/batch.py --project mybook --pack html-svg

产物契约（dest 只放最终件; 中间件一律进 .work/<名>/ —— 宪法第十一条）:
  project/<项目名>/src/                          原图（页 id = 文件名去扩展名）
  project/<项目名>/dest/
    <page>.html                                  pack-1/3 最终件: 书页 HTML（公式已渲染,
                                                 插图相对引用 img/, 离线可开）
    img/<page>.jpg                               pack-1 最终件: 插图裁剪（多图页 <page>-fig<i>.jpg）
    img/<page>.svg                               pack-2 最终件: 重绘 SVG 主档
                                                 （仅 jpg→svg 重绘流程发布; 多图页 <page>-fig<i>.svg）
  figforge/.work/<名>/                           全部中间产物（随批归档, complete 清理）
    pack1/<page>/text.md | figures.json | crops/ | figure-map.json
    pack2/specs/<page>-fig<i>.spec.json
    pack2/svg/<page>-fig<i>.{svg,_text.svg,png,-compare.png}
    pack3/<page>.manifest.json
  project/<项目名>/handoff.md                    角色交接板（收尾自动更新 SEND, 第十三条）
  project/<项目名>/plan.md                       首跑自动生成（宪法第二条）
  project/<项目名>/run-state-<stage>.json        执行级断点（自动维护）

阶段（--stage, 括号为默认值）:
  split-text-image: (detect) 批量插图检测裁剪 | html 对已转录页批量排版（dest/<page>.html）
  px2svg:           (redraw) 批量渲染 specs/ 全部 spec → 四件套并发布主档到 dest/img/
  html-svg:         (compose) 逐页编排: 内嵌已发布 SVG 重排 dest/<page>.html + manifest

宪法约束: 串行单进程 + 页间隔 + --maxseconds 优雅停（第三条）;
          自动接力（宪法第一条②）: 每段优雅停后自动备份 project/（排除各项目
          src/, 第一条①）并继续下一批, 无需人工接力; 直到全部完成 /
          429 熔断（退出码 43 → 停批转 probe-429.sh, 第六条）或无进展止损
          （失败项重试一轮仍无新完成即停）; plan 自动核销（第二条）。
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from runner import run_serial  # noqa: E402
import plan as plan_mod        # noqa: E402

ROOT = os.path.dirname(HERE)
PAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
DEFAULT_STAGE = {"split-text-image": "detect", "px2svg": "redraw", "html-svg": "compose"}
VALID_STAGE = {
    "split-text-image": ["detect", "html"],
    "px2svg": ["redraw"],
    "html-svg": ["compose"],
}


def project_dir(project: str) -> str:
    p = project if os.path.isabs(project) else os.path.join(ROOT, "project", project)
    if not os.path.isdir(p):
        raise SystemExit(f"batch: 项目目录不存在: {p}（先 bash scripts/forge.sh new <pack> {project}）")
    return p


def scan_src(proj: str):
    """返回 [(page_id, image_path)], 按 id 排序。"""
    out = []
    for ext in PAGE_EXTS:
        for f in glob.glob(os.path.join(proj, "src", f"*{ext}")):
            pid = os.path.splitext(os.path.basename(f))[0]
            out.append((pid, os.path.abspath(f)))
    seen, uniq = set(), []
    for pid, p in sorted(out):
        if pid not in seen:
            seen.add(pid)
            uniq.append((pid, p))
    return uniq


def ensure_plan(proj: str, title: str, ids):
    """plan.md 不存在则生成; 存在则把新 id 追加（宪法第二条）。"""
    plan_path = os.path.join(proj, "plan.md")
    if not os.path.exists(plan_path):
        argv = ["init", "--title", title, "--file", plan_path, "--ids"] + list(ids)
        plan_mod.main_with(argv)
    else:
        existing = {it["id"] for it in plan_mod.parse(
            open(plan_path, encoding="utf-8").read().splitlines())}
        new = [i for i in ids if i not in existing]
        if new:
            plan_mod.main_with(["add", "--file", plan_path] + new)


def check_off_plan(proj: str, done_ids, note=None):
    plan_path = os.path.join(proj, "plan.md")
    if os.path.exists(plan_path) and done_ids:
        argv = ["done", "--file", plan_path] + list(done_ids)
        if note:
            argv += ["--note", note]
        try:
            plan_mod.main_with(argv)
        except SystemExit:
            pass  # plan 里无对应项时忽略


def unit_cmd(py, script, *args):
    return [py, os.path.join(ROOT, script), *args]


def work_dir(proj: str) -> str:
    """宪法第十一条: 项目中间产物区 = figforge/.work/<项目名>/。"""
    return os.path.join(ROOT, ".work", os.path.basename(os.path.normpath(proj)))


def build_units(a, proj, py):
    """按 pack/stage 组装 [(unit_id, cmd_list)]; 返回 (units, info)"""
    pack, stage = a.pack, a.stage
    pages = scan_src(proj)
    page_ids = {p for p, _ in pages}
    if a.pages:
        keep = {s.strip() for s in a.pages.split(",") if s.strip()}
        pages = [(p, f) for p, f in pages if p in keep]
    dest = os.path.join(proj, "dest")
    work = work_dir(proj)
    p1 = os.path.join(ROOT, "packs", "split-text-image", "scripts")
    p2 = os.path.join(ROOT, "packs", "px2svg", "scripts")
    p3 = os.path.join(ROOT, "packs", "html-svg", "scripts")

    def work1(pid: str) -> str:
        return os.path.join(work, "pack1", pid)

    def svg_publish_name(pid: str) -> str:
        """单图页 <page>.svg, 多图页 <page>-fig<i>.svg（dest/img 最终件命名）。"""
        fj = os.path.join(work1(pid), "figures.json")
        try:
            n = int(json.load(open(fj, encoding="utf-8")).get("count", 0) or 0)
        except Exception:
            n = 0
        return "multi" if n > 1 else "single"

    if pack == "split-text-image" and stage == "detect":
        if not pages:
            raise SystemExit("batch: src/ 下没有原图（支持 " + " ".join(PAGE_EXTS) + "）")
        units = [(pid, unit_cmd(py, os.path.join(p1, "detect_figures.py"),
                                "--page", pid, "--image", img,
                                "--out", work1(pid)))
                 for pid, img in pages]
        return units, {"to": "transcriber",
                       "send": f"src 全部 {len(units)} 页插图检测裁剪完成",
                       "state": ".work/<名>/pack1/<page>/{figures.json, crops/} 就绪",
                       "next": "按 plan 逐页转录（宪法第零条分块核对），完成写 text.md 后 send 回执"}

    if pack == "split-text-image" and stage == "html":
        units, missing = [], []
        svg_dir = os.path.join(dest, "img")
        for pid, _ in pages:
            tdir = work1(pid)
            if not os.path.exists(os.path.join(tdir, "text.md")):
                missing.append(pid)
                continue
            cmd = unit_cmd(py, os.path.join(p1, "build_html.py"),
                           "--page", pid, "--text", os.path.join(tdir, "text.md"),
                           "--out", os.path.join(dest, f"{pid}.html"),
                           "--workdir", tdir)
            fj = os.path.join(tdir, "figures.json")
            if os.path.exists(fj):
                cmd += ["--figures", fj]
            # dest/img/ 已有发布的重绘主档 → figure-map 相对引用（单图页 <page>.svg / 多图页 -fig<i>）; 无则 build_html 自动发布裁剪 JPG 为 dest/img/<stem>.jpg
            try:
                n_figs = int(json.load(open(fj, encoding="utf-8")).get("count", 0) or 0)
            except Exception:
                n_figs = 0
            fmap = {}
            for i in range(1, n_figs + 1):
                stem = pid if n_figs == 1 else f"{pid}-fig{i}"
                sp = os.path.join(svg_dir, stem + ".svg")
                if os.path.exists(sp):
                    fmap[str(i)] = {"kind": "svg", "path": sp}
            if fmap:
                fmp = os.path.join(tdir, "figure-map.json")
                json.dump(fmap, open(fmp, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                cmd += ["--figure-map", fmp]
            units.append((f"html:{pid}", cmd))
        info = {"to": "compositor",
                "send": f"{len(units)} 页已排版为最终件 dest/<page>.html（公式已渲染, 插图引用 dest/img/）",
                "state": "dest/<page>.html + dest/img/ 就绪; 中间件在 .work/<名>/pack1/",
                "next": "按第九条自检; 需矢量重绘时由 figure-artisan 供 spec 跑 px2svg 后重排"}
        if missing:
            info["send"] += f"；{len(missing)} 页未转录已跳过: {','.join(missing[:8])}{'…' if len(missing) > 8 else ''}"
        if not units:
            raise SystemExit("batch: 没有可排版的页（.work/<名>/pack1/<page>/text.md 均缺失）")
        return units, info

    if pack == "px2svg" and stage == "redraw":
        specs_dir = os.path.join(work, "pack2", "specs")
        spec_files = sorted(glob.glob(os.path.join(specs_dir, "*.spec.json")))
        if a.pages:
            keep = {s.strip() for s in a.pages.split(",") if s.strip()}
            spec_files = [s for s in spec_files
                          if os.path.basename(s).split("-fig")[0] in keep]
        if not spec_files:
            raise SystemExit(f"batch: {specs_dir} 下没有 spec（figure-artisan 量测后编写）")
        svg_dir = os.path.join(dest, "svg")
        units = []
        for spec in spec_files:
            stem = os.path.basename(spec).replace(".spec.json", "")
            page = stem.split("-fig")[0]
            fig_i = stem.split("-fig")[1] if "-fig" in stem else "1"
            cmd = unit_cmd(py, os.path.join(p2, "mpl_redraw.py"),
                           "--spec", spec, "--out", os.path.join(work, "pack2", "svg"),
                           "--publish", os.path.join(dest, "img"),
                           "--publish-name", page if svg_publish_name(page) == "single" else stem)
            crop = os.path.join(work1(page), "crops", f"fig{fig_i}.jpg")
            if os.path.exists(crop):
                cmd += ["--original", crop]
            units.append((stem, cmd))
        return units, {"to": "compositor",
                       "send": f"{len(units)} 个 spec 渲染完成（主档已发布 dest/img/, 四件套在 .work）",
                       "state": "dest/img/<page>.svg 就绪, 对比图在 .work/<名>/pack2/svg/ 需人工查看（宪法第七条）",
                       "next": "查看 compare 对比图验收后, 重跑 batch --pack split-text-image --stage html 内嵌 SVG"}

    if pack == "html-svg" and stage == "compose":
        if not pages:
            raise SystemExit("batch: src/ 下没有原图")
        units, skipped = [], []
        for pid, _ in pages:
            mf = os.path.join(work, "pack3", f"{pid}.manifest.json")
            if os.path.exists(mf):
                try:
                    if json.load(open(mf, encoding="utf-8")).get("complete"):
                        skipped.append(pid)  # 整页终态（redraw_todo 空）才跳过
                        continue
                except Exception:
                    pass
            units.append((f"compose:{pid}",
                          unit_cmd(py, os.path.join(p3, "compose_page.py"),
                                   "--project", proj, "--page", pid)))
        if skipped:
            print(f"[batch] 已整页完成（manifest.complete）, 跳过: {','.join(skipped)}")
        return units, {"to": "figure-artisan",
                       "send": f"{len(units)} 页 compose 编排完成",
                       "state": ".work/<名>/pack3/<page>.manifest.json 记录各图状态",
                       "next": "查 manifest.redraw_todo 非空的页, 量测补 spec 后重跑本阶段"}

    raise SystemExit(f"batch: 组合无效 --pack {pack} --stage {stage}（可选: {VALID_STAGE[pack]}）")


def compose_summary(proj):
    """汇总 .work/<名>/pack3/*.manifest.json 的待重绘清单。"""
    mdir = os.path.join(work_dir(proj), "pack3")
    todo_all, done_all = [], []
    for mf in sorted(glob.glob(os.path.join(mdir, "*.manifest.json"))):
        m = json.load(open(mf, encoding="utf-8"))
        page = m.get("page", "?")
        (done_all if m.get("complete") else todo_all).append(page)
    return done_all, todo_all


def main():
    ap = argparse.ArgumentParser(description="目录驱动批量转换入口")
    ap.add_argument("--project", required=True, help="项目名（figforge/project/ 下）或绝对路径")
    ap.add_argument("--pack", required=True, choices=list(DEFAULT_STAGE))
    ap.add_argument("--stage", default=None, choices=None,
                    help=f"阶段, 默认随 pack: {DEFAULT_STAGE}")
    ap.add_argument("--pages", default=None, help="只处理这些页, 逗号分隔（如 0101,0107）")
    ap.add_argument("--sleep", type=float, default=3.0, help="页间隔秒（宪法第三条）")
    ap.add_argument("--maxseconds", type=int, default=3600,
                    help="单段时长上限, 段末自动备份并接力下一批（宪法第一条②）")
    ap.add_argument("--max-rounds", type=int, default=0,
                    help="自动接力段数上限（0=不限; 无进展止损兑底）")
    ap.add_argument("--dry-print", action="store_true", help="只打印将执行的命令, 不执行")
    a = ap.parse_args()

    stage = a.stage or DEFAULT_STAGE[a.pack]
    if stage not in VALID_STAGE[a.pack]:
        raise SystemExit(f"batch: pack {a.pack} 无阶段 {stage}（可选 {VALID_STAGE[a.pack]}）")
    a.stage = stage  # build_units 使用解析后的默认阶段

    proj = project_dir(a.project)
    os.makedirs(os.path.join(proj, "dest"), exist_ok=True)
    state_path = os.path.join(proj, f"run-state-{stage}.json")

    units, info = build_units(a, proj, sys.executable)

    # compose 重跑语义（workflow ④）: 非终态页每轮全量刷新, 补 spec 后重跑必须生效
    # —— 清掉 state 中本轮待跑单元的旧 ok 记录, 防止被断点跳过
    if a.pack == "html-svg" and stage == "compose" and os.path.exists(state_path):
        st = json.load(open(state_path, encoding="utf-8"))
        force = {u[0] for u in units}
        kept = [x for x in st.get("ok", []) if x not in force]
        if len(kept) != len(st.get("ok", [])):
            st["ok"] = kept
            json.dump(st, open(state_path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"[batch] compose 重跑: 清除 {len(force)} 页旧断点, 本轮全量刷新")

    # html 重跑语义: dest/img/ 重绘主档比 dest/<page>.html 新（重绘刚验收发布）→
    # 清旧断点强制重排, 让最终件引用最新 SVG（断点只表示"执行过", 不表示"最新"）
    if a.pack == "split-text-image" and stage == "html" and os.path.exists(state_path):
        st = json.load(open(state_path, encoding="utf-8"))
        svg_dir = os.path.join(proj, "dest", "img")
        drop = []
        for jid, _cmd in units:
            pid = jid.split(":", 1)[1]
            out_html = os.path.join(proj, "dest", f"{pid}.html")
            if not os.path.exists(out_html):
                drop.append(jid)
                continue
            for sv in glob.glob(os.path.join(svg_dir, f"{pid}*.svg")):
                if os.path.getmtime(sv) > os.path.getmtime(out_html):
                    drop.append(jid)
                    break
        drop = [d for d in drop if d in st.get("ok", [])]
        if drop:
            st["ok"] = [x for x in st["ok"] if x not in drop]
            json.dump(st, open(state_path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"[batch] html 重跑: dest/img 有更新, 清除断点强制重排: {','.join(drop)}")
    print(f"[batch] 项目 {proj}")
    print(f"[batch] {a.pack}/{stage}: {len(units)} 个单元（断点 {state_path}）")

    # plan 自动建立（宪法第二条）
    if not a.dry_print:
        ensure_plan(proj, f"{os.path.basename(proj)} · {a.pack}/{stage}", [u[0] for u in units])

    if a.dry_print:
        for jid, cmd in units:
            print(f"  {jid}: {' '.join(cmd)}")
        print(f"[batch] dry-print 共 {len(units)} 条命令, 未执行")
        return

    # ---- 自动接力（宪法第一条②）: 每段（--maxseconds 优雅停）结束后自动备份
    # project/（排除各项目 src/, 第一条①）并继续下一批, 无需人工接力;
    # 直到全部完成 / 429 熔断 / 无进展止损（失败项重试一轮仍无新完成即停）。
    def _load_ok_fail():
        st = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) \
            else {"ok": [], "fail": []}
        return set(st.get("ok", [])), set(st.get("fail", []))

    def _auto_archive():
        """宪法第一条①/②: 一批完成 → 自动备份 project/（排除 src/）。"""
        subprocess.run(["bash", os.path.join(HERE, "archive.sh")], check=False)

    initial_ok, _ = _load_ok_fail()
    prev_ok = len([u[0] for u in units if u[0] in initial_ok])  # 本批已断点完成数
    pending = [u[0] for u in units if u[0] not in initial_ok]
    if not pending:
        print(f"[batch] 断点显示本批 {len(units)} 单元已全部完成, 跳过执行")
    else:
        round_no = 0
        while True:
            round_no += 1
            rc = run_serial(units, a.sleep, a.maxseconds, state_path,
                            label=f"batch:{stage}·r{round_no}")
            if rc == 43:
                sys.exit(43)  # 429 熔断: 不写 handoff, 等探测恢复后续跑（宪法第六条）
            ok_set, fail_set = _load_ok_fail()
            ok_ids = [u[0] for u in units if u[0] in ok_set]
            remaining = [u[0] for u in units if u[0] not in ok_set]
            if len(ok_ids) == prev_ok:
                print(f"[batch] 自动接力止损: 本段无新完成项（累计失败 {len(fail_set)} 项, "
                      f"state 已记录, 原样重跑可重试）—— 停止接力（宪法第一条②）")
                break
            if remaining:
                print(f"[batch] 第 {round_no} 段完成（新增 {len(ok_ids) - prev_ok} 项）→ "
                      f"自动备份 project/ 后继续下一批（剩余 {len(remaining)} 项, 第一条②）")
                _auto_archive()
            prev_ok = len(ok_ids)
            if not remaining:
                print(f"[batch] 本批 {len(units)} 单元全部完成（自动接力 {round_no} 段）→ 自动备份")
                _auto_archive()
                break
            if a.max_rounds and round_no >= a.max_rounds:
                print(f"[batch] 达 --max-rounds={a.max_rounds}, 停止接力; "
                      f"剩余 {len(remaining)} 项（state 断点, 原样重跑自动续）")
                break

    # state 复核: 只有成功项才核销 plan（宪法第二条"完成才核销"）;
    # 有失败项时如实交接, 不得谎报"整页完成"（第九条诚实交付）
    st = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) \
        else {"ok": [], "fail": []}
    ok_set, fail_set = set(st.get("ok", [])), set(st.get("fail", []))
    ok_ids = [u[0] for u in units if u[0] in ok_set]
    fail_ids = [u[0] for u in units if u[0] in fail_set]
    check_off_plan(proj, ok_ids)

    from handoff import handoff_path
    hp = handoff_path(proj)
    if fail_ids:
        info = {"to": "operator",
                "send": f"{len(ok_ids)}/{len(units)} 完成; 失败 {len(fail_ids)} 项: "
                        f"{','.join(fail_ids[:8])}{'…' if len(fail_ids) > 8 else ''}",
                "state": f"失败项已记 {os.path.basename(state_path)}（重跑自动重试）",
                "next": "排查失败原因（batch 输出 stderr; 插图检测可 --boxes 手工兜底）"
                        "后原样重跑本命令, state 只跳过已完成项"}
    elif a.pack == "html-svg" and stage == "compose":
        done_pages, todo_pages = compose_summary(proj)
        if todo_pages:
            info.update({"to": "figure-artisan",
                         "send": f"compose 完成; 待重绘页: {','.join(todo_pages)}",
                         "state": "manifest.redraw_todo 非空（.work/<名>/pack3/）",
                         "next": "量测补 spec 至 .work/<名>/pack2/specs/ 后重跑 compose"})
        else:
            info.update({"to": "operator",
                         "send": f"整页完成 {len(done_pages)} 页（redraw_todo 全空）",
                         "state": "dest/ 最终件就绪（<page>.html + img/）",
                         "next": "按第九条自检 + archive.sh 归档交付"})
    subprocess.run([sys.executable, os.path.join(HERE, "handoff.py"), "send",
                    "--project", proj, "--from", "operator", "--to", info["to"],
                    "--send", info["send"], "--state", info.get("state", ""),
                    "--next", info.get("next", "")], check=False)
    print(f"[batch] 完成; 交接已记入 {hp}")


if __name__ == "__main__":
    main()
