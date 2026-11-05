#!/usr/bin/env bash
# figforge :: archive.sh —— 阶段归档（宪法第一条）
# 用法: archive.sh <产物目录> [--final]
#   每完成约 10 份/一阶段执行一次: tar.gz 落 /home/z/my-project/backup/（带时间戳）
#   --final: 另同步一份到 /home/z/my-project/final/（最终交付）
set -euo pipefail

src="${1:?usage: archive.sh <dir> [--final]}"
mode="${2:-}"
[ -d "$src" ] || { echo "archive.sh: 目录不存在: $src" >&2; exit 1; }

BK=/home/z/my-project/backup
FN=/home/z/my-project/final
mkdir -p "$BK"

stamp=$(date +%Y%m%d-%H%M%S)
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
