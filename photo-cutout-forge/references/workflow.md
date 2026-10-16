# 端到端流程与命令（photo-cutout-forge）

> 工作目录为项目根。输出统一放 `out\`（案例目录以实际为准）。
> 铁律：**先处理背景、再排文字**；母版是**拷贝**不是引用；改了母版必须重拷再渲染。

## 0 目录

```powershell
New-Item -Force -ItemType Directory cand, cut, out | Out-Null
```

## 1 AI 白底抠图候选（图生图）

按 `cutout-craft.md` 的三套提示词（A 全彩 / B 墨剪影 / C 双色平涂）各出一版，
**模板的主体句按用户对主体物的描述改写**（写法见 `cutout-craft.md` §①：完整连续表述、避免「条带」字面词），
主体为原图中「主要的部分」（建筑弧墙、人物、器物……），纯白底、居中、四周留白。
以敦煌案例为例，落盘为 `cand\A2.jpg`、`cand\B.jpg`、`cand\C2.jpg`（生图有随机性，可多跑几版再挑）。
若主体被遮挡（纱幔、立柱）：先用 `cutout-craft.md` 的 D 模板图生图编辑「去除遮挡、补全被遮面」（敦煌落盘 `cand\A2c.jpg`），再进入抠图。

## 2 白底 → 透明底主体

```powershell
python .trae\skills\photo-cutout-forge\scripts\cutout.py --image cand\A2.jpg --out cut\A2.png --mode color --trim --pad 16
python .trae\skills\photo-cutout-forge\scripts\cutout.py --image cand\B.jpg  --out cut\B.png  --mode ink --trim --pad 16
python .trae\skills\photo-cutout-forge\scripts\cutout.py --image cand\C2.jpg --out cut\C2.png --mode color --auto-white --trim --pad 16
```

- 米黄／非纯白底素材（如双色平涂版）必须加 `--auto-white`，否则整底发灰。
- 边缘白圈 `--shrink 1`；细条纹被吃 `--despeckle 3`（或 0）；浅色薄纱消失 `--floor 24`。

## 3 背景处理 + 自动构图（先背景！）

```powershell
python .trae\skills\photo-cutout-forge\scripts\auto_compose.py `
    --source src-small.jpg --subject cut\A2.png `
    --preset 青金 --seed 3 `
    --out out\bg.A2.png --plan out\plan.A2.json --debug out\debug.A2.png
```

- 自动选版式（`hero-top / hero-right / hero-left / hero-centre`），理由写入 `plan.json`；
  人可 `--layout` 覆盖，或用 `--subject-target / --bd-zoom / --focus / --wash / --bd-blur` 微调。
- 满幅长卷（主体铺满左右）：`--layout hero-band`；去背景窗（纯纸面）：`--no-backdrop`。
- 绘画层（可选）：主体对比不足 `--shadow 0.30`；纸面太空 `--reflection 0.50`（0.30 以下近乎不可见）；纸色不合 `--paper "#E8DCC0"`。
- `--debug` 画出主体 rect（红）、背景窗（蓝）、文字区（绿）——供 Gate 目检。
- 三候选跑完后拼候选板：

```powershell
python .trae\skills\photo-cutout-forge\scripts\board.py --inputs out\bg.A2.png out\bg.B.png out\bg.C2.png `
    --labels 全彩抠图 墨色剪影 双色平涂 --cols 3 --width 480 --out out\cand-board.png
```

- **Gate**：看板选方向（默认自选并在交付说明理由）。

## 3B 撕开牛皮纸路线（装饰备选，替代第 3 步）

整幅真实牛皮纸、上下撕口沿主体轮廓弧撕开，中缝露出内容；**牛皮纸压在内容之上**。
窗口内容两条路：A＝抠图主体（`kraft_tear.py`）；**B＝实拍原图（`kraft_photo.py`，窗口连续、无纸色混入，推荐）**。

```powershell
python .trae\skills\photo-cutout-forge\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --kraft material\kraft.flat.png --wall-top-row 1400 --out out\bg.kraft.png
python .trae\skills\photo-cutout-forge\scripts\textzone_glow.py --bg out\bg.kraft.png --out out\bg.glow.png `
    --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"
```

- 轮廓源：默认 AI 剪影候选；**AI 剪影几何与实拍不符（多翼/U 形、窗口底落进地板行）时改「照片描线 mask」**——
  在照片上按真实边界描 top/bot 控制点 → 折线插值成与照片同尺寸 alpha 带 → 喂 `--cutout`，
  配 `--k 1.0 --smooth 21`（撕口＝真实轮廓±tear；保轮廓不做大波浪），`--wall-top-row` 取描线 top 均值。
- 产出即 `out\bg.png`（替换第 3 步产物，后续照常走）；**之后照常第 4、5 步**（先背景后文字不变）。
- 取景（`--wall-top-row`）、参数表、深底排字、陷阱清单见 `references\kraft-tear.md`。

## 3C 提取双色渐变底场路线（替代背景窗）

不叠背景窗，从原图提取「主色＋副色」→ 偏置双色平滑渐变底场（零肌理）＋主体 over——
纯色渐变深底＋清晰主体＋书法字的路线；**柔焦背景窗被读成「模糊照片贴片」时的替代**
（敦煌二次迭代；三次「斑点、不高级」去肌理改渐变；四次「渐变自下向上＋主体不够突出」加竖版渐变/压暗/投影/主体提色；
五次「整体亮度不够」加底场/主体提亮）。

```powershell
python .trae\skills\photo-cutout-forge\scripts\auto_compose.py `
    --source src-small.jpg --subject cut\A2c.png `
    --bg-mode color --bg-color "#1F3F6E" --bg-grad up --bg-vignette 0.18 --bg-lift 0.30 `
    --subject-paint 1.0 --subject-lift 0.25 --shadow 0.35 --layout hero-band `
    --out out\bg.png --plan out\plan.json
```

- `--bg-color auto`（默认）＝自动提取主色（饱和像素聚类「权重×饱和度」最高簇压深）＋副色（与主色色相距离最大的 ≥6% 簇压沉）；或 `#RRGGBB` 直接指定主色（副色仍从原图提取）。
- `--bg-grad diag|up`：斜入／自下缘向上竖版；`--bg-vignette 0.18` 四缘压暗；`--bg-lift 0.30` 两色提亮（保色相）。
  主体强化：`--subject-paint 1.0` 重绘（鲜明色块）／`--subject-pop 0.25` 轻提饱和对比／`--subject-lift 0.25` 提亮；`--shadow 0.35` 落纸投影。
  敦煌提亮两档均过机检（H 档 0.18/0.15 含蓄、I 档 0.30/0.25 更亮），示例为 I 档。
- 产出即 `out\bg.png`；**之后照常第 4、5 步**——落字时 body 加 `data-theme="deep"`（深底浅字），
  并把 `.stage` 的 `--stage-bg` 改为与底场同值（母版默认 #1F3F6E 为敦煌案例的石青浓）；
  底场经 `--bg-lift` 提亮后文字对比整体下滑，小字墨色需跟随提亮一档（敦煌 I 档 tagline 4.27→4.77）。

## 4 落字（背景定稿之后）

```powershell
# 拷贝母版＋字体＋背景（三样必须同目录）
Copy-Item .trae\skills\photo-cutout-forge\assets\poster-cutout-master.html out\poster.html -Force
Copy-Item .trae\skills\photo-cutout-forge\assets\fonts out\fonts -Recurse -Force
Copy-Item out\bg.A2.png out\bg.png -Force
# 编辑 out\poster.html：改 data-text 文案；body[data-comp] = plan.json 的 layout
python .trae\skills\photo-cutout-forge\scripts\render_png.py --html out\poster.html --out out\poster.png --scale 2 `
    --qa-bg out\poster.bg.png --boxes out\poster.boxes.json
python .trae\skills\photo-cutout-forge\scripts\check_contrast.py --boxes out\poster.boxes.json `
    --bg out\poster.bg.png --full out\poster.png --json out\poster.readability.json
```

- **中英各一版**：`--query "lang=en"`（`render_png.py` 2026-10-12 新增，**三个产物共用同一 query** ——
  成品图、`--qa-bg` 背景图、`#pf-boxes` 文字盒必须同语言，否则机检拿中文盒量英文底）。
  母版里把中英文案写成 `COPY = {zh:{…}, en:{…}}`，按 `?lang=` 写进 `[data-text]` 再 dump，
  一份文件即可一键切（不要再复制两份 HTML）。同理 `?theme=deep`。
   > ⚠ 文档里一直写着「渲染加 `?theme=deep`」，但脚本此前**没有透传 query 的参数** —— 已补 `--query`。

- `data-comp` 与 `plan.json` 的 `layout` **必须一致**（文字落点由它决定；hero-band 复用 `data-comp="hero-top"`）。
- 深色底场（3C）落字：body 加 `data-theme="deep"`（或渲染加 `?theme=deep`）；不换＝暖黑字落深底，机检必挂。
- 不达标先调位置（版式 CSS），再调墨色（`--ink*` 变量）；改完复跑机检。

## 5 交付

- 候选板 `cand-board.png` ＋ 成品 `poster.png` ＋ `plan.json`（版式与 checks 全记录）。
- 归档打包：`Compress-Archive`（剔除 `__pycache__`）。