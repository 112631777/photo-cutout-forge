# Torn-material-layer route (kraft-tear)

> Positioning: the **material-driven background** route of photo-cutout-forge-en — the entire background source image (rock face / stone surface / paper, etc., adaptive to the user's uploaded material),
> with top and bottom tear openings torn along the subject's contour arc, the centre seam revealing a strip of content; **the material layer always overlaps above the content** (the iron rule of background first, type second is unchanged).
> Scripts: `scripts\kraft_tear.py` (A) / `scripts\kraft_photo.py` (B) / `scripts\textzone_glow.py` (legibility support for type on dark ground).

## 0 Input model (three inputs) and composition order (do not swap)

Three inputs: ① one **scene or object photo containing the subject** (`--photo`, used for the window in route B; cut out `--cutout` for the tear-opening contour arc)
+ ② one **material image** (`--material`, background texture; the closer its tone/texture matches the subject's environment, the better the fit)
+ ③ a **description of the subject** — written into the image-to-image prompt of the white-background candidates (rewriting rules in `cutout-craft.md` §①; the description affects the shape and height of the contour band, and thus the tear-opening window — see §4).

```
Full material layer → window content (A cutout subject / B original photo) → light tear-opening cast shadow (narrow band 7px/0.24, preserve content's original colour)
  → top material over (y≤e_top) → bottom material over (y≥e_bot) → paper-core white line 5px + paper-edge slight highlight 0.10
```

Tear-opening geometry: tear-opening line = subject contour arc × k (compression factor; k<1 is gentler) + random torn edge;
edge-overlap auto-positioning: the material edge overlaps the subject by at least 20px (the subject's edge always stays hidden behind the material).

## 1 Two window-content routes (which to pick)

| Route | Script | Window content | Conclusion |
|---|---|---|---|
| A | `kraft_tear.py` | cutout subject | the arc necessarily traps material colour between the arc and the contour (a structural problem when k<1); after hardening the soft edge the subject's original colour recovers, but the window is still not fully continuous |
| **B (recommended)** | `kraft_photo.py` | original photo | the window holds a continuous real-photo image with no material colour mixed in; the Dunhuang final used this route |

Both scripts produce geometrically identical output under the same `--seed` (Dunhuang case @ k=0.60 / zoom 1.45 / seed 33: e_top≈539, e_bot≈1025, tuck 20/20).
The old default-parameter path has been byte-aligned with the v3r final (smoke test md5 matches; new default parameters cause zero regression).

### 1.5 Contour source: AI silhouette vs photo-traced mask (the crux of whether the tear "looks like the subject")

The tear-opening line = the contour arc of the `--cutout` silhouette; the silhouette can come from two routes:

| Contour source | When to use | Method |
|---|---|---|
| ① AI silhouette candidate (default) | subject geometry roughly matches the real photo (front-on / single wing) | white-background candidate → `cutout.py` → feed straight to `--cutout` |
| ② **photo-traced mask** (fidelity) | AI silhouette geometry **does not match** the real photo (multi-wing, U-shaped perspective, oblique view) | trace top/bot control points along the true boundary on the photo → polyline → alpha band mask **at the photo's size** → feed to `--cutout` |

- Route-switch test: after rendering, the window bottom falls into the floor row / the window top exposes the ceiling, and no amount of `--k / --wall-top-row / --zoom` tuning aligns the two wings with the middle section —
  the silhouette's proportions differ from the real-photo perspective (case measured: the AI silhouette's mid-section drop is ≈2× the real-photo geometry).
- Tracing method (case `skill-test-gallery-tear`): overlay a grid on the photo and read by eye (wall S≈0.10-0.25 low saturation, wood floor S≥0.3;
  brightness is disturbed by spotlights/dark bands, so L+S must be read jointly); trace the three top-line segments "left wall top → far mid wall top → right wall top" plus the corresponding wall-base lines;
  `np.interp` builds the polyline, `(yy>=top)&(yy<=bot)` fills alpha → a mask at the photo's size.
- Tracing parameters: `--wall-top-row` = mean of the traced top (photo row); `--k 1.0` (tear-opening line = traced line ±tear, no more compression);
  `--smooth 21` (preserves contour detail — the default 81 would smooth the polyline into a big wave).
- ★ Case: **three-sided curtain wall (left/centre/right U-shape)**, 2026-10-12 case17 — follows the route above exactly:
  overlay grid, read by eye the "three top-line segments + wall-base line" → `np.interp` polyline → alpha mask at the photo's size
  → `torn_edge.py` (tear) → `kraft_photo.py --k 1.0 --smooth 21`.
  Measured values: photo 1537×1920, top-line mean 371, wall-base mean 1099, band-height mean 728 (coverage 37.9%);
  `--wall-top-row 371 --top-edge 420 --yA 420` (⚠ these two parameters, one controls the photo placement and one controls the tear-opening line position,
  **must both be given and consistent**; giving only one shifts the whole thing ~120px).
- ⚠⚠ **Perspective-shrunk side display walls: the mid-section "wall top" sits far lower than where the eye sees it** (measured in case04, 2026-10-12).
  The near wall top on the left of the frame is at photo y≈640, the far mid wall top is at y≈**900**, and the right side rises again to y≈370 ——
  relying only on the eye to read "the ceiling/wall boundary line", you would read the mid-section ~150px too high, and the tear-opening top edge would eat into the grey curtain/ceiling.
  **Reliable method: print a vertical pixel profile column by column** (fix `x`, print RGB from top y downward, find the "dark curtain → bright wall" transition),
  then sample 8–10 x values as control points; locally magnify with a 50px grid only to cross-check, not to read absolute positions.
  The mid-section far-view band is naturally very narrow (band height down to ~190px in the case), **do not** raise the top edge above the wall top just to make "the band look wide" ——
  either accept the narrow waist (dumbbell shape), or cut the bottom edge above the wall base (**never expose the floor**, explicit user requirement).
- Verification (numerical audit): route B window content = photo slice laid in **1:1** —— compare rendered pixels with photo pixels column by column, take the **longest matching run** = the actual window's top/bottom bounds;
  pass line: window top = traced line ±10px (photo row), window bottom = about 100 rows **above** the wall-base line (no floor exposed).

### 1.6 Tear-opening shape: flat bar or dumbbell (added after a team member's feedback, 2026-10-11)

**The shape of the tear-opening line = mask top/bottom edges × k**, so **shape extraction is just choosing the mask's shape**.
Generate with `scripts\band_mask.py`, which has two built-in presets:

| Shape | Feature | Effect |
|---|---|---|
| `flat` | a flat horizontal band with nearly straight top and bottom edges | stable, clean; but **easily splits the frame into top/middle/bottom thirds**, a hard cut |
| `pinch` | **concave middle, expanding ends** (dumbbell shape) | the centre seam is narrow in the middle and wide at the ends; the exposed content breathes and varies, **strong sense of depth** |

A team member's verbatim feedback: "the cutout carves a flat horizontal '一'-shaped pattern out of the original, making the frame very fragmented, becoming a hard three-equal-part situation".

```powershell
python scripts\band_mask.py --w 1537 --h 1920 --shape pinch --out out\mask.png
python scripts\kraft_photo.py --cutout out\mask.png --photo src\scene.jpg --material src\material.jpg `
    --k 1.0 --smooth 21 --zoom 1.45 --wall-top-row 560 --material-gamma 0.52 --out out\bg.png
```

- ⚠ **`--smooth` must be set to 21** (not the default 81): the default would smooth the dumbbell into a big wave, wasting the shape extraction.
- The `pinch` preset (canvas-height ratio): top edge `0.252→0.332→0.258`, bottom edge `0.552→0.476→0.546`
  (7 points, top and bottom edges **deliberately different**). Use `--top` / `--bottom` to pass custom control points for fine-tuning.
- **After changing the shape, the centre-seam's top/bottom edge positions shift** —— all the "text does not overlap the centre seam" check thresholds must shift with them
  (case: centre-seam top edge from 539 → left 380 / mid 583; bottom edge 1167 → left 1191 / mid 990).

### ⚠ Natural feel: control points alone are not enough (added after the lead's feedback, 2026-10-11)

Giving only "concave middle" control points produces **a left-right symmetric smooth arc** —— it is obviously drawn,
not torn (the lead's words: "this dumbbell shape is far too regular, it has no natural feel").

A real tear has three features; all are required:

| Feature | Method |
|---|---|
| **Asymmetry** | use **differently shaped** control points for top and bottom edges (no mirroring); `band_mask.py` prints the left-right asymmetry amount for checking |
| **Multi-scale undulation** | `--jitter` (default 0.012) adds **1D fractal noise**: low frequency gives large waves, high frequency gives fine edges |
| **Fine edge fragmentation** | leave the final touch to `kraft_photo`'s built-in random tear |

```powershell
python scripts\band_mask.py --w 1537 --h 1920 --shape pinch --jitter 0.013 --seed 7 --out out\mask.png
```

- `--jitter 0` turns off noise and reverts to a smooth arc (useful as a control); change `--seed` to change the tear.
- ⚠ **Noise raises the top edge and exposes the ceiling**: the larger `--jitter`, the more the window shifts up, so you must go back and check whether any black is exposed
  → if needed, increase `--wall-top-row` (case 560 → 600).

**⚠ Do not turn this into a hard rule** —— the shape must be analysed case by case against the material:

| Material feature | Suggestion |
|---|---|
| subject is horizontally coherent and the frame already has top/bottom divisions | `flat` is tidier |
| subject is arc-shaped / enveloping, or you need to break the thirds feel | `pinch` gives more depth |
| the mid-section content is the main subject itself (you do not want it "pinched narrow") | use `flat`; or `pinch` but reduce the mid-section undulation |

> Shape extraction is a **layout decision**, not a parameter default. **Look at the material first, then decide**; do not mechanically apply `pinch`.

### 1.7 Shape orientation: horizontal tear band or **vertical irregular window** (added 2026-10-11)

Everything in §1.6 is **horizontal** shape extraction (each mask column's top/bottom edges → one horizontal band), which splits the frame into top/middle/bottom.
But some materials' subjects are **naturally a vertical clump**, and cutting horizontally would split them in two.

| Subject form | Shape orientation | Script |
|---|---|---|
| horizontal sweep: wall surface, long scroll, spanning gauze curtain, a range of mountains | horizontal tear band | `band_mask --orient h` → `kraft_photo.py` |
| **vertical clump: display case, standing figure, artefact, single projection, a column of pattern** | **vertical irregular window** | `band_mask --orient v` → **`kraft_window.py`** |

```powershell
# Vertical window (case16 display-case final parameters)
python scripts\band_mask.py --w 1500 --h 1875 --orient v --shape vpatch `
    --jitter 0.008 --seed 11 --yspan 0.24,0.78 --out cut\win.png
python scripts\kraft_window.py --win cut\win.png --photo src\scene_clean.png `
    --material src\material.jpg --scale 2.13 --focus 0.617,0.50 `
    --material-gamma 0.52 --shadow 0.30 --rim 0.16 --out out\bg.png
```

- `--yspan` limits the vertical range (if not given = spans the full height); the window's **top and bottom ends also get irregular closure** (`--end-jitter`).
  ⚠ **The window's aspect ratio must match the subject region's aspect ratio in the photo**, otherwise it either does not fill (leaving empty space) or crops the subject:
  first measure the subject's bbox in the photo, then set `--yspan` and `--scale` (`scale ≈ window width ÷ subject-region width`).
  Case: subject region 282×422 px → window 601×1070 → scale 2.13 (the photo is only 707×470, 2.13× is near the upper limit,
  any larger and it blurs).
- `--focus` is "which point in the photo aligns with the window centroid" (0..1 relative coordinates), used to push the subject to the window centre.
- `--shadow` (projection inside the hole) and `--rim` (bright edge outside the hole) make the window **not look pasted on**;
  without these two the photo looks like a flat pasted rectangle.

### ⚠ Two measured pitfalls (stepped into the same day, 2026-10-11)

1. **Coordinate-system consistency**: `pa` is the **already-scaled** photo; just subtract the placement from the canvas coordinates;
   in the first version I divided by `scale` one extra time (converted the canvas to original-image pixels, then used it to index the scaled image),
   so the window showed **a different region of the photo** (the frame had no subject at all).
   **The symptom is very misleading**: the background looks "normal", only the content is wrong —— you must check against the material what the window actually contains.
2. **Screenshot-type material carries a coloured border**: in this case the source PNG's **top and left edges each have 2px of pure blue (13,153,255)** (a screenshot-tool artefact).
   `kraft_window`'s **edge clamping** copies it into a whole colour band (a blue strip along the window top).
   → Purify the material before placing: `crop((2,2,w-2,h-2))`, and print it in the log.

### 1.7b ★ Vertical window · landscape (16:9) adaptation (2026-10-13 case weifang-kite-16x9)

The default specification is the 1500×1875 portrait; doing a 16:9 landscape requires changing four things from §1.7:

1. **Canvas size**: `kraft_tear.py` already supports the `PF_W`/`PF_H` environment variables (`kraft_window` inherits them);
   `band_mask.py` **does not inherit**, and must be given explicit `--w 1920 --h 1080`.
   ⚠ `band_mask.py --orient v --yspan` once threw an `IndexError` when **canvas width > height** (iterating by row but indexing by column,
   the portrait version got lucky because `CW < CH`) — **fixed on 2026-10-13**.
2. **Window geometry**: in landscape it is more balanced for the window to occupy only the right half (40.7% coverage in this case). The left edge uses **three equal control points**
   (`--left "0.537,0.537,0.537"`) to get a **straight vertical edge** — in landscape, a left edge with any curvature reads as a "smudge" rather than a "tear".
   The right edge can keep a little outward expansion (`"0.951,0.966,0.979"`) + `--end-jitter 0.006` for a small close.
   `--smooth` set to **101** (landscape control points are far apart, so smoothing must be larger to avoid waves).
3. **★ The centre seam cutting across a long info bar — the biggest silent pitfall in landscape**: the centre seam is a vertical dividing line, and a long horizontal info bar
   (`exhibition dates …–…`／`Tue–Sun…`) is **very easily crossed by it**, while `check_contrast` only measures "whether the contrast inside the box is enough" and
   **does not measure "whether it is cut in the middle"**, so it lets it pass. Self-check method: take each row's x of the first dark pixel in the right half of the bg image as the window's left edge,
   and compare with each `[data-text]` box's `x_end`; **a gap < 24px counts as "overlap / too close"**.
   This case's solution: **split the info bar into two blocks** — the lower-left "exhibition dates / opening hours" (`width: var(--col)`, x_end 934 vs
   window left edge 1027, leaving 93px) + the lower-right inside the window "organisation line + CTA" (the inside-window ground is already soft-light paper, dark type reads clearly).
   Do not count on a halo stroke to brute-force it; the centre seam is a **structural cut**.
4. **The "photo" inside the window can be a composite**: this case's material only had white-background cutout subjects, no real-scene photo →
   use PIL to assemble a **display scene** (warm-paper radial ground `[228,214,186]→[176,155,122]` + soft glow + subject + cast shadow)
   as `--photo`, reading as "the real object displayed under the lamp".
   ⚠ **Do not use a deep brown solid colour for the ground field** — opening a dark window on a paper-colour material reads as an "ink block" rather than "content revealed by the tear" (this case's first version fell into this).
   ⚠ **Leave enough bottom margin for the subject**: when a vertical window runs the full height, if the subject is placed centred, its tail gets cut off by the canvas bottom edge.
   First compute `ky + kh ≤ H − reserved` (this case reserved ~170px for the in-window CTA), then set `target_h`.

### 1.8 ★ Diagonal ragged block: "split" the whole poster (added after the lead's second round of feedback, 2026-10-11)

**The lead's words**: "can't you cut out a **top-right to bottom-left** vertical irregular pattern like the template? your rectangle looks ridiculous in a poster,
the state in the template where the whole poster is split apart is more striking."

The axis-aligned vertical window (§1.7) stuck in the frame is just a "rectangular patch"; the striking quality of the reference poster comes from **one diagonal ragged block running across the full width**.

```powershell
# Diagonal shape extraction (case16 final): wide at both ends, pinched waist in the middle → a large block top-right / narrowed centre / large block bottom-left
python scripts\band_mask.py --w 1500 --h 1875 --shape diag-pinch --rotate 38 `
    --jitter 0.010 --seed 5 --out cut\win.png
python scripts\kraft_window.py --win cut\win.png --photo src\scene_big.png `
    --material src\material.jpg --scale 1.0 --focus 0.600,0.545 `
    --material-gamma 0.52 --shadow 0.28 --rim 0.15 --out out\bg.png
```

**Method**: generate as a horizontal band on a "square canvas of diagonal length" → `PIL.rotate` (**counter-clockwise positive**, `38` gives "top-right → bottom-left") → crop back to centre W×H. `--jitter` / `--yspan` keep the same meaning.

**Three measured criteria (all measured)**:

| Item | Conclusion |
|---|---|
| **Direction self-proof** | the script prints the **four-corner coverage**: `--rotate 38` → top-left 0% / top-right 100% / bottom-left 100% / bottom-right 0% ✓ (this is exactly what we want; `-38` reverses it) |
| **Waist-width setting** | waist width **0.62D → coverage 56.5%**, no paper ground in the centre, nowhere to put text; **0.10D → coverage 39.2%**, top-left + bottom-right each get a paper-ground block ✓; but **a 0.10D waist is only 200px, which would cut the subject in half** → this case takes **≈0.13D (315px)** |
| **Text placement** | print a 6×6 coverage grid (see case `run_case16.py`): the diagonal block occupies top-right + bottom-left, **all text goes on the top-left and bottom-right paper ground**, checked element by element with the "text overlaps window" check (>2% counts as overlap) |

#### ⚠⚠ Break symmetry: do not let the top and bottom edges mirror each other (the lead's feedback, 2026-10-11)

The first version's `diag-pinch` control points were **strictly mirrored** (`bottom = 1 − top`: 0.19/0.81, 0.28/0.72…),
producing a **centre-symmetric hourglass** —— the lead's words: "the cutout is **too centre-symmetric**, the pattern could be a bit more irregular".
The mathematical signature of mirrored control points: the script prints an "asymmetry amount" of **0** (that is exactly what it checks).
Breaking symmetry requires **moving three places together** (preset `diag-rag` already implements it):

| Technique | Method | Value in this case |
|---|---|---|
| ① **Eccentric waist** | the thinnest point is not centred | 0.125D at 3/6, 0.165D at 2/6 |
| ② **Unequal widths at the ends** | the two ends have different thickness | left end 0.755D / right end 0.640D |
| ③ **Different waist depth** | top and bottom edges dip/rise by different amounts | top edge dips to 0.445, bottom edge rises to 0.570 |
| ④ Coarser noise | raise `--jitter` to 0.014–0.016 | 0.016 |
| ⑤ Angle avoids round numbers | avoid the "exactly 45°" regularity | **41°** (34° / 30° would leave the bottom-left corner only 94% / 80% covered) |

Criterion: the script's printed **asymmetry amount** should jump from 0 to the 200–450px range.

**⚠ The cost of a thinner waist**: when the waist is too thin, **the subject gets cut in half** (the display case in this case).
The fix is not to pull the waist back, but to **move the subject to the wider leaf** (`--focus` to 0.42,0.60 so the subject lands in the upper-right leaf).

**⚠ Three coupled constraints of the diagonal version**:

1. **The window runs across the full diagonal → the photo must fill the whole canvas** (`scale ≈ 4`, a source only 707px wide would be blown up blurry)
   → first `LANCZOS` upscale + `UnsharpMask` preprocess into `scene_big.png`, and the script uses `--scale 1.0`.
2. **The paper-ground area is compressed**: the bottom-right corner is only ~680px wide → the bottom bar must change to a **single column** (two side-by-side segments would overflow the canvas,
   see next item), and the Chinese title also changes to **two staggered type columns** (following the reference's '敦煌 ｜ 博物展' [Dunhuang | Museum Exhibition]).
3. **⚠ Canvas overflow is "silent"**: when a `space-between` row's content is too wide, flex pushes the second segment **outside the canvas**,
   landing in the body background colour (`#17130E`). **The element's own `overflowX` stays false**,
   and the machine check shows **`P5 = 0`, CR ≈ 1.14** (it looks like "the material is too dark", but it is actually outside the canvas).
   → Criterion: **if the overlap-window check shows 0% while the machine check gives P5=0, first measure whether the element's right edge exceeds 1500**.

### 1.9 ★★ Natural feel and texture: `torn_edge.py` + texture trio (added after the lead's feedback, 2026-10-11)

**The lead's words**: "the cutout pattern is **still too regular, lacking a natural feel**. and **after cutting out it lacks texture**."

#### Problem one: shape extraction is essentially "1D extrusion"

`band_mask`'s horizontal band is "one top/bottom edge per column", the vertical window is "one left/right edge per row" —— even with fractal noise added,
it is still **a smooth curve + jitter**, which under magnification looks "cut with a wavy knife". **A real tear is irregular at three scales at once**:

| Scale | Phenomenon | Method (`torn_edge.py`) |
|---|---|---|
| Large (tens of px) | notches, bulges, the shape drifts overall | **2D fractal noise displaces the boundary along the normal** (`--edge`) |
| Medium (several–tens of px) | chunks **bitten off** | `--bites` random **elliptical** bite marks, with the **centre placed outside** biting in along the outward normal |
| Small (1–3 px) | **fibre fray**: semi-transparent fine filaments poking in and out | `--fray` high-frequency noise → alpha falls in the 0.3–0.9 transition band |

```powershell
python scripts\band_mask.py --w 1500 --h 1875 --shape diag-rag --rotate 41 --jitter 0.016 `
    --seed 5 --smooth 61 --out cut\win.png
python scripts\torn_edge.py --mask cut\win.png --out cut\win.torn.png `
    --edge 0.016 --bites 9 --bite-size 0.050 --fray 0.55 --fray-px 3.0 --seed 3
```

Measured: coverage 43.1% | **the fray transition band occupies 2.17% of pixels** (0% without tearing).
Tuning feel: to make it "raggeder" raise `--edge / --bites / --bite-size / --fray` together; to make it cleaner lower them all or set to 0.

#### ⚠ Two pitfalls that must be avoided (both stepped into in practice)

| Pitfall | Symptom | Handling |
|---|---|---|
| **Displacement without boundary constraint** | adding noise to the whole image → noise below threshold in solid areas → **a row of white flecks in the middle of the frame** | only allow edge-flipping inside the **slope band** where `abs(ramp−0.5) < 0.34` |
| **Bite centre taken on the boundary / offset direction reversed** | **floating material circles** appear in the centre of the frame | the centre must be pushed outside along the **outward normal** (`r × depth`) so the bite connects to the outer edge as a notch; use **random ellipses** (random aspect ratio and orientation) for bites —— a perfect circle bites a row of identical round notches, which looks regular instead |

#### Problem two: texture comes from "the photo relating to the paper"

`kraft_window.py` adds the **texture trio** (on by default, can be disabled by setting to 0):

| Switch | Method | Effect |
|---|---|---|
| `--seam 0.42` | a **narrow dark ring** hugging the edge | the material looks "pressed" onto the photo (paper thickness) |
| `--fiber 0.55` | the material's **high-frequency detail** laid over the photo along the outside of the edge | torn fibres rest on the image |
| `--grain 0.30` | lets the photo in the window absorb the material's **low-frequency light-and-dark + fine grain** | the photo looks "printed on the same sheet of paper", not a pasted-on image |

> ★ Companion change: `kraft_window`'s window alpha was changed to **keep continuous values** (previously binarised at `> 0.45`,
> which would **drop the entire fray transition band** generated by `torn_edge` —— the direct cause of "no texture".

#### ⚠⚠ But `--bites` does not suit long horizontal bands (measured 2026-10-12)

Bite marks are **random ellipses biting in from outside along the outward normal** —— on a boundary that is **nearly full-width long**, they read as **a row of arcs / scalloped edge**,
not like "a chunk bitten off", but like "holes punched with a round die":

| Parameter set | Measured look |
|---|---|
| `--bites 18 --bite-size 0.030` | the whole edge looks like a **cloud edge**, worst (small and many marks, densely waved) |
| `--bites 10 --bite-size 0.045` | leaves 2–3 **obvious round notches**, acceptable but unnatural |
| **`--bites 0 --edge 0.017 --edge-scale 22 --fray 0.60 --fray-px 3.2`** | ✅ **most like a hand tear**: continuous irregular undulation + fine fibres, no round holes |

→ **For horizontal-band shape extraction, `--bites 0` by default**, handing all irregularity to "2D fractal displacement + fibre fray";
leave the bite marks for **short boundaries** (vertical window / diagonal block), where the round notches read as "a chunk torn off".
When comparing options, board the tear band directly (`board.py`, crop the canvas strip y 430..640) rather than guessing on the full image.

### 1.10 ★★ Fourth route: full-bleed ground (`kraft_full.py`, added 2026-10-12)

**The lead's words**: "make the poster **fill the frame** as much as possible, like these ones" (reference 06 竹编艺术 [bamboo-weaving art] / 07 徽州灯彩 [Huizhou lantern festival] / 13 非遗纸版 [intangible-heritage paper edition]).
The first three routes all **open a window**; this one is the reverse —— **the photo fills the whole canvas directly**, with text pressed onto the photo.

```powershell
python scripts\kraft_full.py --photo src\scene.png --material src\material.jpg --out out\bg.png `
    --focus 0.50,0.52 --overlay 0.42 --vignette 0.30 --tone 0.16 --grain 0.22 `
    --scrim "50,80,790,1460,0.57,230; 1080,100,1500,1060,0.56,260; 0,1360,1500,1875,0.34,150; 980,50,1500,225,0.50,150"
```

Three things: ① photo cover fills the frame (`--focus` for framing); ② **material as paper grain** (high-frequency detail + low-frequency light-and-dark laid on via
`--overlay`) —— the same texture language as the other three routes; ③ darken the four edges + `--tone` biases toward the material colour.

#### ⚠⚠ Core pitfall: at full bleed the photo's light-and-dark is **uncontrollable**, light type will always fail → you must build a "text-area scrim"

References 06/07 can hold light type because **that patch of ground is already dark**; but in this case the top-left curtain wall measured **P95 = 158 (WCAG linear luminance)**,
light type CR is only **1.31**, dark type 3.03 —— **neither meets the bar**.
`--scrim "x0,y0,x1,y1,strength,feather-px;…"` pushes down the patches where text sits:

| Criterion | Value |
|---|---|
| light type (#F2E9D8, L≈0.83) to reach 4.5:1 | the ground's **P95 must be ≤ 37** (linear luminance; ≈ sRGB 105) |
| this case's result | left band 0.57 / right band 0.56 / bottom band 0.34 / top-right corner 0.50 |

Two supporting measurements:

1. **Light-type mode must recolour element by element**: in the base class `.col-sub／.col-tag／.mini／.org` all hard-code `--ink/--ink-2`,
   changing only `.type`'s colour gets overridden (measured CR dropped to 1.03). Override each one inside the master's `body[data-full]`.
2. **The scrim's feather must be large enough**, otherwise **a dark rectangle** appears in the frame (measured at 140px the EN version's right side was visible at a glance →
   raised to 230–260px before it dissolved).
3. **First sweep positions by measurement, then place type**: in this case the EN small label was tried from y980 / 1120 down to **y840**
   (that band is the darkest part of the whole image, CR 6.78); measuring it once saves effort versus moving it back and forth.

### 1.11 ★★ Decoupling shape orientation from script: **a horizontal tear band can also use `kraft_window.py`** (added 2026-10-12)

Above, §1.7 wrote `kraft_window.py` as "vertical-window only", but its mechanism is actually **orientation-independent**:
`--win` only takes alpha, and the photo is placed by `--scale` / `--focus` —— **a horizontal tear band can use it too**, and it uniquely offers **horizontal framing**.

| Script | Photo placement | Horizontal framing | Suited for |
|---|---|---|---|
| `kraft_photo.py` | `by = --top-edge − --wall-top-row × sc` (mask **top-edge mean** anchored to `--yA`) | ✗ can only **centre-crop both sides** (`--zoom`) | subject roughly centred, nothing on the left/right to exclude |
| **`kraft_window.py`** | `ox = cx − fx·pw·sc`, `oy = cy − fy·phh·sc` (`cx/cy` = mask alpha centroid) | ✅ **`--focus` arbitrary positioning** | need "which segment of the photo to take" (including horizontal pan) |

**Criterion (measured in case 05)**: there is a giant gilt title panel on the left of the photo; its text duplicates the poster title, and getting cut in half by the tear makes a wrong character.
`kraft_photo` with `--zoom 1.0 / 1.15 / 2.0` cannot get rid of it (centre-crop naturally keeps the left third);
switching to `kraft_window --scale 1.0 --focus 0.56856,0.38531` lands it in one shot.

**Three steps to compute `--focus`** (avoid the §1.7 pitfall of "dividing by scale repeatedly"):

1. **Read mask geometry**: the **centroid (cx, cy)** of alpha>0.45 + each column's top/bottom edges → get the window's actual range on the canvas
   (when `band_mask` is 1500×1875 at the canvas size, mask pixels = canvas pixels);
2. **Set photo placement**: `ox = 0 − target photo left edge × sc`; `oy = window top-edge canvas y − target photo top edge × sc`;
   `sc = 1500 ÷ target photo width` (if you want to enlarge the photo, preprocess it yourself; the script uses `--scale 1.0`);
3. **`--focus = (cx − ox)/(pw·sc), (cy − oy)/(phh·sc)`**.
   The placement relation is `canvas = photo + (ox, oy)`, i.e. `photo_y = canvas_y − oy` —— **do not divide by scale one more time**.

**Measured values (case 05)**: mask centroid (752, 964), bounding box 1499×992, coverage 47.2%;
target photo region x476..1976 / y640..1592 (already 2× to 2160×2880) → `ox −476`, `oy −146`
→ `--focus 0.56856,0.38531` (script reads back placement `(-476, -146)`, pixel-by-pixel colour comparison matches).

> ⚠⚠ **The two scripts anchor the mask differently** (the easiest place to trip):
> `kraft_photo` only consumes the mask's **shape and band height** —— it anchors the top-edge **mean** to `--yA`; it does not matter which row the mask is drawn on;
> `kraft_window` **consumes the mask's absolute alpha directly** —— the ratio `band_mask` gives for control points is the canvas position.
> Feeding the same mask to both scripts, the window placement will differ by a chunk —— **this is by design, not a bug**; think clearly which route you are taking before changing control points.

> ★ **Enlarge the material before framing**: this case's source is only 1080×1440, but the window needs 1500px wide (interpolation above 2×)
> → first `LANCZOS` 2× + `UnsharpMask(radius=2.0, percent=62, threshold=3)` saved as `scene.2x.png`,
> the script uses `--scale 1.0` to avoid a blurry window.

## 2 Material library (assets\material\)

| Material | Feature | Case conclusion (route B, z1.45/w1550) |
|---|---|---|
| `rock.sand.png` | light sand sandstone, light large surface | recolour final (tonal stops 163,146,126→250,240,226 + `--detail 3.0`) 12/12 all pass (min 6.54) |
| `rock.aged.png` (560×746) | weathered cracked, naturally dark (many dark spots) | native tonal-stop direct 9/12 fail; recolour brighten 12/12 (min 5.13); preserve original colour γ0.52 12/12 (min 4.63) |
| `rock.slate.png` (2074×2768) | grey fine-grain stone surface, uniform | preserve original colour `--material-gain 1.0` direct |
| `kraft.cream.png` | cream crinkled paper | old paper-route material |

Material requirements: shot flat-on, even light, no strong reflection / hard shadow; no hard lower resolution limit (the whole covers and scales up),
but larger is finer (`--detail` only overlays the material's **native-scale** high-pass detail).

## 3 Commands (route B main path, three material-colour modes)

```powershell
# ① default | recolour: material mapped to the --paper-dark/--paper-light two tonal stops (material colour is replaced; rock-face light-sand final tonal stops below)
python .trae\skills\photo-cutout-forge-en\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --material material\rock.sand.png --zoom 1.45 --wall-top-row 1550 `
    --paper-dark "163,146,126" --paper-light "250,240,226" --detail 3.0 --out out\bg.rock.png

# ② preserve original colour · full restoration: no recolour, no lighting removal, direct material colour (--material-gain 1.0)
python .trae\skills\photo-cutout-forge-en\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --material material\rock.slate.png --material-gain 1.0 --zoom 1.45 --wall-top-row 1550 --out out\bg.slate.png

# ③ preserve original colour · power-curve brightening: γ<1 lifts shadows, keeps highlights (use when dark material direct output fails the type zone; pure gain would blow out highlights / clip)
python .trae\skills\photo-cutout-forge-en\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --material material\rock.aged.png --material-gamma 0.52 --zoom 1.45 --wall-top-row 1550 --out out\bg.aged.png

# before type setting on dark ground, add a glow to the lower-left text zone (auto gain, must be computed in linear-luminance terms)
python .trae\skills\photo-cutout-forge-en\scripts\textzone_glow.py --bg out\bg.rock.png --out out\bg.glow.png `
    --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"

# then as usual: copy master + fonts + bg → near-black ink type (--ink #171009 family) → render_png → check_contrast
```

Route A (window = cutout subject, alternative):

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\kraft_tear.py --subject cut\A2c.png --material material\rock.sand.png `
    --k 0.60 --yA 540 --zoom 1.45 --seed 33 --out out\bg.rock.a.png
```

## 4 Route B framing (--zoom / --wall-top-row)

- Scope: `--wall-top-row` = the original-image row aligned to the top tear-opening line (`--top-edge`, default 539);
  `--zoom` scales the contour and photo together (>1 centre-crops both sides), making the tear window taller and the subject occupy more of the frame.
- Dunhuang final: `--zoom 1.45 --wall-top-row 1550` → window 539..1025; photo rows 1549..2487;
  sc = 1500×1.45÷photo width (4202) ≈ 0.518; visible photo x337..1837, by -263.
- Steps:
  1. Use a row luminance profile to set boundaries: take the mean luminance L row by row in the photo's central band (ceiling L low, mural L high, floor L falls back);
  2. Render 2–3 candidates (old 1250/1400/1550; fixed at 1550 after z1.45);
  3. Board and human-eye check: **no black ceiling exposed at top, no floor exposed at bottom** (ceiling lower bound ≈ 1550, mural band reaches ≈ 2600).
- Failure signature: window top edge exposes black → increase `--wall-top-row`; bottom edge exposes floor/foreground object → decrease.
- Window height follows the subject contour band height (near-proportional, measured ≈ ×0.85): the subject description makes the silhouette cleaner, but image generation may draw the subject band **flatter** →
  the window gets shorter and reveals less content. Compensate with `--zoom` in this case (contour and photo scale together, window taller, subject occupies more, both sides cropped).
  Case (skill-test-mural-tear): A5 silhouette z1.0 window 563px (WTR235 → photo rows 235..1023, rather short) → z1.58 window 869px
  (WTR694 → photo rows 694..1464, includes wall base, no floor exposed); final `--zoom 1.58 --wall-top-row 694`.

## 5 Type setting on dark ground (ink type + glow)

- Material ground colours vary in depth, so always use near-black ink type: `--ink #171009` / `--ink-2 #1F150A` / `--ink-3 #251A0D` / label `--gold #271B0D`;
- Glow (`textzone_glow.py`): shape `m = ss((y-cy)/fy) * (1-ss((x-cx)/fx))` (lower-left corner);
  gain `g = (0.26/p5)^(1/2.4) - 1 + 0.005`, **p5 must be taken as WCAG linear luminance (0-1 scale)** ——
  using sRGB 0-255 gives a wrong gain (measured pitfall); case p5 0.139 → g 0.303;
- Machine-check scope: background luminance takes the **single-pixel P5 (dark type)** inside the text box; the old kraft-paper version's near-black ink type + glow had a minimum label of 4.76.

## 6 Adjustable parameters

| Parameter | Effect |
|---|---|
| `--material` (old alias `--kraft`) | background source image (rock face / stone surface / paper etc. related material); if not given, a procedural texture is the fallback |
| `--material-gain` | preserve original colour: overall gain multiplier (1.2≈brighten by 20%); 0 = off, takes recolour route |
| `--material-gamma` | preserve original colour: power curve (<1 lifts shadows, keeps highlights, case 0.52); ≠1 also enables preserving original colour |
| `--paper-dark` / `--paper-light` | recolour two tonal stops (default rock-face tone 185,170,153→241,229,214; light-sand final 163,146,126→250,240,226) |
| `--k` | strength of the tear arc following the contour (0.30 gentle / 0.45 medium / 0.60 strong; Dunhuang fixed at 0.60); **=1.0 means tear line = contour line** (photo-traced mask route, see §1.5) |
| `--smooth` | contour smoothing window px (default 81 = hand-torn big wave; **use 21 for traced mask** to preserve contour detail, too small exposes polyline corners) |
| `--yA` | top tear baseline height (canvas y, case 540; centre seam prefers to sit high) |
| `--zoom` | window content magnification (>1 enlarges then centre-crops both sides, taller tear window; case 1.45) |
| `--wall-top-row` (B) | framing (see §4; case 1550) |
| `--detail` | material detail high-pass overlay amount (default 4.0; rock-face final 3.0, settles the grain) |

## 7 Pitfall list (measured)

- **Recolour wipes the material colour**: `photo_cover` maps the material to the specified two tonal stops —— the material's own colour spots / cracks / mineral colours get replaced
  (user measured feedback "how did the rock face's original colour get wiped out") → preserve original colour via `--material-gain` (1.0 direct / 1.2 brighten 20%) or
  `--material-gamma` (power curve).
- **Dark-spot type zone fails machine check**: the type-zone background luminance takes the **single-pixel P5 (dark type)** —— if a material dark spot falls in the type zone it fails;
  pure gain cannot save it (brightening blows out highlights / clips), use power curve γ0.52 (measured on weathered rock face: after γ0.52, 12/12, min 4.63).
- **Candidate prompt literalised**: describing the subject with literal shape words like '图带/条带' [image band / strip] → the image tool draws the subject as a floating strip (white gaps become holes),
  hole ratio actually rises (measured 11.31% > 10.19% with no description) → rewrite as "one whole complete continuous …, not a strip/fragment, not cut, not separated" (6.54%);
  also note the described contour band may be flatter and the tear window shorter accordingly (563 vs 891px) → `--zoom` compensation (case 1.58 / WTR 694).
- **AI silhouette geometry does not match the real photo (multi-wing / U-shape)**: the silhouette's wall-band ratio ≠ real-photo perspective (case measured mid-section drop ≈2×) → the mid window bottom falls into
  the floor row, the wing window top exposes the ceiling, and no `--k/--wall-top-row/--zoom` tuning aligns it → switch to **photo-traced mask** (§1.5):
  tear = true wall geometry ±tear (user feedback "we only needed the two side galleries, but the middle floor got added in too" is exactly this pitfall).
- **Compressed arc k<1 loses the contour in multi-wing scenes**: k=0.6-0.8 compress the drop from the two wings to the mid-section into a "dune wave", the subject's contour feel disappears
  (user feedback "do not lose the subject's contour just for smoother edges") → prioritise contour fidelity with `--k 1.0` + `--smooth 21`, leaving the hand-torn feel to tear (±10px).
- Material whole-image **mirror tiling** produces symmetric butterfly / diamond artefacts (seams visible to the eye) → must use
  "whole-frame proportional upscale to cover + material native-scale detail high-pass overlay" (`photo_native/photo_cover` + `photo_detail`).
- Cutout soft edge (alpha 0.1-0.4 wide transition) bleeds through on dark material into colour-seeping mud spots → harden alpha to
  a `(m-0.42)/0.10` narrow transition band (fixed inside route A's `build()`).
- **`--bites` on a horizontal band punches round holes**: elliptical bite marks on a near-full-width-long boundary read as a row of scalloped edges (`--bites 18` looks like a cloud edge)
  → **for horizontal-band shape extraction use `--bites 0`**, handing irregularity to `--edge` / `--fray`; leave bite marks for short boundaries (see §1.9).
- **Do not force `kraft_photo` when a horizontal band needs horizontal framing** (it can only centre-crop) → switch to `kraft_window --focus` (see §1.11);
  note the two scripts anchor the mask differently (one anchors the top-edge mean, one uses absolute alpha).
- **`kraft_window`'s `--detail` is a different unit from `kraft_photo`'s**: the former defaults to 0.06 (≈no effect), the latter 4.0;
  when patterned paper is the material, give `kraft_window` 1.5–2.0.
- **★ Magnifying a low-resolution material illustration blurs the fine brushwork** (2026-10-13 case 06): the material is only 573×993, filling a 1500 canvas
  = **2.618×**. Soft-focus areas like mist / distant mountains lose nothing when enlarged, but **fine strokes (calligraphy, text, thin lines) lose their brush edge**,
  reading like "big colour blocks". Three ways to handle it:
  ① let the fine-stroke area occupy only a **narrow band** (in this case the gold character field only shows ~120px at the window's lower edge, reading as texture rather than subject);
  ② when composing, **align the material's content bands with the layout zones** (see the next item);
  ③ after enlarging, apply one `UnsharpMask(radius 2.4, percent 55, threshold 2)` pass — do not overdo it (it will produce white edges).
- **★ The ground crop offset `oy`: do not use `photo_cover`'s default centre-crop** (2026-10-13 case 06).
  Use the formula `poster_y = native_y × scale − oy`; first measure the material's three content bands (e.g. "misty distant mountains / mid-ground / gold character field")
  in their native row ranges, then back-solve `oy` according to "what the title band needs, what the tear window covers, what the bottom text-bearing band needs".
  This case `oy=640` (material native 244..961) → the top band keeps the misty mountains, the window covers the mid-ground, **the exhibition info lands on the fading tail of the character field**.
  ⚠ An easier approach: **pre-crop the material yourself to 1500×1875 and pass it as `--material`** (`_cover`'s `sc=1` is the identity,
  so framing is fully controllable), and on the script side use the usual `--material-gain 1.0`.

- rng sequence: `paper(rng)` must always be called first (even with material), otherwise the tear's random shape changes and the final cannot be reproduced.
- `np.arange(H, dtype=np.float32)` must use the keyword (the second positional argument is treated as stop);
  PIL F mode does not support GaussianBlur (convert to uint8 first); PowerShell chaining uses `;`; board.py labels should avoid "·".

## 8 Case products (`cases\wall-of-visions-photoart\cutout-trial\trial.kraft\`)

- Rock-face final (light sand sandstone, recolour): `bg.rock3.z145.w1550.png` → `poster.rock\poster.png` (machine check 12/12, min 6.54);
- Weathered cracked rock face: recolour brighten `bg.aged3` (12/12, min 5.13) / preserve-original-colour dense version `bg.aged.native2` (γ0.52, 12/12, min 4.63) /
  full restoration `bg.aged.true` (gain 1.0, now `poster.aged\bg.png`);
- Grey stone surface: `bg.slate.z145.w1550.png` → `poster.slate\poster.png` (preserve original colour direct; rendered, machine check not run);
- Comparison boards: `board.rock.poster.png` (kraft paper / cream paper / rock face), `board.aged.poster.png`, `board.slate.poster.png`,
  `board.color.restore.png` (material as-is / original-colour restoration / brighten / curve, four-up), `board.native.mech.png` (colour-mechanism four-up);
- Old kraft-paper version: `bg.v3r-photo.glow.png` + `poster.v3r-photo\poster.png` (12/12) / route A control `bg.v3r-dark2.png` / `board.AB.poster.png`;
- Regression smoke test: `smoke.r6.a.png` = bg.v3r-dark2, `smoke.r6.b.png` = bg.v3r-photo, both md5-consistent.
- (Test case `cases\skill-test-mural-tear`, three inputs) A5 silhouette + `--zoom 1.58 --wall-top-row 694` final:
  `out\bg.png` (window photo rows 694..1464, no floor exposed); control board `diag\board.final.A5.png`, silhouette board `diag\board.alpha.A245.png`.
- (Test case `cases\skill-test-gallery-tear`, two-wing gallery / U-shape) AI silhouette (B2/B3) geometry mismatch → **photo-traced mask** final:
  `out\bg.png` (`--k 1.0 --smooth 21 --wall-top-row 1167 --material-gain 1.0`; measured window top = traced line ±10px,
  window bottom = ~100 rows above the wall base, no floor exposed); audit script `diag\audit.py`; tear comparison board `diag\board.crop.s41vs21.png`.
