# redraw-playbook — 量测与参数手册（107/138 实战沉淀）

## 1. 量测工具链

| 工具 | 用途 |
|---|---|
| 技能脚本 `crop_zoom.py --region x,y,w,h --grid` | 裁剪 + 2-3x 放大 + 50px 坐标网格，直接读顶点 |
| 直线抗差拟合（IRLS） | 长斜边端点精度不够时：对边像素做加权最小二乘，取邻边交点为顶点 |
| 二值化总览 | 文字条目定位：逐项校准 x/y/字号，再用整页 Read 交叉验证 |
| `mpl_redraw.py --original` | 每轮渲染自动产出并排对比图，是唯一验收凭据 |

实战量测脚本（138 用）存于项目 `scripts/`：`measure_138_*.py`（Hough/IRLS 拟合 →
`fig138_calib.json` → `fig138_refine.json`），可作为新测量脚本的模板。

## 2. spec 编写规则

- **坐标系**：与源图像素一致，y 轴向下（引擎已内置 `ax.set_ylim(H, 0)`）。
- **线宽/字号**：以像素记（`width_px`、`size_px`），引擎按 `PT = 72/dpi` 换算；
  dpi 必须与 canvas 一致（默认 100）。
- **文字两种对齐**（与原书版式对应）：
  - 印刷正文/图注：`text`，`weight: bold`，`valign: baseline`（基线）；
  - 数学符号（$\boldsymbol{y}_1$、$\mathbf{C}(A)$ 等）：`math`，LaTeX 子集，
    `valign: center`。注意下标写法：`\boldsymbol{y}_1` 不要把数字并进 `\boldsymbol{}`。
- **颜色**：统一 `ink: "#1a1a1a"`；特殊强调才单独给 `color`。

## 3. 符号参数库

| 符号 | 参数 | 备注 |
|---|---|---|
| 燕尾箭头 stealth | length 33 / width 31 / notch 12 | 后缘内凹；position 默认 0.5（边中点），可调 |
| 简单三角箭头 triangle | length 30 / width 30 | 后缘平直 |
| 主线 | width_px 3 (@100dpi) | solid_capstyle round |
| 虚线 | line + `dash: [6, 4]`（px） | |
| 领结形 | polygon 闭合六边形 + `join: "miter"` | 两条长边在腰部交叉即成领结；fill 白色遮挡下层线 |
| 节点圆点 | dot r=10 | |

## 4. 验收清单（对应宪法第七/八条）

1. compare 图逐项核对：箭头方向、相对长度、顶点位置、交叉关系、标签层级；
2. 数学关系成立（求和/平行/垂直/相切）;
3. SVG 根元素 width/height 为像素整数、与 viewBox 等比；
4. 主档 SVG 在无字体的陌生环境打开不变形（字形已转路径）；
5. 可编辑版 `_text.svg` 在装有 Liberation Serif + STIX 的环境中打开正确。

## 5. 已知坑

- **字体失真**（本项目当初重做主档的原因）：SVG 只写字体名时，查看端无此字体就替换
  → 主档必须 `fonttype="path"`；可编辑版单独交付并注明字体依赖。
- **下标重复**：`\boldsymbol{y1}` 会把数字并入主字符，正确写法 `\boldsymbol{y}_1`。
- **y 轴方向**：matplotlib 默认 y 向上，引擎已翻转；自写渲染脚本别忘了。
- **pt/px 混写**：savefig 出的 SVG 根元素是 pt，引擎已统一改回 px 整数。
- **量测被邻近元素污染**：拟合直线前先按颜色/位置过滤邻近标签像素，否则端点漂移。
