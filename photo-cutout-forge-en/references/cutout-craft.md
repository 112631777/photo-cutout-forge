# Cutout craft: AI white-background source image → subject PNG (alpha)

> The iron rule of this skill: **process the background first, then set the type**. The cutout target is the "subject" ——
> the main part extracted from the original image (arched building wall, figure, artefact, map …), standing on the paper ground as a cutout / silhouette,
> the rest left as negative space for text. Reference example grammar: textured paper ground as the field, subject prominent, large empty space, small bilingual type.

## Process chain

```
original image ──⓪ when subject is occluded: image-to-image edit 'remove occlusion, complete the occluded face' ──► clean original
     ──① AI image-to-image cutout (pure white background) ──► cand\*.png (white-background source; one version each of three candidates)
     ──② cutout.py (white background → alpha + denoise + crop edges) ──► cut\*.png (transparent-background subject)
     ──③ auto_compose.py puts it on paper (background processing + auto-composition) ──► three background versions combined into a candidate board
         ──Gate: pick a direction (default: pick yourself and state the reason in the deliverable)
```

## ① Prompt templates (image-to-image; reference image is the original photo)

The three candidates take "the same subject, different renditions" —— full-colour cutout / ink silhouette / two-colour flat-coat.

**First write the "subject description" (one of the user's three initial inputs)**: a paragraph describing what the subject is, its form, and how its top/bottom edges close off; the subject name and form sentences of the three templates are rewritten from this. Writing rules (measured):

- Describe it as a **complete, continuous object** ('one whole arched wall', 'one whole artefact'), and state explicitly 'not a band, not a fragment; not cut, not separated';
- **Avoid literal shape words** ('图带' [image band], '条带' [strip], 'ribbon') —— the image tool will take them literally and draw the subject as a floating strip, turning white gaps into holes and making recognition worse;
- State explicitly the **top/bottom edge closing positions** ('top edge is the wall top, bottom edge closes neatly along the wall base'), so the tear-opening contour arc lands inside the subject band.

Measured comparison (same material, white-background candidate + cutout.py luminance keying): no description silhouette hole ratio **10.19%** / literal '图带' [image band] **11.31%** (anti-pattern) / complete-continuous phrasing **6.54%**, with zero top/bottom contact and a smooth tear-opening arc. Case rewrite (template A opening sentence): change 'cut out the arched mural wall and the hanging gauze curtain as a whole' to 'the only subject in the frame = that **complete, continuous** arched mineral mural wall in the middle of the photo (including the gauze curtain hanging on its surface) —— **absolutely not a band, not a fragment; do not cut or separate the wall**; top edge is the mural wall top, bottom edge closes neatly along the wall base'. Note: the description makes the silhouette cleaner, but may also draw the subject band **flatter** —— the torn-material route's window becomes shorter, requiring `--zoom` compensation (see `kraft-tear.md` §4).

**A Full-colour cutout (preserve mineral colours)**

```
Cutout material generation: cut the arched mural wall and the hanging gauze curtain out of this exhibition-hall photo as a whole, placed on a pure white background.
The subject includes the arched wall on the left with earth-gold and lapis-lazuli-blue mineral textures, the blue-green landscape mural wall in the centre, and the reddish-gold wall on the right,
plus the semi-transparent gauze curtain hanging from the ceiling; preserve the mural's true mineral-pigment colours and texture, with clean crisp edges;
remove the black ceiling, light fixtures, dark floor and mirror reflections; the subject spreads horizontally, centred, with negative space all around, pure white background, high definition.
```

**B Ink silhouette (shadow-puppet / paper-cut feel)**

```
Silhouette material generation: turn the arched display wall and the gauze curtain from this exhibition-hall photo into a single dark-brown solid silhouette (like shadow puppets and paper cuts),
an overall solid-colour shape with no internal detail, keeping only the arched contour of the display wall and the hanging, undulating edge of the gauze curtain;
place on a pure white background; remove the ceiling, light fixtures, floor and all texture detail; subject centred, negative space all around, high definition.
```

**C Two-colour flat-coat (woodblock-print / print feel)**

```
Woodblock flat-coat material generation: extract the arched display wall from the exhibition hall into a two-colour flat-coat woodblock print —— using only deep azurite-blue and cream-white,
simplifying the mural texture into clear two- or three-step tonal blocks, with no gradient, no bleed, no light-and-shadow;
keep the contour structure of the arched wall and the gauze curtain; place on a pure white background, subject centred, negative space all around, high definition.
```

**D Occlusion removal and repair (when the subject is blocked by gauze curtains / columns etc., repair the original first, then cut out)**

```
Material repair edit: delete the semi-transparent gauze curtain hanging from the ceiling in this photo (remove any other objects blocking the display wall as well),
and complete the occluded arched wall surface —— pattern, colour and continuity with both sides natural, light-and-shadow consistent;
keep the display-wall shape, mineral colours and overall composition unchanged; output on pure white background, high definition.
```

Prompt key points: ① state 'pure white background' explicitly; ② state what to delete (ceiling / floor / reflections / occluders); ③ state 'do not change the subject's shape and colour'; ④ subject centred, negative space all around (for easy auto-cropping); ⑤ rewrite the subject sentence per the user's description as a complete, continuous phrasing (avoid literal shape words like '条带' [strip], see above). Image generation has randomness, so run several versions of the same prompt and pick. Perform occlusion removal (D) and cutout (A/B/C) in two separate steps; do not do it all in one edit pass; measured on the Dunhuang case: after removing the hanging curtain and completing the wall, re-cut with `--auto-white` to get a continuous, complete subject.

## ② Alpha extraction (cutout.py)

- Formula: `a = clip((white − L) / (white − floor), 0, 1) ** gamma`, default white=255, floor=36, gamma=0.92 (measured combination).
- Denoise: binarise (a>0.28) → MaxFilter/MinFilter opening/closing gates small spots; only pixels inside the gate keep their original alpha (PIL-only, no scipy dependency).
- Edges: `--shrink` (MinFilter shrinks edges, removes white rim), `--feather` (Gaussian soft edge, default 0.8).
- Crop edges: `--trim --pad 16` crops to the subject bbox and leaves a transparent margin.
- Mode: `--mode color` keeps original colour | `--mode ink` monochrome silhouette (`--ink #2A231A`) | `--mode duotone` preset LUT flat-coat + chroma retention (`--preset azure-gold`; the Chinese name 青金 still works).

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\A2.jpg --out cut\A2.png --mode color --trim --pad 16
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\B.jpg  --out cut\B.png  --mode ink --trim --pad 16
python .trae\skills\photo-cutout-forge-en\scripts\cutout.py --image cand\C2.jpg --out cut\C2.png --mode color --auto-white --trim --pad 16
```

> The above are the actual saved filenames from the Dunhuang case (image tools often write ASCII filenames); the two-colour flat-coat version has a cream-yellow background,
> **`--auto-white` is required** (estimates background brightness from the edge band), otherwise the whole background turns grey.

## ③ Troubleshooting (measured approach)

| Symptom | Handling |
|---|---|
| edge white ring / white border | first `--shrink 1`; if still not clean, raise floor (36→48) |
| background ghosting (grey haze) | raise floor; or regenerate (emphasise pure white background) |
| small noise dots | `--despeckle 5` (on by default) |
| subject eaten away (light gauze curtain vanishes) | lower floor (36→24) or gamma (0.92→0.8) |
| fine stripes / thin structure eaten | lower `--despeckle` (5→3, or 0 to disable) —— the gate opening kernel wider than the stripe width will erase the whole stripe |
| cream-yellow background turns wholly grey | add `--auto-white` (estimates background brightness from the edge band) |
| subject incomplete / shape altered | regenerate (emphasise "do not change the subject's shape") |
| subject covered by occluders (semi-transparent gauze / columns) | take route ⓪/D: image-to-image edit to remove occlusion and complete the occluded face, then re-cut; do not forcibly fix on the alpha |

## ④ Candidate board

Three background versions (produced by auto_compose) are combined into a candidate board with `board.py`:

```powershell
python .trae\skills\photo-cutout-forge-en\scripts\board.py --inputs out\bg.A2.png out\bg.B.png out\bg.C2.png --labels "full-colour cutout" "ink silhouette" "two-colour flat-coat" --cols 3 --width 480 --out out\cand-board.png
```

> Transparent-background subjects should first go through auto_compose to be placed on paper before boarding (directly boarding a transparent PNG has an uncontrolled background colour).
