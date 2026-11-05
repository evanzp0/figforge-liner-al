# AGENTS.md — figforge 智能体调度入口

> 由 `CONSTITUTION.md` 第十条指认：宪法是唯一入口，本文件是唯一下游调度文档。
> **就位两步**：①读完 `CONSTITUTION.md` 全文与本文件；②输出下方「可用流程清单」。
> 两步未完成前不得开始任何工作（第十条）。

---

## 可用流程清单（就位输出）

解析完 constitution.md 与本文件后，**先原样输出本清单**（或运行
`bash scripts/forge.sh list` 生成同款）再开工：

### 流程（packs）—— 目录驱动批量，统一入口 `batch.py`

| pack | 作用 | 阶段 `--stage`（默认加粗） | 产物落点（dest 只放最终件, 中间件在 `.work/<名>/`） |
|---|---|---|---|
| `split-text-image` | 图文分离：整页转录 → 书页 HTML（公式已渲染, 插图引用 img/） | **detect**（插图检测裁剪）/ html（排版） | `dest/<page>.html + dest/img/<page>.jpg`; 中间件 `.work/<名>/pack1/<page>/` |
| `px2svg` | 像素图重绘 SVG：量测 → matplotlib 引擎 → 对比验收 | **redraw**（渲染 specs/ 全部 spec） | `dest/img/<page>.svg`（多图页 `-fig<i>`, 仅重绘流程）; 四件套在 `.work/<名>/pack2/svg/` |
| `html-svg` | 合用：整页 HTML + 插图引用重绘 SVG | **compose**（逐页编排） | `dest/<page>.html`（插图引用 img/）+ manifest 入 `.work/<名>/pack3/` |

批量命令（按需三选一，`<名>` 为项目名）：

```bash
python3 scripts/batch.py --project <名> --pack split-text-image [--stage html]
python3 scripts/batch.py --project <名> --pack px2svg      [--pages 0107,0138]
python3 scripts/batch.py --project <名> --pack html-svg
```

### 角色（roles/*.prompt，交接只认 `project/<名>/handoff.md`）

- `operator` 批量调度、归档、断点恢复、429 熔断（一/二/三/四/六条）
- `transcriber` 整页转录与版式槽语义（pack-1 文本线，第零条红线、第七条⑤）
- `figure-artisan` 插图量测与重绘 spec + 渲染验收（七/八条）
- `compositor` 合成与交付自检（pack-1/3、第九条、第七条⑤版式对照）

### 工具（scripts/ 与 packs 内脚本）

- `forge.sh`：list（输出本清单）/ doctor（依赖自检）/ new（建项目）
  / clean（清空 project/ 重置工作区, 第十一条⑤）/ install（组合安装）
- `batch.py`（批量入口, 段末自动备份接力, 第一条②）/ `runner.py`（串行核心）
  / `plan.py`（计划核销）
- `handoff.py`（交接板: 每 发→收 一条, send 就地更新, 附录+第十三条）
  / `archive.sh`（归档: 无参数 = 自动备份 project/ 排除各项目 src/, 第一条①）
  / `probe-429.sh`（限流探测）
- `notes.py`（经验库, 第十二/十三条: add 沉淀（同现象自动合并）/ show 检索
  / reindex 重建 INDEX.md）
- `complete.sh`（完成协议, 第十一条: 校验 handoff → 清 `.work` → 打包 figforge 为 .tar.gz）
- pack 脚本：`detect_figures.py`、`build_html.py`、`mpl_redraw.py`、`compose_page.py`
  （pack 脚本只做单页，批量语义只在 batch.py —— 宪法第三条）

---

## 就位后的执行顺序

1. **自检**：`bash scripts/forge.sh doctor`（依赖缺失先补齐）。
2. **建/进项目**：`bash scripts/forge.sh new <pack> <项目名>`，
   原图放入 `project/<项目名>/src/`（页 id = 文件名去扩展名）。
3. **认领角色**（上方清单）：读对应 `roles/<角色>.prompt`；
   pack 级操作手册在 `packs/<pack>/workflow.md`。
4. **批量干活**（宪法第三条）：一切批量走 `batch.py`（见上方清单命令）；
   单页调试才直接调 pack 脚本。
5. **交接只认交接板**（附录协议 + 第十三条）：完成一项立即
   `python3 scripts/handoff.py send --project <名> --from <我> --to <下一棒>`
   （同一 发→收 就地更新, 不逐次追加）；
   开工先 `handoff.py show --project <名> --to <我>`；
   收工 `plan.py done`（批量归档由 batch.py 每段自动执行, 第一条②; 最终交付另
   `scripts/archive.sh <目录> --final`）。
6. **临时区**（第十一条）：临时产物一律写 `figforge/.work/`
   （临时工具装 `.work/tools/`）。
7. **经验沉淀与完成**（第十二/十一条）：排障与开工接活前先
   `python3 scripts/notes.py show [--role <我>] [--grep 关键词]` 查同类经验；
   本棒全部完成后按序——有已解决错误先 `notes.py add` 沉淀（第十二条）→
   `bash scripts/complete.sh --project <名>`（第十一条：自动清 `.work` 并打包
   交付快照，notes/ 一并入库）。

禁止事项速记：并发调 API（三）、绕过对比图交付重绘图或版式（七）、JS `replace` 直拼
含 `$` 内容（五）、429 硬重试（六）、交付前不自检（九）、凭记忆接活（附录）、
未输出流程清单就开工（十）、临时内容写出 `.work/` 或未写 handoff 就 complete（十一）、
排障不查 notes 或同类错误二次出现（十二）、写流水账/逐轮日志或运行日志出 `.work`（十三）。

## 项目工作区结构

> **基线约定（第十一条⑤）**：仓库基线 `project/` 为空——项目工作区与 notes/ 经验库
> 全部由 scripts/roles 运行时生成；`bash scripts/forge.sh clean` 一键清空重置。

```
project/<项目名>/
├── src/                        原图（批量输入）
├── dest/                       ★ 只有最终产物
│   ├── <page>.html             书页 HTML 最终件（公式已渲染, 插图相对引用 img/, 离线可开）
│   └── img/                    插图最终件: <page>.jpg（pack-1 裁剪, 多图页 -fig<i>）;
│                               <page>.svg（pack-2 重绘主档, 仅 jpg→svg 重绘流程存在）
├── handoff.md                  角色交接板（每 发→收 只留最新一条, 第十三条）
├── plan.md / run-state-<stage>.json

figforge/.work/<名>/            ★ 全部中间产物（随批归档, complete 清理, 第十一条）
├── pack1/<page>/               text.md / figures.json / crops/ / figure-map.json
├── pack2/specs/                <page>-fig<i>.spec.json
├── pack2/svg/                  <page>-fig<i>.{svg,_text.svg,png,-compare.png}
└── pack3/                      <page>.manifest.json

project/notes/                  全局经验库（与各项目目录平级, 第十二/十三条）
├── notes_<role>.md             每角色一个错误→解决经验库（五要素条目, 无日期/次数, 非日志）
└── INDEX.md                    检索目录（每角色一行: 文件+关键词, notes.py 自动维护, 非日志）
```
