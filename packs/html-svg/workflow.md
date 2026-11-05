# workflow — pack-3 `html-svg`（合用：原页 → HTML + SVG）

> pack-3 不引入新方法论，只编排 pack-1（转录/裁剪）与 pack-2（SVG 重绘）。
> 两包的方法论与宪法条款在各自 workflow.md，此处只列编排契约。

## 输入 / 输出（项目工作区）

```
project/<名>/src/<page>.png
figforge/.work/<名>/pack2/specs/<page>-fig<i>.spec.json   可选（figure-artisan 供 spec）
  ↓ compose_page.py（内部依次调 pack-1 检测/排版 + pack-2 重绘发布）
figforge/.work/<名>/pack1/<page>/         中间产物（text.md, figures.json, crops/, figure-map.json）
figforge/.work/<名>/pack2/svg/            <page>-fig<i> 四件套
project/<名>/dest/img/<page>.svg          重绘主档（发布, 多图页 -fig<i>; 仅重绘流程存在）
project/<名>/dest/img/<page>.jpg          插图裁剪最终件（pack-1, 多图页 -fig<i>）
project/<名>/dest/<page>.html             ★ 最终书页 HTML（插图槽内嵌 <svg>）
figforge/.work/<名>/pack3/<page>.manifest.json   每图状态（中间件）
```

## 步骤

### ①（可选）pack-1 转录

若 `.work/<名>/pack1/<page>/text.md` 尚不存在，先按 pack-1 workflow 产出
（分块放大核对，插图位置写 `{{FIG:n}}`）。

### ② 编排单页

```bash
python3 packs/html-svg/scripts/compose_page.py --project <名> --page 0107 [--no-detect]
```

内部流程（全部串行，单页一进程，由 batch.py 调度 —— 宪法第三条）：

1. `detect_figures.py` 产出 `figures.json` + `crops/`（`--no-detect` 可复用已有）；
2. 对每个插图 n：`specs/<page>-fig<n>.spec.json` 存在 → 调 `mpl_redraw.py` 出
   四件套（--original 用 crop 图出对比图）；缺 spec → JPG 占位；
3. `build_html.py` + figure-map（重绘 SVG / 裁剪 JPG 均相对引用 img/）→ `dest/<page>.html`；
4. 写 manifest 至 `.work/<名>/pack3/`，登记每图状态与 `redraw_todo` 清单。

### ③ 批量（目录驱动）

```bash
python3 scripts/batch.py --project <名> --pack html-svg
```

自动逐页串行编排 src/ 全部原图；收尾 handoff 自动路由：
`redraw_todo` 非空 → 通知 figure-artisan 补 spec；全空 → 通知 operator 归档交付。

### ④ 补齐重绘（figure-artisan）

对 manifest `redraw_todo` 的每图按 pack-2 workflow（量测 → spec → 渲染 → 对比）
补 spec，然后重跑 ③（run-state 断点只记执行，compose 每轮全量刷新产物，重跑安全）。
**待重绘数=0 才算整页完成。**

### ⑤ 自检（宪法第九条）

- [ ] dest/<page>.html 无 `{{FIG` 残留；插图 img/ 引用可访问（重绘主档发布前已过 pack-2 对比验收）
- [ ] manifest `redraw_todo` 为空（或明确登记为交付范围外）
- [ ] text.md 逐段核对过（pack-1 标准）
- [ ] plan.md 核销 + archive.sh 归档（阶段性成果每 10 页一档）
- [ ] 无流水账/日志残留（第十三条：任何文件不随轮次增长）
- [ ] 完成协议（第十一条）：`.work/` 已清理，`scripts/complete.sh` 已打包交付快照

## 交接（附录协议）

```bash
python3 scripts/handoff.py send --project <名> --from compositor --to figure-artisan \
    --send "0107 有 2 图待重绘" --state "见 .work/<名>/pack3/0107.manifest.json" \
    --next "量测补 spec 后重跑 batch --pack html-svg"
```

角色收尾另按第十一条完成协议：send 交接 → 有已解决错误先 `notes.py add`
沉淀经验（第十二条）→ 清理 `.work/` → `bash scripts/complete.sh --project <名>`
（自动打包交付快照，notes/ 一并入库）。
