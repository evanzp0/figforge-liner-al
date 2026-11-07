# workflow — pack-1 `split-text-image`（图文分离）

> 宪法全文见 `constitution.md`；本文件与其冲突时以宪法为准。

## 输入 / 输出（项目工作区; dest 只放最终件, 中间件在 .work/<名>/ —— 第十一条）

```
project/<项目名>/src/<page>.png            原页扫描图
figforge/.work/<名>/pack1/<page>/          中间件（转录与裁剪）
  ↓ ⓪定版 ①转录 ②插图框 ③裁剪 ④排版
figforge/.work/<名>/pack1/<page>/text.md       转录文本（极简 Markdown, 含 {{FIG:n}}）
figforge/.work/<名>/pack1/<page>/figures.json  插图框 + 说明
figforge/.work/<名>/pack1/<page>/crops/figN.jpg 插图裁剪（中间件）
project/<项目名>/dest/<page>.html          ★ 最终件: 书页 HTML（公式已渲染,
                                            插图相对引用 img/, 离线可开;
                                            页面尺寸 = 版心优先 + 人体工程学页框,
                                            项目定版统一, 第七条第 6 款②③）
project/<项目名>/dest/img/<page>.jpg       ★ 最终件: 插图裁剪（多图页 <page>-fig<i>.jpg;
                                            排版时由 build_html 自动发布）
```

dest 交付单元 = `<page>.html + img/`（同仓自洽, 不引用 .work 中间件 —— 第十一条）;
若后续跑 jpg→svg 重绘流程（pack-2）, 才会出现 `dest/img/<page>.svg` 重绘主档,
重排后插图槽改引用该 SVG。

## 步骤

### ⓪ 开工定版（宪法第七条第 6 款③, 强制红线, 转换任何原图之前）

1. 检查 `project/<名>/handoff.md` 是否已有「定版参数」段 + `project/<名>/page-size.json`
   机器锁（`python3 scripts/calibrate.py check --project <名>`）。
2. **未定版**（交接文件不存在或其中未写明转换后 HTML 的页面宽/高、版心、页面
   padding 等内容布局参数）→ 随机选取 x 张原图试测定版：`python3 scripts/calibrate.py
   --project <名>`——x 取 `config.json` 的 layout_samples（**默认 5**; 新建项目时
   `forge.sh new <pack> <名> --samples x` 设定）。**版心优先策略**：
   逐张测算**版心 = 有效内容区（除去留白）的宽 × 高**（页眉/页码带、页缘噪声排除），
   中位数合并为项目统一版心；**页面 padding 全部由人体工程学计算、禁用原图留白**：
   左右 = (820 − 版心宽)/2 严格等距, 上下 = 0.75 × 左右（Tschichold top:outer ≈ 3:4）,
   页高 = 版心高 + 上/下 padding 夹紧 [1.05,1.60]。结果作为**整个项目所有原图转换
   HTML 的统一参数**，覆盖写入 handoff.md「定版参数」段 + page-size.json 机器锁
   （第七条第 6 款③④; `--pages <id,...>` 可显式指定样本集复现/重算）。
3. **已定版禁止重复测算、禁止逐页另取尺寸**——后续所有页面（含第一个）一律遵守
   同一套参数（宽/高 + 版心 + 四边 padding; build_html 自动读锁复用, .page padding
   字面全项目一致）; **上边距 = 定版 padding（约 100px 级）, 禁止用原图留白或
   {{VOFF}} 复刻扫描件页顶留白**（010 页顶拥挤教训）。改定版参数须整项目重排。
   `batch.py` 开工自动执行本检查（未定版自动抽样定版），禁止跳过。
4. **阅读缩放定版（S, 宪法第七条第 6 款③）**：用户指令改阅读缩放（如 120% 实测
   校准 S=1.2）时——改定版页宽/高的**唯一合法通道**:
   `python3 scripts/calibrate.py rescale --project <名> --scale <S>`（页框锁值
   换算为 820 基准 × S, scale/scale_base 入锁, handoff「定版参数」段覆盖写）;
   **存量现行格式页真参数重定标**: `python3 scripts/rescale_html.py --project <名>
   --scale <S>`（真字号/真边距/真间距 ×S, 幂等, 与按新锁重建数值等价）, 随后
   `validate_html.py` 复验; **禁止 CSS zoom/transform 冒充阅读缩放**（渲染层
   缩放 = 假真参数）; 改 S 须全项目重定标/重排。

### ① 整页通读 → 分块放大逐段核对（宪法第零条，不可跳过）

1. Read 整图，先建立页面清单：标题/页眉/页码、段落数、粗斜体、公式位置、插图数量与
   类型、**版式结构**（并排图行 / 左图右文混排 / 图注带位置 / 标题对齐 / 段首缩进）
   ——版式也是要转录的内容（第七条第 5 款）。
2. **必须**分块放大核对（转录错误头号防线）——用技能脚本 `crop_zoom.py`
   （`skills/image-ocr-svg-redraw/scripts/`）把页面切 2-4 块放大 2-3 倍逐块 Read
   （切片一律输出到 `.work/`，第十一条）：
   - 数字逐位核（矩阵元素、坐标分量）；标点照录（原文 `plane :` 冒号前有空格就照录）；
   - 粗体起止、斜体词、上下标位置。
3. 写出 `.work/<名>/pack1/<page>/text.md`（由 transcriber 角色完成）。**插槽是版式指令**
   （第七条第 5 款），插图位置按原页版式选择写法：
   - 相邻多行 `{{FIG:n}}`（中间无空行）= 原图**并排图行**；
   - `{{FIG:n|aside}}` = **左图右文混排**，紧随其后的连续段落进右侧文字列
     （至下一个插图槽/标题/公式/EOF）；
   - 普通独行 `{{FIG:n}}` = 独立居中图块；
   - 图注一律写进 figures.json 的 caption（随图排版），不写进 text.md 正文。

**text.md 红线**：文件里只允许"原文内容 + 原文图形"。禁止 `<figure>` 包裹标签、
禁止"以下为原图"等元说明、禁止页码页眉复刻、禁止尾部 `---` 分隔线。
判断标准：**这个元素印刷在纸面上吗？** 不在就不写。

### ② 插图框检测（二选一）

```bash
# A. 自动（z-ai vision; 批量由 batch.py 逐页串行调度 —— 宪法第三条）
python3 packs/split-text-image/scripts/detect_figures.py \
    --page 0107 --image project/<名>/src/0107.png --out .work/<名>/pack1/0107

# B. 手工兜底（已知框坐标, 不耗 API 配额）
python3 packs/split-text-image/scripts/detect_figures.py \
    --page 0107 --image project/<名>/src/0107.png --out .work/<名>/pack1/0107 \
    --boxes "60,150,760,380;0,0,200,120"
```

检测后**必逐框核对四缘**（截断/半行文字混入）：vision 框以图形主体为中心，
常偏小/偏移，并排小图尤甚——用 `crop_zoom.py --grid` 网格读数复核 bbox，
不准就重测重裁（第七条：先量测后动笔）；框宁大勿小再裁。

### ③ 排版 HTML（最终件: 公式渲染 + 插图引用 img/ + 尺寸/布局保真）

公式 $...$/$$...$$ 由 math_render.py 渲染为纯 CSS HTML（离线可开, 不引 MathJax/KaTeX）；
版式由 build_html 依槽语义自动产出（第七条第 5 款）：相邻槽 → `.figrow` 并排行
（flex 比例 = 各裁剪实际像素宽, 图注带在较高一图下缘对齐）；`|aside` → `.figaside`
左图右文（图列宽 = 裁剪像素宽 / 正文栏宽, `--text-width` 可调）；图注 = 正文字号
深色非斜体、随图左对齐、图号 "Figure N.N:" 加粗；h2 右对齐（原书风格, 模板内置）。

**尺寸与布局硬保真（宪法第七条第 6 款②③④, 强制红线）**：页面尺寸 = **版心优先 +
人体工程学页框**，全项目统一：宽度一律取 820px 舒适阅读宽（模板设计稿, --u=1）；高度
= ⓪ 定版的**项目统一版心高**（屏显）+ 上/下 padding，夹紧到高/宽 ∈ [1.05, 1.60]；
**四边 padding 均由人体工程学计算、禁用原图留白**：左右 = (820 − 版心宽)/2 严格等距,
上下 = 0.75 × 左右（Tschichold top:outer ≈ 3:4, 屏显约 100px 级, 上边距不得接近页缘）。
项目级参数由 ⓪ 的随机样本定版产出（handoff.md「定版参数」段 + `project/<名>/page-size.json`
机器锁），后续**所有页面**自动读锁复用同一套尺寸与 padding（--page-size-file，禁止照搬各自原图
像素尺寸与原图留白；已定版禁止重复测算; 改定版须整项目重排）。
**上边距人体工程学红线**：上边距 = 定版 padding，与扫描件页顶留白无关；`{{VOFF}}`
禁止用于复刻扫描件页顶留白（仅限印刷区相对版心的光学微调）。
**左右边距等距（④, 扫描件边距失真校正）**：原图是扫描件，页缘左右边距失真
（装订阴影/邻页透印/歪斜使页缘不可信），禁止照搬页缘定位内容——水平基准 =
原图**内容区域**（build_html 按 --src-image 自动测算: 顶部页眉/底部页码带排除 +
页缘噪声段排除），内容区域在 .page 上**水平居中放置, 左右边距严格等距**；定版页测得的
content_w/margin 随 page-size.json 一并锁存，后续所有页面同规则自动等距并对定版
margin 校验（偏差超容差警告人工核对——书名页/特殊版式属预期）。
版式由 build_html 依槽语义自动产出（第七条第 5 款）：相邻槽 → `.figrow` 并排行
（flex 比例 = 各裁剪实际像素宽, 图注带在较高一图下缘对齐）；`|aside` → `.figaside`
左图右文（图列宽 = 裁剪像素宽 / 正文栏宽, `--text-width` 可调）；图注 = 正文字号
深色非斜体、随图左对齐、图号 "Figure N.N:" 加粗；h2 右对齐（原书风格, 模板内置）。
原图文布局逐项复刻：各内容块的竖直位置/居中/对齐用版式指令表达（N 一律为原页
图像素, build_html 按 k = PAGE_W/原图宽 等比落位）——`{{GAP:N}}`（独立一行, 竖直占位）、
`{{PX:N}}`（行尾, 字号覆盖, 同时锁 line-height/margin 让竖直节奏全由 GAP 控制）、
`{{CTR}}`（行尾, 段落居中）、`{{R}}`（行尾, 段落右对齐）、
`{{SX:F}}`（行尾, scaleX 横向压缩, 复刻窄体/condensed 字面）、
`{{HOFF:N}}`（独立一行, 正文流相对等距基准水平微调, 仅限版心特例；版心水平位置
由 build_html 自动等距落位, 不再承担复刻失真偏移）、`{{VOFF:N}}`（独立一行, 正文流
垂直上移, **禁止用于复刻扫描件页顶留白** —— 上边距由定版 padding 决定, 第七条③）、
`{{FLOWW:N}}`（独立一行, 覆盖版心宽=原图印刷区宽, 仍等距居中）、
`{{COLROW}}/{{COL:f}}/{{ENDCOLROW}}`（多栏文本行, f=列宽原图像素, 空列=占位, 列内支持
GAP/PX/CTR/SX/R 与 {{FIG:n}} 插图槽 —— 图文混排图行）、
`{{BOX}}/{{ENDBOX}}`（原页圆角重点框条目组; {{BOX:N}} 可选框宽, N = 原页框体**外宽**
（框线外缘, 原图像素, border-box）——build_html 以框心=版心轴对称落位（凸出两侧
页边也对称; margin:auto 在框宽 > 版心时溢出归零会单侧错位, 已规避, 025 教训）;
框内字号 {{PX}} 与间隙 {{GAP}} 联合实测, 框总高以原页框体高×k 为验收锚）、`{{EQBOX:N}}`（原页矩形公式框行, N=框左缩进原图像素; 行尾
`{{EQN:文本}}` = 框外右侧编号）、
`{{EQGROUP:N}}/{{ENDEQGROUP}}`（多行共用左缘+行尾编号的条目组三列表格 —— 025 点积
三行+(1): N=首列缩进原图像素, 第一列空白, 第二列各行左对齐, 第三列仅编号行右对齐
贴版心右缘+9px 内缩; 组内支持 {{EQBOX}}/{{EQN}}/{{GAP}}; 禁止逐行 {{CTR}} 凑合;
公式上方的名称标签（如 Schwarz/Triangle inequality）**不并入公式行** —— 公式行
保持单一连续文本流, 标签独立成行由排版端实测定位, 第七条第 5 款行上下文校验）、
`{{FACE:sans}}`（独立一行, 无衬线字体族, 书名页等
非 Times 版面用）、
`{{LH:F}}`（独立一行, 其后 {{PX}} 段行距 = F, 原页行距/字号比复刻用, 默认 1.15）。
插图槽：dest/img/ 已有重绘主档 SVG 时相对引用之；否则把 crops/figN.jpg 自动发布为
最终件 dest/img/<stem>.jpg（单图页 <page>, 多图页 <page>-fig<i>）并相对引用 ——
dest/<page>.html + dest/img/ 即完整交付单元, 不引用 .work 中间件（第十一条②）。
```bash
python3 packs/split-text-image/scripts/build_html.py \
    --page 0107 --text .work/<名>/pack1/0107/text.md \
    --figures .work/<名>/pack1/0107/figures.json \
    --figure-map .work/<名>/pack1/0107/figure-map.json \
    --src-image project/<名>/src/0107.png \
    --page-size-file project/<名>/page-size.json \
    --workdir .work/<名>/pack1/0107 \
    --out project/<名>/dest/0107.html --title "Section 3.2" [--page-no 107]
```

### ④ 自检（宪法第九条 + 第十四条机器校验）

**机器校验先行（第十四条, 强制闭环）**——排版完成立即跑, FAIL 不得交付:

```bash
python3 scripts/validate_html.py --project <名> --pages <page>   # 单页（排版后即跑）
python3 scripts/validate_html.py --project <名> --pages all-dest # 收尾全项目回归
```

五层门禁: L0 静态（占位/LaTeX 泄漏/img）→ L1 几何硬门禁（定版锁/等距/框心=
版心轴/矩阵 em 行距/flow 高度不裁剪）→ L2 墨迹节律（同尺度对比: r/块界/分位
点/墨带 + compare.png 人工终审）→ L3 文本保真（数字集合+散文词数, text.md 在
场时）→ L4 外部工具插槽（Docfold 初筛 / OmniDocBench 深诊断, 探测制, 未安装
如实 SKIP）。**处置回路**: 读 FAIL 明细（期望/实测/定位）→ 改 text.md 版式指
令（高度溢出按**均匀比例因子**同压 {{PX}} 与 {{GAP}}, 宪法第十四条 4 款）→
重跑至 PASS; WARN 项人工看 `.work/validate/<page>-compare.png` 判读。

人工自检清单（机器校验之外仍须逐项过）:

- [ ] text.md 与原图逐段核对过（数字/标点/粗斜体/上下标）
- [ ] text.md 无红线违规
- [ ] **尺寸合规**：.page 宽×高、版心与四边 padding = 项目定版参数（版心优先 +
      人体工程学页框, 第七条第 6 款②③; handoff.md「定版参数」段 + page-size.json
      机器锁同值, 全项目同尺寸同 padding 字面, 禁止照搬原图像素与留白; 上边距
      ≈ 100px 级, 不得接近页缘）
- [ ] **等距合规**：内容区左右边距严格等距（第七条第 6 款④; build_html 自动
      等距落位保证; 渲染件 .flow 左右空隙相等, 页缘透印/装订阴影未带入版心）
- [ ] **版式对照**：渲染截图与原页逐项核对（竖直位置/居中/并排行/图文混排/图注带/
      标题对齐/多栏列缘/框体框心=版心轴且总高≈原页框高×k; 第七条第 6 款① + 第 5 款;
      版式指令按 k 等比缩放下对照）
- [ ] **行上下文校验**（第七条第 5 款）：逐行参照上下行对应内容核验对齐——标签
      居中于各自公式、编号贴行尾公式右缘、多行条目组共用左缘; 一行内自然字符
      间距未被改变（接缝 = 普通空格宽, 原书一行仍是一行, 无折行）
- [ ] dest/<page>.html 打开无样式错乱、公式正常显示；`{{FIG:n}}` 全部被替换（grep 无残留 `{{FIG`）
- [ ] 插图相对引用 img/ 且文件就位（dest/<page>.html + img/ 同仓可离线打开）
- [ ] plan.md 核销 + archive.sh 归档（dest 最终件 + .work 中间件, 第一条）
- [ ] 无流水账/日志残留（第十三条：任何文件不随轮次增长）
- [ ] 完成协议（第十一条）：`.work/` 已清理，`scripts/complete.sh` 已打包交付快照

## 批量（页级锁步: detect 一页 → 转录排版一页）

```bash
# 插图检测裁剪（默认阶段, 页级锁步）: 每次只检测"第一个未完成页"（完成 = dest/<page>.html
# 已产出, 全链闭合）—— detect 一页 → 转录排版一页 → 排版完成后重跑本命令自动推进下一页;
# detect 永不跑在转录排版前面（用户规则; 中间件入 .work/<名>/pack1/）
# 开工自动执行定版前置检查（第七条第 6 款③: 未定版则随机抽 x 张原图统计定版, 禁止跳过）
python3 scripts/batch.py --project <名> --pack split-text-image
# 手工兜底: 显式指定页绕过锁步（重检测/补检测指定页, 不耗锁步位）
python3 scripts/batch.py --project <名> --pack split-text-image --pages 0107
# 排版: 对已转录页（text.md 就绪）批量生成最终件 dest/<page>.html + dest/img/<page>.jpg;
# dest/img/ 已有验收通过的重绘主档 SVG 时插图槽自动改引用（比 html 新则强制重排）
python3 scripts/batch.py --project <名> --pack split-text-image --stage html
```

batch.py 自动完成：plan.md 登记/核销、run-state 断点续跑、页间隔与优雅停、
收尾更新 handoff.md 交接板（每 发→收 只一条, 第十三条）。单页手工兜底仍可用：

```bash
python3 packs/split-text-image/scripts/detect_figures.py \
    --page 0107 --image project/<名>/src/0107.png \
    --out .work/<名>/pack1/0107 --boxes "60,150,760,380"
```

## 故障处置

| 症状 | 处置 |
|---|---|
| batch 开工即退出并提示先跑 calibrate | 第七条第 6 款③ 开工前置红线: `python3 scripts/calibrate.py --project <名>` 随机抽 x 张原图定版（x = config.json layout_samples, 默认 5; forge.sh new --samples 设定） |
| vision 返回 429 | 停批 → `scripts/probe-429.sh`，RECOVERED 后续跑（第六条） |
| 插图框不准 | 改用 `--boxes` 手工给定；框是重绘/裁剪的源头，宁手工勿错 |
| HTML 版式偏离原图（并排/混排丢失、图注错位） | 查 text.md 槽语义是否表达了版式（相邻行=并排, `|aside`=混排）; 查 bbox 是否截断（网格重测重裁, 见②） |
| HTML 内容区尺寸 ≠ 项目定版尺寸 | build_html 未传 `--page-size-file`/`--page-size`（第七条第 6 款②③）; 检查调用命令; page-size.json 为项目定版唯一事实源（⓪ 由 calibrate.py 随机样本统计产出） |
| 内容区左右边距不等距 | 等距落位由 build_html 自动保证（④）; 若被破坏查是否手写 width/translateX 覆盖 auto margin; 本页等距边距与定版差异超容差会有警告（书名页/特殊版式属预期, 人工确认） |
| 页面竖直位置/字号与原图不符 | text.md 补版式指令：`{{GAP:N}}` 竖直占位、`{{PX:N}}` 字号覆盖、`{{CTR}}` 居中、`{{R}}` 右对齐（N 为原图像素, build_html 按 k 等比落位） |
| 多栏页（词典/表格版式）列位置错 | text.md 用 `{{COLROW}}/{{COL:f}}/{{ENDCOLROW}}` 表达列结构（f=列宽原图像素, 空列占位）, 列内用 {{GAP}} 控制节奏 |
| HTML 出现重复内容块 | 检查是否有人用 JS `replace` 拼了含 `$` 的内容（第五条） |
| 公式里函数名字面泄漏（页面显示 `\cosθ`） | math_render 未收录该函数名, 走了未知命令诚实渲染兜底（025 教训）: 在 math_render.py `FUNCS` 表补录（正体+细空格）, 并 `grep -P '\\\\(cos\|sin\|…)' dest/` 全项目排查手修 |
| validate_html L1 报 flow 内容高超可用高 | 内容被 .page overflow:hidden 静默裁剪（036 教训）: 按**均匀比例因子** u=可用高/自然高 同压 {{PX}} 与 {{GAP}}（宪法第十四条 4 款）, 只压字号不压间隙会块界比例失真 |
| validate_html L2 报块界失配/r 低 | 先看 `.work/validate/<page>-compare.png`: 块缺失/多余 → 查 text.md; 位置漂移 → 调对应 {{GAP}}; 扫描歪斜已由校验器自动去斜, 勿手调 |
| 会话中断 | `plan.py next` + `run-state-<stage>.json` 断点续跑（第二条） |
| 同类错误反复出现 | 先查 `project/notes/` 经验库（`python3 scripts/notes.py show [--grep 关键词]`）复用已有解法（第十二条） |
| .page 渲染被外层 flex 压缩变形（984 页被压到 952 等） | .page 补 `flex-shrink:0`（模板+存量页）; 浏览器/校验器视口一律 ≥1200×1600（1000 级视口装不下 984 页+观景边距, flex 挤压变形） |
| 改阅读缩放 S 后存量页尺寸/字号未变 | 存量现行格式页跑 `scripts/rescale_html.py` 真参数重定标（×S, 幂等）+ validate_html 复验; 禁止 CSS zoom/transform 冒充（第七条第 6 款③） |

## 交接（附录协议）

插图裁剪完成后 send 给 transcriber；text.md 就绪后 send 给 compositor：

```bash
python3 scripts/handoff.py send --project <名> --from operator --to transcriber \
    --send "N 页插图已裁剪至 .work/<名>/pack1/" --next "逐页转录写 text.md"
```

角色收尾另按第十一条完成协议：send 交接 → 有已解决错误先 `notes.py add`
沉淀经验（第十二条）→ 清理 `.work/` → `bash scripts/complete.sh --project <名>`
（自动打包交付快照，notes/ 一并入库）。
