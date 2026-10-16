# Reference poster library (assets/ref-posters/) · source for learning layout and composition

> **Why this file exists**: the boss put 7 excellent cases **directly into the skill** — "wouldn't it be better to put the template images straight into the skill files so you learn from them, avoiding large errors and saving me from repeatedly stressing the learning points?"
> So: **look at the images before setting the type** (`Read` the files below); do not "recall" their style in your head.

## 0 Usage (three steps, do not skip)

1. **Look at the images**: first `Read` `_contact-sheet.png` (**10 posters** for a quick overview) → pick 1–2 whose temperament matches the current source image, then `Read` those originals individually (see the font-size hierarchy and negative-space relationships clearly).
2. **Pick the moves**: choose 2–4 moves from the "move list" below (**do not use them all**; each reference poster used only 3–4 moves).
3. **Implement**: map to our master templates and classes via the "implementation" column; **fonts, canvas proportions, and font-size hierarchy stay unchanged** (see the hard constraints at the end).

## 1 How to read the seven reference posters (what each used)

| # | File | Exhibition name / source | Background & subject | Key typographic-layout points |
|---|---|---|---|---|
| 01 | `ref-mountains-water.jpg` | 山高水長 (Lofty Mountains and Long Rivers) · 唐宋八大家主题文物展 (Tang–Song Eight Great Prose Masters Thematic Artefact Exhibition)（辽宁省博物馆 / Liaoning Provincial Museum） | top 2/3 beige empty paper, bottom 1/3 blue-green landscape horizontal scroll | **staggered vertical giant calligraphic title** (top-left, 4 characters varying in size and height) + **two vertical subtitle lines** (right of the title, small) + **three horizontal lines of uppercase English** (left-aligned below the subtitle) + **vertical quoted poem top-right** (cultural layer) + **oversized date numerals at the bottom** (celadon green) + three lines of institution info at the bottom + QR code |
| 02 | `ref-dunhuang-museum.jpg` | 敦煌博物展 (Dunhuang Museum Exhibition) · 古代艺术博物馆 (Museum of Ancient Art) | diagonal irregular mural block + beige paper; central white porcelain vase | **two-column staggered vertical title** (right column '敦煌/Dunhuang' large, left column '博物展/Museum Exhibition' slightly smaller and lower) + **vertical small label + thin vertical line** ('壁画展/Mural Exhibition／瓷器展/Porcelain Exhibition') + two horizontal lines of small subtitle + **large numeral date block top-left** (2024 / 09.18 / 09.28) + three lines of institution info at the bottom |
| 03 | `ref-jiguang-pianyu.jpg` | 吉光片羽 (Rare Treasures) · 湖南考古出土陶瓷特展 (Hunan Archaeological Excavated Ceramics Special Exhibition)（长沙博物馆 / Changsha Museum） | **diagonal irregular pottery-shard block** sweeping across the frame + white paper + small line-drawing illustrations | **two-column coloured calligraphic title** ('吉光/Jiguang' upper right column, '片羽/Pianyu' lower left column) + **three lines of small English text** right after the title + two large lines of Chinese subtitle + three lines of English subtitle + **oversized date top-left** (2021 09.28 ｜ 2022 01.03) + **a row of 5 artefact icons with small text at the bottom** + four lines of institution info |
| 04 | `ref-heritage-paper.jpg` | 非遗文化之美 (The Beauty of Intangible Heritage)（纸底版 / paper-base version · 皮影 / shadow puppetry） | yellowed old paper + centred shadow-puppet figure | **horizontal large title spanning the top** (5 characters varied in size, height, and offset) + **large English text pressed onto the title layer as an underlay** + subtitle uses **'／' (slash) as even spacing** (藏/于/时/光 Hidden in time · 见/于/当/下 Seen in the present) + one line of small annotation (以匠心守文脉 … / guarding the cultural lineage with craftsmanship …) + short horizontal line at the lower-left corner as a finish |
| 05 | `ref-heritage-dark.jpg` | 非遗文化之美 (The Beauty of Intangible Heritage)（暗底版 / dark-base version · 傩戏 / nuo opera） | dark-green mural wall + nuo-opera figure | same title structure as 04 (warm gold on the dark base) + **oversized rotated watermark character on the base image** ('傩/nuo') + **vertical small text on the left edge** + **large numeral date at the lower-right** (2026 / 04.14) |
| 06 | `ref-bamboo-weaving.jpg` | 竹编艺术 (Bamboo Weaving Art) · BAMBOO WEAVING | light-grey gradient colour field + bamboo-weaving subject centred, slightly low | **single-column 4-character vertical title staggered + rotated** (top-left, with a seal) + **two vertical small-text passages on the right** (国家级非物质文化遗产 / National Intangible Cultural Heritage ／ 经纬入艺 竹韵新生 / art in warp and weft, bamboo rhythm renewed, with a small seal in between) + **oversized English 'BAMBOO WEAVING' at the bottom, cut off by the lower edge**, filling left and right |
| 07 | `ref-lantern-art.jpg` | 徽州灯彩 (Huizhou Lantern Art) · LANTERN ART | night-dark colour field + fish-lantern subject centre-right | same structure as 06 (same series): staggered 4-character red calligraphic vertical title + seal + vertical small text on the right + **one line of vertical English small text at the far left** (ANCIENT HUIZHOU LANTERN) + **oversized English 'LANTERN ART' cut off at the bottom** |

### 1b The three master sources from the "Visions on the Wall" period (origin of the three skeletons · added to the library 2026-10-12)

| # | File | Exhibition name / source | Background & subject | Key typographic-layout points | Corresponding master template |
|---|---|---|---|---|---|
| 08 | `ref-eastern-essence.jpg` | EASTERN ESSENCE · FLOWING QI | beige grainy paper; **diagonal wall + roof silhouette** pressing the lower 2/3, upper 1/3 left empty | **top bar with three width-filling elements** (`EASTERN ▣ ESSENCE`, square mark in the middle) + small text `FLOWING QI` top-left + `2025` top-right; **a thin info bar at the bottom** (three groups of small text separated by vertical lines) | `poster-sandwich-master.html` (top bar + bottom bar, both ends filled) |
| 09 | `ref-oriental-zen.jpg` | ORIGINAL ZEN · 东方 (East) | solid-colour **red circle (sun)** + dark temple silhouette + a pool of light on the ground | **fully central-axis centred**: `东` / `ORIENTAL` / `ZEN` / `方` (the two single characters top and bottom **form one word** '东方/East'); minimalist, no other information | `poster-axis-master.html` (central-axis centred; **the key single characters must be able to form one word**) |
| 10 | `ref-china-2025.jpg` | CHINA 2025 · @DNA2725 | large negative space on the left; right 2/3 is a **Dunhuang-pattern S-shaped ribbon** (extremely ornate) | **narrow text column on the left**: three lines of copyright-style small text → large `CHINA` → `2 0 2 5` (**letter spacing widened**) → `@DNA2725` credit; **not even a CTA is given** | `poster-editorial-master.html` (left text + large negative space) |

> These three are the original master sources of the "**typographic skeleton**" (the three skeletons in the appendix of `composition-library.md` are abstracted from them). > Do not copy the **picture structure** of 8/9/10 (diagonal wall / red sun / ribbon) verbatim — **what to learn is "how the text is placed within such a picture"**: skeleton 08 = two material strips top and bottom holding the text; 09 = one central axis with the middle entirely given to the image; 10 = text indented into a narrow lower-left column, everything else left blank.

## 2 Move list (reusable, ordered by implementation cost)

> ★ **Open up the hierarchy** (pointed out by the boss on 2026-10-11): reference 115's tiers are **main title ≫ tagline > subtitle > small label ≈ info**, with **clear jumps between tiers**; and **the main title itself is split into two tiers** ('敦煌/Dunhuang' > '博物展/Museum Exhibition'). "Fonts and poster proportions stay unchanged" does not mean "dare not touch the font-size hierarchy" — open up what should be opened up, or the whole poster reads flat. Landing values are in `calligraphy.md`'s "Current finalised font-size master table · column diagonal version".

| Move | Source | Implementation | Status |
|---|---|---|---|
| **A Vertical staggered title** | 01 02 03 06 07 | `art_title.py --orient v` (varied size / left–right offset / vertical offset / slight rotation) + master template `.art.v`; two columns use `.title-wrap` + two `.tcol` (**read right-to-left**) | ✅ implemented |
| **K Top bar with three width-filling elements** | 08 | sandwich top bar `space-between`: left word / mark / right word (the mark is a pure CSS square + concentric circle, no text) | ✅ implemented |
| **L Bottom-bar thin info strip (vertical-line separated)** | 08 | sandwich bottom bar: `space-between` + `<i class="sep">` thin vertical line; **each line fills both ends** (when enlarging the font, prefer changing lines over switching to left alignment) | ✅ implemented |
| **M Central-axis key single characters forming one word** | 09 | axis skeleton: the top and bottom single characters (敦/煌 / Dunhuang) **must be able to form one word**; and **main title ≥ 2× the single character** | ✅ implemented (152 / 70) |
| **N Left narrow text column (copyright-style small text → large title → letter-spaced year → credit)** | 10 | editorial skeleton: text occupies only a narrow lower-left column, the rest is all negative space | ✅ implemented |
| **O Horizontal large title with size stagger** (not vertical!) | 04 05 12 13 | title set horizontally, per-character `--s` / `--dy` stagger (`art_title.py` default `--orient h`) + master template `.tcol` changed to `flex-direction: row`; **placed in the blank material area** | ✅ implemented (case17) |
| **P Large text block avoids the subject** (territory rule) | 06 07 13 | first align the window mask with the canvas → lay a 16×8 "material blank-rate grid" → the title only lands on wholly 100%-empty blocks; use vertical setting for narrow-tall blanks, horizontal setting for wide-flat blanks | ✅ implemented (case17, the whole strip below y≥1187 is empty) |
| **B Vertical small label + thin vertical line** | 02 06 07 | `.side` + `.mini::before` (thin line drawn from the top of the text) | ✅ implemented |
| **C Side vertical small text (cultural layer)** | 01 05 | vertical variant of `.col-tag` (`writing-mode: vertical-rl`) | ✅ implemented |
| **D Oversized date numerals** | 01 02 03 05 | standalone numeral block: Inter (English numerals) at large size (reference ≈ 1/3 of canvas width) + a museum-name / hall line smaller than the date | ✅ can add (just use the existing master template) |
| **E Oversized English cut at the bottom** | 06 07 | master template `.giant` (CSS **verified by measurement**): outer container `overflow:hidden` does the cutting + inner span uses `translateY(28%)` to set the text, **the container box stays inside the canvas**. Insertion: `<div class="giant" data-text="giant"><span>LANTERN ART</span></div>` | ✅ measured (see "three measured attempts at E" below); not enabled in the case |
| **F Subtitle uses "/" as even spacing** | 04 05 | write `藏/于/时/光` (more stable than inserting spaces) in the copy, or use a phrase line opened up with `letter-spacing` | 🟡 use existing classes |
| **G Large English text as underlay** | 04 | same as E, but `z-index` pushed below the title layer, transparency reduced | 🟡 change colour and level per E when needed |
| **H Rotated watermark large text on the base image** | 05 | enlarge the title characters to 500–700px, rotate −15°, `opacity 0.18`, laid across the background layer | 🟡 add when needed |
| **I Artefact icon strip** | 03 | a row of 5 small icons + small-text labels; **icons need source assets** (use category text labels instead when no assets) | 🔴 needs assets |
| **J Horizontal staggered large title** | 04 05 | add `.art` (without `.v`) on the horizontal master template, also via `art_title.py` | 🟡 use existing classes |

## 3 Appendix: three measured attempts at move E (three versions tried before settling; do not repeat the detours)

| Attempt | Result |
|---|---|
| hardcoded font size 208px + `line-height 0.86` | copy 1810px wide → `overflowX`; line-height smaller than Inter's win metrics → `overflowY` |
| container `bottom` set to a negative value so the outer edge is cut | element box **runs past the canvas bottom edge** → machine check samples outside the canvas → **P5 = 0, CR 1.14** (looks like "ground too dark", but actually out of bounds) |
| **✓ outer container `overflow:hidden` + inner span `translateY(28%)`** | box stays inside the canvas (measured (760,1743) 684×132), lower half of the glyphs cleanly cut ✓ |

With the three parameters (copy verbatim):

```css
--size-giant: 178px;        /* = live area 1388 ÷ (getlength(copy)/1000), leaving 8% margin */
/* measured font-size candidates: BAMBOO WEAVING 9.934em→139 ／ LANTERN ART 7.213em→192 ／ HORSE & RIDER 7.527em→184 */
.giant { left: 760px; right: 56px; }   /* the text band is confined to the **paper area**, do not straddle onto the image */
```

⚠ **It is the only move that "allows ovY"**: the cut inevitably makes `scrollHeight > clientHeight`, and the machine check reports `giant(overflow)` — **this is expected**, guarded instead by **human-eye check** (lower half cleanly cut, left/right filled to the edge); if `overflowX` appears, the font size is too large, so go back to the formula and recompute.

## 4 Hard constraints (the boss made clear: these **do not change**)

1. **Fonts do not change**: Chinese title = ZhiMangXing running script (+ art-lettering effect) / subtitle·tagline = MaShanZheng brush regular script / pure information layer = sans; English = Inter (title Black 900). **Do not swap fonts just because a reference poster uses a different one.**
2. **Canvas spec does not change**: 1500 × 1875 (ratio 0.8). Reference images have varying ratios (1.33–1.80); **learn only the typographic relationships, do not copy their canvas ratios**.
3. **Font-size hierarchy does not change**: the three bilingual master templates' hierarchy and tiers are in `calligraphy.md`'s "Current finalised font-size master table"; do not copy the reference posters' absolute font sizes verbatim (those follow the "clean paper + tiny grey text" approach).
4. **Do not delete information**: main title / subtitle / tagline / exhibition dates / hours / venue / CTA — not one fewer (see `calligraphy.md`'s "Information completeness").
5. **★★ Title must be large, not too much negative space** (set by the boss on 2026-10-12) — most reference posters follow the "clean paper + tiny grey text" approach; **learn only "how the text is placed", do not learn the font sizes along with it**; the criteria (cap formula / image window ≥45% / whitespace ratio) are in `SKILL.md` §0-6 and `qa.md` §3-6.

> In one sentence: **what you learn is "how the text is placed", not "what font to use or how large a canvas".**
