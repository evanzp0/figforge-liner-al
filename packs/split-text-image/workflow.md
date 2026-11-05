# workflow — pack-1 `split-text-image`（图文分离）

> 宪法全文见 `constitution.md`；本文件与其冲突时以宪法为准。

## 输入 / 输出（项目工作区; dest 只放最终件, 中间件在 .work/<名>/ —— 第十一条）

```
project/<项目名>/src/<page>.png            原页扫描图
figforge/.work/<名>/pack1/<page>/          中间件（转录与裁剪）
  ↓ ①转录  ②插图框  ③裁剪  ④排版
figforge/.work/<名>/pack1/<page>/text.md       转录文本（极简 Markdown, 含 {{FIG:n}}）
figforge/.work/<名>/pack1/<page>/figures.json  插图框 + 说明
figforge/.work/<名>/pack1/<page>/crops/figN.jpg 插图裁剪（中间件）
project/<项目名>/dest/<page>.html          ★ 最终件: 书页 HTML（公式已渲染,
                                            插图相对引用 img/, 离线可开）
project/<项目名>/dest/img/<page>.jpg       ★ 最终件: 插图裁剪（多图页 <page>-fig<i>.jpg;
                                            排版时由 build_html 自动发布）
```

dest 交付单元 = `<page>.html + img/`（同仓自洽, 不引用 .work 中间件 —— 第十一条）;
若后续跑 jpg→svg 重绘流程（pack-2）, 才会出现 `dest/img/<page>.svg` 重绘主档,
重排后插图槽改引用该 SVG。

## 步骤

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

### ③ 排版 HTML（最终件: 公式渲染 + 插图引用 img/）

公式 $...$/$$...$$ 由 math_render.py 渲染为纯 CSS HTML（离线可开, 不引 MathJax/KaTeX）；
版式由 build_html 依槽语义自动产出（第七条第 5 款）：相邻槽 → `.figrow` 并排行
（flex 比例 = 各裁剪实际像素宽, 图注带在较高一图下缘对齐）；`|aside` → `.figaside`
左图右文（图列宽 = 裁剪像素宽 / 正文栏宽, `--text-width` 可调）；图注 = 正文字号
深色非斜体、随图左对齐、图号 "Figure N.N:" 加粗；h2 右对齐（原书风格, 模板内置）。
插图槽：dest/img/ 已有重绘主档 SVG 时相对引用之；否则把 crops/figN.jpg 自动发布为
最终件 dest/img/<stem>.jpg（单图页 <page>, 多图页 <page>-fig<i>）并相对引用 ——
dest/<page>.html + dest/img/ 即完整交付单元, 不引用 .work 中间件（第十一条②）。
```bash
python3 packs/split-text-image/scripts/build_html.py \
    --page 0107 --text .work/<名>/pack1/0107/text.md \
    --figures .work/<名>/pack1/0107/figures.json \
    --figure-map .work/<名>/pack1/0107/figure-map.json \
    --workdir .work/<名>/pack1/0107 \
    --out project/<名>/dest/0107.html --title "Section 3.2" [--page-no 107]
```

### ④ 自检（宪法第九条）

- [ ] text.md 与原图逐段核对过（数字/标点/粗斜体/上下标）
- [ ] text.md 无红线违规
- [ ] **版式对照**：渲染截图与原页逐项核对（并排行/图文混排/图注带/标题对齐; 第七条第 5 款）
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
| vision 返回 429 | 停批 → `scripts/probe-429.sh`，RECOVERED 后续跑（第六条） |
| 插图框不准 | 改用 `--boxes` 手工给定；框是重绘/裁剪的源头，宁手工勿错 |
| HTML 版式偏离原图（并排/混排丢失、图注错位） | 查 text.md 槽语义是否表达了版式（相邻行=并排, `|aside`=混排）; 查 bbox 是否截断（网格重测重裁, 见②） |
| HTML 出现重复内容块 | 检查是否有人用 JS `replace` 拼了含 `$` 的内容（第五条） |
| 会话中断 | `plan.py next` + `run-state-<stage>.json` 断点续跑（第二条） |
| 同类错误反复出现 | 先查 `project/notes/` 经验库（`python3 scripts/notes.py show [--grep 关键词]`）复用已有解法（第十二条） |

## 交接（附录协议）

插图裁剪完成后 send 给 transcriber；text.md 就绪后 send 给 compositor：

```bash
python3 scripts/handoff.py send --project <名> --from operator --to transcriber \
    --send "N 页插图已裁剪至 .work/<名>/pack1/" --next "逐页转录写 text.md"
```

角色收尾另按第十一条完成协议：send 交接 → 有已解决错误先 `notes.py add`
沉淀经验（第十二条）→ 清理 `.work/` → `bash scripts/complete.sh --project <名>`
（自动打包交付快照，notes/ 一并入库）。
