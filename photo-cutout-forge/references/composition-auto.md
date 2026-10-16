# 自动构图：五版式 · 决策规则 · 文字区

> 需求「可以自主选择怎么构图」的落点：`auto_compose.py` 读主体（抠图 alpha）的
> **宽高比与质量重心**，自动选版式、定主体与背景窗位置，并在 `plan.json` 写明中文理由。
> 人可 `--layout` 覆盖（含可选满幅长卷 `hero-band`）。画布 1500×1875（4:5）。

## 视觉模型（三步合成，先背景后文字）

```
纸面（make_ground：预设纸色＋纹理；--paper 可覆盖纸色）
  → 背景窗（原图经 zoom／裁剪／柔焦／双色调／wash，lens 蒙版，multiply 贴上；--no-backdrop 可去）
    → 倒影／投影（可选绘画层：--reflection 主体下缘水影、--shadow 主体落纸投影）
      → 主体（透明底抠图，over 贴上）
        → 之后才是文字（母版只做排版，不碰背景）
```

## 五版式与参数（已按敦煌案例调优）

| 版式（data-comp） | 何时选（自动规则） | 背景窗（lens，feather 30） | 主体 | 文字区（母版必须与之一致） |
|---|---|---|---|---|
| hero-top | 主体宽高比 ≥ 1.18（横向岛屿） | cx .50 cy .335 rx .415 ry .265 zoom 2.8 | 宽 .72W（高上限 .46H），水平居中，顶 .115 | 下方 [.07, .62, .93, .97] |
| hero-right | 宽高比 ≤ 0.80 且质量重心 x > .50 | cx .70 cy .45 rx .235 ry .30 zoom 2.2 | 高 .52H（宽上限 .38W），中心 x .775，底 .84 | 左侧 [.06, .12, .50, .92] |
| hero-left | 宽高比 ≤ 0.80 且质量重心 x ≤ .50 | cx .30 cy .45 rx .235 ry .30 zoom 2.2（镜像） | 高 .52H（宽上限 .38W），中心 x .225，底 .84 | 右侧 [.50, .12, .94, .92] |
| hero-centre | 其余（0.80–1.18，方正） | cx .50 cy .315 rx .40 ry .245 zoom 2.4 | 宽 .60W（高上限 .42H），居中，顶 .14 | 下方 [.07, .62, .93, .97] |
| hero-band | 全景横幅（宽高比 ≥ 1.30）且要满幅长卷——**不自动选中**，需 `--layout hero-band` | 无（`shape: none`） | 宽 1.0W（高上限 .62H），水平居中，顶 .03 | 下方 [.07, .635, .93, .98] |

- 背景窗一律 `--focus`（默认 0.5 0.40）取景、双色调（默认预设「青金」，chroma .55）、
  **柔焦 `--bd-blur`（默认 10）＋向纸色融合 `--wash`（默认 .40）**、multiply 上纸。
  柔焦与 wash 是抠图路线的命门：背景退成「色场」，清晰主体才有图底层级（敦煌实测）。|
- `--no-backdrop`：整条去掉背景窗（纯纸面背景），任何版式可用；岛式主体背后的柔光椭圆若被读成「光斑／阴影」，它比换取景更彻底（敦煌实测）。
- **`--bg-mode color`（提取双色渐变底场，无窗）**：从原图降采样（宽 220px）取「饱和像素」（S>0.28、18%<V<85%）做 k-means（k=4，seed 同 `--seed`）。
  主色＝**权重×饱和度** 最高簇再压深（V×0.74 夹 [0.30,0.46]、S×1.15 夹 [0.32,0.62]），保留照片自身色相；`--bg-color "#RRGGBB"` 指定时直接采用（副色仍从原图提取）。
  副色＝与主色**色相距离最大**且权重 ≥6% 的簇（距离 ≥20° 才用），压得更沉（S×0.92 夹 [0.28,0.52]、V×0.78 夹 [0.28,0.38]）；无合适簇则同色相浅一档回退。
  底场＝**偏置双色渐变**：`diag`＝`u = 0.62·(y/h) + 0.38·(x/w)`（副色自下缘右侧斜入）；`up`＝`u = 0.88·(y/h) + 0.12·(x/w)`
  （副色自下缘整幅升起成「展台地」、主色占上约 2/3）；u<阈值全为主色，smoothstep 过渡（非五五开）；仅 0.8σ 抖动防色带。
  `--bg-grad {diag,up}` 选方向；`--bg-vignette 0.18` 四缘轻压暗（`1-v·rr²`）收拢视线；`--bg-lift 0.30` 两色同步提亮（V×(1+lift)，色相饱和不变）。
  **纯色渐变、零肌理**——叠云斑／织纹／颗粒会被读成「斑点、不高级」（敦煌三次迭代实测）。柔焦窗被读成「模糊照片贴片」时换这条。
- **纸面与绘画层（可选，opt-in）**：`--paper "#E8DCC0"` 覆盖纸色（默认取 preset）；`--shadow 0.30` 给主体加落纸投影（`--shadow-blur` 26／`--shadow-dy` 20）——修「主体与纸面对比不足」；`--reflection 0.50` 在主体下缘铺一段渐隐水影（`--reflection-blur` 20）——给纸面做层次，**0.30 以下肉眼近乎不可见（敦煌实测）**。**主体强化（color 深底常用）**：`--subject-pop 0.25` 提饱和/对比让主体「立」起来；`--subject-paint 0.6–1.0`「重绘」（中值去噪→提饱和/提亮→对比→色彩分层量化，≥0.45 出手绘块面感）；`--subject-lift 0.25` 提亮（保色相）。 
- 主体缩放取「目标尺寸」中可达的一组（先按主目标，超上限即改为上限）。
- **起始参数**，实测以 `plan.json` 的 checks 全过为准（可微调缩/移/调色）。
- 文字区含义：**主机文字只允许落于此区**（区内不得有主体、背景窗）。

## 决策理由（写进 plan.json 的 layout_reason）

- `宽高比 ≥ 1.18` →「主体横向展开，作横幅式上置岛屿，下方整片纸面承字」
- `宽高比 ≤ 0.80` →「主体竖长，作立柱式侧置；按其质量重心侧选择左/右，让出对侧整栏纸面」
- 其余 →「主体方正，居中浮岛，四周留纸、下缘承字」
- `hero-band`（人工指定）→「全景长卷满幅横贯，作壁上长卷；下缘整片纸面承字」

## 母版对应（数据契约）

`body[data-comp]` 取 hero-top / hero-right / hero-left / hero-centre；各版式文字位置：

| 版式 | presenter | 主块（题＋展讯） | 主标题字号 | 印章 |
|---|---|---|---|---|
| hero-top | 顶部居中 | 左下 7%，宽 62%，bottom 3.4% | 196px | 右 7% bottom 26% |
| hero-right | 左上 | 左 7%，top 26%，宽 43% | 152px | 左 7% bottom 12% |
| hero-left | 右上（右对齐） | 右 7%，top 26%，宽 43%，右对齐 | 152px | 右 7% bottom 12% |
| hero-centre | 顶部居中 | 居中块 left/right 10%，bottom 3.0% | 196px | 右 6.8% bottom 24% |
| hero-band | 顶部居中 | 复用 hero-top 主块：左下 7%，宽 62%，bottom 3.4% | 196px | 右 7% bottom 26% |

- 主块结构沿用母版：ornament／title／subtitle／tagline／meta 三行／cta；字号体系见 calligraphy.md。
- hero-band 的文字区与 hero-top 相近，母版直接用 `data-comp="hero-top"`（敦煌定稿即此配置）。
- **深底浅字主题**：color 底场落字时给母版 `body` 加 `data-theme="deep"`（鎏金题／米白信息／金底 CTA），
  并把 `.stage` 的 `--stage-bg` 改为与底场同值；渲染亦可 `?theme=deep` 切换（机检仪器同可用）。
  底场经 `--bg-lift` 提亮后文字对比整体下滑，小字墨色需跟随提亮一档（敦煌 I 档 tagline `#D3C5A6→#DDD0B2`，4.27→4.77 复过）。
- 渲染后 `boxes.json` 的 overflowX/Y 必须全 false；不过就调字号／栏宽（先位置后墨色）。

## 机检（auto_compose 内置 checks，写入 plan.json）

| 项 | 口径 | 不过怎么办 |
|---|---|---|
| subject×text_zone 重叠 | 覆盖面积占文字区 ≤ 2% | 主体按 0.92 步缩，最多 4 次；仍不过报 fail |
| backdrop×text_zone 重叠 | 同上 | 背景窗同样步缩（或下移） |
| blank_ratio（留白率） | 纸面可见占比 ≥ 0.40 | 缩主体／背景窗 |
| subject 落画 | 主体 rect 完整在画布内 | 回夹位置 |

`plan.json` 字段：layout ＋ layout_reason ＋ subject（aspect、mass_cx、rect_px、pop／paint／lift）＋ backdrop（shape/cx/cy/rx/ry/zoom/focus/crop_px/chroma/wash/blur 或 none）＋ text_zone ＋ checks（pass）＋ shadow（strength/blur/dy 或 null）＋ reflection（strength/blur 或 null）＋ paper（preset/seed/color）＋ **background（"mode": "color" 时含 base 主色／second 副色／grad 方向／vignette／lift 与 source_palette 提取簇；window/paper 时为 "mode"）**。

## CLI 与调试

```powershell
python .trae\skills\photo-cutout-forge\scripts\auto_compose.py --source src.png --subject cut\A.png `
    --preset 青金 --seed 3 --out out\bg.png --plan out\plan.json [--debug out\debug.png] `
    [--layout hero-top|hero-band] [--no-backdrop] [--bg-mode window|color] [--bg-color "#1F3F6E"] `
    [--bg-grad diag|up] [--bg-vignette .18] [--bg-lift .30] [--subject-pop .25] [--subject-paint 1.0] [--subject-lift .25] `
    [--focus .5 .4] [--bd-zoom 2.8] [--bd-blur 10] [--wash .40] [--chroma .55] [--subject-target .72] `
    [--shadow .30] [--reflection .5] [--paper "#E8DCC0"]
```

- `--debug`：在背景图上画出背景窗（蓝）、主体 rect（红）与文字区（绿）矩形，供 Gate 目检。
- 换版式＝`--layout`（含 `hero-band` 满幅长卷）；去窗＝`--no-backdrop`；换色调＝`--preset`；纸纹＝`--seed`；主体大小＝`--subject-target`（占画布宽/高比例）。
- `--bg-mode color`：双色渐变底场路线（无窗）；自动提取主色＋副色，或 `--bg-color` 指定主色（如敦煌石青浓 `#1F3F6E`，副色仍从原图提取）。输出 `background.mode=color`（base/second），落字用 `data-theme="deep"`。方向／压暗／提亮＝`--bg-grad up`／`--bg-vignette`／`--bg-lift`；主体配套 `--subject-paint`／`--subject-pop`／`--subject-lift`，投影 `--shadow`。
- 调参优先级：先 `--subject-target`／`--bd-zoom`（构图），再 `--wash`／`--bd-blur`（层级），最后 `--focus`（取景）。
- 主体对比不足＝`--shadow 0.30`（0.25–0.38）；纸面太空＝`--reflection 0.50`（0.30 以下近乎不可见）；纸色不合＝`--paper`。
- **改完背景再落字**；渲染时 poster.html 的 `body[data-comp]` 必须与 plan.json 的 layout 一致。