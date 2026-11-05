#!/usr/bin/env bash
# figforge :: complete.sh —— 完成协议收尾（宪法第十一条）
#
# 角色完成本棒任务的三步（宪法第十一条）:
#   ① 写好 handoff:  python3 scripts/handoff.py send --project <名> --from <我> --to <下一棒> ...
#   ② 删除 .work/:   可自行 rm -rf .work; complete 会自动再清一遍（幂等）
#   ③ 交付快照:      bash scripts/complete.sh [--project <名>]
#
# complete.sh 行为:
#   1) --project 给出且非 --force 时, 校验 project/<名>/handoff.md 已有 SEND 记录,
#      未写交接拒绝打包（第十一条③: 交接先行）;
#   2) 删除 figforge/.work/（临时工作区整目录清理; --keep-work 仅调试保留）;
#   3) 把整个 figforge/ 打包为 .tar.gz（排除 .work / __pycache__ / *.pyc / *.tar.gz）,
#      落 --out 目录（默认 $FIGFORGE_OUT, 再默认 /home/z/my-project/download/）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${FIGFORGE_OUT:-/home/z/my-project/download}"
NAME="figforge"
PROJECT=""
KEEP_WORK=0
FORCE=0

usage() {
  cat <<'EOF'
figforge :: complete.sh —— 完成协议收尾（宪法第十一条）

用法:
  complete.sh [--project <名>] [--out <目录>] [--name <包名>] [--keep-work] [--force]

角色完成本棒任务的三步:
  ① 写好 handoff:  python3 scripts/handoff.py send --project <名> --from <我> --to <下一棒> ...
  ② 删除 .work/:   可自行 rm -rf .work; complete 会自动再清一遍（幂等）
  ③ 交付快照:      bash scripts/complete.sh [--project <名>]

参数:
  --project <名>  校验 project/<名>/handoff.md 已有 SEND 记录（未写交接拒绝打包）
  --out <目录>    包落点（默认 $FIGFORGE_OUT 或 /home/z/my-project/download/）
  --name <包名>   包基础名（默认 figforge → figforge-<时间戳>.tar.gz）
  --keep-work     调试用: 保留 .work/ 不清理
  --force         跳过 handoff 校验
EOF
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)   PROJECT="${2:?--project 需要项目名}"; shift 2 ;;
    --out)       OUT="${2:?--out 需要目录}"; shift 2 ;;
    --name)      NAME="${2:?--name 需要包名}"; shift 2 ;;
    --keep-work) KEEP_WORK=1; shift ;;
    --force)     FORCE=1; shift ;;
    -h|--help)   usage ;;
    *) echo "complete.sh: 未知参数 $1（--help 看用法）" >&2; exit 1 ;;
  esac
done

[ -f "$ROOT/CONSTITUTION.md" ] || {
  echo "complete.sh: 未找到 $ROOT/CONSTITUTION.md —— 请在 figforge 仓库内运行" >&2
  exit 1
}

# ---- 1) handoff 校验（第十一条: 未写交接不得打包） ----
if [ -n "$PROJECT" ] && [ "$FORCE" -eq 0 ]; then
  hp="$ROOT/project/$PROJECT/handoff.md"
  [ -f "$hp" ] || hp="$PROJECT/handoff.md"   # 允许直接传项目路径
  if [ ! -f "$hp" ]; then
    echo "[complete] ✗ 未找到交接板: $hp" >&2
    echo "  先写 handoff（第十一条①）: python3 scripts/handoff.py send --project $PROJECT \\" >&2
    echo "      --from <我> --to <下一棒> --send '交付了什么/位置'" >&2
    exit 2
  fi
  if ! grep -q -- "- SEND:" "$hp"; then
    echo "[complete] ✗ $hp 尚无 SEND 记录 —— 先 handoff.py send 再 complete（第十一条）" >&2
    exit 2
  fi
  echo "[complete] ✓ handoff 交接板已有 SEND 记录: $hp"
elif [ -n "$PROJECT" ]; then
  echo "[complete] △ --force: 跳过 handoff 校验"
fi

# ---- 2) 清理临时工作区（第十一条②: .work 随时可删, 临时内容不进交付包） ----
if [ "$KEEP_WORK" -eq 1 ]; then
  echo "[complete] △ --keep-work: 保留 .work/（仅调试用; 正式交付请勿保留）"
elif [ -d "$ROOT/.work" ]; then
  sz="$(du -sh "$ROOT/.work" 2>/dev/null | cut -f1 || true)"
  rm -rf "$ROOT/.work"
  echo "[complete] ✓ 已删除 .work/（${sz:-?}）—— 临时内容不进交付包（第十一条②）"
else
  echo "[complete] ✓ .work/ 不存在, 无需清理"
fi

# ---- 3) 打包 figforge/ → .tar.gz（交付快照） ----
mkdir -p "$OUT"
stamp="$(date +%Y%m%d-%H%M%S)"
pkg="$OUT/${NAME}-${stamp}.tar.gz"
tar --exclude='.work' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='*.tar.gz' --exclude='.DS_Store' \
    -czf "$pkg" -C "$(dirname "$ROOT")" "$(basename "$ROOT")"
echo "[complete] ✓ 交付快照: $pkg ($(du -h "$pkg" | cut -f1))"
echo "[complete]   内容 = figforge/ 全仓库（CONSTITUTION + AGENTS + packs + roles + scripts + project/ 产物）"
echo "[complete] 完成协议已履行（第十一条）: handoff → 清 .work → 打包"
