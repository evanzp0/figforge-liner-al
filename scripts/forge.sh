#!/usr/bin/env bash
# figforge :: forge.sh —— 安装器与自检（仿 get-swarm-forge）
# 用法:
#   forge.sh list                       # 列出可用 packs
#   forge.sh doctor                     # 依赖自检（python/matplotlib/PIL/字体/z-ai）
#   forge.sh new <pack> <项目名> [--samples x]
#                                       # 创建项目工作区（project/<名>/）;
#                                       # --samples x = 定版随机抽样数（默认 5, 宪法第七条第 6 款③）
#   forge.sh clean                      # 清空 project/（重置工作区; 建议先 archive.sh 备份）
#   forge.sh install <pack> <target>    # 把 pack + 共享运行时 + 宪法组合到目标目录
#     * pack = html-svg 时自动带上依赖的 split-text-image 与 px2svg
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

usage() {
  echo "usage: forge.sh list | doctor | new <pack> <项目名> [--samples x] | clean | install <pack> <target-dir>" >&2
  exit 1
}

# catalog —— 输出可用流程清单（宪法第十条"就位输出"的唯一数据源;
# AGENTS.md「可用流程清单」章节与本输出同源）
catalog() {
  echo "可用流程（packs）—— 目录驱动批量统一入口 batch.py:"
  for d in "$ROOT"/packs/*/; do
    pj="$d/pack.json"
    [ -f "$pj" ] || fail_missing "$pj"
    python3 - "$pj" <<'PYEOF'
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
b = p.get("batch", {})
stages = b.get("stages", [])
mark = lambda s: f"**{s}**" if s == b.get("default_stage") else s
print(f"  {p['pack']}  —  {p.get('title','')}")
print(f"      stage: {' / '.join(mark(s) for s in stages)}   entry: {b.get('entry','')}")
roles = p.get("roles", [])
if roles:
    print(f"      roles: {', '.join(roles)}")
PYEOF
  done
  echo "可用角色（roles/）: operator / transcriber / figure-artisan / compositor"
  echo "可用工具（scripts/ + packs 内脚本）:"
  echo "  forge.sh(list|doctor|new|clean|install)  batch.py  runner.py  plan.py  handoff.py  archive.sh  probe-429.sh  complete.sh  notes.py  calibrate.py"
  echo "  detect_figures.py  build_html.py  mpl_redraw.py  compose_page.py"
  echo "工作区约定: project/ 基线为空 —— 一切内容（项目工作区/notes/）由 scripts 与流程角色运行时生成;"
  echo "  bash scripts/forge.sh clean 一键清空 project/ 重置工作区（清空前按需 archive.sh 备份）"
}

# scaffold <项目目录> [定版抽样数x] —— 项目工作区骨架: src/ + dest/（只放最终件, 第十一条）
#   + handoff.md + plan.md + config.json（layout_samples, 宪法第七条第 6 款③）
scaffold() {
  proj="$1"; samples="${2:-5}"
  mkdir -p "$proj/src" "$proj/dest/img"
  # 定版抽样数 x（calibrate.py 读取; 默认 5, 第七条第 6 款③）
  [ -f "$proj/config.json" ] || printf '{ "layout_samples": %s }\n' "$samples" > "$proj/config.json"
  [ -f "$proj/handoff.md" ] || cat > "$proj/handoff.md" <<'EOF'
# HANDOFF — 角色交接板（非日志, 宪法第十三条）
> 每个 发→收 只保留最新一条, send 就地更新; 开工先读上一棒 NEXT（scripts/handoff.py show）。只允许更新自己发出的条目。
EOF
  [ -f "$proj/plan.md" ] || printf '# PLAN — 新批量任务\n> 宪法第二条: 每完成一项立即核销; batch.py 首跑会自动登记\n\n' > "$proj/plan.md"
}

fail_missing() {
  echo "forge.sh: 缺少必需文件: $1" >&2
  exit 1
}

cmd="${1:-}"; [ $# -gt 0 ] && shift || true
case "$cmd" in
  list)
    catalog
    ;;

  doctor)
    ok=0; bad=0
    chk() { # chk <说明> <命令...>  （第一个参数仅作显示标签, 其余为真实命令）
      label="$1"; shift
      if "$@" >/dev/null 2>&1; then echo "  ✓ $label"; ok=$((ok+1)); else echo "  ✗ $label"; bad=$((bad+1)); fi
    }
    echo "[doctor] 依赖自检:"
    chk "python3"            python3 -c "import sys"
    chk "matplotlib"         python3 -c "import matplotlib"
    chk "numpy"              python3 -c "import numpy"
    chk "Pillow"             python3 -c "import PIL"
    chk "Liberation Serif"   fc-list
    # 单独确认字体名（注意: pipefail 下禁用 grep -q 管道 —— 命中即关管道, fc-list 收 SIGPIPE 误报失败）
    font_hits="$(fc-list 2>/dev/null | grep -i "Liberation Serif" || true)"
    if [ -n "$font_hits" ]; then
      echo "  ✓ Liberation Serif 字体名匹配"; ok=$((ok+1))
    else
      echo "  ✗ Liberation Serif 字体名匹配（重绘 SVG 将回退）"; bad=$((bad+1))
    fi
    if command -v z-ai >/dev/null 2>&1; then
      echo "  ✓ z-ai CLI（pack-1 自动检测可用）"; ok=$((ok+1))
    else
      echo "  △ z-ai CLI 缺失（pack-1 请用 --boxes 手工框, 不影响其他功能）"
    fi
    echo "[doctor] 通过 $ok 项, 缺失 $bad 项"
    [ "$bad" -eq 0 ]
    ;;

  install)
    pack="${1:?usage: forge.sh install <pack> <target-dir>}"
    target="${2:?usage: forge.sh install <pack> <target-dir>}"
    [ -d "$ROOT/packs/$pack" ] || { echo "forge.sh: 未知 pack: $pack" >&2; exit 1; }
    mkdir -p "$target"
    # 共享层: constitution + roles + scripts（对应 swarmforge main 分支的共享 articles/scripts）
    cp -r "$ROOT/CONSTITUTION.md" "$target/"
    cp -r "$ROOT/README.md" "$target/README.md"
    cp -r "$ROOT/roles" "$target/roles"
    rm -rf "$target/scripts"; cp -r "$ROOT/scripts" "$target/scripts"
    chmod +x "$target"/scripts/*.sh "$target"/scripts/*.py 2>/dev/null || true
    # pack 层: html-svg 依赖另两包
    packs_to_copy="$pack"
    if [ "$pack" = "html-svg" ]; then
      packs_to_copy="html-svg split-text-image px2svg"
    fi
    mkdir -p "$target/packs"
    for p in $packs_to_copy; do
      [ -d "$ROOT/packs/$p" ] || fail_missing "packs/$p"
      rm -rf "$target/packs/$p"
      cp -r "$ROOT/packs/$p" "$target/packs/$p"
    done
    # 项目工作区: 空基线（第十一条: 一切内容由 forge.sh new / batch / roles 运行时生成）
    mkdir -p "$target/project"
    echo "[forge] 已组合 pack '$pack' → $target"
    echo "[forge] project/ 为空基线（无预置项目）; 建项目: bash scripts/forge.sh new $pack <项目名>"
    echo "[forge] 建后: cp 原图 → project/<项目名>/src/ 后跑: python3 scripts/batch.py --project <项目名> --pack $pack"
    ;;

  clean)
    # 清空 project/（重置工作区 —— project/ 基线为空, 一切内容由 scripts/roles 生成）
    pj="$ROOT/project"
    if [ -d "$pj" ]; then
      entries="$(ls -A "$pj" 2>/dev/null || true)"
      if [ -n "$entries" ]; then
        echo "[forge] clean 清空 $pj:"
        echo "$entries" | sed 's/^/  - /'
        echo "  （需要保留的项目产物先 archive.sh 备份）"
      fi
      rm -rf "$pj"
      mkdir -p "$pj"
      echo "[forge] ✓ project/ 已清空（基线状态: 空目录）"
    else
      mkdir -p "$pj"
      echo "[forge] ✓ project/ 不存在, 已创建空目录（基线状态）"
    fi
    ;;

  new)
    pack=""; name=""; samples=5
    while [ $# -gt 0 ]; do
      case "$1" in
        --samples) samples="${2:?--samples 需要正整数 x（定版随机抽样数, 宪法第七条第 6 款③）}"; shift 2 ;;
        *) if [ -z "$pack" ]; then pack="$1"; elif [ -z "$name" ]; then name="$1"; fi; shift ;;
      esac
    done
    pack="${pack:?usage: forge.sh new <pack> <项目名> [--samples x]}"
    name="${name:?usage: forge.sh new <pack> <项目名> [--samples x]}"
    case "$samples" in ''|*[!0-9]*|0) echo "forge.sh: --samples 需要正整数 x（默认 5, 宪法第七条第 6 款③）" >&2; exit 1;; esac
    [ -d "$ROOT/packs/$pack" ] || { echo "forge.sh: 未知 pack: $pack" >&2; exit 1; }
    case "$pack" in html-svg) packs_to_copy="html-svg split-text-image px2svg";; *) packs_to_copy="$pack";; esac
    for p in $packs_to_copy; do [ -d "$ROOT/packs/$p" ] || fail_missing "packs/$p"; done
    proj="$ROOT/project/$name"
    if [ -d "$proj" ]; then echo "[forge] 项目已存在: $proj" >&2; exit 1; fi
    mkdir -p "$proj"
    scaffold "$proj" "$samples"
    echo "[forge] 项目 '$name'（$pack）已创建: $proj"
    echo "[forge] 定版抽样数 x=$samples（写入 config.json; 开工 batch.py 自动随机抽 x 张原图定版, 第七条第 6 款③）"
    echo "[forge] 下一步: cp 原图 → $proj/src/ 后跑: python3 scripts/batch.py --project $name --pack $pack"
    ;;

  -h|--help|*)
    usage
    ;;
esac
