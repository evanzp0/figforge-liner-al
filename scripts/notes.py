#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: notes.py —— 经验库与检索目录（宪法第十二/十三条）

流程处理完当前项目收尾时, 若本棒处理过程中遇到过错误且已解决, 对应角色把
经验沉淀到 project/notes/notes_<role>.md; notes/ 下自动维护 INDEX.md 供检索。

经验库不是日志（第十三条）: 一条经验一个条目, 只写 现象/根因/解决/预防/标签
五要素——无日期、无次数、无项目统计; 同一现象再次 add 只覆盖刷新解法字段,
不追加新条目; 每角色条目数有上限（超限先合并同类）。INDEX.md 是**目录不是
经验清单**: 每角色一行（文件+关键词聚合）, 行数 ≤ 角色数, 恒定大小, 不随
经验条数增长——"一行一条经验"的现象表/日期/次数列都是台账, 一律禁止。

用法:
  notes.py add --role operator \
      --symptom "vision 检测连续 429" --fix "停批转 probe-429.sh 低频探测" \
      [--cause "账号级共享配额限流"] [--prevent "批量只走 batch.py"] \
      [--tags "429,detect"]
  notes.py show [--role operator] [--tag 429] [--grep 配额] [-n 5]
  notes.py reindex            # 从全部 notes_*.md 重建 INDEX.md（手工改动后用）

文件布局:
  figforge/project/notes/notes_<role>.md   每角色一个经验库（五要素条目, 有上限）
  figforge/project/notes/INDEX.md          检索目录（每角色一行, add/reindex 重建）
"""
import argparse
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # figforge/
NOTES_DIR = os.path.join(ROOT, "project", "notes")
ENTRY = re.compile(r"^## (?P<symptom>.+?)\s*$")
FIELD = re.compile(r"^- (根因|解决|预防|标签): (.*)$")
FIELD_ORDER = ("根因", "解决", "预防", "标签")
SYMPTOM_MAX = 100   # 现象一句话上限（字符）
FIELD_MAX = 200     # 各字段上限（字符）
MAX_ENTRIES = 20    # 每角色条目上限——超限先合并/精简同类再 add（第十三条: 不许越滚越长）
TAGS_MAX = 12       # INDEX 每行关键词上限（去重聚合后截断）


def trunc(s: str, n: int) -> str:
    """压成单行并截断——条目必须一行一个字段, 不许长篇大论（第十三条）。"""
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s if len(s) <= n else s[:n] + "…"


def tags_of(raw: str) -> str:
    return " ".join("#" + t.strip().lstrip("#") for t in (raw or "").split(",") if t.strip())


def entry_path(role: str) -> str:
    if not re.fullmatch(r"[\w\-]+", role):
        raise SystemExit(f"notes.py: 角色名非法: {role!r}（用于文件名, 只允许字母/数字/下划线/连字符）")
    return os.path.join(NOTES_DIR, f"notes_{role}.md")


def parse_file(path: str):
    """解析一个 notes_<role>.md, 返回条目列表（文件内正序; 旧统计行自动忽略）。"""
    m = re.match(r"notes_(.+)\.md$", os.path.basename(path))
    role = m.group(1) if m else "?"
    entries, cur = [], None
    for ln in open(path, encoding="utf-8"):
        m = ENTRY.match(ln.rstrip())
        if m:
            cur = {"role": role, "symptom": m.group("symptom"), "fields": {}}
            entries.append(cur)
        elif cur is not None:
            f = FIELD.match(ln.strip())
            if f:
                cur["fields"][f.group(1)] = f.group(2)
    return [e for e in entries if e["symptom"]]


def all_entries():
    out = []
    for p in sorted(glob.glob(os.path.join(NOTES_DIR, "notes_*.md"))):
        out.extend(parse_file(p))
    return out


def render_file(role: str, entries) -> str:
    lines = [
        f"# NOTES — {role} 经验库（错误 → 解决）",
        "> 宪法第十二/十三条: 项目收尾把已解决的错误提炼在此; 一条经验一个条目,",
        "> 只写 现象/根因/解决/预防/标签 五要素（非日志: 无日期/次数/统计, 有条目上限）;",
        "> 由 scripts/notes.py add 写入与合并; 检索先看 INDEX.md 或 notes.py show。",
    ]
    for e in entries:
        lines += ["", f"## {e['symptom']}"]
        for k in FIELD_ORDER:
            if e["fields"].get(k):
                lines.append(f"- {k}: {e['fields'][k]}")
    return "\n".join(lines) + "\n"


def cell(text: str) -> str:
    """INDEX.md 表格单元格转义（竖线会破坏表格）。"""
    return (text or "").replace("|", "／")


def rebuild_index() -> int:
    """从全部 notes_*.md 重建 INDEX.md——每角色一行目录（文件+关键词）; 返回行数。"""
    paths = sorted(glob.glob(os.path.join(NOTES_DIR, "notes_*.md")))
    lines = [
        "# NOTES INDEX — 经验库检索目录（非日志, 第十三条）",
        "> 由 scripts/notes.py 自动维护（add/reindex 重建）; 手工改动会被覆盖。",
        "> 目录不是经验清单: 每角色一行, 无现象/日期/次数; 详情读对应 notes_<role>.md",
        "> 或检索: python3 scripts/notes.py show [--role R] [--tag T] [--grep 关键词]",
        "",
        "| 文件 | 关键词 |",
        "|---|---|",
    ]
    for p in paths:
        role = re.match(r"notes_(.+)\.md$", os.path.basename(p)).group(1)
        tags = []
        for e in parse_file(p):
            for t in e["fields"].get("标签", "").split():
                if t and t not in tags:
                    tags.append(t)
        if tags:
            kw = " ".join(tags[:TAGS_MAX]) + (" …" if len(tags) > TAGS_MAX else "")
        else:
            kw = "—"
        lines.append(f"| {cell(os.path.basename(p))} | {cell(kw)} |")
    if not paths:
        lines.append("| （暂无经验文件——收尾遇错并解决后用 notes.py add 沉淀） |  |")
    os.makedirs(NOTES_DIR, exist_ok=True)
    open(os.path.join(NOTES_DIR, "INDEX.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return len(paths)


def add(args):
    path = entry_path(args.role)
    os.makedirs(NOTES_DIR, exist_ok=True)
    entries = parse_file(path) if os.path.exists(path) else []
    symptom = trunc(args.symptom, SYMPTOM_MAX)
    merged = next((e for e in entries if e["symptom"] == symptom), None)
    if merged is None and len(entries) >= MAX_ENTRIES:
        raise SystemExit(
            f"notes.py: {os.path.basename(path)} 已达上限 {MAX_ENTRIES} 条"
            f"（第十三条: 不许越滚越长）——先合并/精简同类条目（编辑后 notes.py reindex）再 add")
    if merged is not None:
        if args.cause:
            merged["fields"]["根因"] = trunc(args.cause, FIELD_MAX)
        merged["fields"]["解决"] = trunc(args.fix, FIELD_MAX)  # 最新解法覆盖旧解法
        if args.prevent:
            merged["fields"]["预防"] = trunc(args.prevent, FIELD_MAX)
        if args.tags:
            merged["fields"]["标签"] = tags_of(args.tags)
        verb = "已合并（同现象, 解法字段已刷新）"
    else:
        e = {"role": args.role, "symptom": symptom,
             "fields": {"解决": trunc(args.fix, FIELD_MAX)}}
        if args.cause:
            e["fields"]["根因"] = trunc(args.cause, FIELD_MAX)
        if args.prevent:
            e["fields"]["预防"] = trunc(args.prevent, FIELD_MAX)
        if args.tags:
            e["fields"]["标签"] = tags_of(args.tags)
        entries.append(e)
        verb = f"已沉淀（新条目 {len(entries)}/{MAX_ENTRIES}）"
    open(path, "w", encoding="utf-8").write(render_file(args.role, entries))
    n = rebuild_index()
    print(f"[notes] {verb}: {args.role} @ {path}")
    print(f"[notes] INDEX.md 已更新（{n} 行目录——每角色一行, 不随条目增长）")


def show(args):
    hits = [e for e in all_entries()
            if (not args.role or e["role"] == args.role)
            and (not args.tag or f"#{args.tag.lstrip('#')}" in e["fields"].get("标签", ""))
            and (not args.grep or args.grep.lower() in " ".join(
                [e["symptom"]] + list(e["fields"].values())).lower())]
    if args.n:
        hits = hits[:args.n]
    if not hits:
        print("[notes] 无匹配条目（notes/ = " + NOTES_DIR + "）")
        return
    for e in hits:
        print(f"## [{e['role']}] {e['symptom']}")
        for k in FIELD_ORDER:
            if e["fields"].get(k):
                print(f"- {k}: {e['fields'][k]}")
        print()
    print(f"[notes] 共 {len(hits)} 条（notes/ = {NOTES_DIR}）")


def reindex(args):
    n = rebuild_index()
    print(f"[notes] INDEX.md 已重建（{n} 行目录, {NOTES_DIR}/INDEX.md）")


def main():
    ap = argparse.ArgumentParser(description="经验库与检索目录（宪法第十二/十三条, 五要素条目, 无统计）")
    sub = ap.add_subparsers(dest="verb", required=True)

    p1 = sub.add_parser("add", help="沉淀一条经验（同现象自动合并; 无日期/次数统计）")
    p1.add_argument("--role", required=True, help="角色, 如 operator / transcriber")
    p1.add_argument("--symptom", required=True, help="现象（一句话, 与已有条目相同则合并）")
    p1.add_argument("--fix", required=True, help="怎么解决的（命令/参数/位置; 合并时覆盖旧解法）")
    p1.add_argument("--cause", default=None, help="根因（可选）")
    p1.add_argument("--prevent", default=None, help="预防措施（可选）")
    p1.add_argument("--tags", default=None, help="逗号分隔标签, 如 429,detect")
    p1.set_defaults(fn=add)

    p2 = sub.add_parser("show", help="检索经验（先扫 INDEX.md 目录定位文件）")
    p2.add_argument("--role", default=None)
    p2.add_argument("--tag", default=None, help="按标签过滤（不带 #）")
    p2.add_argument("--grep", default=None, help="全文关键词过滤")
    p2.add_argument("-n", type=int, default=None, help="只看前 N 条")
    p2.set_defaults(fn=show)

    p3 = sub.add_parser("reindex", help="从全部 notes_*.md 重建 INDEX.md")
    p3.set_defaults(fn=reindex)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
