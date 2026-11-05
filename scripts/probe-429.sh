#!/usr/bin/env bash
# figforge :: probe-429.sh —— 账号级 429 低频探测（宪法第六条）
# 用法: probe-429.sh <任意一张源图> [探测间隔秒, 默认 540]
# 行为: 循环轻量探测; 输出 RECOVERED 才允许恢复批量。
#       等待期间不做任何写入操作（保证断点状态一致 —— 宪法第一条）。
#       探测响应只写 figforge/.work/probe.json（第十一条: 临时内容只进 .work）。
set -u

img="${1:?usage: probe-429.sh <source-image> [interval-sec]}"
interval="${2:-540}"
[ -f "$img" ] || { echo "probe-429.sh: 找不到图片 $img" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/.work"
mkdir -p "$WORK"

echo "[probe] 429 探测启动: 每 ${interval}s 一次（≥9 分钟, 宪法第六条）"
while true; do
  if timeout 90 z-ai vision -p "Reply with the first 5 words you see." \
       -i "$img" -o "$WORK/probe.json" >/dev/null 2>&1; then
    echo "RECOVERED at $(date +%H:%M) —— 允许恢复批量"
    echo "        （按宪法第三条: 单进程前台 + 页间隔; 禁止报复性并发补进度）"
    exit 0
  fi
  echo "still 429 at $(date +%H:%M); ${interval}s 后再探测（等待期间不做任何写入）"
  sleep "$interval"
done
