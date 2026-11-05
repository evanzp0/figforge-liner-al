# FIGFORGE — 教材扫描页图文数字化工作流（swarmforge 式 packs 架构）

把一批教材/文档扫描图，变成**可编辑文本 + 可复用矢量图**。架构仿
[unclebob/swarm-forge](https://github.com/unclebob/swarm-forge)：
`constitution/` 宪法约束行为，`packs/` 可组合流程包，`roles/` 角色提示，
`scripts/` 共享运行时，`project/<项目名>/` 项目工作区（src → dest、handoff 交接）。

> 执行流程只需读 `CONSTITUTION.md`（唯一入口，第十条）→ `AGENTS.md`（调度与
> 可用流程清单）。本章「背景与教训」是条款的来龙去脉，供人类理解与改进规则，
> **AI 执行流程无需阅读**（节约 tokens）；本 README 不属于执行路径。

## 三个 pack

| pack | 干什么 | 输入 → 输出 |
|---|---|---|
| `split-text-image` | **图文分离**：整页转录成文本并排版成书页 HTML（公式已渲染）；插图裁剪 | `src/` 原图 → `dest/<page>.html + dest/img/<page>.jpg`（最终件）; 中间件 `.work/<名>/pack1/` |
| `px2svg` | **像素图重绘 SVG**：量测 → matplotlib 引擎重绘 → 对比验收（107/138 实战同款） | spec → `dest/img/<page>.svg` 重绘主档（仅重绘流程存在）; 四件套在 `.work/<名>/pack2/svg/` |
| `html-svg` | **合用**：图文分离 + 逐图 SVG 重绘，插图引用重绘主档 | `src/` 原图 → `dest/<page>.html`（最终件）+ manifest 入 `.work/<名>/pack3/` |

## 项目工作区（目录驱动批量）

> **基线约定（第十一条⑤）**：仓库基线 `project/` 为空——下方结构全部由
> scripts/roles 运行时生成（`forge.sh new` 建项目、`batch.py`/`handoff.py`/`notes.py`
> 写产物与状态）；`bash scripts/forge.sh clean` 一键清空 `project/` 重置工作区。

```
figforge/project/<项目名>/
├── src/                          # 一批原图（批量输入; 页 id = 文件名去扩展名）
├── dest/                         # ★ 只有最终产物（<page>.html + img/ 即完整交付单元）
│   ├── <page>.html               #   书页 HTML（公式已渲染, 插图相对引用 img/, 离线可开）
│   └── img/                      #   <page>.jpg 裁剪（多图页 <page>-fig<i>.jpg）;
│                                 #   <page>.svg 重绘主档（仅 jpg→svg 重绘流程存在）
├── handoff.md                    # 角色交接板（SEND/STATE/NEXT, 附录协议; 每 发→收 只一条, 第十三条）
├── plan.md                       # 任务清单（batch 首跑自动生成）
└── run-state-<stage>.json        # 执行级断点（自动维护）

figforge/.work/<名>/               # ★ 全部中间产物（随批归档, complete 清理, 第十一条）
├── pack1/<page>/                  #   text.md / figures.json / crops/ / figure-map.json
├── pack2/specs|svg/               #   spec + 四件套/对比图
└── pack3/                         #   <page>.manifest.json
```

`figforge/project/notes/`（全局经验库，与各项目目录平级，第十二/十三条）：
`notes_<role>.md` 每角色一个“错误 → 解决”经验库（**非日志**：按现象去重合并，
只存 现象/根因/解决/预防/标签 五要素，无日期/次数/项目统计，条目数有上限），
`INDEX.md` 由 `scripts/notes.py` 自动维护（**每角色一行的检索目录：文件+关键词**，
大小恒定，不随经验条数增长）。

```
figforge/
├── CONSTITUTION.md            # 宪法 v3.5（唯一入口, 只写强制规则; 第十条单一入口+就位输出, 第十一条 .work+complete, 第十二条 notes 经验沉淀, 第十三条无日志原则）
├── AGENTS.md                  # 唯一下游调度入口（可用流程清单）
├── packs/…                    # 三个流程包（pack.json / workflow.md / scripts/）
├── roles/                     # operator / transcriber / figure-artisan / compositor
├── .work/                     # 临时工作区（第十一条; 运行期生成, 临时工具在 .work/tools/, 交付前自动删除）
├── scripts/
│   ├── forge.sh               #   list / doctor / new <pack> <项目名> / install
│   ├── batch.py               #   ★ 目录驱动批量入口（扫描 src/ 批量转换）
│   ├── runner.py              #   串行执行核心（--maxseconds 优雅停 / 断点 / 43 熔断）
│   ├── handoff.py             #   handoff.md 交接板写入与查看（每 发→收 一条）
│   ├── plan.py  archive.sh  probe-429.sh  notes.py
│   └── complete.sh            #   ★ 完成协议（第十一条: 校验 handoff → 清 .work → 打包 .tar.gz）
└── examples/
```

## 快速开始（目录驱动）

> 本节仅供人类速览；AI 执行路径是 constitution.md → AGENTS.md（第十条）。

```bash
# 0) 就位（宪法第十条）: 输出可用流程清单 + 自检; 建项目（src/ 放入一批原图）
bash scripts/forge.sh list
bash scripts/forge.sh doctor
bash scripts/forge.sh new split-text-image mybook
cp ~/scans/*.png project/mybook/src/

# 1) pack-1 批量: 插图检测裁剪（逐页串行, 自动 plan/state/handoff）
python3 scripts/batch.py --project mybook --pack split-text-image
#    转录（transcriber 角色, 宪法第零条分块核对）→ .work/<名>/pack1/<page>/text.md
# 1') 排版: 对已转录页批量生成书页 HTML
python3 scripts/batch.py --project mybook --pack split-text-image --stage html

# 2) pack-2 批量: 渲染 .work/<名>/pack2/specs/ 下全部 spec（figure-artisan 供 spec）
python3 scripts/batch.py --project mybook --pack px2svg

# 3) pack-3 批量: 逐页编排 HTML + 内嵌 SVG
python3 scripts/batch.py --project mybook --pack html-svg

# 交接板与断点
python3 scripts/handoff.py show --project mybook
python3 scripts/plan.py show --file project/mybook/plan.md
scripts/archive.sh project/mybook/dest --final

# 重置工作区: 清空 project/（一切内容下次由 scripts/roles 重新生成; 第十一条⑤）
# 建议先备份需要保留的产物: scripts/archive.sh project/<名>/dest
bash scripts/forge.sh clean

# 收尾沉淀经验（宪法第十二条）: 本棒遇错且已解决时；排障/接活先扫 INDEX.md 再 notes.py show
python3 scripts/notes.py add --role operator \
    --symptom "现象一句话" --fix "怎么解决的" --tags "标签1,标签2"

# 4) 完成协议（宪法第十一条）: 写好 handoff 后, 清 .work 并打包交付快照
bash scripts/complete.sh --project mybook
```

`batch.py` 常用参数：`--stage`（见各 pack）、`--pages 0101,0107`（子集）、
`--maxseconds 1800`（单次前台时长, 接力续跑）、`--sleep 3`（页间隔）、
`--dry-print`（只打印将执行的命令, 不执行）。

## 宪法要点（全文见 constitution.md）

- **第三条（最高优先级）**：单进程前台串行，批量只走 `batch.py`；
- **第六条**：429 → 退出码 43 熔断 → `probe-429.sh` 低频探测，禁止硬重试；
- **第五条**：含 `$` 的替换必须函数形式；HTML 拼装在 Python 端；
- **第七/八条**：先量测后动笔、必出对比图、双档 SVG、Liberation Serif + STIX；
- **第十一条**：临时内容只进 `.work/`（临时工具进 `.work/tools/`）；角色完成 =
  handoff → 清 `.work` → `complete.sh` 打包交付快照；
- **第十二条**：项目收尾遇错且已解决 → `notes.py add` 沉淀到 `project/notes/`
  （五要素条目, 同现象自动合并, 无日期/次数统计）；排障/接活先扫 `INDEX.md`（每角色
  一行目录）再 `notes.py show` 查同类经验；
- **第十三条**：无日志原则——任何文件不得随运行轮次线性增长；状态类文件覆盖写；
  `INDEX.md` 是每角色一行的目录不是经验清单；notes 条目无日期/次数流水；
  handoff 交接板每 发→收 只一条；运行日志只进 `.work/`；
- **附录**：角色交接只认 `handoff.md` 交接板（SEND/STATE/NEXT）。

## 背景与教训（条款的来龙去脉；AI 执行流程无需阅读本节）

- **第三条 · 8 并发打爆配额**：最初 8 并发 worker 调视觉 API 立刻大量 429，降到
  5、3 仍间歇限流；持续重试曾导致**连续 1.5 小时全部 429**。并发越高，浪费在
  失败与退避上的时间越多，吞吐反而更低。结论：串行单进程 + 页间隔最稳。
- **第五条 · 269 个 HTML 双份注入**：`html.replace(oldCfg, newCfg)` 中替换串含
  `['$','$']`，JS 把 `$'` 当"插入匹配点之后的全部内容"，269 个已生成 HTML 全部
  被注入两份重复内容，且批处理正在写文件放大了事故。结论：含 `$` 一律函数替换；
  本仓库改为 Python 端拼装规避。
- **第六条 · 共享配额没有捷径**：SDK 与 CLI 共用账号级配额，CLI 兜底同样被拒；
  越重试限流窗口越久。结论：退出码 43 熔断 + ≥9 分钟低频探测。
- **第四条 · nohup 静默被杀**：`nohup ... &` 在工具会话结束时被 SIGKILL，
  日志 0 字节、无报错，极易误判脚本有 bug。结论：必须 setsid 完全脱离会话。
- **第七条 · 138 右侧失真打回**：凭目测画的"意思相近的图"顶点误差偏大，整版
  被打回重测。结论：先量测后动笔、对比图是唯一验收凭据。
- **第七条 · 版式丢失打回**：转录只抄了文字，插图一律竖排居中堆叠，纸面的
  "两图并排 + 左图右文"结构全部丢失，整页布局被打回重排；同批右图裁剪框
  偏移半个图宽（y 轴整段截掉）。结论：插槽不只是占位符，是版式指令——
  相邻槽 = 并排、`|aside` = 左图右文；图注随图、样式照原书（正文字号/深色/
  非斜体/图号加粗）；vision 裁剪框必须逐框网格复核（并排小图最易偏小偏移）。
- **第八条 · SVG 字体替换失真**：SVG 只写字体名时，查看端无此字体就替换，
  衬线变无衬线。结论：主档字形转路径 + 可编辑版双档交付。
- **第一条/第二条**：沙箱随时重置、会话随时中断——产物不及时归档、计划不核销，
  就要从头再来。

## 依赖

python3 + matplotlib + numpy + Pillow；可选 `z-ai` CLI（pack-1 自动检测插图框；
`detect_figures.py --boxes` 手工兜底不耗配额）；字体 Liberation Serif / STIX
（`forge.sh doctor` 自检）。临时安装的依赖一律装到 `figforge/.work/tools/`
（第十一条，如 `pip install --target .work/tools <包>`），不污染系统环境。

## 变更记录

- v3.9（2026-11-05）：版式保真入宪——第七条新增第 5 款：原页版式结构（并排图行/
  图文混排/图注带/标题对齐/段首缩进）必须逐项复刻，转录插槽即版式指令（相邻槽 =
  并排行, `|aside` = 左图右文）；build_html 新增 .figrow/.figaside 渲染语义与原版式
  图注（正文字号/深色/非斜体/图号加粗, --text-width 换算图列宽）；transcriber 页面
  清单与 compositor 验收增加"版式对照"；检测后必逐框核对四缘（网格重测重裁）。
  宪法第七条⑤、AGENTS、workflow、roles、pack.json 同步。
- v3.8（2026-11-05）：project/ 空基线——仓库基线 `project/` 为空目录，一切内容
  （项目工作区/notes/ 经验库）只能由 scripts（forge.sh new / batch.py / handoff.py /
  notes.py）与流程角色运行时生成，禁止手工预置（移除预置 project/README.md 与
  历史遗留目录，README 内容并入根 README）；`forge.sh install` 不再预置 example
  项目；新增 `forge.sh clean` 子命令一键清空 project/ 重置工作区。宪法第十一条⑤、
  AGENTS、README 同步。
- v3.7（2026-11-05）：产物契约再收窄——`dest/` 只放最终件：`<page>.html` +
  `img/<page>.jpg`（pack-1 插图裁剪升级为最终件, 多图页 `-fig<i>`），重绘主档改发布到
  `dest/img/<page>.svg`（仅 jpg→svg 重绘流程存在）；HTML 插图槽改为相对引用 `img/`
  （`<page>.html + img/` 即完整交付单元, 不再 base64 内嵌, 发布失败才兑底）；
  dest 下不再出现 transcriber/figure-artisan/compositor 角色子目录（中间件全部
  归位 `.work/<名>/pack{1,2,3}/`）。宪法八/九/十一条、AGENTS、workflows、
  pack.json、forge.sh scaffold、roles 同步。
- v3.5（2026-11-05）：经验库彻底去日志——`INDEX.md` 从“一行一条经验”表改为
  **每角色一行的检索目录**（文件+关键词聚合, 无现象/次数/最近列, 行数≤角色数,
  恒定大小）；`notes_<role>.md` 条目只留 现象/根因/解决/预防/标签 五要素，
  删除 统计（次数/首次/最近/项目）行；`notes.py` 去掉 `--project`；
  新增每角色条目上限（20 条, 超限先合并同类）。宪法十二/十三条同步改写。
- v3.4（2026-11-05）：无日志原则——宪法新增第十三条：任何文件禁止随运行轮次线性
  增长（流水账/逐轮日志/雷同重复条目）；状态类文件一律覆盖写；`handoff.md` 改为
  **交接板**（每 发→收 只保留最新一条, send 就地更新, batch 收尾不再逐轮追加）；
  `notes_<role>.md` 与 `INDEX.md` 改为**按现象去重合并**（一条经验一个条目,
  同错再现只累加统计, 去掉日期/项目流水列）；运行日志（如 `run.log`）显式落
  `.work/`。`notes.py`/`handoff.py` 相应重构, roles/workflows/pack.json 同步。
- v3.3（2026-11-05）：经验沉淀——宪法新增第十二条：项目收尾时遇错且已解决 →
  对应角色在 `project/notes/notes_<role>.md` 提炼经验（全局库, 只追加），
  `notes/INDEX.md` 供检索；新增 `scripts/notes.py`（add/show/reindex, 自动维护
  INDEX.md）；完成协议插入第②步（handoff → notes → 清 `.work` → complete）；
  roles/workflows/故障处置同步。
- v3.2（2026-11-05）：临时工作区与完成协议——宪法新增第十一条：一切临时产物
  只进 `figforge/.work/`（临时工具进 `.work/tools/`）；pack 中角色完成 =
  handoff → 清 `.work` → `complete.sh` 打包交付快照。新增 `scripts/complete.sh`
  （校验 handoff / 清 `.work` / 打包 figforge 为 .tar.gz）；`probe-429.sh`、
  `detect_figures.py` 临时文件改道 `.work/`；workflow/roles 同步；顺手修复
  `forge.sh install` 在大小写敏感文件系统上的 constitution.md 路径。
- v3.1（2026-11-04）：单一入口——宪法新增第十条（constitution.md → AGENTS.md →
  packs/roles/scripts），禁止第二入口；删除 packs/*/project.prompt（与 roles 重复）。
  就位输出——解析完宪法与 AGENTS.md 后必须先输出可用流程清单（forge.sh list 与
  AGENTS.md 同源，pack.json 新增 batch.stages/default_stage）。
- v3.0（2026-11-04）：宪法瘦身——只留强制规则，背景与教训移入 README；
  新增 `project/<项目名>/` 工作区（src/ + dest/<角色>/ + handoff.md 交接台账）；
  新增 `batch.py` 目录驱动批量入口与 `handoff.py`；compose_page 项目化改造。
- v2.0（2026-11-04）：重写宪法（继承六条教训，新增七/八/九条）；建立 packs 架构；
  沉淀 107/138 matplotlib 重绘引擎 `mpl_redraw.py`。
