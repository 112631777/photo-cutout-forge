# 书法字体与排版规范

## ★ 当前定稿字号总表（三套双语母版 · 2026-10-11）

> 这张表就是「当前结果」——**默认出图照此，不要重新发明**。
> 换素材时字号可微调（受落字区与中缝约束），但**层级比例与字体分工不要改**。

| 母版 | 中文 | 英文 |
|---|---|---|
| **sandwich**（顶栏＋底栏） | 主字 **220px**（行书＋艺术字）· 副字 28 · 底栏 **32**（副题/tagline 楷书） · CTA 26 | 主字 **102px / Black 900**（上限 104）· 副字 30 / 700 · 底栏 30（副题 32/700、tagline 24/400） · CTA 26 |
| **axis**（中轴居中） | 主标题 **152px** · 题眼单字 **70**（比例 2.17×）· 底部 **30** · CTA 27.6 | 主标题 **102px / 900** · 单字 74 · 底部 26 · CTA 24 |
| **editorial**（左文＋大留白） | 标题 **128px** · 三行小字 24 · 年份 34（字距 0.62em）· 署名 40 | 标题 **146 + 88px / 900**（两行同宽）· 副题 30/700 · tagline 22 · meta 19（label 17/500）· CTA 24 |
| **column**（竖排不规则 · 2026-10-11 加） | 标题 **190px**（竖排字柱，艺术字错落）· 竖排副题 34 · 竖排 tagline 30 · 竖排小标签 24 · 信息 30 · CTA 28 · 主办 26 | 标题竖排三行 **76/76/120（900）** · 副题 30/700 · tagline 24 · 标签 24/600 · 信息 30 · CTA 28 |
| **column · 斜向版（`data-diag`）** | 标题**两档** **185 / 167**（右柱大、左柱次之，学模板「敦煌＞博物展」）· tagline 横排两行 **46** · 副题竖排 30 · 小标签 26 · 信息 **展期 36 ／ 时间·地点 28** · CTA 30 | 标题四行**两档 66/66/132/132** · 副题 30/700 · tagline **40**/400 · 标签 24/600 · 信息 36/28 · CTA 30 |

**字体分工（三套统一）**：主标题=志莽行书＋艺术字 ／ 副题·tagline=**马善政毛笔楷书**（传播语属书法层）
／ 展期·时间·地点·CTA=纯信息层才允许 sans ／ 英文全部 Inter（标题 Black 900）。

## 字体清单（assets/fonts/，SIL OFL 开源，随包分发）

| 文件 | 字体 | 默认用途 |
|---|---|---|
| ZhiMangXing-Regular.ttf | 志莽行书 | 主标题（--f-brush） |
| MaShanZheng-Regular.ttf | 马善政毛笔楷书 | 副题／短句／印章文字／拼版标签（--f-brush-2） |
| LiuJianMaoCao-Regular.ttf | 柳建毛草 | 可选强调字 |

- 标题层**不用常规字体**（要求 ②）。母版里 sans（--f-cjk-sans）只允许出现在「现代信息层」：主办机构（.presenter）、展讯数值（.meta）、按钮（.cta）——与书法层分工，不参与标题。
- **★ 传播语属书法层，不是信息层（2026-10-11 老大指出）**：副题（「敦煌色彩数字沉浸展」）、
  tagline（「在流动的色彩中，走近千年的想象」）必须走 **MaShanZheng 楷书（--f-zh-brush2）**，
  落 sans／宋体都「太不高级」。**只有展期／时间／地点／CTA 这些纯信息才允许 sans。**
  三套母版已落地：sandwich `.bar-bottom .brush` ／ axis `.foot .f-sub,.f-tag` ／ editorial `.tiny`。
  ⚠ 楷书**不加粗**（font-weight 400）—— 加粗会糊掉笔锋。
- 曾尝试 LongCang（龙藏体），源文件损坏（渲染全空、Pillow bbox 高 0），已弃用；不要重新引入同名文件。
- 母版用 `@font-face` 相对路径 `fonts/…`；**拷贝母版到别处时必须同时拷 fonts/ 目录**。
- 无头渲染（render_png.py）可直接加载本地字体，已验证。

## 字号体系（母版默认，@1500×1875 画布）

| 元素 | 字号 | 说明 |
|---|---|---|
| 主标题 .title | hero-top 196 / hero-centre 196 / hero-right 152 / hero-left 152 | 行高 1.04，字距 0.015em |
| 副题 .subtitle | 44px | MaShanZheng，字距 0.14em |
| 短句 .tagline | 29px | MaShanZheng，字距 0.10em |
| 主办 .presenter | 26px | sans，字距 0.44em |
| 展讯标签 .k | 22px | 金色，字距 0.22em，右对齐（min-width 118px） |
| 展讯数值 .v | 24px | 单行不折（white-space: nowrap） |
| 按钮 .cta | 25px | 墨底纸字，胶囊形 |
| 印章 span | 38px | 2×2 格，104×104 印面 |

- 侧栏版式（hero-right/left）主块宽 43%，标题 152px 时「四字题」约 620px，接近栏宽上限；
  再长就换两行题或缩字号。改字号后**必须复跑 check_contrast**。
- 装饰细线 .ornament 132×2px（金 C9A96A）；hero-left 版式随块右对齐。

## 版面色值与对比度

| 变量 | 值 | 用途 |
|---|---|---|
| --ink | #2A231A | 主标题墨色 |
| --ink-2 | #4A4034 | 副题／数值 |
| --ink-3 | #56503F | 短句／主办（勿再调浅，4.5:1 会破） |
| --gold | #6B4E1E | 展讯标签（可读的金棕；装饰金 #C9A96A 只用于非文字） |
| --seal | #8A3220 | 朱砂印面；印面文字 #F3E7D3 必须显式给 span（QA 读取元素 computed color） |

### ★ 朱砂方印当「落款点」（2026-10-12）

整幅都是米灰调时，**一枚朱砂方印是最省的暖色落款**（比加装饰有效）——
sandwich 顶栏的「左词 ▣ 右词」结构里，中间的几何徽标（`.mark`）可直接换成方印：

```css
.seal { width:94px; height:94px; flex:none; background:#9A3423; color:#F6ECD6;
        font-family: var(--f-zh-brush2); font-size:37px; line-height:1.06;
        display:flex; flex-direction:column; align-items:center; justify-content:center; }
```
```html
<div class="seal" data-text="seal"><span>永</span><span>玉</span></div>
```

- 印章内容**中英版共用**（印是落款，不随语言换；不要翻成拉丁字）。
- 给 `data-text` 让机检也量它：`pf-qa-bg` 只清字色、**印面底色块保留**，所以
  `check_contrast` 量到的是「米白字 vs 朱砂底」（案例 05 实测 6.38:1，达标）。
- `margin-top` 要与**主标题字面的视觉中心**对齐，不是与行盒对齐：
  208px 字号、行高 1.30 时，印顶 ≈ `--top-y + 0.40 × 字号`（案例取 82px）。
- 印别抢标题：宽度按标题字号的 **0.45 倍**左右（208px 标题 → 94px 印）。

## 中文版排版规则

- 标题字距 0.015em；副题/短句 0.10–0.14em；机构 0.44em＋text-indent 同值（首字缩进抵消）。
- 印章「壁上万象」2×2 朱砂印，落于题侧或对角；印是**落款**，不是装饰，位置服从构图（见各版式 CSS）。
- 日期中文格式「2026年11月8日至2027年1月18日」；时间「周二至周日 10:00–20:00」（en-dash）。
- 展讯三行（展期/开放时间/地点）用 `.k+.v` 对；标签金色、数值墨色，居中式等居中版式 `justify-content: center`。

## 英文版排版规则（Inter）

**字体已定为 Inter** —— `assets/fonts/Inter-{Regular,Medium,SemiBold,Bold,ExtraBold,Black}.ttf`（SIL OFL）。
选型依据：参考海报「start business」逐字形比对 —— **i 为方点、a 双层、t 顶部斜切、字重 Black** → Inter；
几何体（Futura / Poppins / Century Gothic）的 i 点是圆的、a 是单层，可排除。
终验：用 Inter Black 渲染同一句 `start business`，与参考逐字母吻合（案例 `11-字体决定性验证.png`）。

**★ 2026-10-11 起三套母版（sandwich/axis/editorial）的英文层也全部切 Inter**（`--f-en`）——
EB Garamond 高对比衬线被老大否掉：「英文文字太纤细了撑不起画面」，指定以旧版定稿
（editorial 英文，Inter Black）为准。标题 **weight 900**，副题 700，tagline 400，信息行 600。

### 旧版定稿的实测字号（对参考图量墨迹得出，@1500 画布）

| 元素 | 字号 | 备注 |
|---|---|---|
| 标题 l1 `VISIONS` | ≈162px / 900 | 两行**同宽 ≈692px**（「两行各自撑满」） |
| 标题 l2 `ON THE WALL` | ≈98px / 900 | 7.03em×98 ≈ 692 ✓ |
| 副题 `DUNHUANG COLOR · DIGITAL IMMERSION` | ≈32px / 700 | |
| tagline | ≈24px / 400 | |
| meta label（DATES/HOURS/VENUE） | ≈17px / 500 | label 比 value 小半档、稍浅 |
| meta value | ≈20px / 600 | |
| CTA 胶囊字 | ≈24px | 胶囊高 ≈53px |

> editorial 实际落地 146/88（参考的 90%）—— 信息行比参考多，块顶受中缝硬约束
> （SEAM 底左端 1191），首跑 156/96 压中缝 53px。**再想放大：先减行，不是删信息。**

### 三套母版的英文落地值（2026-10-11 实测）

| 母版 | 标题 | 约束式 |
|---|---|---|
| sandwich 「两词同排」 | **102px / 900** | `(VISIONS 4.254em + ON THE WALL 6.998em + 字距 0.72em) × S + 徽标 84px ≤ 1332` → **S ≤ 104px** |
| axis 单行居中 | **102px / 900** | `(11.57 + 19×0.04)em × S ≤ 1340`；⚠ Inter Black 更宽，衬线时代的 114px 会超宽 |
| editorial 两行 | **146 / 88px / 900** | 两行各撑满 ≈700px |

- ⚠ **顶栏两词必须单行**：`.w-main` 加了 `white-space: nowrap` ——
  空间不够时**宁可被机检判 overflowX**，也不要静默折行把「两词同排」变成三排
  （2026-10-11 踩过：108px 时 `ON THE WALL` 悄悄折成 `ON THE` / `WALL`）。
- ⚠ **换了字体，度量全换**：Inter Black 的 win 纵向度量比衬线高，axis 行高 1.24 就报 ovY → 提到 1.32。

## 中轴骨架的「主次比例」（2026-10-11 老大指出）

「敦／煌」两个题眼单字与主标题**字号太接近 → 主次不分**。
落地比例：**标题 152px ／ 单字 70px（≈2.17×）**，`--gap` 18→14px 换回高度
（块底边 564.7 ＜ 中缝顶 583 ✓）。
> 判据：**题眼单字是「夹住」标题的括号，不是第二个标题** —— 它只要「能合成一个词」即可，
> 字号不该抢主标题。经验值：**主标题 ≥ 单字的 2 倍**。

用法：`body[data-lang="en"]`（或渲染时 `?lang=en`）。**母版已内置整套英文覆盖，不必再写版式覆盖。**

### 字号：先量宽再定，不要估

栏宽 = 画布宽 × 版式占比（hero-top 62% = 930 ／ hero-centre 80% = 1200 ／ 侧栏 43% = 645）。
Inter-Black 实测（@100px）：**VISIONS 4.28em ／ ON THE WALL 7.03em**。
公式：`字号 = 栏宽 × 100 ÷ font.getlength(文案)`。

### 两行标题 .l1 / .l2（仿参考海报「两行各自撑满」）

```html
<h1 class="title" data-text="title-main"><span class="l1">VISIONS</span><span class="l2">ON THE WALL</span></h1>
```

hero-top 930px 栏宽下 `.l1` 168px ／ `.l2` 104px（各占约 78%）。单行标题省略 .l1/.l2，直接用 `.title` 字号。

### ⚠ 三条实测硬约束

1. **`line-height` 必须 ≥ 1.211**（Inter 的 hhea 行高）。小于它时字形 ascender/descender 溢出 line box →
   `scrollHeight > clientHeight` → 机检判 `overflowY`。踩坑：0.98 时 176px 的行溢出 33px，title-main 直接挂。
2. **英文标题比中文高**（两行 vs 一行）。改完必须确认 block **顶边仍在背景素材区内**——
   撕纸/横幅版式别压到中缝（案例：中文 block 顶 1215 → 英文 1194，中缝下缘 1167）。
   不够就收紧 `.meta`/`.cta` 的 `margin-top`（母版英文版已收到 16px）。
3. **英文 label 只有 18px、字框小**，矩形内最暗 5% 更易踩到素材暗斑 →
   中褐底材质（土墙/岩壁）上 label 色压到**纯黑 #000000**（案例 HOURS：#271B0D 时 4.25，改纯黑后 5.31）。

### 其它

- 印章仍用中文书法体 —— 朱砂印是**落款**，换拉丁字会失掉印的语义；要纯英文版可自行替换 .seal 内容。
- `.meta` 标签用短词（DATES / HOURS / VENUE），`min-width: 104px` 右对齐成列。
- 数值格式：日期「NOV 8, 2026 – JAN 18, 2027」；时间「TUE–SUN 10:00–20:00」（en-dash）。

## 艺术字效果（中文大标题）· 2026-10-11

参考海报（非遗系列：竹编艺术／徽州灯彩／非遗文化之美／山高水长）的中文大标题
**不是端正排一行**，而是同时具备下面几项：

| 效果 | 做法 | 参数区间 |
|---|---|---|
| **大小错落** | 每字不同 `font-size` | 0.82–1.22 倍 |
| **纵向拉长** | `transform: scaleY` | 1.05–1.32 |
| **高低错位** | `transform: translateY` | ±16px |
| **轻微旋转** | `transform: rotate` | ±7° |

**字体不变**（仍是 ZhiMangXing 等书法体），**只改效果** —— 老大明确要求「文字字体保持我们之前的，只做效果改变」。

### 用法

```powershell
python scripts\art_title.py --text "壁上万象" --style dramatic --seed 3
python scripts\art_title.py --text "千年一骑" --style dramatic --seed 21 --orient v   # 竖排字柱
# → <span style="--s:1.12;--sy:1.18;--dx:-6px;--dy:-7px;--rot:-3.2deg">壁</span>…
```

### 艺术字的档位（按"要活还是要正"选，别一律 dramatic）

| 档 | 旋转 | 拉伸 | 错位 | 用在哪 |
|---|---|---|---|---|
| `subtle` | ±1.2° | 1.00–1.05 | ±4px | 轻呼吸 |
| `lively` | ±4° | 1.00–1.12 | ±10px | 有手写感 |
| `stretch` | ±2° | **1.16–1.38** | ±6px | 要挺拔 |
| `dramatic` | **±7°** | 1.05–1.32 | ±16px | 要强烈动态 |
| **`upright`**（2026-10-12 加） | **±0.5°** | 1.00–1.02 | ±2px | **要"正"** |

> ⚠ **别默认用 `dramatic`**。老大 2026-10-12 反馈：「中文标题大字**不够正，全是歪七扭八放的**」——
> 需要端正就用 `upright`，**间距靠容器的 `letter-spacing` 放大**（本案 `0.08em`），
> 不要靠给每个字加 margin/rotate 去凑。

`--orient v`（2026-10-11 加）：**竖排字柱**——母版 `.art.v` 把 span 逐字向下排，
此时**左右错位 `--dx`** 才是主要的不规则来源（横排用不到，恒为 0 保持兼容）。
配套 CSS：`transform: translate(var(--dx,0), var(--dy,0)) rotate(...) scaleY(...)`。
竖排母版为 `poster-column-master.html`（与 `kraft_window` 竖向开窗配套）。

四档预设：`subtle`（英文／小字）／`lively`（中）／`stretch`（专攻拉长）／`dramatic`（强，
最接近参考海报的强度）。输出直接填进 `<div class="… art">` 里 —— 母版已内置 `.art` 的 CSS。

### ⚠ 两条实测坑

1. **`transform-origin` 必须给 `50% 82%`**（**以字脚为支点**）。
   默认的 `50% 50%` 会让拉长向上下**同时**扩展，把整组字顶出安全区。
2. **transform 后的字形会超出 span 的框，Chrome 的 `scrollWidth/Height` 会把它算进来**
   → 机检判 `overflow`（实测：`rotate` 让 t-left 报 ovX、`scaleY` 让 t-right 报 ovY）。
   解法：`.art` 用 `padding: 0.07em 0.10em` 撑开 ＋ 等量负 margin 抵消，**视觉位置不变**。

### 剪影变体

```css
.art.silhouette > span { color: transparent; -webkit-text-stroke: 3px var(--ink); }
```

空心描边，用于需要「镂空剪影」气质的版面。**花材质底上慎用** —— 空心字比实心更难读。

## ★ 信息完整性（brief 给的文字必须全部上版）· 2026-10-11

**海报是信息载体，不是纯图形练习。** 老大原话：「这些给你的文字信息要全部体现在海报上才对啊，尽量填充版面。」

### 必上版清单（照 brief 逐项核）

| 层级 | 内容 | 不能省的理由 |
|---|---|---|
| 主标题 | 展览名（可拆两行/艺术字） | 题眼 |
| 副题 | 「敦煌色彩数字沉浸展」这类定性语 | 说明展是什么 |
| tagline | 「在流动的色彩中，走近千年的想象」 | brief 给了就要用 |
| 展期 | 起止日期 | 读者据此安排 |
| 开放时间 | 周二至周日 10:00–20:00 | 同上 |
| 地点 | 场馆 ＋ 展厅 | 同上 |
| **预约观展** | **CTA 按钮** | **行动转化，最容易漏** |

> ⚠️ **反面案例**：为了学参考海报的「极简」，我把 sandwich/axis/editorial 三套的
> tagline、副题、CTA 全砍了，只剩两行日期地点。老大当场指出。
> **参考海报的极简 ≠ 我们删信息的理由** —— 那些海报要么信息层级已由其它渠道承担，
> 要么本身就没有这些字段。**模仿风格时只模仿「怎么说」，不能模仿「没说什么」。**

### 「尽量填充版面」的执行顺序

信息变多 → 文字块变高 → 会压安全区/中缝。**处理顺序固定，不许跳到最后一条：**

1. **改行／改结构**（拆成多行、改列布局）
2. **收字号**（优先收信息层，主标题最后动）
3. **调位置**（`bottom` 百分比、`gap`）
4. ✗ **删信息** —— 这一条不在选项里

### CTA 按钮（`.cta`）

```css
.cta { display:inline-block; padding:15px 42px; border-radius:999px;
       background: var(--ink); color:#F2E9D8; font-size:26px;
       letter-spacing:.14em; text-indent:.14em; }
```

- 深底浅字胶囊。**它是信息层里的「行动提示」，不是装饰** —— 花底上用深底块反而最稳
  （CR 天然高，不受材质影响）。英文 `BOOK NOW`。
- ⚠️ 别把它和信息行放同一条 flex 行里做 `space-between` —— 实测会和最后一列信息
  **重叠**（CR 掉到 1.00）。**改成竖排**：信息区占满宽，CTA 独占一行右对齐。

### 英文比中文长的连锁反应

英文同信息量通常比中文长 1.6–2 倍。合并成一行的写法（`VENUE · DATES · HOURS`）
**极易溢出画布**（CR 报 1.00 —— 那是背景跑到画布外，不是字太小）。

→ 解法：**加一行**，不是缩字号。sandwich 底栏从「2 行」变「3 行」后中英都稳过。
英文地点的翻译用短式 `CITY CULTURAL CENTER · IMMERSIVE HALL 1F`；
日期用 `NOV 8 2026 – JAN 18 2027`（不要照中文写 `2026.11.8`）。

## 落字后必做

0. **逐项核「信息完整性」清单**（标题/副题/tagline/展期/时间/地点/CTA），漏一项都不算完。
1. `render_png.py --qa-bg --boxes` 拍无字背景与文字盒；
2. `check_contrast.py` 全项 ≥ 门槛（大字号 3.0:1，其余 4.5:1）；
3. 目检：题不被背景窗／主体压、数值不折行（boxes.json overflowX/Y 应全 false）、印章不压字。

## 反面清单（实测踩坑）

- 不要用全角空格/多空格凑字距——用 letter-spacing＋text-indent。
- `.meta` 不要设百分比宽度（fit-content 父级中形成循环约束，数值被压到折行）。
- QA 隐藏文字用 `html.pf-qa-bg [data-text]{color:transparent}`；只管文字墨色，印面/按钮底色块保留（否则对比度参照错）。
- 改了母版必须重新拷贝到案例目录再渲染——案例 HTML 是拷贝，不是引用（本版最大一次返工原因）。