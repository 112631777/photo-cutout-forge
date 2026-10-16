# Machine-check criteria (two tracks: composition checks + readability WCAG)

## 1. Composition checks (built into auto_compose.py, written to plan.json)

| Item | Criterion | What to do if it fails |
|---|---|---|
| subject×text_zone | subject coverage of the text zone ≤ 2% (alpha>0.10 counts as coverage) | shrink the subject in 0.92 steps, up to 4 times |
| backdrop×text_zone | backdrop-window coverage of the text zone ≤ 2% (mask>0.12 counts as coverage) | shrink the backdrop window by the same step (rx/ry×0.92), up to 4 times |
| blank_ratio | visible paper ground ratio ≥ 0.40 (not covered by subject or backdrop window) | shrink the backdrop window further (×0.94), up to 6 times |
| subject_in_canvas | subject rect fully inside the canvas | re-clamp position |

- checks are computed throughout on a 1/4 downsampled canvas (1500×1875 → 375×469).
- when `plan.json`'s `checks.pass` is false, the script returns exit code 1 (can be wired into a pipeline).

## 2. Readability (check_contrast.py, criteria must not be changed)

- Background luminance takes the **single-pixel P95 (light text) / P5 (dark text)** inside the text rectangle, not the mean; the rectangle is inset 14% inward.
- Threshold: font size ≥ 48px @1500 canvas width → large text 3.0 : 1; others 4.5 : 1.
- Also outputs overflowX / overflowY: **must all be false** (values do not wrap, title does not exceed the column).
- Usage: `--boxes poster.boxes.json --bg poster.bg.png --full poster.png --json report.json`.

### ⚠ But passing the machine check ≠ visually clear enough (added after user feedback on 2026-10-11)

P5/P95 are **conservative compliance lines** (guaranteeing "readable even in the worst case"), **not equal to perceived quality**. When the material background (earth wall / rock face / torn paper) is mottled with light and dark patches, P5 may pass, yet the eye still sees "dark text mixed into a busy ground of alternating dark and light" — the user's own words were "the text colour is too close to the base material".

**`text_contrast.py` adds two criteria**:

| Criterion | Meaning | Judgement |
|---|---|---|
| `cr_p50` | text colour vs background **median** (overall impression) | < 3.6 → visibly insufficient |
| `bg_std` | standard deviation of luminance inside the text box (how busy the ground is) | ≥ 26 → text blurs into the texture |

```powershell
python scripts\text_contrast.py --bg out\poster.bg.png --boxes out\poster.boxes.json `
    --report out\text-contrast.json [--plate out\bg.png]
```

`--plate` does a **hue-preserving lift / darken** in the text area (large-radius feathering), generating a legibility plate; overwrite with the new `bg.png` and re-render.

### Three legibility aids (in increasing strength; use the lightest first)

1. **Light stroke** (first choice): `-webkit-text-stroke: 1.8px` + **`paint-order: stroke fill`** — the latter is the key: it draws the stroke **under** the glyph body, otherwise it erodes the interior of the strokes and the text gets thinner.
2. **Add weight to small text**: Chinese information-layer sans uses 600; Latin serif uses 500.
3. **Legibility plate** (`text_contrast.py --plate`): only use when the ground is especially busy; it weakens the material feel.

> ⚠️ **After adding a stroke, the QA instrument's `-webkit-text-stroke-color` must also be cleared to `transparent`.** > If only `color` is cleared, the light stroke remains in the "text-free background" and is treated as background luminance, **inflating all machine-check values** (measured: bgP95 jumped from level 150 to level 220 — not obvious at a glance, but the machine-check reference is already broken).

### ⚠ The machine check measures **the background itself**: strokes / glow / weight are not counted

Measured 2026-10-12 (case17, three-sided mural wall): dark ink text pressed onto **the dark part of the mural**, P5 only 22 → CR 2.40 failed. Adding a light stroke or a glowing shadow to the text **helps the numbers not at all** — `check_contrast` reads the `--bg` image that has "the text ink and stroke hidden". → Conclusion: **when the ground is both busy and dark, the only option is to add a "legibility plate" in the background layer** (`text_contrast.py --plate`, or the soft paper-coloured veil in case `run_case17.py`: a rectangle + large feathering, blended toward the paper colour). ⚠ The feathering must be large (this case 120–220px) — if small, a **visible bright/dark rectangle** appears in the frame.

#### ⚠⚠ But the plate **only covers the small patch that "really needs it", with the minimum strength** (conclusion after the boss's feedback on 2026-10-12)

In the first version I laid two large patches (x60–880 and x1180–1480, strength 0.46 / 0.48) → **the whole cutout motif was washed out**: the boss's exact words were "the cutout colour stays as in the original — not faded — but **the final piece looks faded**, a bit blurry". (Compare `半成品.png` with the final piece and it is obvious at a glance.)

The correct approach:

1. **First drop the plate and measure** each text's P5; only add to those that **really fall short** (after dropping the plate in this case: the Chinese title 93 / left-edge small label 94 / info line 108 were already enough; only the **right-edge vertical small text** pressed onto the bright part of the mural, 30–45, fell short);
2. **Derive the strength backwards from the gap**: for dark text `P5_ground ≥ 0.225` (linear luminance), `f ≈ (0.225 − P5_ground) / (paper luminance − P5_ground)`; this case was about 15–22%, measured and taken as 0.34–0.40;
3. **Tighten the range to hug the text**: keep only the strip pressing on the small text (this case x1150–1500 hugging the right edge), and **pull the text's box inside this strip** (if the box edge sticks out beyond the strip, the machine check catches a bright ground — that is how the EN tagline at 4.25 failed).

### Ink colour: take the most prevalent dark colour in the frame (`pick_ink.py`, added 2026-10-12)

The fixed ink colour `#17130E` is the fallback; when the frame itself has a dominant hue, **taking the ink colour from the most prevalent dark tier in the frame is more harmonious**. Method: take the darkest `--dark-pct`% of pixels (default 18) → use an **8×8×8 3D histogram** to weight-average the heaviest few bins (more stable than a direct average; stray noise will not pull it grey) → **clamp-darken** to `--max-lum`.

| Point | Explanation |
|---|---|
| Sampling source | sample the **source scene**, not the final image — in the final image the material's grey tone dominates, and what you get is grey (measured `#86867C`) |
| How to set `--max-lum` | derive from the **most demanding small-text ground**: `L_text ≤ (p5_bg + 0.05)/4.5 − 0.05`; this case p5≈0.23 → ≤0.0125 |
| **Must leave margin** | sitting exactly on the threshold fails (measured 0.0125 → CR 4.49, off by 0.01); this case stepped down one notch to **0.011** to pass |
| Output | `ink` (main text colour) / `ink2` (lifted 12%, for secondary text such as tagline) |

## 3. Human-eye gate (beyond the machine check)

1. Candidate board: three background variants side by side to pick a direction (is the subject prominent, has the background receded into a "colour field", is there enough negative space).
2. `--debug` image: the positional relationship of subject rect / backdrop window / text zone is clear at a glance.
3. Final piece: title not pressed, seal not covering text, subtitle and short phrase clearly hierarchised, overall breathing room in the negative space.
4. **★ Zero "off-colour edge band" on all four edges** (criterion changed 2026-10-12): with a **full-bleed ground**, the photo itself may have a whole strip of dark edge (case: the top 144px is the scene's black ceiling), and the old "report any dark band" would misjudge it. Now look at **features**: ① the luminance difference between the outermost 8px and the inner 60px is > 18 ② the outermost 8px's own std < 8 (it is an "edge band" rather than picture content) — both conditions must hold to count as leaked ground colour. Implemented in each `run_*.py`'s `edge_report()`.

   **The machine check cannot catch this** — it only looks at the text rectangle; if the page ground colour shows through, it still passes.

   Measured cause (2026-10-10): when `render_png.py` uses `--headless=new`, `--window-size` is the "**outer window size**", but the actual viewport is smaller than it (on this machine Edge 135 measured scale=2, short by 21×91 CSS px). The screenshot is output at window-size × scale → the page is only rendered up to the viewport → **the body ground colour shows in the lower right** (the master template body is `#17130E`, i.e. a black edge). Most glaring in dark / torn-paper scenes; it was also present in early light-paper scenes, just harder to notice.

   The current `render_png.py` fixes this with "enlarge window-size then crop back to the design size". If a narrow band appears again, run a pixel audit: the length of any continuous dark band on all four edges should be **all zero**.

   **★ Second cause (fixed 2026-10-12): the master template's CSS**. The background image was originally written as `<img class="art">`, sharing `.art` with the title art lettering, and `.art`'s `padding:0.15em 0.12em` + equal **negative margin** (reserved for the art-lettering transform) would push the `inset:0;width:100%` image off by ≈2.4px overall → **the final piece shows ~5px of `--stage-bg` on the right / bottom edges**. All five master templates have been changed to `<img class="bg">`.

   > Remember the criterion: **the outermost 8px having `std ≈ 0` = leaked ground colour**. Viewport leakage and CSS offset produce identical symptoms, but one cause is in rendering and the other in the master template — first check "is it the stage-bg colour" to tell them apart.

5. **★ Text does not press the "window" (exclusive to the `kraft_window.py` route)**: this route has no "centre seam", so instead check the **overlap area between text boxes and the window mask** (criterion: `alpha>128` counts as inside the window, overlap >2% counts as pressing). `run_case16.py` already has this check built in (iterates boxes.json × window mask, printing the overlap percentage per element).

   > The horizontal route checks "does not press the centre seam", the vertical route checks "does not press the window" — **the check item follows the shape extraction**. ⚠ But **if the horizontal tear band also goes through `kraft_window`** (see kraft-tear.md §1.11), the check item follows the **script**: you still check "does not press the window" (here the window = that horizontal band).

6. **★★ Layout-aesthetics baseline (set by the boss on 2026-10-12)**: after both the machine check and the human-eye gate pass, you must still verify these three:

   | Item | Quantitative criterion |
   |---|---|
   | **Title must be large** | set the main title by "how large the type-setting area can hold": `font size ≤ (live area − mark) ÷ (2.8 × word count)` (sandwich, two words of three characters each → cap ≈225px) |
   | **Not too much negative space** | ① the image window / subject **occupies ≥ 45% of the frame**; ② within each paper strip the **sum of top and bottom whitespace around the text block ≤ 1.5× the text block's own height** |
   | **The whole must be aesthetically pleasing** | human-eye check of the visual weight distribution (title / small text / info bar / image / negative space); the four corners should not be one crammed full and one empty |

   If it fails, handle it as "① change lines / structure ② reduce font size ③ adjust position" — **do not delete information**. Also: the ink colour / seal colour must be traceable to the source image (`pick_ink.py`; when the source has warm tones, use a vermilion square seal as the signature point).

7. **★ `giant` (oversized English cut at the bottom) has an expected `overflowY`**: the cut is done by the container's `overflow:hidden`, so the cropped glyphs inevitably push scrollHeight out of bounds — this item is guarded by **human-eye check** (lower half cleanly cut, left/right filled to the edge); if `overflowX` appears, that means the font size is too large, so go back to the formula and recompute.

8. **★ Troubleshooting criterion: `P5 = 0` while "pressing window" = 0% → first suspect the element overflowed the canvas.** Even the darkest part of the material has P5 ≈ 60–80; once the machine check reports **P5 = 0 / CR ≈ 1.14** while the window-overlap check is 0%, it is most likely the element was pushed **outside the canvas** by flex (landing on the body ground colour `#17130E`). ⚠ In this case **the element's own `overflowX` is still false** (the over-wide thing is the row container, not the element), so only measuring "is the element's right edge > 1500" reveals it. Measured: two segments totalling 817px in a `space-between` row squeezed into a 500px row → the second segment ran to x1618 (118px outside the canvas) → P5=0, CR 1.14. → Remedy: **change to single column / change lines**, do not shrink the font size.

## 4. Measured cases (Dunhuang "Visions on the Wall")

- Subject A2 (full-colour cutout) auto hero-top; first-round hero-band finalised blank_ratio 0.6472 → pass (historical).
- Second-round final: subject swapped to A2c (re-drawn without the hanging curtain, aspect 1.60) + azure-gold pale paper + shadow 0.30 / reflection 0.18 (shadow/reflection do not participate in checks, guarded by the human-eye gate): subject×zone 0.0 / backdrop×zone 0.0 / blank_ratio 0.7153 / inside-canvas true → pass. Final piece 12/12 all passed (main title 11.28, smallest presenter 5.63), overflow all false.
- Iteration lessons: the blue-grey framing lens backdrop window was read as a "light spot" → only resolved by removing the window / going full-bleed; the hanging curtain occluded the subject → image-to-image editing to remove it then re-cut; reflection below 0.30 is nearly invisible to the eye (visible range ≈0.50).

### Case 05 (2026-10-12, curved light-box photo wall + Qinghai ripple-pattern paper · cultural-event key visual)

- Route: horizontal tear band, but **the window script uses `kraft_window.py`** (horizontal framing to rule out the giant gilt main panel on the left of the photo): `band_mask --orient h` (band height ≈0.458H) → `torn_edge --edge 0.017 --bites 0 --fray 0.60` → `kraft_window --material-gain 1.0 --detail 2.0 --scale 1.0 --focus 0.56856,0.38531`.
- Machine check: Chinese and English each **10/10 all passed** (lowest 10.25, main title 15.15 under the 3.0 large-text threshold); overflow all false.
- Human-eye gate: four-edge audit **outermost 8px std all > 0.02, max difference from inner 60px is 0.19 but std is not 0 → no ground leakage**; text pressing window **0.00%** (window top edge min 487, title block bottom 404; window bottom edge max 1445, info block top 1580).
- All three layout-aesthetics baseline items met: main title 208px (cap ≈225), image window coverage **47.2%**, top-bar and bottom-bar text-block whitespace about 0.54× / 1.31× their own height respectively.

## 5. Troubleshooting (common causes of failure)

| Symptom | Handling (position first, then ink colour) |
|---|---|
| Text presses onto the backdrop window / subject | adjust the layout CSS position or shrink the background with `--subject-target` / `--bd-zoom`; re-run auto_compose's checks |
| Values wrap (overflowX) | do not set `.meta` to a percentage width; if the column is too narrow, shrink the font size first |
| Light text lacks contrast | increase the backdrop window's `--wash` (more faded) or move the subject / window down; adjust the ink colour only last |
| Insufficient negative space | shrink the subject target, shrink the backdrop window rx/ry |
| **Finished piece has off-colour narrow bands on all four edges** | render-viewport compensation failed: increase `render_png.py`'s `PAD` (`--headless=new`'s `--window-size` only frames the window, the viewport is smaller, and the page's bottom / right will reveal the body ground colour) |
