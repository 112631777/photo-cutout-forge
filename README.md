# photo-cutout-forge · 摄影素材 → 抠图主体 + 书法艺术海报

> 把「摄影素材」编译成海报纸级主视觉的**生产级 Skill** —— 抠主体 + 材质撕口 + 书法落字，
> 五套双语母版，全程可量化机检。
>
> 不是提示词模板，而是**有输入契约、有决策树、有验收口径、有反面清单**的视觉生产系统。

本仓库收录该 Skill 的**中文版与英文版两套完整实现**，功能等价、语言不同。

---

## 一、仓库结构

```
photo-cutout-forge/          中文版
├── SKILL.md                 技能入口：输入契约、默认出图规范、决策树、目录、快速上手
├── references/              7 篇参考文档（kraft-tear 撕纸路线为主文档）
│   ├── kraft-tear.md            撕纸路线：两条轮廓源、三输入、色彩三模式、排障
│   ├── cutout-craft.md          抠图：候选提示词模板与排障表
│   ├── composition-auto.md      五版式参数、决策规则、文字区、plan 契约
│   ├── workflow.md              完整命令（候选板、排障）
│   ├── calligraphy.md           书法落字规范
│   ├── qa.md                    出图验收口径
│   └── ref-posters.md           10 张参考海报的读法 + 14 条可复用招式
├── scripts/                 16 个脚本（取形 / 撕裂 / 四条撕纸路线 / 构图 / 出图验收）
│   ├── cutout.py                白底 → 透明底（含 --auto-white）
│   ├── auto_compose.py          背景处理 + 自动构图（先背景）
│   ├── band_mask.py             撕口带的形状与位置（横/竖向）
│   ├── torn_edge.py             光滑取形 → 二维撕裂边缘（多尺度 + 咬痕 + 纤维毛边）
│   ├── kraft_tear.py            撕纸 A 路线：窗口 = 抠图主体
│   ├── kraft_photo.py           撕纸 B 路线：窗口 = 实拍原图（推荐，窗口连续、无素材色混入）
│   ├── kraft_window.py          竖向不规则开窗
│   ├── kraft_full.py            满幅铺底
│   ├── motif_band.py            文化母题带
│   ├── art_title.py             书法标题
│   ├── pick_ink.py              从画面取「占比最大的深色」当字色
│   ├── textzone_glow.py         左下文字区光晕（深底排字护读）
│   ├── board.py                 候选拼板
│   ├── render_png.py            HTML 母版 → PNG（无头 Edge/Chrome）
│   ├── check_contrast.py        文字对比度机检（门槛 4.5:1）
│   └── text_contrast.py         对比度计算
└── assets/
    ├── poster-*-master.html     5 套双语母版（cutout / column / axis / editorial / sandwich）
    ├── presets.json             版式预设
    ├── fonts/                   10 款字体（中文书法 + 英文 Inter/EB Garamond）
    ├── material/                4 张材质素材（岩壁 / 石面 / 牛皮纸）
    └── ref-posters/             10 张参考海报 + 联系表
photo-cutout-forge-en/       英文版（同上结构，内容为英文）
```

两包**各自自带全部资源**、可独立安装使用；除文本类文件（`SKILL.md`／`references/`／`scripts/`／母版 HTML／`presets.json`）外，
字体、材质素材与参考海报为同一批文件。

---

## 二、输入契约：三件套（缺一不可，缺了就必须问用户）

| # | 输入 | 作用 |
|---|---|---|
| ① | **含主体物的实拍原图** | 撕口窗口的**内容** + 剪影源 |
| ② | **材质素材图** | 背景纹理（岩壁／石面／纸…），背景随上传素材自动适配 |
| ③ | **主体物描述** | 一段话，说明要抠取的是**哪一层／哪一部分**；写进图生图提示词，决定白底候选的剪影识别纯度 |

> ③ 不可省。实测：无描述内孔率 10.19% ／描述写作「条带」11.31% ／
> 改为「一整面完整连续的墙，不是条带、不是碎片」→ **0%**。
> 主体识别的准确度几乎全压在这段描述上。

**输出**：同一母版下的中英双语成品（2400×1350 与 4800×2700 两档）＋ 设计说明。

---

## 三、核心设计决策

1. **三段式顺序不可换：背景 → 主体 → 文字。** 文字先落会绑架背景的明度与色相，画面变灰变淡。
2. **取形由主体形态定**：横向带 / 竖向开窗 / 斜向块 / 满幅铺底，不机械套模板。
3. **内容与材质分层**：避免材质颜色混入主体、避免内容混杂。
4. **轮廓源两条路**：AI 剪影 ／ **照片描线**（AI 剪影几何与实拍透视不符时的回退：用实拍轮廓线生成同尺寸 mask，配 `--k 1.0 --smooth 21`）；
   压缩弧系数 `k<1` 会把手撕感做出来，但在多翼场景会把轮廓压成「沙丘波浪」——**轮廓保真优先**。
5. **机检是成稿最后一道闸门**：文字与其背后底场的对比度逐项计算，门槛 **4.5:1**，全部达标方可交付。

---

## 四、环境依赖

- **Python 3** ＋ `numpy` ＋ `Pillow`（仅此两项第三方依赖，其余为标准库）
- **无头浏览器**：调用系统自带 **Edge / Chrome**（不依赖 Playwright）
- **字体随包分发**，无需额外安装

```bash
pip install numpy Pillow
```

---

## 五、快速上手

```powershell
# 输入三件：①含主体物的实拍素材 ②材质素材（背景纹理）③主体物描述
New-Item -Force -ItemType Directory cand, cut, out | Out-Null

# 1) 按主体描述改写模板句，AI 图生图出白底候选（三套模板见 references\cutout-craft.md）
#    落盘示例：cand\A2.jpg（全彩） cand\B.jpg（墨剪影） cand\C2.jpg（双色平涂）

# 2) 白底 → 透明底
python photo-cutout-forge\scripts\cutout.py --image cand\A2.jpg --out cut\A2.png --mode color --trim --pad 16

# 3) 背景处理 + 自动构图（先背景！）
python photo-cutout-forge\scripts\auto_compose.py --source src-small.jpg --subject cut\A2.png `
    --preset 青金 --seed 3 --out out\bg.A2.png --plan out\plan.A2.json --debug out\debug.A2.png

# 3B) 撕开素材层路线（推荐 B：窗口 = 实拍原图）
python photo-cutout-forge\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --material material\rock.sand.png --zoom 1.45 --wall-top-row 1550 --out out\bg.rock.png

# 4) 落字（背景定稿后）：拷母版 + fonts + bg → 改文案 → 渲染 + 机检
Copy-Item photo-cutout-forge\assets\poster-cutout-master.html out\poster.html -Force
Copy-Item photo-cutout-forge\assets\fonts out\fonts -Recurse -Force
Copy-Item out\bg.A2.png out\bg.png -Force
python photo-cutout-forge\scripts\render_png.py --html out\poster.html --out out\poster.png --scale 2 `
    --qa-bg out\poster.bg.png --boxes out\poster.boxes.json
python photo-cutout-forge\scripts\check_contrast.py --boxes out\poster.boxes.json --bg out\poster.bg.png
```

完整命令（含候选板与排障）见 `references/workflow.md`；默认出图规范见 `SKILL.md` §〇。

---

## 六、来源与授权

- 本仓库是《人工智能与设计创新》课程作业（一）**第 22 组**（朱智贤／庞煜莹／郑越／陈诗祺／王童全）的测试对象，
  配套测试报告与结果统计文档另行提交。
- **字体授权**：Inter、EB Garamond 为 SIL OFL；中文书法字体（Ma Shan Zheng / Liu Jian Mao Cao / Zhi Mang Xing）
  来自 Google Fonts（OFL）。再分发请保留原始授权说明。
- **参考海报**（`assets/ref-posters/`）版权归原作者，仅作排版学习参考，不作商业使用。

---

## English

**photo-cutout-forge** is a production-grade skill that compiles photographic sources into
poster-grade bilingual key visuals: subject cutout + torn-material window + calligraphic typography,
with five bilingual master templates and machine-checked text contrast (WCAG 4.5:1).

**Input contract (three items, all required):** ① a real-world photo containing the subject
(window content + silhouette source) ② a material image used as the background texture
③ a written description of the subject (fed into the image-to-image prompt and decisive for
cutout purity).

**Output:** the same master rendered in both Chinese and English, at 2400×1350 and 4800×2700,
plus a design note. See `photo-cutout-forge-en/SKILL.md` for the full English specification.
