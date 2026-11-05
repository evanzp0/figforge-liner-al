# FIGFORGE CONSTITUTION — 图文数字化流水线宪法（v3.6）

> 本文档是 figforge 工作流的最高行为准则与**唯一入口**（第十条），**只写强制规则**。
> 条款背后的背景与教训一律放在 `README.md`「背景与教训」章节（人类读物，
> 执行流程无需阅读，节约 tokens）。
> 冲突裁决：本宪法 > `AGENTS.md` > `packs/*/workflow.md` > `roles/*.prompt` > 临场约定。

**就位顺序（第十条）**：读本文件 → 按第十条进入 `AGENTS.md` → 由 AGENTS.md 检索
到 packs / roles / scripts → 输出可用流程清单 → 开工。

**条款索引**：第零条 技能优先 / 第一条 归档 / 第二条 计划与恢复 / 第三条 单进程前台串行 /
第四条 setsid / 第五条 `$` 替换禁令 / 第六条 429 熔断 / 第七条 几何与版式保真 /
第八条 字体保真 / 第九条 交付自检 / 第十条 单一入口与就位输出 /
第十一条 `.work` 临时工作区与完成协议 / 第十二条 经验沉淀（project/notes）/
第十三条 无日志原则 / 附 交接协议

---

## 第零条 · 技能优先

1. 文本转录与 SVG 重绘优先使用 `skills/image-ocr-svg-redraw/` 的方法与脚本
   （crop_zoom.py 分块放大、网格量测、渲染自检）。
2. 禁止跳过"分块放大逐段核对"直接看整图转录。
3. 转录产物只允许"原文内容 + 原文图形"。判断标准：**这个元素印刷在纸面上吗？**
   不在就不写（禁止元说明、页码页眉复刻、尾部 `---` 分隔线、纠正原文标点）。

## 第一条 · 归档铁律

1. **自动备份范围**：每次自动备份只针对 `project/` 目录里的内容
   （dest 最终件、plan/handoff/run-state、全局经验库 notes/ 等），
   **不包括具体项目下的 `src/` 目录**（原图不入备份，可从源重取）；
   执行 `bash scripts/archive.sh`（无参数）即按此范围归档到
   `/home/z/my-project/backup/`（包名 `project-<时间戳>.tar.gz`）。
2. **批后自动备份 + 自动接力**：每处理完一批原图（batch 一段，
   `--maxseconds` 优雅停）自动执行一次 `scripts/archive.sh` 备份，
   随后**自动继续处理下一批，无需人工接力**，直到全部单元完成、
   429 熔断（第六条）或连续无进展止损（失败项重试一轮仍无新完成即停）。
3. 最终交付物执行 `scripts/archive.sh <目录> --final`，同步到 `/home/z/my-project/final/`。
4. spec JSON、对比图等中间产物与最终件同等归档——它们是复现的唯一起点。

## 第二条 · 计划与恢复

1. 批量开始前必须有 `plan.md`（`scripts/batch.py` 首跑自动生成；
   手动批量用 `scripts/plan.py init --ids ...`）。
2. 每完成一项立即核销（`plan.py done <id>`）。
3. 中断恢复先 `plan.py next`，禁止凭记忆续跑。
4. 执行级断点由 `run-state.json` 双保险记录（batch.py / runner.py 自动维护）。

## 第三条 · 只用单进程前台串行（最高优先级）

1. 禁止多线程/多协程/多 worker 并发调用 API；只允许单个进程在前台串行处理。
2. 批量统一走 `scripts/batch.py --project <项目名>`：内部实现串行 + 页间隔
   （`--sleep`）+ `--maxseconds` 优雅停止（做完当前页即停）+ **自动接力**
   （每段结束自动备份 project/ 并续跑下一批，第一条②；禁止并发替代接力）。
3. pack 脚本一律"一次调用只处理一页"（或一个 spec），批量语义只在 batch/runner 层。

## 第四条 · 后台任务必须 setsid

1. 确需脱离会话的后台任务，必须 `(setsid <cmd> > run.log 2>&1 < /dev/null &)`。
2. 有替代方案时一律选用第三条的前台分块模式。

## 第五条 · `$` 替换禁令

1. 凡替换内容可能含 `$`（数学公式、LaTeX、代码），必须用函数替换：
   `str.replace(search, () => replacement)`；禁止直接传字符串。
2. 本仓库 HTML 拼装一律在 Python 端完成（`build_html.py`，字面替换无此坑）；
   禁止浏览器端 JS 直接拼接含 `$` 的内容。
3. 批处理运行期间禁止并行执行"全局修补/重建"类脚本；修改共享文件先停批，改完再恢复。

## 第六条 · 429 熔断与低频探测

1. pack 脚本检测到 429 风暴（账号级共享配额限流）→ 以**退出码 43** 退出；
   batch.py / runner.py 收到 43 立即停批。严禁换通道接着打、严禁硬重试。
2. 停批后：**停止一切写入** → `scripts/probe-429.sh <任意源图>` 低频探测
   （≥9 分钟间隔）→ 输出 RECOVERED 才允许恢复。
3. 恢复后按第三条原样续跑（state 自动跳过已完成项），禁止报复性并发补进度。

## 第七条 · 几何与版式保真

1. **先量测后动笔**：顶点/端点坐标必须来自网格读数（crop_zoom.py --grid）或
   直线抗差拟合，禁止目测估值直接画。
2. 图中数学关系（求和/平行/垂直/相切）必须在重绘中成立，作为交叉校验。
3. **对比闭环**：每轮渲染必须人工查看 compare 对比图并逐项核对（箭头方向、
   相对长度、标签位置、线宽层级），通常 2-3 轮收敛；未看对比图不得宣布完成。
4. 坐标系 = 源图像素、y 轴向下；印刷正文 text 基线对齐、数学符号 math 中心对齐。
5. **版式保真**：要交付的不只是文字与图，还有版式——原页结构（并排图行/
   图文混排/图注带/标题对齐/段首缩进）必须在最终 HTML 逐项复刻；版式语义由
   转录槽表达（pack-1 约定：相邻插图槽 = 并排行，`|aside` = 左图右文）；
   验收与第 3 款同款对比闭环（渲染件 vs 原页逐项对照）。

## 第八条 · 字体保真

1. 主档 SVG 字形转路径（`svg.fonttype="path"`，不依赖查看端字体），发布到
   `dest/img/<page>.svg`（多图页 `<page>-fig<i>.svg`，单图页 `<page>.svg`；仅 jpg→svg
   重绘流程才有此文件）；可编辑版 `<name>_text.svg`（`fonttype="none"`）与 300dpi PNG 副本存
   `.work/<项目>/pack2/svg/` 随归档（复现用，不进 dest）。
2. 字体方案：正文 Liberation Serif + 数学 STIX（`mathtext.fontset="stix"`）。
3. PNG 300dpi 副本随归档；SVG 根元素 width/height 必须为像素整数且与 viewBox 等比。

## 第九条 · 交付自检

逐项核对，不通过不放行：

- [ ] dest/ 只有最终件：`<page>.html`（pack-1/3：公式已渲染、插图相对引用
      `img/`）+ `img/<page>.jpg`（pack-1 插图裁剪，多图页 `-fig<i>`）+
      `img/<page>.svg`（pack-2 重绘主档，仅 jpg→svg 重绘流程存在，多图页 `-fig<i>`）；
      中间产物（text.md / figures.json / crops / spec / 四件套 / manifest）在
      `.work/<项目>/` 且已随批归档
- [ ] 无占位残留（`{{FIG`、`TODO`、`XXX`、`【】`）
- [ ] compare 对比图已人工查看通过（第七条）
- [ ] 文字与原图逐段核对过（第零条）
- [ ] 归档完成（第一条）、plan.md 已核销（第二条）
- [ ] handoff.md 已写交接（见附录；交接板每 发→收 只一条，第十三条）
- [ ] 经验已沉淀（第十二条：本棒有已解决的错误 → `notes.py add`；无则跳过）
- [ ] 无流水账/日志残留（第十三条：任何文件不随轮次增长）
- [ ] 完成协议已履行：`.work/` 已清理、`scripts/complete.sh` 已打包交付快照（第十一条）

## 第十条 · 单一入口与就位输出

1. **入口只能有一个**：一切执行从 `constitution.md`（本文件）开始，由它进入
   `AGENTS.md`，再由 AGENTS.md 检索到 packs / roles / scripts；
   禁止从 README、workflow.md、脚本或任何其他文件直接进入执行
   （README 仅供人类，不属于执行路径）。
2. 解析完 `CONSTITUTION.md` 与 `AGENTS.md` 后，**必须先输出可用流程清单**
   ——运行 `bash scripts/forge.sh list`（与 AGENTS.md「可用流程清单」章节同源），
   向调用方展示 packs / 阶段 / 角色 / 工具，然后才开始任何工作；
   清单是就位凭证，未输出清单不得开工。
3. 其他文档不得宣称存在第二入口；两处入口描述不一致时，以
   CONSTITUTION.md → AGENTS.md 链为准，先停下核对再继续。

---

## 第十一条 · 临时工作区 `.work` 与完成协议（complete）

1. **临时内容只进 `.work`**：一切临时产物（放大切片、网格量测图、中间 JSON、
   探测输出、日志、草稿）只允许写入 `figforge/.work/`；各 pack 的中间处理文件
   （text.md、figures.json、crops、spec、四件套、manifest 等）同属临时产物，
   写入 `.work/<项目>/pack<N>/` 对应子目录（随批归档, 复现起点）；临时安装的工具
   （Python 包、字体、外部脚本、CLI）只允许装到 `figforge/.work/tools/`
   （用 `PYTHONPATH` / `PATH` 引用）。禁止把临时内容散落在仓库其他位置或 `/tmp`。
2. **`.work` 随时可删**：最终产物只认 `project/<名>/dest/`（归档见第一条）——
   书页 HTML 公式离线可渲染、插图相对引用 `dest/img/`（最终件同仓：
   `<page>.html + img/` 即完整交付单元），不引用 `.work` 中间件。
   `.work` 里还要用的内容必须先转为正式产物或归档，再清理；交接状态只认
   handoff 交接板（附录），禁止把交接信息藏在 `.work` 里。
3. **完成协议**：pack 中一个角色完成本棒任务时，按序收尾：
   ① 写好 handoff：`scripts/handoff.py send`（附录）；
   ② 经验沉淀：本棒遇错且已解决 → `scripts/notes.py add`（第十二条；无则跳过）；
   ③ 删除 `.work/`（角色可自行删；complete 会自动再清一遍，幂等）；
   ④ 调用 `bash scripts/complete.sh [--project <名>]`：校验 handoff 已写 →
   删除 `.work/` → 把整个 `figforge/` 打包为 `.tar.gz` 交付快照（默认落
   `/home/z/my-project/download/`，`--out` 可改；`--no-project` 可排除
   `project/` ——交付快照不含项目工作区，产物另行按第一条归档）。
   未写 handoff 时 complete 拒绝打包（`--force` 仅限调试）。
4. **先自检后打包**：第九条自检全部通过才允许调用 complete；打包即交付快照，
   打包后仓库再有改动须重新 complete 生成新快照。
5. **`project/` 空基线**：仓库基线 `project/` 为空目录——其中任何文件/目录
   （项目工作区 `project/<名>/`、全局经验库 `project/notes/`）只能由 scripts
   （`forge.sh new`、`batch.py`、`handoff.py`、`notes.py` 等）与流程角色运行时
   生成，禁止手工预置或遗留非流程产物；`bash scripts/forge.sh clean` 一键清空
   `project/` 重置工作区（清空有价值的产物前先 `archive.sh` 备份, 第一条）。

---

## 第十二条 · 经验沉淀（project/notes）

1. **触发条件**：流程处理完当前项目收尾时，若本棒处理过程中**遇到过错误且已解决**，
   对应角色必须把经验沉淀到 `project/notes/notes_<角色>.md`（如 `notes_operator.md`）；
   一切顺利则不写（不凑数）。
2. **位置与格式**：经验库全局一份 `figforge/project/notes/`（跨项目复用），
   每角色一个 `notes_<role>.md`。**经验库不是日志**（第十三条）：按现象去重合并、
   一条经验一个条目，**只写 现象 / 根因 / 解决 / 预防 / 标签 五要素**；
   **禁止日期、次数、项目等一切统计字段**（“第几次遇到”无检索价值，只会让文件
   越滚越大、白花 token）；同错再现 add 只覆盖刷新解法字段；条目数有上限
   （notes.py 强制，超限先合并同类再写）。
3. **检索**：`notes/` 下由 notes.py 自动维护 `INDEX.md` **检索目录**——
   **每角色一行（文件 + 关键词聚合）**，无现象、无日期、无次数，行数 ≤ 角色数、
   大小恒定，不随经验条数增长；开工接活与排障前先扫 INDEX.md 关键词定位文件，
   再读对应 `notes_<role>.md` 或
   `python3 scripts/notes.py show [--role <我>] [--tag <t>] [--grep 关键词]`
   查同类经验——同类错误二次出现视为违反本条。
4. **时序与归属**：经验沉淀在完成协议（第十一条③）的 handoff 之后、complete 之前
   执行；`notes/` 属于正式仓库内容（不进 `.work`），随 complete 打包进交付快照。

---

## 第十三条 · 无日志原则（禁止流水账）

1. **任何文件不得随运行轮次线性增长**：禁止在仓库任何文件里追加时间序流水
   （运行记录、逐轮日志、内容雷同的重复条目）；文件只存“当前有效的结论/状态”，
   每次更新要么覆盖旧值，要么合并进既有条目。
2. **状态类文件一律覆盖写**：`run-state-*.json`、`*.manifest.json`、
   `probe.json` 等只保留当前状态；`plan.md` 只翻转核销标记，不追加过程记录。
3. **交接是交接板不是日志**（附录）：`handoff.md` 每个 发→收 组合只保留
   最新一条，send 就地更新；batch.py 收尾更新而非逐轮追加 operator 的 SEND。
4. **经验库是知识库不是台账**（第十二条）：`notes_<role>.md` 条目只存五要素，
   无日期、无次数、无项目统计；`INDEX.md` 是**每角色一行的目录**（文件+关键词）——
   禁止把“一行一条经验”的现象清单或日期/次数列搬进 INDEX（那是台账，随经验数
   线性膨胀）；禁止把过程记录、对话摘录、逐页进度搬进经验库。
5. **运行日志只进 `.work`**：如第四条的 `run.log` 必须写 `figforge/.work/`
   （随 `.work` 删除）；禁止把日志留在 `project/`、`dest/` 或仓库根目录。
6. 第九条自检须确认“无流水账/日志残留”；发现违规文件立即合并或删除。

---

## 附 · 交接协议（handoff.md）

1. 每个项目一份 `project/<项目名>/handoff.md`（**交接板**，第十三条），
   角色间交接**只认交接板**：
   - 完成一项立即 `scripts/handoff.py send --project <名> --from <我> --to <下一棒>`
     写入 SEND / STATE / NEXT 三行；同一 发→收 的 send **就地更新**
     （每个 发→收 只保留最新一条，不是日志）；
   - 开工先 `scripts/handoff.py show --project <名> --to <我>` 读取上一棒的 NEXT，
     禁止凭记忆接活。
2. batch.py 每轮批量收尾自动**更新** operator 的 SEND 条目（交接板语义，不逐轮追加）。
3. 只允许更新自己发出的条目，禁止改写他人条目。
4. 角色完成本棒全部任务后，按第十一条完成协议收尾：send 交接 → 清理
   `.work/` → `bash scripts/complete.sh` 打包交付快照。
