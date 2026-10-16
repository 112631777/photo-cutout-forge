# Calligraphy fonts and typography rules

## ★ Current finalised font-size master table (three bilingual master templates · 2026-10-11)

> This table is the "current result" — **output follows it by default; do not reinvent it**.
> Font sizes may be fine-tuned when swapping source images (constrained by the type-setting area and the centre seam), but **do not change the hierarchy ratios or the font division of labour**.

| Master template | Chinese | English |
|---|---|---|
| **sandwich** (top bar + bottom bar) | main title **220px** (running script + art lettering) · secondary 28 · bottom bar **32** (subtitle/tagline in regular script) · CTA 26 | main title **102px / Black 900** (cap 104) · secondary 30 / 700 · bottom bar 30 (subtitle 32/700, tagline 24/400) · CTA 26 |
| **axis** (central-axis centred) | main title **152px** · key single character **70** (ratio 2.17×) · bottom **30** · CTA 27.6 | main title **102px / 900** · single char 74 · bottom 26 · CTA 24 |
| **editorial** (left text + large negative space) | title **128px** · three lines of small text 24 · year 34 (letter spacing 0.62em) · credit 40 | title **146 + 88px / 900** (two lines same width) · subtitle 30/700 · tagline 22 · meta 19 (label 17/500) · CTA 24 |
| **column** (vertical setting, irregular · added 2026-10-11) | title **190px** (vertical character column, art lettering staggered) · vertical subtitle 34 · vertical tagline 30 · vertical small label 24 · info 30 · CTA 28 · presenter 26 | title three vertical lines **76/76/120 (900)** · subtitle 30/700 · tagline 24 · label 24/600 · info 30 · CTA 28 |
| **column · diagonal version (`data-diag`)** | title **two tiers** **185 / 167** (right column larger, left column next, modelled on template "DUNHUANG > MUSEUM EXHIBITION") · tagline two horizontal lines **46** · vertical subtitle 30 · small label 26 · info **exhibition dates 36 / hours·venue 28** · CTA 30 | title four lines **two tiers 66/66/132/132** · subtitle 30/700 · tagline **40**/400 · label 24/600 · info 36/28 · CTA 30 |

**Font division of labour (unified across the three templates)**: main title = ZhiMangXing running script + art lettering / subtitle·tagline = **MaShanZheng brush regular script** (the tagline belongs to the calligraphic layer) / exhibition dates·hours·venue·CTA = sans only allowed in the pure information layer / all English uses Inter (title Black 900).

## Font list (assets/fonts/, SIL OFL open source, bundled with the package)

| File | Font | Default use |
|---|---|---|
| ZhiMangXing-Regular.ttf | ZhiMangXing running script | main title (--f-brush) |
| MaShanZheng-Regular.ttf | MaShanZheng brush regular script | subtitle / short phrase / seal text / contact-board label (--f-brush-2) |
| LiuJianMaoCao-Regular.ttf | LiuJianMaoCao running-cursive | optional emphasis character |

- The title layer **does not use a regular font** (requirement ②). Within the master templates, sans (--f-cjk-sans) is only allowed in the "modern information layer": presenting institution (.presenter), exhibition-info values (.meta), button (.cta) — it is divided from the calligraphic layer and does not take part in the title.
- **★ The tagline belongs to the calligraphic layer, not the information layer (pointed out by the boss on 2026-10-11)**: the subtitle ("Dunhuang Colours Digital Immersion Exhibition"), tagline ("in flowing colour, approach a thousand years of imagination") must go through **MaShanZheng regular script (--f-zh-brush2)**; setting them in sans / Song typeface both look "not refined enough". **Only pure information such as exhibition dates / hours / venue / CTA may use sans.** The three master templates have implemented this: sandwich `.bar-bottom .brush` / axis `.foot .f-sub,.f-tag` / editorial `.tiny`. ⚠ Regular script is **not bold** (font-weight 400) — bold would blur the brush strokes.
- LongCang (Longcang script) was once tried, but the source file was corrupt (rendered completely blank, Pillow bbox height 0); it has been deprecated — do not reintroduce a file of the same name.
- The master templates use the `@font-face` relative path `fonts/…`; **when copying a master template elsewhere, you must copy the `fonts/` directory at the same time**.
- Headless rendering (render_png.py) can load local fonts directly; verified.

## Font-size system (master-template default, @1500×1875 canvas)

| Element | Font size | Notes |
|---|---|---|
| Main title .title | hero-top 196 / hero-centre 196 / hero-right 152 / hero-left 152 | line-height 1.04, letter spacing 0.015em |
| Subtitle .subtitle | 44px | MaShanZheng, letter spacing 0.14em |
| Short phrase .tagline | 29px | MaShanZheng, letter spacing 0.10em |
| Presenter .presenter | 26px | sans, letter spacing 0.44em |
| Exhibition-info label .k | 22px | gold, letter spacing 0.22em, right-aligned (min-width 118px) |
| Exhibition-info value .v | 24px | single line, no wrap (white-space: nowrap) |
| Button .cta | 25px | ink background, paper text, capsule shape |
| Seal span | 38px | 2×2 grid, 104×104 stamp face |

- For the sidebar layouts (hero-right/left), the main block is 43% wide; at title 152px a "four-character title" is about 620px, close to the column-width cap; any longer and you must switch to a two-line title or shrink the font size. After changing font sizes you **must re-run check_contrast**.
- Decorative thin line .ornament 132×2px (gold C9A96A); the hero-left layout right-aligns with the block.

## Layout colours and contrast

| Variable | Value | Use |
|---|---|---|
| --ink | #2A231A | main-title ink colour |
| --ink-2 | #4A4034 | subtitle / values |
| --ink-3 | #56503F | short phrase / presenter (do not lighten further, 4.5:1 would break) |
| --gold | #6B4E1E | exhibition-info label (legible gold-brown; decorative gold #C9A96A used only for non-text) |
| --seal | #8A3220 | vermilion stamp face; stamp-face text #F3E7D3 must be set explicitly on the span (QA reads the element's computed colour) |

### ★ Use the vermilion seal as a "signature point" (2026-10-12)

When the whole piece is in a beige-grey tone, **a single vermilion square seal is the most economical warm-colour signature** (more effective than adding decoration) — in the sandwich top-bar's "left word ▣ right word" structure, the central geometric mark (`.mark`) can be replaced directly with a square seal:

```css
.seal { width:94px; height:94px; flex:none; background:#9A3423; color:#F6ECD6;
        font-family: var(--f-zh-brush2); font-size:37px; line-height:1.06;
        display:flex; flex-direction:column; align-items:center; justify-content:center; }
```
```html
<div class="seal" data-text="seal"><span>永</span><span>玉</span></div>
```

- The seal content is **shared by the Chinese and English editions** (the seal is a signature and does not change with language; do not translate it into Latin characters).
- Set `data-text` so the machine check measures it too: `pf-qa-bg` only clears the text colour, **the stamp-face background block is kept**, so `check_contrast` measures "cream-white text vs vermilion ground" (case 05 measured 6.38:1, passed).
- `margin-top` must align with **the visual centre of the main-title glyphs**, not with the line box: at 208px font size with line-height 1.30, the seal top ≈ `--top-y + 0.40 × font size` (case used 82px).
- Do not let the seal steal focus from the title: set its width to about **0.45×** the title font size (208px title → 94px seal).

## Typography rules for the Chinese edition

- Title letter spacing 0.015em; subtitle/short phrase 0.10–0.14em; institution 0.44em + text-indent of the same value (first-character indent offsets it).
- The seal "壁上万象" is a 2×2 vermilion seal, placed at the side of or diagonally opposite the title; the seal is a **signature**, not decoration, and its position follows the composition (see each layout's CSS).
- Chinese date format "2026年11月8日至2027年1月18日"; time "周二至周日 10:00–20:00" (en-dash).
- The three exhibition-info lines (exhibition dates / opening hours / venue) use the `.k+.v` pair; labels are gold, values are ink, centred layouts use `justify-content: center`.

## Typography rules for the English edition (Inter)

**The font is fixed as Inter** — `assets/fonts/Inter-{Regular,Medium,SemiBold,Bold,ExtraBold,Black}.ttf` (SIL OFL).
Selection basis: comparing the reference poster "start business" glyph by glyph — **the i has a square dot, the a is double-storey, the t is cut at the top, weight Black** → Inter; geometric typefaces (Futura / Poppins / Century Gothic) have a round i dot and a single-storey a, so they are ruled out.
Final verification: render the same phrase `start business` in Inter Black and it matches the reference letter by letter (case `11-字体决定性验证.png`).

**★ From 2026-10-11 the English layer of all three master templates (sandwich/axis/editorial) also switched to Inter** (`--f-en`) — EB Garamond, a high-contrast serif, was rejected by the boss: "the English text is too thin to hold up the composition", and the boss specified using the old finalised version (editorial English, Inter Black) as the standard. Title **weight 900**, subtitle 700, tagline 400, info line 600.

### Measured font sizes from the old finalised version (derived by measuring ink on the reference image, @1500 canvas)

| Element | Font size | Note |
|---|---|---|
| Title l1 `VISIONS` | ≈162px / 900 | two lines **same width ≈692px** ("each line fills its width") |
| Title l2 `ON THE WALL` | ≈98px / 900 | 7.03em×98 ≈ 692 ✓ |
| Subtitle `DUNHUANG COLOR · DIGITAL IMMERSION` | ≈32px / 700 | |
| tagline | ≈24px / 400 | |
| meta label (DATES/HOURS/VENUE) | ≈17px / 500 | label is half a step smaller and slightly lighter than value |
| meta value | ≈20px / 600 | |
| CTA capsule text | ≈24px | capsule height ≈53px |

> editorial actually landed at 146/88 (90% of the reference) — there are more info lines than the reference, and the block top is hard-constrained by the centre seam (SEAM bottom-left end 1191); the first run at 156/96 pressed 53px into the seam. **To enlarge further: cut lines first, do not delete information.**

### English landing values for the three master templates (measured 2026-10-11)

| Master template | Title | Constraint formula |
|---|---|---|
| sandwich "two words on one line" | **102px / 900** | `(VISIONS 4.254em + ON THE WALL 6.998em + letter spacing 0.72em) × S + mark 84px ≤ 1332` → **S ≤ 104px** |
| axis single-line centred | **102px / 900** | `(11.57 + 19×0.04)em × S ≤ 1340`; ⚠ Inter Black is wider; the 114px from the serif era would overflow |
| editorial two lines | **146 / 88px / 900** | each line fills ≈700px |

- ⚠ **The two top-bar words must stay on one line**: `.w-main` has `white-space: nowrap` added — when space is tight, **prefer the machine check flagging overflowX** over silently wrapping and turning "two words on one line" into three lines (hit on 2026-10-11: at 108px `ON THE WALL` quietly wrapped to `ON THE` / `WALL`).
- ⚠ **Changing the font changes all the metrics**: Inter Black's win vertical metrics are taller than the serif's, so axis at line-height 1.24 already reported ovY → raised to 1.32.

## The central-axis skeleton's "primary–secondary ratio" (pointed out by the boss on 2026-10-11)

The two key single characters "敦/煌" and the main title had **font sizes too close → no primary–secondary distinction**.
Landing ratio: **title 152px / single char 70px (≈2.17×)**, `--gap` 18→14px swapped to recover height (block bottom edge 564.7 < seam top 583 ✓).
> Criterion: **the key single characters are parentheses that "bracket" the title, not a second title** — they only need to "be able to form one word"; their font size should not steal from the main title. Rule of thumb: **main title ≥ 2× the single character**.

Usage: `body[data-lang="en"]` (or `?lang=en` at render time). **The master templates already embed the full English override; no further layout override needs to be written.**

### Font size: measure width first, then set — do not guess

Column width = canvas width × layout proportion (hero-top 62% = 930 / hero-centre 80% = 1200 / sidebar 43% = 645).
Inter-Black measured (@100px): **VISIONS 4.28em / ON THE WALL 7.03em**.
Formula: `font size = column width × 100 ÷ font.getlength(text)`.

### Two-line title .l1 / .l2 (after the reference poster's "each line fills its width")

```html
<h1 class="title" data-text="title-main"><span class="l1">VISIONS</span><span class="l2">ON THE WALL</span></h1>
```

Under the hero-top 930px column width, `.l1` is 168px / `.l2` is 104px (each about 78%). A single-line title omits .l1/.l2 and uses the `.title` font size directly.

### ⚠ Three measured hard constraints

1. **`line-height` must be ≥ 1.211** (Inter's hhea line height). Below that, the glyph ascender/descender overflow the line box → `scrollHeight > clientHeight` → the machine check flags `overflowY`. Pitfall: at 0.98, a 176px line overflowed by 33px and title-main failed outright.
2. **English titles are taller than Chinese** (two lines vs one). After changing, you must confirm the block's **top edge is still inside the background source-image area** — torn-paper / banner layouts must not press into the centre seam (case: Chinese block top 1215 → English 1194, seam bottom edge 1167). If not enough, tighten `.meta`/`.cta`'s `margin-top` (the English edition of the master template already tightened to 16px).
3. **English labels are only 18px with a small glyph box**, so the darkest 5% inside the rectangle is more likely to hit a dark patch in the source image → on mid-brown materials (earth wall / rock face) the label colour is pushed to **pure black #000000** (case HOURS: 4.25 at #271B0D, 5.31 after switching to pure black).

### Miscellaneous

- The seal still uses a Chinese calligraphic typeface — the vermilion seal is a **signature**, and swapping in Latin characters would lose the seal's meaning; for a pure-English edition you may replace the .seal content yourself.
- `.meta` labels use short words (DATES / HOURS / VENUE), `min-width: 104px` right-aligned into a column.
- Value format: dates "NOV 8, 2026 – JAN 18, 2027"; time "TUE–SUN 10:00–20:00" (en-dash).

## Art-lettering effects (Chinese large titles) · 2026-10-11

The Chinese large titles of the reference posters (intangible-heritage series: 竹编艺术 / Bamboo Weaving Art, 徽州灯彩 / Huizhou Lantern Art, 非遗文化之美 / The Beauty of Intangible Heritage, 山高水长 / Lofty Mountains and Long Rivers) are **not set neatly in one straight line**; instead they simultaneously have the following features:

| Effect | Method | Parameter range |
|---|---|---|
| **Varied sizes** | different `font-size` per character | 0.82–1.22× |
| **Vertical stretch** | `transform: scaleY` | 1.05–1.32 |
| **Vertical offset** | `transform: translateY` | ±16px |
| **Slight rotation** | `transform: rotate` | ±7° |

**The font stays the same** (still calligraphic typefaces such as ZhiMangXing), **only the effect changes** — the boss explicitly required "keep the text font we used before; only change the effect".

### Usage

```powershell
python scripts\art_title.py --text "壁上万象" --style dramatic --seed 3
python scripts\art_title.py --text "千年一骑" --style dramatic --seed 21 --orient v   # vertical character column
# → <span style="--s:1.12;--sy:1.18;--dx:-6px;--dy:-7px;--rot:-3.2deg">壁</span>…
```

### Art-lettering tiers (choose by "lively or upright", do not always use dramatic)

| Tier | Rotation | Stretch | Offset | Where to use |
|---|---|---|---|---|
| `subtle` | ±1.2° | 1.00–1.05 | ±4px | light breathing |
| `lively` | ±4° | 1.00–1.12 | ±10px | handwritten feel |
| `stretch` | ±2° | **1.16–1.38** | ±6px | wants uprightness |
| `dramatic` | **±7°** | 1.05–1.32 | ±16px | wants strong dynamism |
| **`upright`** (added 2026-10-12) | **±0.5°** | 1.00–1.02 | ±2px | **wants "upright"** |

> ⚠ **Do not default to `dramatic`**. The boss's feedback on 2026-10-12: "the large Chinese title characters are **not upright enough; they are all tilted and askew**" — when you need uprightness, use `upright`, and **enlarge the spacing via the container's `letter-spacing`** (this case `0.08em`); do not fudge it by adding margin/rotate per character.

`--orient v` (added 2026-10-11): **vertical character column** — the master template `.art.v` stacks spans character by character downward; at this point **the left–right offset `--dx`** is the main source of irregularity (horizontal setting does not use it and keeps it at 0 for compatibility).
Companion CSS: `transform: translate(var(--dx,0), var(--dy,0)) rotate(...) scaleY(...)`.
The vertical master template is `poster-column-master.html` (paired with `kraft_window`'s vertical window).

Four presets: `subtle` (English / small text) / `lively` (medium) / `stretch` (focuses on stretching) / `dramatic` (strong, closest to the reference posters' intensity). The output goes straight into `<div class="… art">` — the master template already embeds the `.art` CSS.

### ⚠ Two measured pitfalls

1. **`transform-origin` must be set to `50% 82%`** (**use the foot of the character as the pivot**). The default `50% 50%` makes the stretch expand **both** up and down, pushing the whole character group out of the safe area.
2. **The transformed glyph overflows the span's box, and Chrome's `scrollWidth/Height` counts it in** → the machine check flags `overflow` (measured: `rotate` made t-left report ovX, `scaleY` made t-right report ovY). Fix: `.art` uses `padding: 0.07em 0.10em` to expand + an equal negative margin to offset it, **the visual position stays unchanged**.

### Silhouette variant

```css
.art.silhouette > span { color: transparent; -webkit-text-stroke: 3px var(--ink); }
```

Hollow stroke, used for layouts that need a "cut-out silhouette" quality. **Use with caution on patterned materials** — hollow characters are harder to read than solid ones.

## ★ Information completeness (all text given in the brief must appear on the layout) · 2026-10-11

**A poster is an information carrier, not a pure graphics exercise.** The boss's exact words: "all this text information given to you must be reflected on the poster, fill the layout as much as you can."

### Mandatory on-layout checklist (check item by item against the brief)

| Level | Content | Reason it cannot be omitted |
|---|---|---|
| Main title | exhibition name (may split into two lines / art lettering) | key character |
| Subtitle | qualitative phrase like "Dunhuang Colours Digital Immersion Exhibition" | explains what the exhibition is |
| tagline | "in flowing colour, approach a thousand years of imagination" | if the brief gives it, use it |
| Exhibition dates | start and end dates | readers plan around it |
| Opening hours | Tue–Sun 10:00–20:00 | same as above |
| Venue | venue + exhibition hall | same as above |
| **Book a visit** | **CTA button** | **conversion action; most easily missed** |

> ⚠️ **Anti-pattern**: to learn from the reference posters' "minimalism", I cut the tagline, subtitle, and CTA from all three sandwich/axis/editorial templates, leaving only two lines of dates and venue. The boss pointed this out on the spot. > **The reference posters' minimalism ≠ our reason to delete information** — those posters either have their information hierarchy carried by other channels, or simply do not have those fields. **When imitating style, imitate only "how it speaks", never "what it omits".**

### Execution order for "fill the layout as much as possible"

More information → taller text blocks → presses into the safe area / centre seam. **The handling order is fixed; do not skip to the last item:**

1. **Change lines / change structure** (split into multiple lines, change column layout)
2. **Reduce font size** (reduce the information layer first; touch the main title last)
3. **Adjust position** (`bottom` percentage, `gap`)
4. ✗ **Delete information** — this is not an option

### CTA button (`.cta`)

```css
.cta { display:inline-block; padding:15px 42px; border-radius:999px;
       background: var(--ink); color:#F2E9D8; font-size:26px;
       letter-spacing:.14em; text-indent:.14em; }
```

- Dark background, light text capsule. **It is an "action prompt" within the information layer, not decoration** — on a patterned background, a dark-background block is actually the most stable (CR is naturally high and unaffected by the material). English `BOOK NOW`.
- ⚠️ Do not put it in the same flex row as the info lines using `space-between` — in practice it **overlaps** with the last info column (CR drops to 1.00). **Change to vertical setting**: the info area spans the full width, and the CTA takes its own right-aligned line.

### The chain reaction of English being longer than Chinese

English with the same information is usually 1.6–2× longer than Chinese. The one-line merge style (`VENUE · DATES · HOURS`) **very easily overflows the canvas** (CR reports 1.00 — that means the background ran outside the canvas, not that the text is too small).

→ Fix: **add a line**, do not shrink the font size. After the sandwich bottom bar went from "2 lines" to "3 lines", both Chinese and English passed stably. Translate the English venue in short form `CITY CULTURAL CENTER · IMMERSIVE HALL 1F`; for dates use `NOV 8 2026 – JAN 18 2027` (do not write `2026.11.8` as in Chinese).

## Must-do after setting the type

0. **Check the "information completeness" checklist item by item** (title/subtitle/tagline/exhibition dates/hours/venue/CTA); missing any one means it is not done.
1. `render_png.py --qa-bg --boxes` captures the text-free background and text boxes;
2. `check_contrast.py` all items ≥ threshold (large font 3.0:1, others 4.5:1);
3. Human-eye check: title not pressed by the backdrop window / subject, values do not wrap (boxes.json overflowX/Y should all be false), seal does not cover text.

## Anti-pattern list (measured pitfalls)

- Do not use full-width spaces / multiple spaces to fake letter spacing — use letter-spacing + text-indent.
- Do not set `.meta` to a percentage width (it forms a circular constraint inside a fit-content parent, squeezing values into a wrap).
- QA hides text with `html.pf-qa-bg [data-text]{color:transparent}`; it only handles the text ink colour, keeping the stamp-face / button background blocks (otherwise the contrast reference is wrong).
- After changing a master template you must copy it back into the case directory before rendering — the case HTML is a copy, not a reference (this caused the biggest rework in this version).
