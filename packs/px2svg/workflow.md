# workflow — pack-2 `px2svg`（像素图重绘 SVG）

> 宪法全文见 `constitution.md`；重点条款：**第七条（量测→重绘→对比）、第八条（字体保真）**。

## 输入 / 输出（项目工作区）

```
插图源图（.work/<名>/pack1/<page>/crops/fig<i>.jpg）  +  spec（量测后编写）
  ↓ mpl_redraw.py（--publish 发布主档到 dest/img/）
figforge/.work/<名>/pack2/specs/<page>-fig<i>.spec.json          spec 存放约定
figforge/.work/<名>/pack2/svg/<page>-fig<i>.svg                  主档（字形转路径）
figforge/.work/<名>/pack2/svg/<page>-fig<i>_text.svg             可编辑版
figforge/.work/<名>/pack2/svg/<page>-fig<i>.png                  300dpi
figforge/.work/<名>/pack2/svg/compare-<page>-fig<i>.png          对比图（验收凭据）
project/<名>/dest/img/<page>.svg                                 ★ 最终件: 发布的重绘主档
                                                                 （多图页 <page>-fig<i>.svg）
```

## 步骤

### ① 量测（第七条：先量测后动笔，禁止目测直接画）

- **网格读数**：用技能脚本 `crop_zoom.py --region x,y,w,h --grid -o .work/grid.png`
  叠加 50px 网格（标注为整图坐标），直接读出顶点/端点/标签位置
  （临时量测图只进 `.work/`，第十一条）；
- **直线拟合**（斜线/长直边精度不够时）：对边做抗差拟合（IRLS）取交点；
  实战脚本见 `references/redraw-playbook.md`；
- **数学交叉校验**：图中若标明 a₃ = a₁ + a₂，重绘的三支箭头必须满足同一关系；
  平行、垂直、相切等关系要成立。

### ② 编写 spec JSON

- 坐标系 = 源图像素，**y 轴向下**；元素类型与字段见 `pack.json` 的 spec_schema_summary；
- 文字标注：印刷正文用 `text`（基线对齐、bold），数学符号用 `math`
  （LaTeX 子集，STIX 渲染、中心对齐）；
- **存放约定**：`.work/<名>/pack2/specs/<page>-fig<i>.spec.json`
  （spec 内 name 字段可与文件名不同, compose 会统一改名）；
- 现成示例：`examples/directed-graph.spec.json`（107 有向图完整数据，可直接跑通）。

### ③ 渲染

```bash
python3 packs/px2svg/scripts/mpl_redraw.py \
    --spec .work/<名>/pack2/specs/0107-fig1.spec.json \
    --out .work/<名>/pack2/svg --publish project/<名>/dest/img \
    --original .work/<名>/pack1/0107/crops/fig1.jpg --compare-height 540
```

批量渲染全部 spec（src 目录不需要动, 自动逐 spec 串行）:

```bash
python3 scripts/batch.py --project <名> --pack px2svg
```

### ④ 对比验收（第七条：没有对比图的交付等于没交付）

Read 打开 `<page>-fig<i>-compare.png`，逐项核对：
- 箭头方向、燕尾形状与相对长度；
- 顶点/端点相对位置、交叉关系（如领结形腰部交叉）；
- 标签文字、位置、字号层级；线宽层级（主线/辅助线/虚线）。

不像就改 spec 重渲染，通常 2-3 轮收敛；每轮对比图都保留归档（第一条）。

### ⑤ 自检（宪法第九条）

- [ ] 四件套齐全（svg / _text.svg / png / compare, 在 .work/<名>/pack2/svg/）且主档已发布 dest/img/
- [ ] SVG 根元素 width/height 为像素整数、与 viewBox 等比（引擎已保证）
- [ ] 对比图已人工查看通过
- [ ] spec JSON 与对比图一并归档（复现起点）
- [ ] 无流水账/日志残留（第十三条：任何文件不随轮次增长）
- [ ] 完成协议（第十一条）：`.work/` 已清理，`scripts/complete.sh` 已打包交付快照

## 交接（附录协议）

spec 就绪或渲染验收完成后 send 给 compositor：

```bash
python3 scripts/handoff.py send --project <名> --from figure-artisan --to compositor \
    --send "0107-fig1 SVG 四件套已过对比验收" \
    --state "specs/ 与 svg/ 就绪" --next "重跑 batch --pack html-svg 内嵌"
```

角色收尾另按第十一条完成协议：send 交接 → 有已解决错误先 `notes.py add`
沉淀经验（第十二条）→ 清理 `.work/` → `bash scripts/complete.sh --project <名>`
（自动打包交付快照，notes/ 一并入库）。

## 经验参数（详见 references/redraw-playbook.md）

| 项 | 值 |
|---|---|
| 字号/线宽换算 | `PT = 72/dpi`；size_px × PT → pt |
| 燕尾箭头初值 | length 33, width 31, notch 12（原图目测起值，对比后微调） |
| 主线宽 | 3 px（@dpi=100） |
| 领结形闭合多边形 | `polygon` + `join:"miter"`，长边在腰部交叉 |
| 坐标系 | y 向下；text 基线对齐 / math 中心对齐 |
