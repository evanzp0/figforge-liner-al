#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: handoff.py —— 项目角色交接板（宪法附录·交接协议 + 第十三条）

角色间交接只认 handoff.md 交接板（swarmforge handoff 风格）:
  * 完成一项立即 send 写入 SEND / STATE / NEXT 三行;
  * 开工先 show --to <我> 读取上一棒的 NEXT, 禁止凭记忆接活;
  * 交接板不是日志（第十三条）: 每个 发→收 组合只保留最新一条, send 就地更新,
    文件不随运行轮次线性增长;
  * 只允许更新自己发出的条目, 禁止改写他人条目;
  * 交接板另含固定一段「定版参数」（宪法第七条第 6 款③: 页面宽/高、上下左右
    边距等项目级统一参数）——只允许 scripts/calibrate.py 经 params 子命令
    覆盖写（非日志）, send/show 永不删除该段。

用法:
  handoff.py send --project <your_project_name> --from operator --to transcriber \
      --send "3 页插图已裁剪至 dest/transcriber/" \
      [--state "figures.json + crops/ 就绪"] [--next "按 plan 逐页转录, 完成写 text.md"]
  handoff.py show --project <your_project_name> [--to transcriber] [--from operator] [-n 5]
  handoff.py params --project <your_project_name> --line "- page_w/page_h: 820x1042px" [--line ...]
  handoff.py params-check --project <your_project_name>   # 未定版退出码 3（开工前置检查）

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
PARAMS_HEAD = re.compile(r"^## 定版参数")
PARAMS_TITLE = "## 定版参数（项目级布局参数, 全页遵守 —— 宪法第七条第 6 款③）"
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
    """把交接板解析为条目块列表（每块 = [头行, SEND/STATE/NEXT...]）。
    「定版参数」段（PARAMS_HEAD）视为独立块, send 重建文件时原样保留。"""
    blocks, cur = [], None
    for ln in text.splitlines():
        s = ln.strip()
        if ENTRY.match(s) or PARAMS_HEAD.match(s):
            if cur:
                blocks.append(cur)
            cur = [s]
        elif cur is not None and s:
            cur.append(s)
    if cur:
        blocks.append(cur)
    return blocks


def params_lines(project: str) -> list:
    """返回定版参数段各行（无则 []）—— batch/calibrate 开工前置检查用。"""
    path = handoff_path(project)
    if not os.path.exists(path):
        return []
    for b in _parse_blocks(open(path, encoding="utf-8").read()):
        if PARAMS_HEAD.match(b[0]):
            return b[1:]
    return []


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
    if getattr(args, "params", False):
        pl = params_lines(args.project)
        print(PARAMS_TITLE)
        for l in pl:
            print(l)
        if not pl:
            print("[交接] 尚未定版（无定版参数段; 先跑 scripts/calibrate.py）")
        return
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


def params_set(args):
    """写入/更新定版参数段（覆盖写, 非日志; 只允许 scripts/calibrate.py 调用）。
    send 永不删除该段（附录: send/show 不得删除定版参数段）。"""
    path = handoff_path(args.project)
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else HEADER
    blocks = [b for b in _parse_blocks(text) if not PARAMS_HEAD.match(b[0])]
    blocks.append([PARAMS_TITLE] + list(args.line))
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(HEADER)
        for b in blocks:
            fp.write("\n" + "\n".join(b) + "\n")
    print(f"[交接] 定版参数已覆盖写: {path}（宪法第七条第 6 款③, 非日志）")


def params_check(args):
    """开工前置检查: handoff.md 是否已写明布局定版参数（宪法第七条第 6 款③）。
    退出码 0=已定版; 3=未定版（需先跑 scripts/calibrate.py）。"""
    pl = params_lines(args.project)
    if not pl:
        print("[交接] 未定版: handoff.md 无「定版参数」段 ——"
              " 先跑 python3 scripts/calibrate.py --project <名>（第七条第 6 款③）")
        raise SystemExit(3)
    print("[交接] 已定版（handoff.md 定版参数段）:")
    for l in pl:
        print("  " + l)


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
    p2.add_argument("--params", action="store_true", help="只看定版参数段（第七条第 6 款③）")
    p2.set_defaults(fn=show)

    p3 = sub.add_parser("params", help="写入/更新定版参数段（覆盖写, 非日志; calibrate.py 专用）")
    p3.add_argument("--project", required=True)
    p3.add_argument("--line", action="append", required=True,
                    help="参数行（可重复）; 每行一条, 建议以 '- 字段: 值' 格式")
    p3.set_defaults(fn=params_set)

    p4 = sub.add_parser("params-check", help="检查是否已定版（退出码 0/3, 开工前置检查）")
    p4.add_argument("--project", required=True)
    p4.set_defaults(fn=params_check)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
