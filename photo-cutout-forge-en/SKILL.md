---
name: photo-cutout-forge-en
description: Photographic source → cutout subject + calligraphic art poster. Cut the main part out of a photo (white background → transparent), then process the original through framing / upscaling / cropping / masking / duotone into a background (a soft-focus backdrop window, or a two-colour gradient extracted from the image as a ground field). The subject stands on the paper and the calligraphy is set last — background first, type second. There is also a torn-material-layer route with three inputs (a photo containing the subject + a material image such as rock face / stone surface / paper + a description of the subject, which is written into the candidate prompt to sharpen recognition): the tear follows the subject's outline and the centre seam reveals the content, while the background adapts to whatever material is uploaded. Use for exhibition / performance / festival key visuals, and for any poster in the "photo cutout + calligraphic title" style. Trigger words: cutout poster, silhouette subject, white-background cutout, automatic composition, calligraphic poster, paper ground, duotone, mask, torn-paper poster, material background, rock-face background, machine check.
---

# photo-cutout-forge · photographic source → cutout subject + calligraphic art poster

> Turn one photograph into an exhibition key visual in which the cutout subject stands on paper
> and the calligraphy is set on top: cut the main part out of the original (cutout / silhouette),
> process that original through framing, upscaling, cropping, masking and duotone into a background,
> then handle the background first and the type second. Four compositions are **chosen automatically**
> by the scripts from the subject's shape (plus a full-width scroll `hero-band` that can be requested by
> hand), and the reason is written out in plain English.
>
> There is also a "torn material layer" route (`kraft_tear.py` / `kraft_photo.py`, **three inputs**:
> one real-world photo containing the subject + one material image (the background texture — the background
> adapts to whatever is uploaded: rock face / stone surface / paper …) + a **description of the subject**,
> which goes into the white-background candidate's image-to-image prompt and markedly improves cutout
> purity). The whole material layer is torn open top and bottom along arcs that follow the subject's
> outline, and the centre seam reveals the content — the window can hold the cutout subject (A) or
> **the original photo (B, recommended: the window stays continuous, with no material colour bleeding in)**;
> see `references/kraft-tear.md`.
>
> When to use: exhibition / performance / festival key visuals; any poster in the
> "photo cutout + calligraphic title" style.
> Keywords: cutout poster, silhouette subject, white-background cutout, automatic composition,
> calligraphic poster, paper ground, duotone, mask, machine check.
>
> Sibling skill: photo-art-forge (translation / collage route, nine paradigms); this skill takes the
> "cutout subject" route — four automatic layouts plus a full-width scroll.

## 0. Default output contract (★ set by the lead on 2026-10-11, **now the default way of working**)

> The lead's words: "From now on, whenever I ask this skill to produce a poster, it works this way…
> The Chinese and English text requirements (size, layout, and so on) are the current state we have
> arrived at through all the training you and I have done, and **you will not always need several
> layouts**. If there are special requirements I will tell you directly."

### Inputs = a set of three (none may be missing — if one is missing, ask)

| # | Input | Description |
|---|---|---|
| ① | **Material image** | The background texture: weathered earth wall / rock face / stone surface / paper … (`--material`) |
| ② | **Scene or object photo** | The real-world photo containing the subject (`--photo`) |
| ③ | **Subject description** | A paragraph saying **which layer / which part** is to be cut out (it goes into the white-background candidate prompt and markedly improves cutout purity) |

> ★★ **Large text blocks go only on blank material, never over the cutout motif** (set by the lead on
> 2026-10-12) — "from now on, try not to put big blocks of text where they cover the cutout motif."
> Blank areas must be **measured**, not guessed: align the window mask with the canvas and print a
> "material blank-rate grid" (16×8 cells), then take a 100% whole cell for the title. Reference case:
> the grid printout in `test/case17-walls/run_case17.py`.
> The title is also **not necessarily vertical**: staggered horizontal setting (see the 13/12
> "非遗文化之美" [The Beauty of Intangible Cultural Heritage] example) works just as well — choose by the
> shape of the blank area (narrow and tall → vertical; wide and flat → horizontal).
>
> ★★ **Take the ink colour from the picture itself** (asked for by the lead on 2026-10-12): "you could add
> a step that **extracts the most prevalent dark colour in the image** and gives the type a colour from it,
> which will be more harmonious" → `pick_ink.py` takes the heaviest cluster in the shadows as ink
> (plus a secondary ink2).
> ⚠ Sample the **source scene** (the darks in a finished poster are dominated by the material's grey cast,
> so you would get a grey back);
> ⚠ `--max-lum` must be back-calculated from the **most demanding small-text background** and given
> **headroom** (in that case at 0.0125 the f-2 line scored only 4.49; it only passed once tightened to 0.011).
>
> ★★ **The visual weight of every part of the picture must be balanced too** (the lead's reminder,
> 2026-10-12): do not let one corner be crammed while another sits empty; after setting the type, look back
> at the overall **visual weight distribution** (how much the title, the small text, the info bar and the
> negative space each carry).
>
> ★ **Look at the pictures before you set type**: `assets/ref-posters/` holds **10 excellent examples** the
> lead put into the skill directly (山高水長 [High Mountains, Long Waters] / 敦煌博物展 [Dunhuang Museum
> Exhibition] / 吉光片羽 [Glimpses of a Rare Treasure] / 非遗文化之美 [The Beauty of Intangible Cultural
> Heritage] ×2 / 竹编艺术 [Bamboo Weaving Art] / 徽州灯彩 [Huizhou Lantern Art], plus the three parent
> pieces from the "壁上万象" [Wall Vision] period: EASTERN ESSENCE / ORIENTAL ZEN / CHINA 2025 — the last
> three being the **original sources** of the sandwich / axis / editorial skeletons).
> **Learn the layout from them; do not work from memory** — read `references/ref-posters.md`
> (it contains a reading for each poster plus 14 reusable moves and how to apply them).
> **Learn only "how the type is placed"; the typefaces and canvas spec do not change**
> (Chinese calligraphic system / Inter for English; 1500×1875).

> ③ Do not skip it. Measured: with no description the hole ratio was 10.19%; the literal word
> "band" [条带] gave 11.31%; the full continuous phrasing ("three walls join one another continuously,
> forming a complete encircling structure, one whole continuous wall, not a band, not fragments, not cut
> apart, not separated") gave **0%**. **The accuracy of subject recognition rests almost entirely on this
> paragraph**, and it must say clearly "which layer" is wanted (pitfall: the display wall was cut out when
> what the lead wanted was the semi-transparent gauze curtain).

### Default output

1. **Route**: tear open the material layer. **Work out the shape orientation first** (from the subject's
   form; do not apply a template mechanically):

   | Subject form | Shape | Command |
   |---|---|---|
   | **A horizontal strip** (wall surface, banner, scroll) | Horizontal tear band | `band_mask.py --orient h --shape flat/pinch` → `kraft_photo.py` (route B, window = the original photo); **switch to `kraft_window.py` if you need to choose a section horizontally** (see ★ below) |
   | **A vertical mass** (display case, standing figure, vessel, single projection) | **Irregular vertical window** | `band_mask.py --orient v --shape vpatch --yspan a,b` → **`kraft_window.py`** |
   | **Something that should cut diagonally across the whole sheet** | **Diagonal ragged block** | `band_mask.py --shape diag-rag --rotate 41` → **`kraft_window.py`** |
   | **The photo filling the entire poster** (like refs 06/07) | **Full-bleed ground** | **`kraft_full.py`** (plus `--scrim` to press a dark base under the type) |

   > Both shape routes must then be run through **`torn_edge.py`** (2D tearing: multi-scale
   > displacement + bite marks + fibre fray) — `band_mask` produces a smooth shape that is merely "cut
   > with waves", the *torn* quality comes from torn_edge, and "the photo entering into a relationship
   > with the paper" comes from `kraft_window`'s **texture trio** (`--seam/--fiber/--grain`).
   > Criteria and pitfalls: `references/kraft-tear.md` §1.6–1.9.

   > The vertical window is the third route, added on 2026-10-11 (case16, display case): material fills
   > the sheet and one **irregular vertical patch** is opened to reveal the photo. A horizontal band
   > would slice a vertical subject into two halves, and that is when you change orientation.
   > Criteria and pitfalls: `references/kraft-tear.md` §1.6 / §1.7.

   > ★★ **Shape orientation and script are decoupled** (added 2026-10-12): the mechanism of
   > `kraft_window.py` (it takes only the mask's alpha, and places the photo by `--scale/--focus`) has
   > **nothing to do with orientation** — **a horizontal tear band can use it too**, and it alone offers
   > **`--focus` for choosing a section horizontally**.
   > Criterion: if the tear-band route needs "which stretch of the photo" (there is an unwanted element
   > beside the subject, or one side must be cropped away) → use `kraft_window`; if you only need a
   > symmetric crop (`--zoom`) → `kraft_photo` is less trouble.
   > ⚠ The two scripts **anchor the mask differently**: `kraft_photo` anchors the mask's **mean top edge**
   > to `--yA` (it uses only the shape and the band height; the absolute position is irrelevant), while
   > `kraft_window` **uses the mask's absolute alpha directly** (the proportions given by `band_mask`'s
   > control points are positions on the canvas).
   > See `references/kraft-tear.md` §1.11.
2. **One version in Chinese, one in English**: `body[data-lang="en"]` toggles with one attribute, sharing
   a single master template.
3. **Only one skeleton by default** (not several layouts every time). Choose the skeleton from the material:
   - Torn-paper backgrounds (horizontal centre seam): `poster-sandwich-master.html` (top bar + bottom bar, the most robust)
   - Type extremely restrained, the middle band entirely image: `poster-axis-master.html` (centred on the axis)
   - Generous negative space wanted: `poster-editorial-master.html` (text left + large empty field)
   - **Vertical window + staggered vertical type**: `poster-column-master.html` (irregular vertical columns)
   - **Full-bleed ground**: also `poster-column-master.html`, with **`data-full`** on the body
     (vertical title top-left / vertical small text on the right edge / a small tag on the left edge /
     **an oversized cropped English word at the bottom**; light-type mode)
   - Non-torn-paper scenes: `poster-cutout-master.html` (four layouts, auto-selected)
   **How many skeletons and which one is decided by the lead's wording on the day.**
4. **Type specification = the current frozen values** (do not reinvent them, and do not fall back):
   - **Not one piece of information may be dropped**: main title / subtitle / tagline / exhibition dates /
     opening hours / venue / **booking CTA**
     (details under "information completeness" in `references/calligraphy.md`).
   - Chinese: title in ZhiMangXing (志莽行书) with the **art-lettering treatment**; **subtitle / tagline in
     MaShanZheng brush kaishu** (the tagline belongs to the calligraphic layer); only dates / hours /
     venue / CTA — pure information — use the sans.
   - English: **Inter**, titles at **Black 900**; sizes and layout follow the
     "English values for the three master templates" table in `calligraphy.md`
     (sandwich 102 / axis 102 / editorial 146+88).
   - **Hierarchy on the axis skeleton**: the main title is at least twice the size of a single key
     character (152 / 70 as delivered).
5. **Must-pass acceptance**: `check_contrast.py` fully passing (no overflow) + `text_contrast.py`
   diagnosis + two human-eye gates: **zero off-colour banding on all four edges** and
   **no text crossing the centre seam** (the threshold follows how heavy the chosen shape is).
6. **★★ Aesthetic floor (set by the lead on 2026-10-12, "work this way from now on")** — passing every
   machine check does not mean it looks good; these three rank alongside the human-eye gates:

   | Requirement | How it is measured | If it fails |
   |---|---|---|
   | **The title must be big** | Size the main title by **how large the type area can take**, **not** by the small-type proportions of a reference poster. Two words plus a mark in the top bar: `size ≤ (live area − mark) ÷ (2.8 × word count)` (sandwich, two three-character words + an 84px mark → ceiling ≈225px, 208px in practice) | Measure the string width with `getlength` first, then set the size; **change the line breaks** in preference to shrinking the type |
   | **Do not leave too much empty space** | ① **The image window / subject occupies ≥ 45% of the picture** (2026-10-12 case: 47.2%); ② in each paper band, **the type block's top and bottom margins together ≤ 1.5× the type block's own height** | Work through "① change the lines / change the structure ② reduce the size ③ move it" — **you may not delete information** |
   | **The whole must look good** | On the final pass, look back at the **visual weight distribution** (how much title / small text / info bar / image / negative space each carries); no corner crammed, no corner empty | Add size or one further information element to the light side — **not decoration** |

   > ★ Two more closing moves of the same rank: **the ink colour and the seal colour must be traceable
   > back to the material** (`pick_ink.py` takes the picture's main dark; when the material contains warm
   > minerals / gilding / wooden lattice, a **vermilion square seal** as the warm signature point is more
   > effective than adding decoration); and **look at `assets/ref-posters/` before setting the type**
   > (learn only "how the type is placed").

### Special requirements override the defaults

If on the day the lead says "three skeletons", "change the palette", "change the size", "no CTA" or
anything similar, **that instruction wins** — but **information completeness** and the
**machine checks plus the two human-eye gates** are the floor and are never skipped for a special request.

### ★ Non-0.8-ratio canvases (landscape 16:9 and so on) — added 2026-10-13

The default spec is **1500×1875 (4:5 portrait)**. When the brief calls for a **16:9 landscape**, take the four steps
below — **do not** edit the script sources by hand:

1. **Canvas size goes through environment variables**: `kraft_tear.py` already supports `PF_W` / `PF_H` overrides
   (`kraft_window` / `kraft_photo` take their `W/H` from it). Set them before calling the script and the default
   behaviour is unchanged:
   ```powershell
   $env:PF_W = "1920"; $env:PF_H = "1080"
   ```
   ⚠ **`band_mask.py` does not read the environment variables** — you must pass `--w 1920 --h 1080` explicitly
   (omitting them raises a missing-argument error).
2. **All type is absolutely positioned and recomputed for the canvas**: the masters' `:root` is a portrait baseline
   (`--stage-h 1875`, `--margin 78px`, Chinese `--size-main 220px`). Landscape means redefining `--stage-w/h`,
   tightening `--margin` to about 104px, and **re-sizing the main title by "how large it can be"** (at a 16:9
   column width of 830px, about 176px for Chinese and 82px for English are the measured values).
   ⚠ In landscape, **do not** apply the sandwich top-bar + bottom-bar directly — the two paper bands are too thin
   inside 1080px of height and the title collides with the ICH line.
   The verified landscape skeleton is **"left-hand type column (830 wide) + vertical torn window on the right"**;
   copy it from that case.
3. **`band_mask.py --orient v --yspan` had an out-of-bounds bug** in landscape (canvas wider than tall), **fixed
   2026-10-13** (it iterated rows but indexed columns). If you hit `IndexError: index ... is out of bounds`,
   check that the script is this version first.
4. **★ Type against the centre seam — the landscape trap that catches most people**:
   - The seam is a **vertical dark/light boundary**, and long horizontal information lines
     (`dates …–… / Tue–Sun …`) are **extremely easy for it to run straight through**, while the machine check only
     measures "is the contrast inside the box sufficient" and **not "is it cut in half"** — so it **passes silently**.
   - Criterion (what the self-check script `_seam.py` does): for each row take the x of the first dark pixel in the
     right half of the bg image as the window's left edge, then compare it with each `[data-text]` box's `x_end`;
     **a gap < 24px counts as "overlapping / too close"**.
   - Fixes, in priority order: ① **move the whole info block clear of the window's left edge** (that case: the
     lower-left "dates / hours" block pushed out to x=934 with `width: var(--col)` against a window left edge of
     1027, leaving 93px) ② **split it in two**, keeping the long line on plain paper and moving the organisation
     line + CTA into the lower right of the window (what that case did) ③ raise the window's bottom edge above the
     info block (only viable when the subject is short) ④ only then change the window geometry.
   - Do not try to muscle through "with a halo stroke" — the seam is a **structural cut** and a stroke cannot save it.

> Reference implementation: `test/weifang-kite-16x9/` (1920×1080, left type column + vertical window on the right,
> machine check PASS in both Chinese and English).

### ★ The non-torn route: material filling the sheet + multi-subject collage — added 2026-10-14

When the client says "the torn paper looks jarring" or "complete the background material, do not tear it", take
this route (the second version of that case):

1. **The background simply fills the sheet, with no tear at all**: `.stage > .bg { position:absolute; inset:0;
   width:100%; height:100%; object-fit:cover; }`. The tear mask, the synthesised display ground and `kraft_window`
   all drop out of the pipeline.
2. **Legibility comes from "lifting the background locally"** (the least trouble and the cleanest legibility fix
   when there is no tear): lay a **soft masked lift** over the type column — fading out horizontally about 0.3 of
   the canvas width beyond the column's right edge, 140px top and bottom, a lift of +34, with a `GaussianBlur(26)`
   transition. In that case the left column's p5 rose to **248**, the black title had an extremely clean backing,
   and `text_contrast` reported 0 busy-backing items.
   ⚠ **Do not** solve it with a dark plate or a heavier stroke — the material is pale paper, so lifting is enough.
   **★ But when the background image is "busy", switch to a black-point lift rather than an overall lift**
   (settled 2026-10-14, v3): if the background is **a picture with content in it** (say an ink-wash village with a
   band of black tiles running across the middle, straight through the title band), an overall lift only washes the
   painting into milky white (the ink's force is lost — measured, it fails). The right move is a **black-point
   lift**: `out = lo + src × (255 − lo) / 255` — lifting only the shadows, leaving the highlights almost untouched.
   At `lo=170` ink black (≈20) rises to ≈182 while paper highlights (≈235) stay at ≈249, so **the house shapes
   survive (it still reads as a painting) but black type can hold its ground**; it applies only to the type column,
   with `lo=0` elsewhere to preserve the original, and a **350–450px horizontal gradient plus 24px Gaussian
   feather** between the two, so it reads like "morning mist rising" rather than the edge of a mask.
   Tuning experience: on an ink-wash background, moving `lo` from 142 to 170 raised the lowest machine-check item
   from 7.27 to 9.78 and the look from "dirty" to "clean".
3. **When the background is not 16:9, crop it with `object-fit: cover`**, never stretch it; watch that **the edge
   you crop away is not the edge with the most content** (in v3 the source was 1920×1273, taller than 16:9, so
   cropping 193px top and bottom by centre removed only mist, keeping the willow branches at the top and the small
   boat at the bottom).
4. **Multi-subject collage layer**: composite all the cut-out subjects into one separate transparent PNG
   (e.g. `layers/KITES.png`, 1920×1080 RGBA) and stack it in the HTML as a `.stage > .kites` layer above `.bg` and
   below the `.type` text (`object-fit:contain; pointer-events:none`).
   **The typography does not change at all** — the new layer takes no part in the type layout and not one
   `[data-text]` element needs touching.
5. **Collage rules**:
   - **★ 3–5 subjects is about right** (real feedback 2026-10-14: eight and then seven were both read as "too many,
     too crowded"; the client asked for "three or four is enough"). Fewer than 3 leaves the right half empty, more
     than 5 fight each other and smudge into a mass; **the count is an independent layer parameter, so changing it
     does not touch the background or the HTML** — re-run the collage-layer script and swap `KITES.png`, and the
     machine-check values do not move at all (the text boxes' backing depends only on the background).
   - **The key visual is the largest, sitting centre-right as the anchor** (that case: a sand swallow at 470px
     high); the rest step down by **1.2–1.6×** and alternate in size; with only 4 left, the anchor can go to 560px
     with the four of them holding the four corners, which is the most stable arrangement.
   - Stagger the vertical positions so several do not land on one horizontal line; a slight bleed off the canvas
     horizontally reads more naturally;
   - Give each a **soft cast shadow** (offset 10/16, blur 22, strength 0.26–0.34) — a dark subject on pale paper
     must have one or it "smears" into the sheet;
   - **★ The information band (bottom bar + CTA) must be kept entirely clear**: never place a subject in the bottom
     bar's information row, or the type lands on a pattern (in the first version of that case two kites at
     cy 830–880 ran over the organisation line).
   - **★ When you swap "the key visual one", every other subject has to give way again** (added 2026-10-14): a new
     subject can have the same **bounding box** and still spread much further **beyond its outline** (in this
     example the sand swallow's wings are wide with flared tips, so it "occupies" more than the flying apsara it
     replaced) → dropping it straight into the old position covered nearly half of its neighbour (the apsara was
     about 50% hidden). The way to do it: pull the new subject in slightly (566→540), then spread the whole group
     out so the overlap stays in the 40–60px "flying behind / in front" band.
   - **★ Before reusing an old cutout, check for white-background residue**: composite it onto a **saturated
     magenta/cyan ground** and inspect by eye — the notches and the area outside the outline should be cleanly
     transparent. **Cutting a cream subject out of a white background** is the easiest way to leave dirt, and the
     eye cannot see it on pale paper.
6. **★ The silent risk changes place: "type over a subject" instead of "type over the seam"**: the machine check
   only measures "is the contrast inside the box sufficient", **not "is there a pattern behind the type"**.
   Criterion: per box, measure the collage layer's alpha coverage plus the background's p5 luminance;
   **coverage > 8% and p5 < 170 counts as "overlapping"**. With that case's eight kites laid out, every text box in
   both versions measured `kite-cov = 0.0%`.

> Reference implementation: v2 of `test/weifang-kite-16x9/` (`_build_bg2.py` for the background lift +
> `_build_kites.py` for the collage layer); for the black-point-lift version used when the background is "busy",
> see `test/weifang-kite-v3/` (`_build_bg3.py` plus §2's addendum in this section of the skill).

### ★ A universal keying recipe for flat colour backgrounds — added 2026-10-14

When a batch of material (say eight kite photos) has different background colours, **scout first, then decide the
strategy**: read the mean of the four 24px corners and the border std. If `std ≈ 0` the background is a **flat
colour**, and one recipe covers them all — **do not tune each image by hand**:

1. Sample the four corners → background colour `bg`; `d = ‖px − bg‖` (Euclidean); `alpha = clip((d − 12)/30, 0, 1)`
   as a soft threshold.
2. **Saturation compensation** (rescues "pale painted areas that sit close to the background colour"):
   `sat_excess = clip((sat − sat_bg − 6)/26, 0, 1)`, `alpha = max(alpha, sat_excess · (d > 6))`.
3. **The fallback criterion must be relative to the background colour, never an absolute threshold**
   (★ stepped on in v3, 2026-10-14):
   - background **light** (`bg_lum ≥ 128`) → dark ink lines / dark structures are the subject:
     `lum < 42 → alpha ≥ 0.95`;
   - background **dark** (`bg_lum < 128`) → bright silk / white wall is the subject: `lum > 205 → alpha ≥ 0.92`.
   ⚠ Writing these as two side-by-side absolute criteria **misfires across the whole image on dark-background
   material** — the original intent of "`lum < 42` → subject" is "dark ink lines on a light background belong to
   the subject", but when the background itself is at lum≈14 that condition holds for **every pixel** → alpha all
   1 → the cutout **fails 100%** (three dark-background images from the same batch: 99.1% / 100% / 98.6%, a clean
   sweep of failures). Choosing by background luminance instead brought it down to 22%–40%, which is normal.
4. **Connected-component cleanup** (keep the largest component plus those ≥ 6% of the area), where
   **★ any component touching one of the four edges counts as background** — this is the cure for a "background
   that is really a frame all the way round".
   (With no scipy on this machine, a hand-written 4-neighbour BFS labelling is enough; 1.7M pixels finish in
   seconds.)
5. `MinFilter(3)` → `MaxFilter(3)` (erode then dilate to remove white/dark fringes) → `GaussianBlur(0.8)` → crop
   to the bbox with a pad of 16.

⚠ **If the background is a "picture frame" rather than a "ground", it must be done in two passes**: when the
subject occupies only the middle of the image (say a wide dark border all the way round, with the histogram showing
a large share of pixels in the background colour), keying directly leaves the border as a huge edge-hugging
component and outputs a near-full-frame false foreground. The fix: first estimate the subject's extent with
"per-column / per-row count of non-background pixels > 2% of the canvas dimension" → **rough-crop the border away**
→ then re-sample the four corners on the cropped image and key there. (That case's `7.jpg` was exactly this; after
the rough crop it was 46.6% opaque.)

## 1. Five hard requirements → pipeline map

| Requirement | Where it lands |
|---|---|
| ① Composition must be chosen independently | `auto_compose.py` reads the subject's aspect ratio and mass centre and picks one of four layouts (hero-top / right / left / centre), writing the reason into `plan.json`; `--layout` overrides, and the full-width scroll `hero-band` is a manual option |
| ② Calligraphic typefaces, not ordinary fonts | Three open-source calligraphic typefaces in `assets/fonts/` (ZhiMangXing / MaShanZheng / LiuJianMaoCao) plus the master templates' type system; the sans is used only for the modern information layer. **English uses Inter** (Black/ExtraBold/Bold/SemiBold/Medium/Regular, SIL OFL) — `body[data-lang="en"]` switches the English typesetting in one step; details in `references/calligraphy.md` |
| ③ The original is upscaled / scaled down / cropped / masked into a better background | Backdrop window: framing `--focus` → upscale `--bd-zoom` (default 2.8) → crop → duotone LUT → chroma retention → soft focus `--bd-blur` → wash towards the paper colour `--wash` → lens feather mask → multiply onto the paper; `--no-backdrop` removes the window entirely (plain paper); **`--bg-mode color`: no window — it extracts a "primary + secondary colour" pair from the original into an offset two-colour gradient ground field (primary about 2/3, secondary entering diagonally from the bottom edge, smooth and speckle-free), `--bg-color "#RRGGBB"` sets the primary; direction `--bg-grad {diag,up}`, edge darkening `--bg-vignette`, two-colour lift `--bg-lift`** |
| ④ Cut out the main part, leave the rest empty | Three AI white-background candidates (full colour / ink silhouette / two-colour flat coat; the prompt includes the user's description of the subject) → `cutout.py` luminance→alpha plus denoise gating → the transparent subject over the paper (optional paint layers: `--shadow` cast shadow on the paper, `--reflection` water reflection on the sheet, `--paper` overrides the paper colour; subject strengthening: `--subject-pop` raises saturation/contrast, `--subject-paint` "repaints" in bold colour fields, `--subject-lift` brightens); the rest of the paper is left for the type |
| ⑤ Background first, type second | The pipeline enforces two stages: `auto_compose.py` emits `bg.png` (with built-in checks) → the master template only lays out type (**four master templates**: four layouts `poster-cutout-master.html` / top bar + bottom bar `poster-sandwich-master.html` / centred on the axis `poster-axis-master.html` / text left + large empty field `poster-editorial-master.html`; the last three are bilingual and all suit torn-paper / centre-seam backgrounds) |

## 2. Contents

```
photo-cutout-forge-en/
├── SKILL.md                        this document
├── assets/
│   ├── poster-cutout-master.html   calligraphic typesetting master (four layouts via data-comp, includes QA instruments)
│   ├── poster-sandwich-master.html "top bar + bottom bar" master (bilingual, includes QA instruments;
│   │                               suits torn-paper / centre-seam backgrounds — the middle band is left
│   │                               to the image and two material bands top and bottom carry the type)
│   ├── poster-axis-master.html     "centred on the axis (Chinese / English alternating)" master (bilingual,
│   │                               includes QA instruments; the most restrained — the type occupies one
│   │                               central line, single characters above and below form a word, and the
│   │                               middle band is entirely image)
│   ├── poster-editorial-master.html"text left + large empty field" master (bilingual, includes QA instruments;
│   │                               the type occupies a narrow column in the lower left, the least
│   │                               information and the most negative space)
│   ├── poster-column-master.html   "irregular vertical columns" master (bilingual, includes QA instruments;
│   │                               the main title becomes a **staggered column of characters**, with
│   │                               vertical small text and fine-line tags, pairing with the "vertical
│   │                               window" — the setting of the Dunhuang Museum Exhibition reference)
│   ├── presets.json                6 duotone presets (default azure-gold)
│   ├── ref-posters/                ★ reference poster library (**10** excellent examples plus a
│   │                               _contact-sheet.png overview) — put into the skill by the lead; look
│   │                               before you set type; how to read them is in references/ref-posters.md
│   ├── material/                   background material library (rock.sand pale sandstone / rock.aged
│   │                               weathered and cracked / rock.slate grey stone surface / kraft.cream
│   │                               cream paper)
│   └── fonts/                      Chinese: ZhiMangXing / MaShanZheng / LiuJianMaoCao;
│                                   English: Inter ×6 weights, EB Garamond (variable) — all SIL OFL
├── scripts/
│   ├── cutout.py                   white-background source → transparent subject PNG (alpha, color/ink/duotone)
│   ├── auto_compose.py             background processing + automatic composition → bg.png + plan.json
│   │                               (built-in checks; two routes: window / colour-extracted ground field)
│   ├── render_png.py               HTML → PNG (headless Edge/Chrome; can capture the QA background and text boxes)
│   ├── check_contrast.py           legibility machine check (WCAG: darkest 5% single-pixel measure inside the text box)
│   ├── text_contrast.py            text / backing contrast diagnosis (median measure plus background
│   │                               clutter std) + legibility plate generation (--plate); see references/qa.md §2
│   ├── board.py                    multi-image contact board (candidate boards / archive sheets)
│   ├── kraft_tear.py               torn material layer · A (window = the cutout subject; --material for the background material)
│   ├── kraft_photo.py              torn material layer · B (window = the original photo, recommended; --material for the background material)
│   ├── kraft_window.py             ★ torn material layer · C "**irregular vertical window**" (material fills
│   │                               the sheet and an irregular vertical patch is opened to reveal the
│   │                               photo); take the shape with band_mask --orient v / --rotate; includes the
│   │                               **texture trio** `--seam` (dark line of paper thickness) / `--fiber`
│   │                               (fibres catching on the edge) / `--grain` (matching paper grain);
│   │                               see references/kraft-tear.md §1.7–1.9
│   ├── kraft_full.py               ★ torn material layer · D "**full-bleed ground**" (photo across the whole
│   │                               canvas + material as paper grain + a scrim darkening the type area);
│   │                               learnt from refs 06/07/13 "fill the poster as far as possible",
│   │                               see references/kraft-tear.md §1.10
│   ├── pick_ink.py                 ★ takes the **most prevalent dark colour** in the picture as the ink
│   │                               colour (fallback: darkened to L ≤ --max-lum without sacrificing
│   │                               contrast); see references/qa.md "ink colour from the picture's main dark"
│   ├── torn_edge.py                ★ smooth shape → **2D torn edge** (large-scale displacement + random
│   │                               elliptical bite marks + fibre fray, keeping continuous alpha); the
│   │                               antidote to "the shape is too regular, it lacks naturalness",
│   │                               see references/kraft-tear.md §1.9
│   ├── band_mask.py                generate a shape mask: `--orient h` horizontal tear band (flat / pinch,
│   │                               concave in the middle and flared at both ends) / `--orient v`
│   │                               **vertical window** (vpatch, optionally limited vertically with
│   │                               --yspan, also closing irregularly at both ends); criteria in
│   │                               references/kraft-tear.md §1.6/§1.7
│   ├── art_title.py                Chinese main-title "art lettering" parameter generation (staggered sizes /
│   │                               vertical stretching / high-low offsets / slight rotation, reproducible
│   │                               via seed); details in calligraphy.md
│   ├── motif_band.py               motif band (slice the subject's pattern → flatten → arrange along an
│   │                               S-shaped ribbon; experimental route)
│   └── textzone_glow.py            glow in the lower-left text zone (legibility when setting type on a dark ground)
└── references/
    ├── cutout-craft.md             prompt templates (including subject-description rules) + alpha extraction craft + troubleshooting
    ├── composition-auto.md         five-layout parameters, decision rules, text zones, the plan contract, CLI
    ├── calligraphy.md              calligraphic typefaces and typesetting specification
    ├── ref-posters.md              ★ how to read the reference poster library (10 cases × 14 moves × how to apply them)
    ├── workflow.md                 end-to-end flow and commands
    ├── kraft-tear.md               the torn-material-layer route (three inputs / material library / three colour modes / framing / traps)
    └── qa.md                       the two machine-check measures + the human-eye gate
```

## 3. Visual model (three stages of composition, order not interchangeable)

```
paper ground (make_ground: preset paper colour + texture)
  → backdrop window (the original through zoom / crop / soft focus / duotone / wash, lens mask, multiplied on)
    → subject (transparent cutout, placed over)
      → only then the type (the master template only sets type and never touches the background)

or (--bg-mode color, a two-colour gradient ground field — no window):
extracted ground field (bg_ground: "primary + secondary colour" offset, smooth gradient, zero texture;
            direction --bg-grad, edge darkening --bg-vignette, two-colour lift --bg-lift)
  → subject (transparent cutout — repaint --subject-paint / raise colour --subject-pop / brighten
             --subject-lift — placed over)
    → only then the type (add data-theme="deep" to the body, light type on a dark ground)
```

## 4. Quick start

```powershell
# Three inputs (the initial material): (1) the real photo containing the subject (2) the material image
# (background texture) (3) the description of the subject (rewritten into the candidate prompt; rules in
# references\cutout-craft.md §1)

# 0) directories
New-Item -Force -ItemType Directory cand, cut, out | Out-Null

# 1) rewrite the template's subject sentence from the description, run image-to-image for white-background
#    candidates (three template sets in references\cutout-craft.md; run several and pick)
#    example output: cand\A2.jpg (full colour) cand\B.jpg (ink silhouette) cand\C2.jpg (two-colour flat coat)

# 2) white background → transparent (add --auto-white for a cream base; details in the cutout-craft.md troubleshooting table)
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\A2.jpg --out cut\A2.png --mode color --trim --pad 16

# 3) background processing + automatic composition (background first! run the three candidates with the same
#    preset/seed and pick a direction from the contact board)
python .trae\skills\photo-cutout-forge-en\scripts\auto_compose.py --source src-small.jpg --subject cut\A2.png `
    --preset azure-gold --seed 3 --out out\bg.A2.png --plan out\plan.A2.json --debug out\debug.A2.png

# 3B) torn-material-layer route (three inputs: --photo the original containing the subject + --material the
#     material image + the subject description (already used for the candidate prompt); B recommended:
#     window = the original photo)
#     three material colour modes: re-colour by default (--paper-dark/--paper-light set the stops) | keep the
#     original colours straight through (--material-gain 1.0) | keep the original colours and lift the
#     shadows (--material-gamma 0.52 power curve) — see references\kraft-tear.md
#     outline source: when the AI silhouette's geometry does not match the photo (multiple wings / U shape,
#     the window bottom falling onto a row of floor or the top showing ceiling) → switch to a
#     "traced-line mask from the photo" with --k 1.0 --smooth 21 (kraft-tear.md §1.5)
python .trae\skills\photo-cutout-forge-en\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --material material\rock.sand.png --zoom 1.45 --wall-top-row 1550 --out out\bg.rock.png
python .trae\skills\photo-cutout-forge-en\scripts\textzone_glow.py --bg out\bg.rock.png --out out\bg.glow.png `
    --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"   # probes = the lower-left text zone; adjust per layout

# 3C) colour ground-field route (replaces the backdrop window; use it when the soft-focus window reads as a
#     "blurry photo patch")
#     Dunhuang final parameters: vertical gradient + edge darkening + ground/subject lift + subject repaint +
#     cast shadow (machine check 12/12)
python .trae\skills\photo-cutout-forge-en\scripts\auto_compose.py --source src-small.jpg --subject cut\A2c.png `
    --bg-mode color --bg-color "#1F3F6E" --bg-grad up --bg-vignette 0.18 --bg-lift 0.30 `
    --subject-paint 1.0 --subject-lift 0.25 --shadow 0.35 --layout hero-band --seed 3 `
    --out out\bg.color.png --plan out\plan.color.json

# 4) set the type (once the background is frozen): copy the master + fonts + bg + **every external asset** →
#    edit the copy → set data-comp=plan.layout → render + machine check
#    ★ anything the HTML references via src (logo.svg / extra layer PNGs …) must sit beside the HTML —
#      one missing file means a broken image (see the first anti-pattern in §6)
#    for a dark ground field (3C) also add data-theme="deep" (light type on dark) and set .stage's
#    --stage-bg to the same value as the ground field
Copy-Item .trae\skills\photo-cutout-forge-en\assets\poster-cutout-master.html out\poster.html -Force
Copy-Item .trae\skills\photo-cutout-forge-en\assets\fonts out\fonts -Recurse -Force
Copy-Item <organisation LOGO>.svg out\logo.svg -Force
Copy-Item out\bg.A2.png out\bg.png -Force
python .trae\skills\photo-cutout-forge-en\scripts\render_png.py --html out\poster.html --out out\poster.png --scale 2 `
    --qa-bg out\poster.bg.png --boxes out\poster.boxes.json
    # ↑ render_png has a built-in asset pre-check: if any referenced relative asset is missing it errors out
    #   instead of silently producing a broken image
python .trae\skills\photo-cutout-forge-en\scripts\check_contrast.py --boxes out\poster.boxes.json --bg out\poster.bg.png
```

Full commands (including contact boards and troubleshooting) are in `references/workflow.md`.

## 5. Case evidence (the Dunhuang "壁上万象" [Wall Vision] case)

- Material: a curved mineral-mural exhibition hall; three candidates → `cut\A2.png` (chosen) / `B.png` /
  `C2.png`; A2 was automatically judged `hero-top`.
- Iterative repair: the original subject was hidden by a hanging gauze curtain → image-to-image edit to
  remove the obstruction and complete the hidden wall surface (`cand\A2c.jpg`) → re-cut `cut\A2c.png`.
- The final ran the **`hero-band` full-width scroll** (requested by hand) with azure-gold pale paper,
  a 0.30 cast shadow and a restrained 0.18 reflection: the subject spanning `[0,56,1500,935]`, no backdrop
  window, the paper carrying the type; all checks passed (subject×zone 0.0 / backdrop×zone 0.0 /
  blank_ratio 0.7153 / in-canvas true).
- The finished piece passed 12/12 machine checks (main title 11.28, smallest presenter 5.63), overflow all false.
- The torn-paper decorative version ran **route B** (window = the exhibition photo, framing
  `--wall-top-row 1400`; near-black ink `#171009` family plus a lower-left glow at gain 0.303):
  12/12 machine checks (lowest label 4.76); the A/B comparison is `trial.kraft\board.AB.poster.png`
  in the case directory.
- Material-driven background (user feedback: "switch to a rock-face material, it suits the subject better")
  → the skill moved to a **two-image material input model** (and to three inputs the same day, see the next
  entry): `--photo` the original containing the subject plus `--material` the background material image
  (rock face / stone surface / paper; the background adapts to whatever is uploaded); framing upgraded to
  `--zoom 1.45 --wall-top-row 1550` (window 539..1025, photo rows 1549..2487). Three materials tried —
  pale sandstone (stops 163,146,126→250,240,226 with `--detail 3.0`) 12/12 (min 6.54) / weathered cracked
  rock face: re-coloured and lifted 12/12, **original colours kept** at γ0.52 12/12 (min 4.63; `--material-gain`
  and `--material-gamma` were added after the user said "the original colours have been wiped out") /
  grey stone surface straight through with original colours. See `references\kraft-tear.md`.
- Second background iteration (user feedback: "the soft-focus backdrop window is blurry and ugly") →
  `--bg-mode color`, extracting a ground field: automatic clustering gave #60432A (bronze); the final used
  deep azurite `#1F3F6E` (a mural azurite-family dark blue, close to the reference posters) with
  `data-theme="deep"` on the master.
- Third background iteration (user feedback: "there are always speckles, it does not feel refined") →
  the ground field lost its texture and became a "primary + secondary colour" offset two-colour gradient:
  auto #60432A→#3E4E61 (blue-grey secondary), deep azurite #1F3F6E→#614C35 (warm dark-umber secondary);
  12/12 machine checks (min 6.09); old-texture/new-gradient comparison boards are
  `trial.color\board.grad.png` and `board.gradposter.png`.
- Fourth background iteration (user feedback: "try the gradient from the bottom upwards? the subject is not
  prominent enough") → `--bg-grad up`, a vertical gradient (the secondary colour rising across the full
  width from the bottom edge, the primary holding roughly the upper 2/3)
  plus `--bg-vignette 0.18` edge darkening, `--shadow 0.35` cast shadow and `--subject-pop 0.25`;
  "repainting" the subject with `--subject-paint 1.0` (denoise → raise saturation and brightness → contrast
  → colour quantisation) comes closest to the bold colour fields of the reference posters.
- Fifth background iteration (user feedback: "the overall brightness is not enough") → `--bg-lift` /
  `--subject-lift` (lifting value while keeping hue): both the H setting 0.18/0.15 and the I setting 0.30/0.25
  passed every machine check (the I ground field is brighter; the tagline ink #D3C5A6→#DDD0B2 lifted one
  step and re-passed at 4.77); the lift comparison boards are `trial.color\board.lift.poster.png` and
  `board.lift.bg.png`.
- Three-input upgrade (the lead's ruling 2026-10-10: the skill's initial inputs are the photo containing the
  subject + the material image + the subject description) → the candidate prompt is rewritten from the
  description: the literal word "band" [图带] caused banding (hole ratio 11.31%, a negative); "one whole
  continuous curved wall, not a band, not fragments, not cut apart, not separated" gave the cleanest
  silhouette (hole ratio 6.54% against 10.19% with no description, and zero contact top and bottom).
  After the description the outline band became flatter → the tear window became shorter (563px against
  891px) → compensated with `--zoom 1.58` (window 869px, subject enlarged and centred, the walls cropped on
  both sides, no floor showing), final `cases\skill-test-mural-tear\out\bg.png`.
- **Case 04 (2026-10-12) | oil-painting gallery photo + pale sandstone surface**: route B, horizontal tear
  band, outline source = a traced-line mask from the photo (`--k 1.0 --smooth 21`). Three candidates
  (A walls only / B walls plus a grey ceiling band above / C the complete horizontal band) went onto a
  contact board and **B** was chosen — with walls only the opening is all white wall, whose luminance is
  **too close to the pale stone for the tear to read**; including a grey band along the top (B/C) gives it
  the necessary layering. Final `bg.png` → sandwich master → one Chinese and one English version,
  both passing **10/10** machine checks with zero edge banding.
  ★ Two new lessons: ① **the "wall top line" of the display walls on both sides is far lower in the middle
  than it looks** (on the left the near wall top is at photo y≈640, in the middle distance it is at y≈900,
  and on the right it rises again to y≈370) — judging the "ceiling/wall boundary" by eye reads the middle
  wall top about 150px too high and the tear then eats into the grey band; use a **column-by-column pixel
  profile** (print RGB top-down at y=x) plus a zoomed grid to confirm. ② **Ink colour on a pale material**
  cannot copy the default `--max-lum`: the pale sandstone's dark speckles sit at p5≈0.20 (linear) →
  back-calculating for small type gives `L_ink ≤ 0.0056`, and **#0B0C0C (L≈0.0034)** was taken in practice
  to leave headroom (at `--max-lum 0.016`, 6/10 lines sat on the line).
- **Case 06 (2026-10-13) | ink-wash paper + a photo of the "水·名贤" [Water · Worthy Ancestors] gallery (poster
  for the water-governing sages)**: three inputs — material = a 573×993 ink-wash paper (distant misted mountains +
  a field of golden running script on the ground + one standing figure), scene = a 1394×690 photo of the gallery
  (hung scroll maps + standing figures of six water-governing sages + a Song-style model). Route: **horizontal
  tear band with `kraft_window.py` carrying the window** (in order to use `--focus` framing to crop out the
  visitors on the left).
  - **Shape**: `band_mask --orient h` with custom control points, mean top edge 500 / mean bottom edge 1390
    (band height ≈890), `--smooth 61 --jitter 0.012 --seed 11` → `torn_edge --edge 0.017 --edge-scale 22 --bites 0
    --fray 0.60 --fray-px 3.2` (no bite marks on a horizontal band), covering **46.8%**, fray transition band 2.72%.
  - **Window content**: photo native `x600..1394, y150..689` → 1500×990 (**s=1.889**, LANCZOS + UnsharpMask
    2.0/62); three settings s=1.64 / 1.85 / 2.20 went onto a contact board and **1.85** was chosen — at 1.64 the
    sages were too small, at 2.20 the window's top edge had no dark ceiling and the tear stopped reading.
    ★ **A dark ceiling at the top of the window is part of "tear legibility"**: taking only the bright wall leaves
    paper white and wall white too close in luminance and the upper tear disappears.
  - **Ground**: material cropped native `(0,244)-(573,961)` → 1500×1875 (2.618×), with `oy=640` so the exhibition
    notice lands on the pale tail of the script field; the trap of enlarging a low-resolution material and the
    back-solution for `oy` are in `references\kraft-tear.md` §7.
  - **Master template, sandwich**: top bar `治水 ▣ 名贤` (ZhiMangXing **220px**) plus a **vermilion square seal
    reading 安澜** replacing the geometric mark; a three-line complete exhibition notice in the bottom bar
    (subtitle/tagline in MaShanZheng kaishu, notice/CTA in the sans, 34px). The English version used
    `--size-main 162px` (WATER 3.85em + SAGES 3.50em + a 94px mark ≤ a 1344 live area, ceiling 168px).
  - Machine check: **11/11** in both Chinese and English (lowest 6.38 for the vermilion seal; titles 11.26 / 12.84);
    `text_contrast` worst 6.38 with 0 busy-backing items; zero edge banding; **0.00% type over the window**; window
    coverage 46.8%; top/bottom bar margins 0.22× / 1.26× the block height.
  - ★ Two new lessons: ① **the ink colour and the seal colour must each have a source** — `pick_ink` took the
    scene's main dark #2B2C2C → `--ink #232323` settled; the material has a gilded script field → use a vermilion
    seal as the warm signature. ② **"one HTML file switching Chinese/English with one toggle" is not achievable at
    present**: the five masters' `data-lang` switches the typeface only, with no copy dictionary → derive the
    English HTML from the Chinese one (see `references\workflow.md` §4).
- **Case 05 (2026-10-12) | curved lightbox photo wall + Qinghai-wave pattern paper** (a cultural-event key
  visual whose brief explicitly asked for "a big title / not too much empty space / it must be beautiful"):
  a horizontal tear band with the window = the original photo, but **carried by `kraft_window.py`** rather
  than `kraft_photo.py` — the photo's left side holds an enormous gilded main panel whose "黃永玉 大事記"
  [Huang Yongyu Chronology] duplicates the poster title and, cut in half by the tear, reads as wrong
  characters; `kraft_photo` can only crop symmetrically (`--zoom 1.0 / 1.15 / 2.0` all failed to remove the
  left third), whereas `kraft_window --scale 1.0 --focus 0.56856,0.38531` did it in one step (photo area in
  the window x182..932 / y320..796).
  Shape: `band_mask --orient h` with custom control points (band height ≈0.458H, **both edges rising about
  70px to the right** to echo the curve; the `pinch` preset's dumbbell shape had nothing to do with the
  material) → `torn_edge --edge 0.017 --bites 0 --fray 0.60 --fray-px 3.2`.
  Material: Qinghai-wave paper with original colours kept, `--material-gain 1.0 --detail 2.0`; the photo was
  pre-processed with 2× `LANCZOS` plus `UnsharpMask(2.0,62,3)`.
  Master: sandwich, a 208px ZhiMangXing top bar (`art_title --style upright`) plus a **vermilion square
  seal** (replacing the geometric mark as the warm accent); a three-line complete exhibition notice plus CTA
  in the bottom bar; one file for both languages, `?lang=en` to switch. Machine check 10/10 in both
  languages (lowest 10.25), zero edge banding, 0.00% window overlap. ★ Four lessons in §6.

## 6. Anti-pattern list (measured pitfalls)

- Letting the backdrop window show the original directly makes a "photo within a photo": it must be softened
  and washed before it recedes into a colour field — the image-layer hierarchy is the lifeblood of the
  cutout route.
- The lens glow ellipse behind an island subject easily reads as "a light spot / a shadow"; switching to a
  warmer framing only relieves it — prefer `--no-backdrop` or the `hero-band` full-width solution
  (measured on the Dunhuang case).
- The "soft-focus backdrop window" as a whole can read as a "blurry photo patch" (user feedback on the
  second Dunhuang iteration) → switch to `--bg-mode color` and a two-colour gradient ground field; type on a
  dark ground must have `data-theme="deep"`, since warm black type on a dark ground always fails the check.
- Texture laid over the ground field (cloud mottling / weave / grain) reads as "speckles, not refined"
  (user feedback on the third Dunhuang iteration) → bg_ground does only the two-colour gradient, keeping
  just 0.8σ of dither against banding; texture survives only on the window / paper route (make_ground).
- "The subject is not prominent enough" — three levers: `--shadow` cast shadow → `--bg-vignette` edge
  darkening to draw the eye in → `--subject-pop` raising saturation/contrast; for the reference posters'
  "repainted" feel on a photographic subject use `--subject-paint` (0.6–1.0: denoise + raise saturation +
  colour quantisation).
- "The overall brightness is not enough" — use `--bg-lift` / `--subject-lift` (keeping hue and saturation,
  lifting value only); **after lifting a dark ground every text contrast drops together**, so small type
  such as the tagline needs its ink lifted by one step to follow (on the Dunhuang I setting it went
  4.27→4.77 before passing).
- A cream-based material without `--auto-white` greys the whole ground; a `--despeckle` kernel that is too
  large (>5) eats fine stripes.
- When the cut-out subject is covered in the original by an obstruction (gauze, column): first run an
  image-to-image edit to "remove the obstruction and complete the hidden surface", then re-cut — do not
  patch the alpha by hand (measured on the Dunhuang hanging curtain).
- If contrast is insufficient add `--shadow` first; if the paper then feels too empty add `--reflection`;
  **below 0.30 a reflection is almost invisible to the eye — the visible setting is about 0.50**.
- The master template is copied, not referenced: once `assets\poster-cutout-master.html` is changed it must be
  re-copied into the case directory before rendering.
- **★★ Assets must sit beside the HTML (one file missing renders a "broken image") — actually hit on 2026-10-14**:
  the master sat in `layouts/` and the HTML said `<img class="logo" src="logo.svg">`, but `logo.svg` had only been
  copied into `src/`, another directory → the browser resolved it as `layouts/logo.svg`, **404**.
  The consequence: the headless browser **reports nothing at all** and merely draws a broken-image icon plus grey
  alt text in the top-left corner of the output; **the machine check cannot catch it at all** (`check_contrast` only
  looks at text rectangles, not at whether your images loaded), so a full round of QA comes back green. In that
  case both the Chinese and English versions went through two rounds (v1 torn, v2 complete) before anyone noticed
  — the lead spotted it first, by eye.
  → Fixes: ① copy every dependency (fonts / logo / background image) **beside the HTML** (fonts already live in a
    `fonts/` subdirectory, same idea);
    ② **`render_png.py` now has a pre-render check** (2026-10-14): it scans every relative `src=` and CSS `url()`
    in the HTML and exits with an error (exit 2) if any is missing, instead of silently producing an image. If you
    see "render pre-check failed: the HTML references assets that do not exist", this is that class of problem.
  → Lesson: **a "silent failure" trap belongs in the tool, not only in the docs** — docs depend on someone
    remembering to read them; the tool runs every time.
- **★ The background image's class must be kept separate from the title art lettering** (fixed 2026-10-12):
  all five masters originally used `<img class="art">`, sharing `.art` with the title lettering — and `.art`
  carries `padding:0.15em 0.12em` plus an equal **negative margin** (originally only there to leave room for
  the transform), and that negative margin pushed the `inset:0;width:100%` background out of place by about
  2.4px, **exposing a ~5px band of the light `--stage-bg` along the right and bottom edges**.
  → all five masters now use `<img class="bg">` plus `.stage > .bg`.
  Criterion: in a four-edge audit, **a std ≈ 0 across the outermost 8px means the ground colour is leaking**
  (real picture content cannot have std = 0) — do not wave it through as "a dark material edge". This is
  exactly why the "zero off-colour banding on all four edges" gate exists.
- `body[data-comp]` disagreeing with `plan.json.layout` = type landing in the wrong zone (the machine check
  catches overlap; the eye catches it sooner).
- The QA instruments (`?pf-qa=bg` and `#pf-boxes`) may not be deleted; without them check_contrast has no reference.
- Torn-paper route: mirroring and tiling the material whole produces symmetric butterfly artefacts → you must
  "scale the whole piece up to cover, plus a high-pass of the material's native-scale detail".
- Soft cutout edges (an alpha 0.1–0.4 wide transition) bleed through dark material into muddy stains → tighten
  alpha into the narrow transition band (m-0.42)/0.10.
- The tear arc is a compressed version of the outline arc (k<1), so material colour is inevitably caught
  between arc and outline — for "fully continuous inside the window" take the original-photo route (B).
- The material's default "re-colour" maps colours onto the two `--paper-dark/--paper-light` stops, wiping out
  the material's own stains, cracks and mineral colours (user feedback: "the rock face's original colours have
  been wiped out") → to keep the original colours use `--material-gain` (overall gain) or `--material-gamma`
  (power curve).
- A dark patch in the material falling inside a text box fails the machine check (background luminance is
  taken as the single-pixel P5 inside the text box, dark-ink measure) — plain gain cannot save it (it blows
  the highlights or clips), so use a power curve `--material-gamma 0.52` to lift the shadows and keep the
  highlights (Dunhuang weathered rock face: γ0.52 then 12/12, min 4.63).
- A glow gain on a dark ground must be computed in WCAG linear luminance (0–1) for p5:
  g=(0.26/p5)^(1/2.4)-1+0.005; using the sRGB 255 scale computes the wrong gain.
- Literal shape words in the candidate prompt ("band", "strip") get made literal by the image generator — the
  subject is drawn as a floating band and the white gaps become holes, so the hole ratio rises instead
  (measured 11.31% against a 10.19% no-description baseline) → rewrite the description as "one whole
  continuous …, not a band, not fragments, not cut apart, not separated" (6.54%); afterwards the outline band
  may be flatter and the tear window shorter (563 against 891px) → compensate with `--zoom` (1.58 in that
  case, WTR 694).
- Torn-paper route with a multi-wing subject (e.g. "display walls on both left and right", a U-shaped
  perspective): the AI silhouette's wall-band proportions did not match the photo (measured in that case:
  the middle pressed down about 2×) → the window bottom landed on a row of floor and the wing tops showed
  ceiling (user feedback: "I only want the two galleries, the floor in the middle has been included"), and no
  combination of k / framing / zoom matched → switch to a "traced-line mask from the photo" (control-point
  polyline on the photo → an alpha band of the same size) with `--k 1.0` (tear = true outline ± tear) and
  `--smooth 21` (preserving the outline; the default 81 is a big wave); measured in `cases\skill-test-gallery-tear`:
  window top = traced line ±10px, window bottom = about 100 rows above the wall foot (no floor showing).
- **★ A horizontal tear band is not `kraft_photo`'s private property** (case 05, 2026-10-12):
  `kraft_window.py`'s mechanism (taking only the mask's alpha and placing the photo by `--scale/--focus`) has
  **nothing to do with the shape orientation**, so a horizontal band can use it too, and it alone offers
  **`--focus` for choosing a section horizontally**. Criterion: needing "which stretch of the photo" (an
  unwanted element beside the subject / a side to crop away) → `kraft_window`; only needing a symmetric crop
  (`--zoom`) → `kraft_photo` is less trouble. See `references/kraft-tear.md` §1.11.
- **★ The two B routes anchor the mask differently**: `kraft_photo` anchors the mask's **mean top edge** to
  `--yA` (so the mask's absolute vertical position is irrelevant; only its shape and band height are used),
  while `kraft_window` **uses the mask's absolute alpha directly** (the proportions given by `band_mask`'s
  control points are positions on the canvas). Feed the same mask to both scripts and the window lands
  noticeably differently — this is by design, not a bug.
- **★ `torn_edge --bites` punches holes along a long horizontal band** (measured 2026-10-12): on a
  near-full-width boundary the elliptical bite marks read as a row of arcs / scallops
  (`--bites 18 --bite-size 0.030` is worst, the whole edge looking like a cloud; `--bites 10 --bite-size 0.045`
  also leaves several obvious round notches). **For a horizontal band use `--bites 0`** and leave the
  irregularity to `--edge 0.017 --edge-scale 22` plus `--fray 0.60 --fray-px 3.2` (fine fibres, closer to
  hand-torn); keep bite marks for **short boundaries** (vertical windows / diagonal blocks).
- **`kraft_window`'s `--detail` is on a different scale from `kraft_photo`'s**: the former defaults to `0.06`
  (≈ no effect), the latter to `4.0`. With a patterned paper (Qinghai wave / textile / stone) as the material,
  `kraft_window` needs **1.5–2.0** before the detail shows.
- **Beware photos containing "elements with large lettering"** (2026-10-12): the characters on a display
  wall's main title panel, a shop sign or a stele, cut in half by the tear, read as wrong characters — and
  they duplicate the poster title. The remedy is to **change the framing and exclude the whole block**; do not
  patch the alpha by hand, and when a symmetric crop cannot remove it use `kraft_window --focus`.
- **★★ Three traps of a landscape (16:9) canvas** (all hit in case weifang-kite-16x9, 2026-10-13):
  1. `kraft_tear.py`'s canvas was once hard-coded to `1500×1875` → the output came out the wrong size.
     **`PF_W`/`PF_H` environment variables were added to override it**; `kraft_window` / `kraft_photo` inherit
     them. `band_mask.py` **does not inherit**, so pass `--w/--h` explicitly.
  2. `band_mask.py --orient v --yspan` always crashed with `IndexError` when **the canvas was wider than tall**
     (it iterated rows but indexed columns; portrait survived by luck because `CW < CH`). **Fixed** (the correct
     semantics being "the vertical range of each column x" ∩ "the horizontal range of each row y").
  3. **A centre seam running through a long information line is a silent error** — the machine check only measures
     whether the contrast inside the box is sufficient, not whether it is cut in two, so it lets it pass.
     Self-check: for each row take the x of the first dark pixel in the right half of the bg image as the window's
     left edge and compare it with each text box's `x_end`; **a gap < 24px counts as "overlapping / too close"**.
     Fixes are in this document under "Special requirements override the defaults → non-0.8-ratio canvases" §4.
- **★ The "photo" inside the torn window can be synthesised** (2026-10-13): when the material has only
  white-background cutouts and no real scene, build a **display ground** with PIL (warm paper-coloured radial base
  + soft glow + subject + cast shadow) and feed it to `kraft_window` as `--photo` — the result is far better than
  laying the white-background cutout straight in, because the window then reads as "an object on display under a
  lamp" instead of a smudge. Take the ground colour from the material (that case took the sand swallow's
  rice-paper tones) and **do not** use a flat dark brown — a dark window opened in paper-coloured material reads
  as an "ink slab" rather than "content revealed by tearing".
