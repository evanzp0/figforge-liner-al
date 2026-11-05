#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: plan.py —— plan.md 生成与核销（宪法第二条）

用法:
  plan.py init --title "图文分离 200 页" --ids 0001 0002 ... [--file plan.md]
  plan.py done 0107 [--note "缺图, 已人工登记"] [--file plan.md]
  plan.py next                    # 打印第一个未完成项（中断恢复入口 —— 宪法第二条）
  plan.py show                    # 进度总览
  plan.py add 0201 0202           # 追加任务

plan.md 行格式: "- [ ] <id> — <备注>"（完成改 [x]）
"""
import argparse
import datetime as _dt
import os
import re
import sys

LINE = re.compile(r"^- \[( |x)\] (\S+)(?: — (.*))?$")


def read_lines(path):
    if not os.path.exists(path):
        raise SystemExit(f"plan.py: {path} 不存在（先 init）")
    return open(path, encoding="utf-8").read().splitlines()


def write_lines(path, lines):
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def parse(lines):
    items = []
    for ln in lines:
        m = LINE.match(ln)
        if m:
            items.append({"done": m.group(1) == "x", "id": m.group(2), "note": m.group(3) or ""})
    return items


def main_with(argv=None):
    """可编程入口（batch.py import 调用）; argv 默认取命令行。"""
    ap = argparse.ArgumentParser(description="plan.md 生成/核销/恢复")
    ap.add_argument("verb", choices=["init", "done", "next", "show", "add"])
    ap.add_argument("ids", nargs="*", help="任务 id（位置传参）")
    ap.add_argument("--ids", dest="ids_opt", nargs="*", default=None,
                    help="任务 id（--ids 传参, 与位置传参等价可混用）")
    ap.add_argument("--title", default="figforge 批量任务")
    ap.add_argument("--note", default=None)
    ap.add_argument("--file", default="plan.md")
    a = ap.parse_args(argv if argv is not None else None)
    all_ids = list(a.ids) + list(a.ids_opt or [])
    if a.verb in ("init", "add", "done") and not all_ids:
        raise SystemExit(f"plan.py {a.verb}: 需要 id（位置参数或 --ids）")

    if a.verb == "init":
        lines = [f"# PLAN — {a.title}",
                 f"> 生成于 {_dt.date.today().isoformat()}（宪法第二条: 每完成一项立即核销;"
                 f" 中断恢复先 plan.py next）", ""]
        for i in all_ids:
            lines.append(f"- [ ] {i}")
        write_lines(a.file, lines)
        print(f"[plan] {a.file}: {len(all_ids)} 项已生成")
        return

    lines = read_lines(a.file)
    items = parse(lines)

    if a.verb == "done":
        targets = set(all_ids)
        hit = 0
        for idx, it in enumerate(items):
            if it["id"] in targets:
                items[idx]["done"] = True
                if a.note:
                    items[idx]["note"] = (items[idx]["note"] + "; " if items[idx]["note"] else "") + a.note
                hit += 1
        if not hit:
            raise SystemExit(f"plan.py: 未找到任务 {sorted(targets)}")
        out, k = [], 0
        for ln in lines:
            m = LINE.match(ln)
            if m and m.group(2) in targets:
                it = items[k] if k < len(items) else None
                k += 1
                note = it["note"]
                out.append(f"- [x] {m.group(2)}" + (f" — {note}" if note else ""))
            else:
                out.append(ln)
        write_lines(a.file, out)
        print(f"[plan] 已核销 {hit} 项")

    elif a.verb == "add":
        new = [i for i in all_ids if i not in {it['id'] for it in items}]
        out = lines + [f"- [ ] {i}" for i in new]
        write_lines(a.file, out)
        print(f"[plan] 追加 {len(new)} 项")

    elif a.verb == "next":
        todo = [it for it in items if not it["done"]]
        if not todo:
            print("[plan] 全部完成 ✔")
        else:
            print(f"[plan] 下一项: {todo[0]['id']}" + (f" — {todo[0]['note']}" if todo[0]["note"] else ""))
            print(f"[plan] 剩余 {len(todo)}/{len(items)}")

    elif a.verb == "show":
        done = [it for it in items if it["done"]]
        todo = [it for it in items if not it["done"]]
        print(f"[plan] 进度 {len(done)}/{len(items)}")
        if todo:
            print(f"[plan] 未完成（前 10）: {', '.join(it['id'] for it in todo[:10])}")
        if done:
            print(f"[plan] 已完成（末 5）: {', '.join(it['id'] for it in done[-5:])}")


def main():
    main_with(None)


if __name__ == "__main__":
    main()
