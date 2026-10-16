# End-to-end process and commands (photo-cutout-forge-en)

> The working directory is the project root. Output goes uniformly to `out\` (case directories follow the actual situation).
> Iron rule: **process the background first, then set the type**; the master template is a **copy**, not a reference; after editing the master you must re-copy and re-render.

## 0 Directories

```powershell
New-Item -Force -ItemType Directory cand, cut, out | Out-Null
```

## 1 AI white-background cutout candidates (image-to-image)

Produce one version each from the three prompt sets in `cutout-craft.md` (A full-colour / B ink silhouette / C two-colour flat-coat),
**rewrite the template's subject sentence per the user's description of the subject** (writing method in `cutout-craft.md` §①: complete continuous phrasing, avoid the literal word '条带' [strip]),
the subject being the "main part" of the original image (arched building wall, figure, artefact …), on a pure white background, centred, with negative space all around.
Using the Dunhuang case as an example, save as `cand\A2.jpg`, `cand\B.jpg`, `cand\C2.jpg` (image generation has randomness, so run several versions and pick).
If the subject is occluded (gauze curtain, column): first use the D template in `cutout-craft.md` for an image-to-image edit to "remove occlusion, complete the occluded face" (Dunhuang saved as `cand\A2c.jpg`), then proceed to cutout.

## 2 White background → transparent-background subject

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\A2.jpg --out cut\A2.png --mode color --trim --pad 16
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\B.jpg  --out cut\B.png  --mode ink --trim --pad 16
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\C2.jpg --out cut\C2.png --mode color --auto-white --trim --pad 16
```

- Cream-yellow / non-pure-white-background source images (e.g. the two-colour flat-coat version) must add `--auto-white`, otherwise the whole background turns grey.
- Edge white ring `--shrink 1`; fine stripes eaten `--despeckle 3` (or 0); light thin gauze vanishing `--floor 24`.

## 3 Background processing + auto-composition (background first!)

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\auto_compose.py `
    --source src-small.jpg --subject cut\A2.png `
    --preset azure-gold --seed 3 `
    --out out\bg.A2.png --plan out\plan.A2.json --debug out\debug.A2.png
```

- Auto-selects layout (`hero-top / hero-right / hero-left / hero-centre`), writing the reason into `plan.json`;
  a human can override with `--layout`, or fine-tune with `--subject-target / --bd-zoom / --focus / --wash / --bd-blur`.
- Full-width scroll (subject fills left-right): `--layout hero-band`; remove backdrop window (pure paper ground): `--no-backdrop`.
- Painting layer (optional): insufficient subject contrast `--shadow 0.30`; paper ground too empty `--reflection 0.50` (below 0.30 nearly invisible); paper colour mismatch `--paper "#E8DCC0"`.
- `--debug` draws the subject rect (red), backdrop window (blue), text area (green) — for the human-eye gate.
- After the three candidates run, combine the candidate board:

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\board.py --inputs out\bg.A2.png out\bg.B.png out\bg.C2.png `
    --labels "full-colour cutout" "ink silhouette" "two-colour flat-coat" --cols 3 --width 480 --out out\cand-board.png
```

- **Gate**: review the board and pick a direction (default: pick yourself and state the reason in the deliverable).

## 3B Torn-kraft-paper route (decorative alternative, replaces step 3)

The whole real kraft paper, with top and bottom tear openings torn along the subject's contour arc, the centre seam revealing content; **the kraft paper overlaps above the content**.
Two routes for the window content: A = cutout subject (`kraft_tear.py`); **B = original photo (`kraft_photo.py`, continuous window, no paper colour mixed in, recommended)**.

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\kraft_photo.py --cutout cut\A2c.png --photo material\mural.original.png `
    --kraft material\kraft.flat.png --wall-top-row 1400 --out out\bg.kraft.png
python .trae\skills\photo-cutout-forge-en\scripts\textzone_glow.py --bg out\bg.kraft.png --out out\bg.glow.png `
    --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"
```

- Contour source: AI silhouette candidate by default; **when the AI silhouette geometry does not match the real photo (multi-wing / U-shape, window bottom falls into the floor row), switch to the "photo-traced mask"** ——
  trace top/bot control points along the true boundary on the photo → interpolate into an alpha band at the photo's size → feed `--cutout`,
  with `--k 1.0 --smooth 21` (tear-opening = true contour ±tear; preserves contour without big waves), `--wall-top-row` takes the traced top mean.
- The output is `out\bg.png` (replaces step 3's product; proceed normally afterwards); **then follow steps 4 and 5 as usual** (background first, type second unchanged).
- Framing (`--wall-top-row`), parameter table, type setting on dark ground, and the pitfall list are in `references\kraft-tear.md`.

## 3C Extract two-colour gradient ground-field route (replaces the backdrop window)

Instead of stacking a backdrop window, extract "main colour + secondary colour" from the original → a biased two-colour smooth gradient ground field (zero texture) + subject over ——
the route of solid-gradient dark ground + clear subject + calligraphic type; **the alternative when the soft-focus backdrop window reads as a "blurry photo patch"**
(Dunhuang iteration 2; iteration 3 removed texture for a gradient because of "spots, not refined"; iteration 4 added a vertical gradient / darkening / cast shadow / subject colour lift because "the gradient goes bottom-up but the subject is not prominent enough";
iteration 5 added ground field / subject brightening because "overall brightness is insufficient").

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\auto_compose.py `
    --source src-small.jpg --subject cut\A2c.png `
    --bg-mode color --bg-color "#1F3F6E" --bg-grad up --bg-vignette 0.18 --bg-lift 0.30 `
    --subject-paint 1.0 --subject-lift 0.25 --shadow 0.35 --layout hero-band `
    --out out\bg.png --plan out\plan.json
```

- `--bg-color auto` (default) = auto-extract the main colour (saturate-pixel clustering, the highest cluster by "weight × saturation" is pushed dark) + secondary colour (the cluster ≥6% away in hue from the main colour is pushed deep); or specify the main colour directly with `#RRGGBB` (secondary still extracted from the original).
- `--bg-grad diag|up`: diagonal entry / vertical from the bottom edge upward; `--bg-vignette 0.18` darkens the four edges; `--bg-lift 0.30` brightens both colours (preserves hue).
  Subject enhancement: `--subject-paint 1.0` repaint (vivid colour block) / `--subject-pop 0.25` slight saturation-contrast lift / `--subject-lift 0.25` brighten; `--shadow 0.35` cast shadow on the paper.
  Both Dunhuang brightening levels pass the machine check (level H 0.18/0.15 is subtle, level I 0.30/0.25 is brighter); the example uses level I.
- The output is `out\bg.png`; **then follow steps 4 and 5 as usual** —— when setting the type, add `data-theme="deep"` to body (dark ground, light type),
  and change `.stage`'s `--stage-bg` to the same value as the ground field (the master default #1F3F6E is Dunhuang case's deep azurite);
  after the ground field is brightened by `--bg-lift`, text contrast drops overall, so the small-type ink colour must brighten one level with it (Dunhuang level I tagline 4.27→4.77).

## 4 Set the type (after the background is finalised)

```powershell
# Copy master template + fonts + background (all three must be in the same directory)
Copy-Item .trae\skills\photo-cutout-forge-en\assets\poster-cutout-master.html out\poster.html -Force
Copy-Item .trae\skills\photo-cutout-forge-en\assets\fonts out\fonts -Recurse -Force
Copy-Item out\bg.A2.png out\bg.png -Force
# Edit out\poster.html: change data-text copy; body[data-comp] = layout from plan.json
python .trae\skills\photo-cutout-forge-en\scripts\render_png.py --html out\poster.html --out out\poster.png --scale 2 `
    --qa-bg out\poster.bg.png --boxes out\poster.boxes.json
python .trae\skills\photo-cutout-forge-en\scripts\check_contrast.py --boxes out\poster.boxes.json `
    --bg out\poster.bg.png --full out\poster.png --json out\poster.readability.json
```

- **One version each in Chinese and English**: `--query "lang=en"` (`render_png.py` added 2026-10-12, **all three products share the same query** ——
  the final image, the `--qa-bg` background image, and the `#pf-boxes` text box must be in the same language, otherwise the machine check measures the English ground with Chinese boxes).
  ⚠ **Measured (2026-10-13): the five master templates' `data-lang` only switches font and layout, and carries no Chinese/English copy dictionary** (grep `assets/` for `COPY` and find nothing). So "one file, one-click switch" is **not yet possible**;
  the workable approach is to **derive an English HTML from the Chinese version**: change `<html lang>`, `<body data-lang>`, and all `[data-text]` copy — the layout and font system stay untouched, line for line; the two HTML files share the same `bg.png` and `fonts/`.
  Likewise `?theme=deep`.
   > ⚠ The docs have always said "add `?theme=deep` when rendering", but the script previously **had no parameter to pass the query through** —— `--query` has been added.

- `data-comp` and `plan.json`'s `layout` **must match** (text placement is decided by it; hero-band reuses `data-comp="hero-top"`).
- Type setting on the dark ground field (3C): add `data-theme="deep"` to body (or add `?theme=deep` at render); not switching = warm-black type on a dark ground, which will fail the machine check.
- If it does not pass, first adjust position (layout CSS), then adjust ink colour (`--ink*` variables); re-run the machine check after changes.

## 5 Deliverable

- Candidate board `cand-board.png` + final `poster.png` + `plan.json` (full record of layout and checks).
- Archive packaging: `Compress-Archive` (exclude `__pycache__`).
