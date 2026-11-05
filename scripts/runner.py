#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: runner.py —— 单进程前台串行执行核心（宪法第三条）

两种用法:
  A. 命令行（通用调度）:
     runner.py --jobs jobs.txt \
         --cmd "python3 packs/.../detect_figures.py --page {id} --image in/{id}.png" \
         [--sleep 3] [--maxseconds 1800] [--state run-state.json] [--start-from 0107]
  B. 被脚本复用（batch.py import run_serial）:
     run_serial(units, sleep, maxseconds, state_path)
     units: [(jid, cmd)] —— cmd 为 str（shell 执行）或 list（argv 执行）

行为（宪法第三条/第六条）:
  * 严格串行: 恒定单进程, 不提供任何并发选项;
  * 页间隔: 每项之间 sleep 秒;
  * 优雅停: 已运行超过 --maxseconds 时做完当前项即停（断点记入 state）;
  * 断点续跑: state 中 ok 的项自动跳过（与 plan.md 双保险 —— 宪法第二条）;
  * 429 熔断: 子进程退出码 43 → 立即停批并提示转入 probe-429.sh（宪法第六条）,
    本函数返回 43 交由调用方处理。
"""
import argparse
import json
import os
import subprocess
import sys
import time


def load_state(path):
    if os.path.exists(path):
        try:
            st = json.load(open(path, encoding="utf-8"))
            st.setdefault("ok", [])
            st.setdefault("fail", [])
            return st
        except Exception:
            print(f"[runner] state 文件损坏, 备份后重建: {path}", file=sys.stderr)
            os.replace(path, path + ".corrupt")
    return {"ok": [], "fail": []}


def save_state(path, state):
    json.dump(state, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def run_serial(units, sleep=3.0, maxseconds=3600, state_path="run-state.json",
               label="runner", start_from=None):
    """串行执行 units；返回退出码 0（全部完成/到点优雅停）或 43（429 熔断）。"""
    state = load_state(state_path)
    if start_from:
        ids = [u[0] for u in units]
        if start_from in ids:
            units = units[ids.index(start_from):]

    t0 = time.monotonic()
    ran = 0
    n = len(units)
    for i, (jid, cmd) in enumerate(units):
        if jid in state["ok"]:
            print(f"[{label}] 跳过已完成: {jid}")
            continue
        if i > 0 and time.monotonic() - t0 > maxseconds:
            print(f"[{label}] 达到 --maxseconds={maxseconds}s, 优雅停止; 下次断点: {jid}")
            break
        shown = cmd if isinstance(cmd, str) else " ".join(cmd)
        print(f"[{label}] ({i + 1}/{n}) {shown}", flush=True)
        p = subprocess.run(cmd, shell=isinstance(cmd, str))
        if p.returncode == 0:
            state["ok"].append(jid)
            if jid in state["fail"]:
                state["fail"].remove(jid)
        elif p.returncode == 43:
            if jid not in state["fail"]:
                state["fail"].append(jid)
            save_state(state_path, state)
            print(f"[{label}] 退出码 43 = 429 风暴（宪法第六条）。立即停止, 措施:")
            print("  1) 停止一切写入;  2) scripts/probe-429.sh <任意源图> 低频探测;")
            print("  3) RECOVERED 后原样续跑（单进程 + 页间隔, 禁止报复性并发）")
            return 43
        else:
            if jid not in state["fail"]:
                state["fail"].append(jid)  # 去重: 重试失败不重复记（第十三条, 状态覆盖语义）
            print(f"[{label}] 项 {jid} 失败 (rc={p.returncode}), 记入 state, 继续", flush=True)
        save_state(state_path, state)
        ran += 1
        if i < n - 1:
            time.sleep(sleep)

    save_state(state_path, state)
    print(f"[{label}] 本次执行 {ran} 项 / 累计失败 {len(state['fail'])} 项")
    if state["fail"]:
        print(f"[{label}] 失败清单: {state['fail']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="单进程前台串行调度器")
    ap.add_argument("--jobs", required=True, help="任务清单文件, 每行一个 {id}")
    ap.add_argument("--cmd", required=True, help='命令模板, {id} 为占位符')
    ap.add_argument("--sleep", type=float, default=3.0, help="项间隔秒（宪法第三条）")
    ap.add_argument("--maxseconds", type=int, default=3600, help="单次前台接力时长上限")
    ap.add_argument("--state", default="run-state.json")
    ap.add_argument("--start-from", default=None, help="从该 id 起跑（含）")
    a = ap.parse_args()

    ids = []
    for line in open(a.jobs, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            ids.append(s)
    if not ids:
        raise SystemExit("runner: jobs 清单为空")

    units = [(jid, a.cmd.replace("{id}", jid)) for jid in ids]
    sys.exit(run_serial(units, a.sleep, a.maxseconds, a.state, start_from=a.start_from))


if __name__ == "__main__":
    main()
