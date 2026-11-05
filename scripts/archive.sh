#!/usr/bin/env bash
# figforge :: archive.sh —— 阶段归档（宪法第一条）
# 用法:
#   archive.sh                # 自动备份: project/ 全部内容（排除各项目 src/, 第一条①）
#                             # 包名 project-<时间戳>.tar.gz → /home/z/my-project/backup/
#   archive.sh project        # 同上（显式模式字）
#   archive.sh <产物目录>     # 归档指定产物目录（兼容旧用法）
#   archive.sh <产物目录> --final
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BK=/home/z/my-project/backup
FN=/home/z/my-project/final
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BK"

# ---- 模式一: project/ 自动备份（宪法第一条①: 只备 project/, 排除各项目 src/） ----
if [ $# -eq 0 ] || [ "${1:-}" = "project" ]; then
  [ -d "$ROOT/project" ] || { echo "archive.sh: 未找到 $ROOT/project" >&2; exit 1; }
  out="$BK/project-${stamp}.tar.gz"
  tar -czf "$out" -C "$ROOT" \
      --exclude='project/*/src' --exclude='*/src' \
      project
  echo "[archive] project/ 自动备份: $out ($(du -h "$out" | cut -f1))"
  echo "[archive] 范围 = project/ 全部内容, 排除 project/<名>/src/（原图不入备份, 第一条①）"
  echo "[archive] backup/ 当前归档数: $(ls -1 "$BK" | wc -l)"
  exit 0
fi

# ---- 模式二: 指定产物目录（兼容旧用法） ----
src="${1:?usage: archive.sh [project] | <dir> [--final]}"
mode="${2:-}"
[ -d "$src" ] || { echo "archive.sh: 目录不存在: $src" >&2; exit 1; }

name=$(basename "$src")
out="$BK/${name}-${stamp}.tar.gz"
tar -czf "$out" -C "$(dirname "$src")" "$name"
echo "[archive] $out ($(du -h "$out" | cut -f1))"
echo "[archive] backup/ 当前归档数: $(ls -1 "$BK" | wc -l)"

if [ "$mode" = "--final" ]; then
  mkdir -p "$FN"
  tar -czf "$FN/${name}-${stamp}.tar.gz" -C "$(dirname "$src")" "$name"
  echo "[archive] final 同步: $FN/${name}-${stamp}.tar.gz"
fi
