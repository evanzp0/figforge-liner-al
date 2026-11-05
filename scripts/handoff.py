#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: handoff.py —— 项目角色交接板（宪法附录·交接协议 + 第十三条）

角色间交接只认 handoff.md 交接板（swarmforge handoff 风格）:
  * 完成一项立即 send 写入 SEND / STATE / NEXT 三行;
  * 开工先 show --to <我> 读取上一棒的 NEXT, 禁止凭记忆接活;
  * 交接板不是日志（第十三条）: 每个 发→收 组合只保留最新一条, send 就地更新,
    文件不随运行轮次线性增长;
  * 只允许更新自己发出的条目, 禁止改写他人条目。

用法:
  handoff.py send --project mybook --from operator --to transcriber \
      --send "3 页插图已裁剪至 dest/transcriber/" \
      [--state "figures.json + crops/ 就绪"] [--next "按 plan 逐页转录, 完成写 text.md"]
  handoff.py show --project mybook [--to transcriber] [--from operator] [-n 5]

交接板位置: figforge/project/<项目名>/handoff.md（--project 也可直接给路径）
"""
import argparse
import datetime as _dt
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = re.compile(
    r"^## (?P<ts>[0-9: \-]+) \| (?P<frm>[\w\-]+) → (?P<to>[\w\-]+)\s*$"
)
HEADER = ("# HANDOFF — 角色交接板（非日志, 宪法第十三条）\n"
          "> 每个 发→收 只保留最新一条, send 就地更新; 开工先读上一棒 NEXT"
          "（scripts/handoff.py show）。只允许更新自己发出的条目。\n")


def handoff_path(project: str) -> str:
    p = project if os.path.isabs(project) or os.path.isdir(project) \
        else os.path.join(ROOT, "project", project)
    if os.path.isdir(p):
        return os.path.join(p, "handoff.md")
    # 给的是项目名但目录不存在 → 在 project/ 下定位（供 send 首次创建）
    guess = os.path.join(ROOT, "project", project)
    os.makedirs(guess, exist_ok=True)
    return os.path.join(guess, "handoff.md")


def _parse_blocks(text: str):
    """把交接板解析为条目块列表（每块 = [头行, SEND/STATE/NEXT...]）。"""
    blocks, cur = [], None
    for ln in text.splitlines():
        if ENTRY.match(ln.strip()):
            if cur:
                blocks.append(cur)
            cur = [ln.strip()]
        elif cur is not None and ln.strip():
            cur.append(ln.strip())
    if cur:
        blocks.append(cur)
    return blocks


def send(args):
    path = handoff_path(args.project)
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = [f"## {ts} | {args.frm} → {args.to}", f"- SEND: {args.send}"]
    if args.state:
        entry.append(f"- STATE: {args.state}")
    if args.next:
        entry.append(f"- NEXT: {args.next}")

    blocks = _parse_blocks(
        open(path, encoding="utf-8").read()) if os.path.exists(path) else []
    replaced = False
    for i, b in enumerate(blocks):  # 同 发→收 就地更新（第十三条: 不是日志）
        m = ENTRY.match(b[0])
        if m and m.group("frm") == args.frm and m.group("to") == args.to:
            blocks[i] = entry
            replaced = True
            break
    if not replaced:
        blocks.append(entry)
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(HEADER)
        for b in blocks:
            fp.write("\n" + "\n".join(b) + "\n")
    verb = "已更新" if replaced else "已记录"
    print(f"[交接] {verb}: {args.frm} → {args.to} @ {path}（交接板: 每 发→收 一条）")


def show(args):
    path = handoff_path(args.project)
    if not os.path.exists(path):
        print(f"[交接] 交接板不存在: {path}")
        return
    blocks = _parse_blocks(open(path, encoding="utf-8").read())
    hits = [b for b in blocks
            if ENTRY.match(b[0])
            and (not args.to or ENTRY.match(b[0]).group("to") == args.to)
            and (not args.frm or ENTRY.match(b[0]).group("frm") == args.frm)]
    if args.n:
        hits = hits[-args.n:]
    if not hits:
        print("[交接] 无匹配交接条目")
        return
    for b in hits:
        print("\n".join(b))
        print()
    print(f"[交接] 共 {len(hits)} 条（交接板 {path}）")


def main():
    ap = argparse.ArgumentParser(description="handoff.md 角色交接板（每 发→收 一条, send 即更新）")
    sub = ap.add_subparsers(dest="verb", required=True)

    p1 = sub.add_parser("send", help="写入/更新一条交接（同 发→收 就地更新）")
    p1.add_argument("--project", required=True)
    p1.add_argument("--from", dest="frm", required=True)
    p1.add_argument("--to", required=True)
    p1.add_argument("--send", required=True, help="交付了什么（含产物位置）")
    p1.add_argument("--state", default=None, help="当前状态/输入就绪情况")
    p1.add_argument("--next", default=None, help="对下一棒的明确指令")
    p1.set_defaults(fn=send)

    p2 = sub.add_parser("show", help="查看交接条目")
    p2.add_argument("--project", required=True)
    p2.add_argument("--to", default=None)
    p2.add_argument("--from", dest="frm", default=None)
    p2.add_argument("-n", type=int, default=None, help="只看最近 N 条")
    p2.set_defaults(fn=show)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
