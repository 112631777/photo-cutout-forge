# Automatic composition: five layouts · decision rules · text zone

> The landing point for the requirement "can choose how to compose autonomously": `auto_compose.py` reads the subject's (cutout alpha) **aspect ratio and mass centre**, automatically selects a layout, sets the subject and backdrop-window positions, and writes the reasoning (in Chinese) into `plan.json`. A human can override with `--layout` (including the optional full-width scroll `hero-band`). Canvas 1500×1875 (4:5).

## Visual model (three-step compositing, background first, type second)

```
paper ground (make_ground: preset paper colour + texture; --paper can override the paper colour)
  → backdrop window (original image via zoom / crop / soft focus / duotone / wash, lens mask, multiply on; --no-backdrop can remove it)
    → reflection / shadow (optional painting layer: --reflection water reflection at the subject's lower edge, --shadow cast shadow on the paper)
      → subject (transparent-background cutout, over on top)
        → only then the text (the master template handles typography only, not the background)
```

## Five layouts and parameters (tuned on the Dunhuang case)

| Layout (data-comp) | When selected (automatic rule) | Backdrop window (lens, feather 30) | Subject | Text zone (master template must match) |
|---|---|---|---|---|
| hero-top | subject aspect ratio ≥ 1.18 (horizontal island) | cx .50 cy .335 rx .415 ry .265 zoom 2.8 | width .72W (height cap .46H), horizontally centred, top .115 | below [.07, .62, .93, .97] |
| hero-right | aspect ratio ≤ 0.80 and mass centre x > .50 | cx .70 cy .45 rx .235 ry .30 zoom 2.2 | height .52H (width cap .38W), centre x .775, bottom .84 | left [.06, .12, .50, .92] |
| hero-left | aspect ratio ≤ 0.80 and mass centre x ≤ .50 | cx .30 cy .45 rx .235 ry .30 zoom 2.2 (mirrored) | height .52H (width cap .38W), centre x .225, bottom .84 | right [.50, .12, .94, .92] |
| hero-centre | the rest (0.80–1.18, square) | cx .50 cy .315 rx .40 ry .245 zoom 2.4 | width .60W (height cap .42H), centred, top .14 | below [.07, .62, .93, .97] |
| hero-band | panoramic banner (aspect ratio ≥ 1.30) and wants a full-width scroll — **not auto-selected**, requires `--layout hero-band` | none (`shape: none`) | width 1.0W (height cap .62H), horizontally centred, top .03 | below [.07, .635, .93, .98] |

- The backdrop window always uses `--focus` (default 0.5 0.40) for framing, duotone (default preset "azure-gold", chroma .55), **soft focus `--bd-blur` (default 10) + blending toward paper colour `--wash` (default .40)**, multiplied onto the paper. Soft focus and wash are the lifeblood of the cutout route: the background recedes into a "colour field" so the sharp subject gains foreground/background hierarchy (measured on Dunhuang).
- `--no-backdrop`: removes the backdrop window entirely (pure paper background), usable in any layout; if the soft-light ellipse behind an island subject is read as a "light spot / shadow", this is more thorough than re-framing (measured on Dunhuang).
- **`--bg-mode color` (extract duotone-gradient ground field, no window)**: downsample the original (width 220px), take "saturated pixels" (S>0.28, 18%<V<85%) and run k-means (k=4, seed same as `--seed`). Main colour = the cluster with the **highest weight×saturation**, then darkened (V×0.74 clamped [0.30,0.46], S×1.15 clamped [0.32,0.62]), preserving the photo's own hue; when `--bg-color "#RRGGBB"` is given it is used directly (the secondary colour is still extracted from the original). Secondary colour = the cluster with the **largest hue distance** from the main colour and weight ≥6% (used only if distance ≥20°), pressed darker (S×0.92 clamped [0.28,0.52], V×0.78 clamped [0.28,0.38]); if no suitable cluster, fall back one step lighter in the same hue. Ground field = **biased two-colour gradient**: `diag` = `u = 0.62·(y/h) + 0.38·(x/w)` (secondary colour enters diagonally from the lower-right edge); `up` = `u = 0.88·(y/h) + 0.12·(x/w)` (secondary colour rises across the whole lower edge into a "stage floor", main colour occupies the upper ≈2/3); where u<threshold it is all main colour, smoothstep transition (not a 50/50 split); only 0.8σ jitter to prevent banding. `--bg-grad {diag,up}` selects direction; `--bg-vignette 0.18` gently darkens the four edges (`1-v·rr²`) to draw the eye inward; `--bg-lift 0.30` brightens both colours together (V×(1+lift), hue and saturation unchanged). **Pure colour gradient, zero texture** — overlaying cloud mottling / weave / grain would be read as "speckles, not refined" (measured across three Dunhuang iterations). Switch to this route when the soft-focus window is read as a "blurred photo patch".
- **Paper and painting layers (optional, opt-in)**: `--paper "#E8DCC0"` overrides the paper colour (default takes the preset); `--shadow 0.30` adds a cast shadow on the paper to the subject (`--shadow-blur` 26 / `--shadow-dy` 20) — fixes "insufficient contrast between subject and paper"; `--reflection 0.50` lays a fading water reflection along the subject's lower edge (`--reflection-blur` 20) — adds layering to the paper, **below 0.30 it is nearly invisible to the eye (measured on Dunhuang)**. **Subject enhancement (common on colour deep grounds)**: `--subject-pop 0.25` boosts saturation/contrast to make the subject "stand out"; `--subject-paint 0.6–1.0` "repaint" (median denoise → boost saturation/brightness → contrast → colour-layer quantisation, ≥0.45 gives a hand-drawn block feel); `--subject-lift 0.25` brightens (preserving hue).
- Subject scaling picks an achievable set from the "target size" (start from the main target; if it exceeds the cap, use the cap).
- **Starting parameters**: in practice, aim for all `plan.json` checks to pass (you may fine-tune shrink / move / colour).
- Meaning of the text zone: **host text may only land in this zone** (no subject or backdrop window may be inside it).

## Decision rationale (the layout_reason written into plan.json)

- `aspect ratio ≥ 1.18` → "the subject spreads horizontally; place it as a horizontal top island, with the whole paper below carrying the text"
- `aspect ratio ≤ 0.80` → "the subject is tall and narrow; place it as a vertical side pillar; choose left/right by its mass centre, giving up the opposite full column of paper"
- the rest → "the subject is square; centre it as a floating island, with paper around it and text carried at the lower edge"
- `hero-band` (manually specified) → "panoramic scroll spans the full width as a wall scroll; the whole paper below carries the text"

## Master-template mapping (data contract)

`body[data-comp]` takes hero-top / hero-right / hero-left / hero-centre; text positions per layout:

| Layout | presenter | Main block (title + exhibition info) | Main-title font size | Seal |
|---|---|---|---|---|
| hero-top | top centred | lower-left 7%, width 62%, bottom 3.4% | 196px | right 7% bottom 26% |
| hero-right | top-left | left 7%, top 26%, width 43% | 152px | left 7% bottom 12% |
| hero-left | top-right (right-aligned) | right 7%, top 26%, width 43%, right-aligned | 152px | right 7% bottom 12% |
| hero-centre | top centred | centred block left/right 10%, bottom 3.0% | 196px | right 6.8% bottom 24% |
| hero-band | top centred | reuses hero-top main block: lower-left 7%, width 62%, bottom 3.4% | 196px | right 7% bottom 26% |

- The main-block structure follows the master template: ornament / title / subtitle / tagline / meta three lines / cta; the font-size system is in calligraphy.md.
- hero-band's text zone is close to hero-top's, so the master template directly uses `data-comp="hero-top"` (the Dunhuang final used exactly this config).
- **Deep-ground light-text theme**: when setting type on a colour ground, add `data-theme="deep"` to the master template `body` (gilt title / cream info / gold-ground CTA), and change `.stage`'s `--stage-bg` to the same value as the ground field; rendering can also switch with `?theme=deep` (the machine-check instrument can use it too). After the ground field is brightened by `--bg-lift`, overall text contrast drops, so the small-text ink must be brightened one notch to follow (Dunhuang tier-I tagline `#D3C5A6→#DDD0B2`, recovered from 4.27→4.77).
- After rendering, `boxes.json`'s overflowX/Y must all be false; if not, adjust font size / column width (position first, then ink colour).

## Machine check (auto_compose's built-in checks, written to plan.json)

| Item | Criterion | What to do if it fails |
|---|---|---|
| subject×text_zone overlap | coverage of the text zone ≤ 2% | shrink the subject in 0.92 steps, up to 4 times; if still failing, report fail |
| backdrop×text_zone overlap | same as above | shrink the backdrop window by the same step (or move it down) |
| blank_ratio (negative-space ratio) | visible paper ratio ≥ 0.40 | shrink the subject / backdrop window |
| subject inside canvas | subject rect fully inside the canvas | re-clamp position |

`plan.json` fields: layout + layout_reason + subject (aspect, mass_cx, rect_px, pop / paint / lift) + backdrop (shape/cx/cy/rx/ry/zoom/focus/crop_px/chroma/wash/blur or none) + text_zone + checks (pass) + shadow (strength/blur/dy or null) + reflection (strength/blur or null) + paper (preset/seed/color) + **background (when "mode": "color", includes base main colour / second secondary colour / grad direction / vignette / lift and the source_palette extracted clusters; when window/paper, just "mode")**.

## CLI and debugging

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\auto_compose.py --source src.png --subject cut\A.png `
    --preset azure-gold --seed 3 --out out\bg.png --plan out\plan.json [--debug out\debug.png] `
    [--layout hero-top|hero-band] [--no-backdrop] [--bg-mode window|color] [--bg-color "#1F3F6E"] `
    [--bg-grad diag|up] [--bg-vignette .18] [--bg-lift .30] [--subject-pop .25] [--subject-paint 1.0] [--subject-lift .25] `
    [--focus .5 .4] [--bd-zoom 2.8] [--bd-blur 10] [--wash .40] [--chroma .55] [--subject-target .72] `
    [--shadow .30] [--reflection .5] [--paper "#E8DCC0"]
```

- `--debug`: draws the backdrop window (blue), subject rect (red), and text zone (green) rectangles on the background image for the human-eye gate.
- change layout = `--layout` (including `hero-band` full-width scroll); remove window = `--no-backdrop`; change colour tone = `--preset`; paper texture = `--seed`; subject size = `--subject-target` (proportion of canvas width/height).
- `--bg-mode color`: the duotone-gradient ground-field route (no window); automatically extracts the main + secondary colour, or `--bg-color` specifies the main colour (e.g. Dunhuang deep azurite `#1F3F6E`, secondary still extracted from the original). Outputs `background.mode=color` (base/second); set type with `data-theme="deep"`. Direction / darkening / brightening = `--bg-grad up` / `--bg-vignette` / `--bg-lift`; subject pairing `--subject-paint` / `--subject-pop` / `--subject-lift`, shadow `--shadow`.
- Parameter-tuning priority: first `--subject-target` / `--bd-zoom` (composition), then `--wash` / `--bd-blur` (hierarchy), last `--focus` (framing).
- insufficient subject contrast = `--shadow 0.30` (0.25–0.38); too empty paper = `--reflection 0.50` (below 0.30 nearly invisible); wrong paper colour = `--paper`.
- **Set the type only after the background is done**; at render time, poster.html's `body[data-comp]` must match plan.json's layout.
