---
name: photo-cutout-forge
description: 摄影素材 → 抠图主体 + 书法艺术海报：从照片抠出主要部分（白底→透明底），原图经取景/放大/裁剪/蒙版/双色调处理成背景（柔焦背景窗或提取双色渐变底场），主体立于纸面、书法落字，先背景后文字；另有「撕开素材层」路线——三输入（含主体物原图＋材质素材图，如岩壁/石面/纸＋对主体物的描述——描述写进候选提示词提升识别），撕口沿主体轮廓弧撕开、中缝露出内容，背景随上传素材自动适配。适用场景：展览／演出／节庆主视觉；任何「照片抠图＋书法标题」风格的海报生成。触发词：抠图海报、剪影主体、白底抠图、自动构图、书法海报、纸面、双色调、蒙版、撕纸海报、素材背景、岩壁背景、机检。
---

# photo-cutout-forge · 摄影素材 → 抠图主体 + 书法艺术海报

> 把一张照片变成「抠图主体立于纸面、书法落字」的展览主视觉：
> 从原图抠出主要部分（抠图／剪影），原图经取景放大、裁剪、蒙版、双色调融合处理成背景，
> 先处理背景、再排文字；构图四版式由脚本按主体形态**自动选择**（另有满幅长卷 `hero-band` 可人工指定），并写入中文理由。
>
> 另有「撕开素材层」路线（`kraft_tear.py`／`kraft_photo.py`，**三输入**：一张含主体物的实拍素材＋一张材质素材
> （背景纹理，背景随上传素材自动适配——岩壁／石面／纸等）＋**对主体物的描述**——描述写进白底候选的
> 图生图提示词，显著提升抠图识别纯净度）：整幅素材层、上下撕口沿主体轮廓弧撕开，
> 中缝露出内容——窗口可用抠图主体（A）或**实拍原图（B，推荐：窗口连续、无素材色混入）**；详见 `references/kraft-tear.md`。
>
> 触发场景：展览／演出／节庆主视觉；任何「照片抠图＋书法标题」风格的海报生成。
> 关键词：抠图海报、剪影主体、白底抠图、自动构图、书法海报、纸面、双色调、蒙版、机检。
>
> 姊妹 skill：photo-art-forge（转译／拼贴路线，九范式）；本 skill 走「抠图主体」路线，四自动版式＋满幅长卷。

## 〇、默认出图契约（★ 老大 2026-10-11 定，**以后默认按这套走**）

> 老大原话：「以后我让这个 Skill 产出海报都是这个逻辑……使用的中英文文字要求（大小和版式等）
> 就是上述我不断对你训练过程得出的当前结果，**不一定每次都需要多种版式**。
> 如果有特殊要求会和你直接说明。」

### 输入 = 三件套（缺一不可，缺了就问）

| # | 输入 | 说明 |
|---|---|---|
| ① | **材质素材图** | 背景纹理：破败土墙／岩壁／石面／纸…（`--material`） |
| ② | **场景或物品图** | 含主体物的实拍原图（`--photo`） |
| ③ | **主体物描述** | 一段话，说明要抠取的是**哪一层／哪一部分**（写进白底候选提示词，显著提升抠图纯净度） |

> ★★ **大字块只放在材质空白区，不压抠出来的图案**（2026-10-12 老大定）——
> 「以后大块的文字尽量也不要放在遮挡抠图图案的地方」。
> 空白区要**量**不要猜：把窗口 mask 与画布对齐后打「材质空白率网格」（16×8 格），
> 取 100% 的整块放标题；参考案例：`test/case17-walls/run_case17.py` 里那段网格打印。
> 标题也**不一定是竖排**：横排大小错落（参考 13/12 的「非遗文化之美」）同样成立，
> 按空白区的形状选（窄高→竖排；宽扁→横排）。
>
> ★★ **字色从画面里取**（2026-10-12 老大要的）：「可以给 Skill 加上**提取画面中占比最大的深色**
> 去给字体加一个颜色，会更和谐」→ `pick_ink.py` 取暗部最重的一簇当 ink（＋次级 ink2）。
> ⚠ 取样取**源场景**（成品图的暗部被材质灰调主导，会取出灰的）；
> ⚠ `--max-lum` 要按**最苛刻的小字底色**反推并**留余量**（本案 0.0125 时 f-2 只有 4.49，收到 0.011 才过）。
>
> ★★ **画面各位置的比重也要协调**（2026-10-12 老大提醒）：不要让某一角挤满、另一角空荡；
> 落字后回看一眼整体的**视觉重量分布**（标题、小字、信息条、留白各占多少）。
>
> ★ **落字之前先看图**：`assets/ref-posters/` 里是老大直接放进 skill 的 **10 张优秀案例**
> （山高水長／敦煌博物展／吉光片羽／非遗文化之美×2／竹编艺术／徽州灯彩 ＋ 「壁上万象」时期的
> 三张母本：EASTERN ESSENCE／ORIENTAL ZEN／CHINA 2025 —— 后三张正是 sandwich／axis／editorial
> 三套骨架的**原始出处**）。
> **排版布局从它们身上学，不要凭印象回忆** —— 读 `references/ref-posters.md`
> （内含每张的读法 ＋ 14 条可复用招式 ＋ 落地方式）。
> **只学"文字怎么摆"，字体与画布规格不变**（中文书法体系／英文 Inter；1500×1875）。

> ③ 不要省。实测：无描述内孔率 10.19% ／字面「条带」11.31% ／
> 完整连续表述（「三面墙彼此连续衔接、构成完整环抱结构，是一整面完整连续的墙，
> 不是条带、不是碎片，不切割、不分离」）→ **0%**。**主体识别的准确度几乎全压在这段描述上**，
> 且要写清「要哪一层」（踩过：把展墙抠了，老大要的是半透明纱幕）。

### 默认产出

1. **路线**：撕开素材层。**先判断取形方向**（按主体形态，别机械套）：

   | 主体形态 | 取形 | 命令 |
   |---|---|---|
   | **横向一片**（墙面、横幅、长卷） | 横向撕口带 | `band_mask.py --orient h --shape flat/pinch` → `kraft_photo.py`（B 路线，窗口＝实拍原图）；**要横向选景就换 `kraft_window.py`**（见下方 ★） |
   | **竖向一团**（展示柜、立像、器物、单个投影） | **竖向不规则开窗** | `band_mask.py --orient v --shape vpatch --yspan a,b` → **`kraft_window.py`** |
   | **要斜贯全幅、把海报劈开** | **斜向不规则块** | `band_mask.py --shape diag-rag --rotate 41` → **`kraft_window.py`** |
   | **要照片铺满整张海报**（像参考 06/07） | **满幅铺底** | **`kraft_full.py`**（＋`--scrim` 给文字压出暗底子） |

   > 两条取形都要再走一遍 **`torn_edge.py`**（二维撕裂：多尺度位移＋咬痕＋纤维毛边）——
   > `band_mask` 出来的是"切得有波浪"的光滑形状，**撕**的质感来自 torn_edge，
   > 而"照片和纸发生关系"来自 `kraft_window` 的**质感三件套**（`--seam/--fiber/--grain`）。
   > 判据与踩坑见 `references/kraft-tear.md` §1.6–1.9。

   > 竖向开窗是 2026-10-11（case16 展示柜）新加的第三条路线：材质铺满，开一块**竖向不规则贴片**
   > 露照片。横向带会把竖向主体切成上下两截，这时就该换方向。
   > 判据与踩坑见 `references/kraft-tear.md` §1.6／§1.7。

   > ★★ **取形方向与脚本是解耦的**（2026-10-12 加）：`kraft_window.py` 的机制（只取 mask 的 alpha ＋
   > 照片按 `--scale/--focus` 落位）**与取向无关** —— **横向撕口带也能用它**，而且它独有 **`--focus` 横向选景**。
   > 判据：撕口带路线需要「照片里取哪一段」（主体旁有不想要的元素、要把某一侧裁掉）→ 走 `kraft_window`；
   > 只需居中裁两侧（`--zoom`）→ `kraft_photo` 更省事。
   > ⚠ 两条脚本对 mask 的**锚定方式不同**：`kraft_photo` 把 mask **上缘均值**锚到 `--yA`（只吃形状与带高，绝对位置无所谓）；
   > `kraft_window` **直接用 mask 的绝对 alpha**（`band_mask` 控制点的比例就是画布位置）。
   > 详见 `references/kraft-tear.md` §1.11。
2. **中英各一版**：`body[data-lang="en"]` 一键切，共用同一份母版。
3. **默认只出一套骨架**（不每次都出多版式）。骨架按素材选：
   - 撕纸类背景（横向中缝）：`poster-sandwich-master.html`（顶栏＋底栏，最稳）
   - 文字要极克制、中段全留图：`poster-axis-master.html`（中轴居中）
   - 想要大留白：`poster-editorial-master.html`（左文＋大留白）
   - **竖向开窗 ＋ 文字要竖排错落**：`poster-column-master.html`（竖排不规则）
   - **满幅铺底**：同样用 `poster-column-master.html`，body 加 **`data-full`**
     （竖排标题左上／右缘竖排小字／左缘小标签／**底部裁切超大英文**；浅色字模式）
   - 非撕纸场景：`poster-cutout-master.html`（四版式自动选）
   **要出几套、要哪套，以老大当次说明为准。**
4. **文字规范 = 当前定稿值**（不要重新发明，也不要退回去）：
   - **信息一条不删**：主标题／副题／tagline／展期／开放时间／地点／**预约观展 CTA**
     （细则见 `references/calligraphy.md`「信息完整性」）。
   - 中文：标题志莽行书 ＋ **艺术字效果**；**副题／tagline 用马善政毛笔楷书**（传播语属书法层）；
     只有展期／时间／地点／CTA 纯信息走 sans。
   - 英文：**Inter**，标题 **Black 900**；字号／版式照 `calligraphy.md`
     「三套母版的英文落地值」表（sandwich 102 ／ axis 102 ／ editorial 146+88）。
   - 中轴骨架**主次比例**：主标题 ≥ 题眼单字的 2 倍（落地 152 ／ 70）。
5. **必过验收**：`check_contrast.py` 全项达标（无 overflow）＋ `text_contrast.py` 诊断
   ＋ 两项人目 Gate：**四边零异色窄带**、**文字不压中缝**（阈值随取形重量）。
6. **★★ 版面美观底线（老大 2026-10-12 定，「以后按这套走」）**——机检全过 ≠ 好看，这三条与人目 Gate 同级：

   | 要求 | 量化口径 | 不达标怎么办 |
   |---|---|---|
   | **标题要大** | 主标题按「**落字区能放多大**」定，**不是**照参考海报的小字比例。两词＋徽标的顶栏：`字号 ≤ (版心 − 徽标) ÷ (2.8 × 词数)`（sandwich 两词各三字＋徽标 84px → 上限 ≈225px，实战取 208px） | 先用 `getlength` 量字宽再定字号，**改行**优先于缩字号 |
   | **不要留白太多** | ① **图像窗／主体占画面 ≥ 45%**（2026-10-12 案例 47.2%）；② 每条纸带里**文字块的上下余白之和 ≤ 文字块自身高度的 1.5 倍** | 按「① 改行／改结构 ② 收字号 ③ 调位置」处理——**不许删信息** |
   | **整体要美观** | 收尾回看整幅的**视觉重量分布**（标题／小字／信息条／图像／留白各占多少），四角不要一角挤满、一角空荡 | 给低重量侧补字号或补一枚信息元素——**不靠加装饰** |

   > ★ 另两条同级的收尾动作：**字色／印色都要能从素材里找到出处**（`pick_ink.py` 取画面主深色；
   > 素材里有暖色矿物／鎏金／木格栅时，用一枚**朱砂方印**当暖色落款点，比加装饰有效）；
   > **落字之前先看 `assets/ref-posters/`**（只学"文字怎么摆"）。

### 特殊要求覆盖默认

当天说了「要三套骨架」「换配色」「改字号」「不要 CTA」之类，**当次说明优先**，
但**信息完整性**与**机检＋两项人目 Gate** 是底线，不因特殊要求跳过。

## 一、五条硬要求 → 管线对照

| 要求 | 落点 |
|---|---|
| ① 可自主选择构图 | `auto_compose.py` 读主体宽高比＋质量重心自动选四版式之一（hero-top / right / left / centre），理由写入 `plan.json`；可 `--layout` 覆盖，满幅长卷 `hero-band` 为人工选项 |
| ② 书法艺术字体，不用常规字体 | `assets/fonts/` 三款开源书法字体（志莽行书／马善政毛笔楷书／柳建毛草）＋母版字体体系；sans 只用于现代信息层。**英文版用 Inter**（Black/ExtraBold/Bold/SemiBold/Medium/Regular，SIL OFL）——`body[data-lang="en"]` 一键切英文排版，细则见 `references/calligraphy.md` |
| ③ 原图放大／缩小／裁剪／蒙版 → 更美的背景 | 背景窗：取景 `--focus` → 放大 `--bd-zoom`（默认 2.8）→ 裁剪 → 双色调 LUT → 彩度保留 → 柔焦 `--bd-blur` → 向纸色融合 `--wash` → lens 羽化蒙版 → 正片叠底上纸；`--no-backdrop` 可整条去窗（纯纸面）；**`--bg-mode color`：不叠窗，从原图提取「主色＋副色」做偏置双色渐变底场（主色约 2/3、副色自下缘斜入，平滑无斑点），`--bg-color "#RRGGBB"` 可指定主色；方向 `--bg-grad {diag,up}`、四缘压暗 `--bg-vignette`、两色提亮 `--bg-lift`** |
| ④ 抠图提取主要部分，其余留白 | AI 白底三候选（全彩／墨剪影／双色平涂；提示词含用户对主体物的描述）→ `cutout.py` 亮度→alpha＋去噪门控 → 透明底主体 over 上纸（可选绘画层：`--shadow` 落纸投影、`--reflection` 纸面水影、`--paper` 覆盖纸色；主体强化：`--subject-pop` 提饱和/对比、`--subject-paint`「重绘」鲜明色块、`--subject-lift` 提亮）；纸面其余留白给文字 |
| ⑤ 先背景、后文字 | 管线强制两段：`auto_compose.py` 出 `bg.png`（含内置 checks）→ 母版只做文字排版（**四套母版**：四版式 `poster-cutout-master.html` ／ 顶栏＋底栏 `poster-sandwich-master.html` ／ 中轴居中 `poster-axis-master.html` ／ 左文＋大留白 `poster-editorial-master.html`；后三套中英双语、均适合撕纸/中缝类背景） |

## 二、目录

```
photo-cutout-forge/
├── SKILL.md                        本文档
├── assets/
│   ├── poster-cutout-master.html   书法排版母版（四版式 data-comp，含机检仪器）
│   ├── poster-sandwich-master.html 「顶栏＋底栏」母版（中英双语，含机检仪器；
│   │                               适合撕纸/中缝类背景——中段留给图像、上下两条素材带承字）
│   ├── poster-axis-master.html     「中轴居中（汉字／英文交替）」母版（中英双语，含机检仪器；
│   │                               最克制——文字占一条中轴，上下单字合成一个词，中段全留给图像）
│   ├── poster-editorial-master.html「左文＋大留白」母版（中英双语，含机检仪器；
│   │                               文字占左下一条窄列，信息量最小、留白最大）
│   ├── poster-column-master.html   「竖排不规则」母版（中英双语，含机检仪器；
│   │                               大标题成**错落字柱**，配竖排小字与细线标签，
│   │                               与「竖向开窗」配套——参考《敦煌博物展》的排法）
│   ├── presets.json                6 组双色调预设（默认「青金」）
│   ├── ref-posters/                ★ 参考海报库（**10 张**优秀案例原图 ＋ _contact-sheet.png 速览）——
│   │                               老大直接放进 skill，落字前先看；读法见 references/ref-posters.md
│   ├── material/                   背景素材库（rock.sand 浅砂砂岩／rock.aged 风化开裂／rock.slate 灰调石面／kraft.cream 奶油纸）
│   └── fonts/                      中文：ZhiMangXing / MaShanZheng / LiuJianMaoCao；
│                                   英文：Inter ×6 字重、EB Garamond（可变）—— 均 SIL OFL
├── scripts/
│   ├── cutout.py                   白底素材 → 透明底主体 PNG（alpha，color/ink/duotone）
│   ├── auto_compose.py             背景处理＋自动构图 → bg.png ＋ plan.json（内置 checks；窗口／color 提取色底场双路线）
│   ├── render_png.py               HTML → PNG（无头 Edge/Chrome，可拍 QA 背景与文字盒）
│   ├── check_contrast.py           可读性机检（WCAG：字框内最暗 5% 单像素口径）
│   ├── text_contrast.py            文字/底板对比度诊断（中位口径＋背景杂度 std）
│   │                               ＋ 护读底衬生成（--plate）；见 references/qa.md §二
│   ├── board.py                    多图网格拼版（候选板／归档图）
│   ├── kraft_tear.py               撕开素材层·A（窗口＝抠图主体；--material 背景素材）
│   ├── kraft_photo.py              撕开素材层·B（窗口＝实拍原图，推荐；--material 背景素材）
│   ├── kraft_window.py             ★ 撕开素材层·C「**竖向不规则开窗**」（材质铺满，开一块
│   │                               竖向贴片露照片）；用 band_mask --orient v／--rotate 取形；
│   │                               内置**质感三件套** `--seam`（纸厚暗线）／`--fiber`（纤维搭边）／
│   │                               `--grain`（同纸颗粒）；见 references/kraft-tear.md §1.7–1.9
│   ├── kraft_full.py               ★ 撕开素材层·D「**满幅铺底**」（照片铺满整张画布＋材质当纸纹＋
│   │                               文字区 scrim 压暗）；学参考 06/07/13「尽可能让海报铺满」，
│   │                               见 references/kraft-tear.md §1.10
│   ├── pick_ink.py                 ★ 从画面里取**占比最大的深色**当字色（保底压暗到 L ≤ --max-lum，
│   │                               不牺牲对比度）；见 references/qa.md「字色取画面主深色」
│   ├── torn_edge.py                ★ 光滑取形 → **二维撕裂边缘**（大尺度位移 ＋ 随机椭圆咬痕 ＋
│   │                               纤维毛边，保留连续 alpha）；"取形太规整、缺乏自然感"的解药，
│   │                               见 references/kraft-tear.md §1.9
│   ├── band_mask.py                生成取形 mask：`--orient h` 横向撕口带（flat／pinch 中间凹
│   │                               两端扩）／`--orient v` **竖向开窗**（vpatch，可 --yspan 限纵向
│   │                               范围，两端也做不规则收口）；判据见 references/kraft-tear.md §1.6/§1.7
│   ├── art_title.py                中文大标题「艺术字」参数生成（大小错落／纵向拉长／
│   │                               高低错位／轻微旋转，seed 可复现）；细则见 calligraphy.md
│   ├── motif_band.py               纹样图带（主体纹样切片→平面化→S 形飘带排布；实验路线）
│   └── textzone_glow.py            左下文字区光晕（深底排字护读）
└── references/
    ├── cutout-craft.md             提示词模板（含主体描述规则）＋alpha 提取工艺＋排障
    ├── composition-auto.md         五版式参数、决策规则、文字区、plan 契约、CLI
    ├── calligraphy.md              书法字体与排版规范
    ├── ref-posters.md              ★ 参考海报库的读法（10 张案例 × 14 条招式 × 落地方式）
    ├── workflow.md                 端到端流程与命令
    ├── kraft-tear.md               撕开素材层路线（三输入／素材库／三色彩模式／取景／陷阱）
    └── qa.md                       两道机检口径＋目检 Gate
```

## 三、视觉模型（三步合成，先后不可换）

```
纸面（make_ground：预设纸色＋纹理）
  → 背景窗（原图经 zoom／裁剪／柔焦／双色调／wash，lens 蒙版，multiply 贴上）
    → 主体（透明底抠图，over 贴上）
      → 之后才是文字（母版只做排版，不碰背景）

或（--bg-mode color，提取双色渐变底场——无窗）：
提取色底场（bg_ground：原图「主色＋副色」偏置平滑渐变，零肌理叠加；
            方向 --bg-grad、四缘压暗 --bg-vignette、两色提亮 --bg-lift）
  → 主体（透明底抠图——重绘 --subject-paint／提色 --subject-pop／提亮 --subject-lift——over 贴上）
    → 之后才是文字（body 加 data-theme="deep"，深底浅字）
```

## 四、快速上手

```powershell
# 输入三件（初始素材）：①含主体物的实拍素材 ②材质素材（背景纹理）③对主体物的描述（改写进候选提示词，规则见 references\cutout-craft.md §①）

# 0) 目录
New-Item -Force -ItemType Directory cand, cut, out | Out-Null

# 1) 按主体描述改写模板主体句，AI 图生图出白底候选（三套模板见 references\cutout-craft.md；同题多跑再挑）
#    落盘示例：cand\A2.jpg（全彩） cand\B.jpg（墨剪影） cand\C2.jpg（双色平涂）

# 2) 白底 → 透明底（米黄底加 --auto-white；细节见 cutout-craft.md 排障表）
python .trae\skills\photo-cutout-forge\scripts\cutout.py --image cand\A2.jpg --out cut\A2.png --mode color --trim --pad 16

# 3) 背景处理＋自动构图（先背景！三候选同 preset/seed 跑，拼板选方向）
python .trae\skills\photo-cutout-forge\scripts\auto_compose.py --source src-small.jpg --subject cut\A2.png `
    --preset 青金 --seed 3 --out out\bg.A2.png --plan out\plan.A2.json --debug out\debug.A2.png

# 3B) 撕开素材层路线（三输入：--photo 含主体物原图 ＋ --material 材质素材图 ＋ 主体描述（已用于候选提示词）；推荐 B：窗口＝实拍原图）
#     素材色彩三模式：默认重上色（--paper-dark/--paper-light 定色阶）｜保留原色直出（--material-gain 1.0）
#     ｜保留原色提暗部（--material-gamma 0.52 幂曲线）——详见 references\kraft-tear.md
#     轮廓源：AI 剪影几何与实拍不符（多翼/U 形、窗口落进地板行/露天花）→ 换「照片描线 mask」＋ --k 1.0 --smooth 21（kraft-tear.md §1.5）
python .trae\skills\photo-cutout-forge\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --material material\rock.sand.png --zoom 1.45 --wall-top-row 1550 --out out\bg.rock.png
python .trae\skills\photo-cutout-forge\scripts\textzone_glow.py --bg out\bg.rock.png --out out\bg.glow.png `
    --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"   # 探针＝左下文字区，按版式调整

# 3C) 提取色底场路线（替代背景窗；柔焦窗被读成「模糊照片贴片」时换这条）
#     敦煌案例定稿参数：竖版渐变＋四缘压暗＋底场/主体提亮＋主体重绘＋投影（机检 12/12）
python .trae\skills\photo-cutout-forge\scripts\auto_compose.py --source src-small.jpg --subject cut\A2c.png `
    --bg-mode color --bg-color "#1F3F6E" --bg-grad up --bg-vignette 0.18 --bg-lift 0.30 `
    --subject-paint 1.0 --subject-lift 0.25 --shadow 0.35 --layout hero-band --seed 3 `
    --out out\bg.color.png --plan out\plan.color.json

# 4) 落字（背景定稿后）：拷母版＋fonts＋bg → 改文案 → data-comp=plan.layout → 渲染＋机检
#    深色底场（3C）再加 data-theme="deep"（深底浅字），并把 .stage 的 --stage-bg 改为与底场同值
Copy-Item .trae\skills\photo-cutout-forge\assets\poster-cutout-master.html out\poster.html -Force
Copy-Item .trae\skills\photo-cutout-forge\assets\fonts out\fonts -Recurse -Force
Copy-Item out\bg.A2.png out\bg.png -Force
python .trae\skills\photo-cutout-forge\scripts\render_png.py --html out\poster.html --out out\poster.png --scale 2 `
    --qa-bg out\poster.bg.png --boxes out\poster.boxes.json
python .trae\skills\photo-cutout-forge\scripts\check_contrast.py --boxes out\poster.boxes.json --bg out\poster.bg.png
```

完整命令（含候选板、排障）见 `references/workflow.md`。

## 五、案例实证（敦煌「壁上万象」）

- 素材：弧形矿物壁画展厅；三候选 → `cut\A2.png`（主选）／`B.png`／`C2.png`；A2 自动判定 `hero-top`。
- 迭代修图：原主体被垂下的纱帘遮挡 → 图生图编辑去除遮挡、补全被遮墙面（`cand\A2c.jpg`）→ 重抠 `cut\A2c.png`。
- 定稿走 **`hero-band` 满幅长卷**（人工指定）＋青金浅纸＋投影 0.30＋含蓄倒影 0.18：
  主体满幅横贯 `[0,56,1500,935]`、无背景窗、纸面承字；
  checks 全过（subject×zone 0.0 ／ backdrop×zone 0.0 ／ blank_ratio 0.7153 ／ 落画 true）。
- 成品机检 12/12 全过（主标题 11.28，最小 presenter 5.63），overflow 全 false。
- 撕纸装饰版定稿走 **B 路线**（窗口＝展览实拍原图，取景 `--wall-top-row 1400`；墨字近黑 `#171009` 系＋左下光晕 gain 0.303）：
  机检 12/12 全过（最低 label 4.76）；A/B 对比见案例目录 `trial.kraft\board.AB.poster.png`。
- 素材驱动背景（用户反馈「改用岩壁素材更契合主体」）→ skill 改**素材双图输入模型**（同日再升级为三输入，见下条）：`--photo` 含主体物原图 ＋
  `--material` 背景素材图（岩壁/石面/纸，背景随上传素材自动适配）；取景升级 `--zoom 1.45 --wall-top-row 1550`
  （窗口 539..1025、照片行 1549..2487）。三素材试版——浅砂砂岩（色阶 163,146,126→250,240,226＋`--detail 3.0`）
  12/12（min 6.54）／风化开裂岩壁：重上色提亮 12/12、**保留原色** γ0.52 12/12（min 4.63；用户反馈「原有颜色
  被抹去」后新增 `--material-gain`／`--material-gamma`）／灰调石面原色直出。详见 `references\kraft-tear.md`。
- 背景二次迭代（用户反馈「柔焦背景窗模糊又难看」）→ `--bg-mode color` 提取色底场：
  自动聚类 #60432A（青铜）；定稿石青浓 `#1F3F6E`（壁画石青系深蓝，近参考海报）＋母版 `data-theme="deep"`。
- 背景三次迭代（用户反馈「老是有斑点，不高级」）→ 底场去肌理，改「主色＋副色」偏置双色渐变：
  auto #60432A→#3E4E61（蓝灰副色）、石青浓 #1F3F6E→#614C35（暖簇深赭副色）；
  机检 12/12 全过（最低 6.09）；旧肌理/新渐变对比板见 `trial.color\board.grad.png`、`board.gradposter.png`。
- 背景四次迭代（用户反馈「渐变试试从下向上？主体不够突出」）→ `--bg-grad up` 竖版渐变（副色自下缘整幅升起、主色占上约 2/3）
  ＋ `--bg-vignette 0.18` 四缘压暗 ＋ `--shadow 0.35` 落纸投影 ＋ `--subject-pop 0.25`；
  主体「重绘」`--subject-paint 1.0`（去噪→提饱和提亮→对比→色彩量化）最贴近参考海报的鲜明色块观感。
- 背景五次迭代（用户反馈「整体亮度不够」）→ `--bg-lift`／`--subject-lift`（保色相只抬明度）：H 档 0.18/0.15 与
  I 档 0.30/0.25 两版均机检全过（I 档底场更亮，tagline 墨色 #D3C5A6→#DDD0B2 提亮一档后 4.77 复过）；
  提亮对比板见 `trial.color\board.lift.poster.png`、`board.lift.bg.png`。
- 三输入升级（用户定调 2026-10-10：调用 skill 初始输入＝含主体素材＋材质素材＋主体描述）→ 候选提示词按描述改写：
  字面「图带」致条带化（内孔 11.31%，反面）；「一整面完整连续弧墙、不是条带/碎片、不切割不分离」得最干净剪影
  （内孔 6.54% vs 无描述 10.19%、上下缘零接触）；  描述后轮廓带变扁 → 撕口窗口变矮（563px vs 891px）→
  `--zoom 1.58` 补偿（窗口 869px、主体放大居中、两侧墙裁切、不露地），定稿 `cases\skill-test-mural-tear\out\bg.png`。
- **案例 04（2026-10-12）｜油画展厅实拍＋浅砂石面**：B 路线横向撕口带，轮廓源＝照片描线 mask（`--k 1.0 --smooth 21`）。
  三候选（A 只取墙面／B 墙面＋上方灰幕／C 完整横带）拼板选 **B**——只取墙面（A）时开口全是白墙，与浅色石面
  **明度太近、撕口读不出来**；带上顶部一条灰幕（B/C）才有层次。定稿 `bg.png` → sandwich 母版 → 中英各一版
  机检 **10/10 全过**、四边零窄带。
  ★ 两条新经验：① **两侧展墙的"墙顶线"在中段比看上去低得多**（左侧近处墙顶在照片 y≈640，中段远处墙顶
  在 y≈900，右侧又升到 y≈370）——只靠眼睛看「天花/墙交界」会把中段墙顶读高 ~150px、撕口就吃到灰幕；
  要用**逐列像素剖面**（`y=x 处从上往下打 RGB`）+ 局部放大网格确认。② **浅色材质上的字色**不能照搬
  `--max-lum` 默认值：浅砂石面暗颗粒 p5≈0.20（线性）→ 反推小字要 `L_ink ≤ 0.0056`，
  实际取 **#0B0C0C（L≈0.0034）** 才留出余量（`--max-lum 0.016` 时 6/10 挂线）。
- **案例 05（2026-10-12）｜弧形灯箱照片墙 ＋ 青海波纹样纸**（文化活动主视觉，brief 明确「标题要大／不要留白太多／要美观」）：
  横向撕口带＋窗口＝实拍原图，但**用 `kraft_window.py` 承载横向带**（不用 `kraft_photo.py`）——
  照片左侧有一块巨型鎏金主面板，其「黃永玉 大事记」与海报标题重复、被撕口切一半就读成错字；
  `kraft_photo` 只能居中裁（`--zoom 1.0／1.15／2.0` 都排不掉左三分之一），
  换 `kraft_window --scale 1.0 --focus 0.56856,0.38531` 一次到位（窗口照片区 x182..932 / y320..796）。
  取形：`band_mask --orient h` 自定义控制点（带高 ≈0.458H、**上下缘都向右上抬 ≈70px**，呼应弧线走向；
  照 `pinch` 预设的哑铃形反而与素材无关）→ `torn_edge --edge 0.017 --bites 0 --fray 0.60 --fray-px 3.2`。
  材质：青海波纸保留原色 `--material-gain 1.0 --detail 2.0`；照片先 2× `LANCZOS` ＋ `UnsharpMask(2.0,62,3)` 预处理。
  母版 sandwich：顶栏 208px 志莽行书（`art_title --style upright`）＋**朱砂方印**（替掉几何徽标当暖色落点）；
  底栏三行完整展讯＋CTA；中英同一文件 `?lang=en` 切。机检中英各 **10/10 全过**（最低 10.25），
  四边零窄带、压窗 0.00%。★ 四条经验见 §六。

## 六、反面清单（实测踩坑）

- 背景窗直接透原图会「照片套照片」：必须柔焦＋wash 才退成「色场」——图底层级是抠图路线的命门。
- 岛式主体背后的 lens 柔光椭圆容易读成「光斑／阴影」；换暖色取景只是缓解，
  优先考虑 `--no-backdrop` 或 `hero-band` 满幅消解（敦煌实测）。
- 「柔焦背景窗」整体可被读成「模糊照片贴片」（敦煌二次迭代用户反馈）→ 换 `--bg-mode color` 双色渐变底场；
  深底落字必须 `data-theme="deep"`，暖黑字落深底机检必挂。
- 底场叠肌理（云斑／织纹／颗粒）会被读成「斑点、不高级」（敦煌三次迭代用户反馈）→ bg_ground 只做双色渐变，
  仅留 0.8σ 抖动防色带；肌理只保留在 window/纸面（make_ground）路线。
- 「主体不够突出」三杠杆：`--shadow` 落纸投影 → `--bg-vignette` 四缘压暗收视线 → `--subject-pop` 提饱和/对比；
  实拍主体要参考海报那种「重绘感」用 `--subject-paint`（0.6–1.0，去噪＋提饱和＋色彩量化）。
- 「整体亮度不够」用 `--bg-lift`／`--subject-lift`（保持色相/饱和，只抬 V）；**深底提亮后全部文字对比整体下滑**，
  tagline 等小字墨色需跟随提亮一档（敦煌 I 档 4.27→4.77 才过线）。
- 米黄底素材不加 `--auto-white` 会整底发灰；`--despeckle` 核过大（>5）会吃掉细条纹。
- 抠出的主体被原图遮挡物（纱幔、立柱）盖住：先图生图编辑「去除遮挡、补全被遮面」再重抠，不要在 alpha 上硬修（敦煌实测：垂帘）。
- 对比不足先加 `--shadow`，纸面太空再 `--reflection`；**倒影 0.30 以下肉眼近乎不可见，可见档约 0.50**。
- 母版是拷贝不是引用：改了 `assets\poster-cutout-master.html` 必须重拷到案例目录再渲染。
- **★ 背景图类名必须与标题艺术字分开**（2026-10-12 修）：五套母版原来写的是 `<img class="art">`，
  与标题艺术字共用 `.art` —— 而 `.art` 带 `padding:0.15em 0.12em` ＋等量**负 margin**
  （本来只是给 transform 留余量），负 margin 会把 `inset:0;width:100%` 的背景图整体推偏 ≈2.4px，
  **成品右缘／下缘各露出 ~5px 的 `--stage-bg` 浅色窄带**。
  → 五套母版已改为 `<img class="bg">` ＋ `.stage > .bg`。
  判据：四边审计里**最外 8px 的 std ≈ 0** 就是漏底色（真实画面内容不可能 std=0），
  别按"材质暗边"放过 —— 这正是「四边零异色窄带」Gate 存在的意义。
- `body[data-comp]` 与 `plan.json.layout` 不一致 = 文字落错区（机检能抓 overlay，肉眼更直接）。
- QA 仪器（`?pf-qa=bg` 与 `#pf-boxes`）不可删，删了 check_contrast 无参照。
- 撕纸路线：素材整张镜像平铺会出现对称蝶形伪影 → 必须「整幅等比放大盖满＋素材原生尺度细部高通叠加」。
- 抠图软边（alpha 0.1-0.4 宽过渡）在深色素材上透底成渗色泥斑 → alpha 收硬为 (m-0.42)/0.10 窄过渡带。
- 撕口弧是轮廓弧的压缩（k<1），弧与轮廓之间必然夹出素材色——要「窗口内完全连续」走实拍原图路线（B）。
- 素材默认「重上色」会把颜色映射到 `--paper-dark/--paper-light` 两色阶，素材自带色斑/裂纹/矿物色被抹掉
  （用户反馈「岩壁原有的颜色被抹去了」）→ 保原色用 `--material-gain`（整体增益）／`--material-gamma`（幂曲线）。
- 素材暗斑落入文字框即机检挂（背景亮度取字框内单像素 P5，深字口径）——纯增益救不了（炸亮部/裁切），
  用幂曲线 `--material-gamma 0.52` 提暗部保亮部（敦煌风化岩壁：γ0.52 后 12/12，min 4.63）。
- 深底光晕增益须用 WCAG 线性亮度（0-1）算 p5：g=(0.26/p5)^(1/2.4)-1+0.005；用 sRGB 255 口径会算错增益。
- 候选提示词用字面形状词（「图带」「条带」）会被生图工具字面化——主体画成漂浮条带、白隙成孔，内孔率反升
  （实测 11.31% ＞ 无描述基线 10.19%）→ 描述改写为「一整面完整连续的…，不是条带、不是碎片，不切割不分离」（6.54%）；
  描述后轮廓带可能更扁、撕口窗口随之变矮（563 vs 891px）→ `--zoom` 补偿（案例 1.58 / WTR 694）。
- 撕纸路线多翼主体（如「左右两侧展示墙」U 形透视）：AI 剪影的墙带比例与实拍不符（案例实测中段下压≈2 倍）→
  窗口底落进地板行、翼顶露天花（用户反馈「只要两边画廊，中间地面被加进来」），调 k/取景/zoom 都对不上 →
  换「照片描线 mask」（照片上控制点折线→同尺寸 alpha 带）＋ `--k 1.0`（撕口＝真实轮廓±tear）＋ `--smooth 21`（保轮廓，
  默认 81 是大波浪）；案例 `cases\skill-test-gallery-tear` 实测：窗口顶＝描线±10px、窗口底＝墙脚之上 ~100 行（不露地）。
- **★ 横向撕口带不是 `kraft_photo` 的专利**（2026-10-12 案例 05）：`kraft_window.py` 的机制
  （只取 mask 的 alpha ＋ 照片按 `--scale/--focus` 落位）**与取形方向无关**，横向带也能用它，
  而且它独有 **`--focus` 横向选景**。判据：需要「照片里取哪一段」（主体旁有不想要的元素／要裁掉某一侧）
  → 走 `kraft_window`；只需居中裁两侧（`--zoom`）→ `kraft_photo` 更省事。见 `references/kraft-tear.md` §1.11。
- **★ 两条 B 路线对 mask 的锚定方式不同**：`kraft_photo` 把 mask 的**上缘均值**锚到 `--yA`
  （所以 mask 的绝对纵向位置无所谓，只吃它的形状与带高）；`kraft_window` 则**直接用 mask 的绝对 alpha**
  （`band_mask` 控制点给的比例＝画布上的位置）。同一张 mask 喂两条脚本，窗口落点会差一截——这是设计，不是 bug。
- **★ `torn_edge --bites` 在长横带上会「打孔」**（2026-10-12 实测）：椭圆咬痕在近满幅长的边界上读成
  一排圆弧／扇贝边（`--bites 18 --bite-size 0.030` 最糟，整条像云朵边；`--bites 10 --bite-size 0.045`
  也留下几处明显圆缺）。**横带取形建议 `--bites 0`**，把不规则性交给
  `--edge 0.017 --edge-scale 22` ＋ `--fray 0.60 --fray-px 3.2`（细碎纤维，更像手撕）；
  咬痕留给**短边界**（竖向开窗／斜向块）。
- **`kraft_window` 的 `--detail` 与 `kraft_photo` 不同量纲**：前者默认 `0.06`（≈无效果），后者 `4.0`。
  拿图案纸（青海波／织物／石面）当材质时，`kraft_window` 要给 **1.5–2.0** 才看得出细部。
- **照片里有「带大字的构件」要当心**（2026-10-12）：展墙主标题面板、招牌、碑刻上的字被撕口切一半
  会读成错字，而且与海报标题重复。处置是**换取景把它整块排除**，不要在 alpha 上硬修；
  居中裁排不掉时走 `kraft_window --focus`。