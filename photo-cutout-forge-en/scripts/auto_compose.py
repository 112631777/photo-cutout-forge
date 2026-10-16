#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
auto_compose.py — background stylisation + automatic composition: original photo +
transparent-background subject -> processed background (bg.png)

Step 3 of photo-cutout-forge (where requirements 1/3/5 land):
  1. Process the background first: the original goes through "framing (focus) -> zoom ->
     crop -> duotone -> mask (lens-feathered ellipse) -> multiply" to become a
     "background window" on the paper;
  2. The subject (cutout alpha) stands on the paper via over; the rest is negative space;
  3. Automatic composition: read the subject's aspect ratio and mass centre, auto-pick one
     of four layouts (hero-top/right/left/centre), and write the reason in plan.json;
     a human can override with --layout;
  4. Built-in checks (subject x text zone, background x text zone, negative-space ratio, drop
     onto canvas), retried with a 0.92 step shrink;
  5. Only the background is produced — text typography is the master template's job
     (poster-cutout-master.html); the iron rule is "background first, type second".

There is also --bg-mode color: instead of a background window, extract "main colour + secondary
colour" from the original to make a biased two-colour gradient ground (main ~2/3, secondary
slants in from the lower edge; smooth, no speckle) + subject over — a route of solid gradient
ground + crisp subject + calligraphy (main colour --bg-color can override).

Visual model: paper (make_ground) -> background window (multiply) -> subject (over) ->
(then comes the type)

Usage:
    python auto_compose.py --source src.png --subject cut\A.png --preset azure-gold --seed 3 \
        --out out\bg.png --plan out\plan.json [--layout hero-top] [--debug out\debug.png]
    python auto_compose.py --list-layouts
"""

import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS_PATH = os.path.join(HERE, "..", "assets", "presets.json")
W, H = 1500, 1875          # canvas 4:5
Q = 4                      # machine-check downsample factor

# ---------------------------------------------------------------------------
# Four layouts (starting parameters; the final pick is validated by the checks in plan.json)
# ---------------------------------------------------------------------------
LAYOUTS = {
    "hero-top": {
        "when": "subject aspect ratio ≥ 1.18 (horizontal island)",
        "reason": "Subject spreads horizontally: sit it as a banner-like island up top, leaving the whole lower sheet for type",
        "backdrop": {"cx": 0.50, "cy": 0.335, "rx": 0.415, "ry": 0.265, "zoom": 2.8},
        "subject": {"mode": "width", "target": 0.72, "cap": 0.46, "cx": 0.50, "top": 0.115},
        "text_zone": [0.07, 0.62, 0.93, 0.97],
    },
    "hero-right": {
        "when": "aspect ratio ≤ 0.80 and mass centre x > 0.50",
        "reason": "Subject is tall: set it as a side column; mass centre leans right, freeing the whole left column of paper",
        "backdrop": {"cx": 0.70, "cy": 0.45, "rx": 0.235, "ry": 0.30, "zoom": 1.5},
        "subject": {"mode": "height", "target": 0.52, "cap": 0.38, "cx": 0.775, "bottom": 0.84},
        "text_zone": [0.06, 0.12, 0.50, 0.92],
    },
    "hero-left": {
        "when": "aspect ratio ≤ 0.80 and mass centre x ≤ 0.50",
        "reason": "Subject is tall: set it as a side column; mass centre leans left, freeing the whole right column of paper",
        "backdrop": {"cx": 0.30, "cy": 0.45, "rx": 0.235, "ry": 0.30, "zoom": 1.5},
        "subject": {"mode": "height", "target": 0.52, "cap": 0.38, "cx": 0.225, "bottom": 0.84},
        "text_zone": [0.50, 0.12, 0.94, 0.92],
    },
    "hero-centre": {
        "when": "everything else (0.80–1.18, square-ish)",
        "reason": "Subject is square-ish: centred as a floating island, paper on all sides, type along the bottom edge",
        "backdrop": {"cx": 0.50, "cy": 0.315, "rx": 0.40, "ry": 0.245, "zoom": 2.4},
        "subject": {"mode": "width", "target": 0.60, "cap": 0.42, "cx": 0.50, "top": 0.14},
        "text_zone": [0.07, 0.62, 0.93, 0.97],
    },
    "hero-band": {  # full-width scroll: not auto-selected (bold), needs --layout hero-band explicitly
        "when": "panoramic banner (aspect ratio ≥ 1.30) wanted as a full-width scroll",
        "reason": "Panorama runs edge to edge as a wall scroll; the whole bottom strip of paper takes the type",
        "backdrop": None,
        "subject": {"mode": "width", "target": 1.0, "cap": 0.62, "cx": 0.50, "top": 0.030},
        "text_zone": [0.07, 0.635, 0.93, 0.98],
    },
}
FEATHER = 30.0


# ---------------------------------------------------------------------------
# Colour / preset / LUT / paper (same conventions as cutout.py)
# ---------------------------------------------------------------------------
def rgb_of(hx):
    return np.array([int(hx[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def mix(a, b, t):
    return a * (1.0 - t) + b * t


def load_presets():
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_preset(presets, name):
    """Accept an English slug, the Chinese name (zh), or the display name (en)."""
    if name in presets:
        return name, presets[name]
    low = name.strip().lower()
    for key, val in presets.items():
        if val.get("zh") == name.strip():
            return key, val
        if str(val.get("en", "")).strip().lower() == low:
            return key, val
    return None, None


def build_lut(preset, gamma=1.0):
    shadow, mid, light = rgb_of(preset["shadow"]), rgb_of(preset["mid"]), rgb_of(preset["light"])
    paper = rgb_of(preset["paper"])
    top = mix(paper, np.array([255.0, 255.0, 248.0], np.float32), 0.5)
    pts = [(0.0, shadow), (0.45, mid), (0.82, light), (1.0, top)]
    lut = []
    for i in range(256):
        t = (i / 255.0) ** (1.0 / gamma)
        c = pts[-1][1]
        for j in range(len(pts) - 1):
            a0, c0 = pts[j]
            a1, c1 = pts[j + 1]
            if t <= a1 or j == len(pts) - 2:
                u = 0.0 if a1 == a0 else (t - a0) / (a1 - a0)
                c = mix(c0, c1, min(1.0, max(0.0, u)))
                break
        lut.extend(int(round(float(v))) for v in c)
    return lut


def make_ground(preset, seed, size=(W, H)):
    """Paper: paper colour + low-frequency mottling + fine-grain noise + sparse dark specks +
    light corner pressure."""
    w, h = size
    rng = np.random.default_rng(seed)
    arr = np.tile(rgb_of(preset["paper"]), (h, w, 1)).astype(np.float32)
    low = rng.normal(0, 1, (h // 28 + 2, w // 28 + 2)).astype(np.float32)
    mot = np.asarray(Image.fromarray(((low * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8))
                     .resize((w, h), Image.BICUBIC), np.float32) / 255.0 - 0.5
    arr += (mot * 10.0)[..., None]
    arr += rng.normal(0, float(preset.get("grain", 0.05)) * 255.0 * 0.5, (h, w, 1)).astype(np.float32)
    n = int(w * h * 0.00030)
    idx = rng.choice(w * h, size=n, replace=False)
    arr.reshape(-1, 3)[idx] *= 0.965
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.sqrt(((xx / w - 0.5) * 2) ** 2 + ((yy / h - 0.5) * 2) ** 2) / 1.414
    arr *= (1.0 - 0.05 * rr ** 2)[..., None]
    return np.clip(arr, 0, 255)


# ---------------------------------------------------------------------------
# Background colour fill (--bg-mode color): extract main colour from original ->
# dark ground + fabric texture
# ---------------------------------------------------------------------------
def rgb_hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(max(0.0, min(255.0, float(v))))) for v in rgb)


def rgb2hsv(rgb):
    r, g, b = [float(v) / 255.0 for v in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d <= 1e-6:
        return 0.0, 0.0, mx
    if mx == r:
        h = ((g - b) / d) % 6.0
    elif mx == g:
        h = (b - r) / d + 2.0
    else:
        h = (r - g) / d + 4.0
    return h * 60.0, d / mx, mx


def hsv2rgb(h, s, v):
    i = int(h // 60.0) % 6
    f = h / 60.0 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]
    return np.array([r, g, b], np.float32) * 255.0


def _lift_rgb(col, amount):
    """Lift a colour (keep hue/saturation, V x (1+amount))."""
    h, s, v = rgb2hsv(col)
    return hsv2rgb(h, s, min(1.0, v * (1.0 + amount)))


def _kmeans(a, k=4, iters=14, seed=11):
    rng = np.random.default_rng(seed)
    c = a[rng.choice(len(a), k, replace=False)].copy()
    for _ in range(iters):
        lab = ((a[:, None, :] - c[None, :, :]) ** 2).sum(-1).argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                c[j] = a[m].mean(0)
    w = np.bincount(lab, minlength=k).astype(np.float32) / len(a)
    o = np.argsort(-w)
    return c[o], w[o]


def extract_bg_color(src, override="auto", seed=11):
    """Original -> (ground main colour, secondary colour, main-colour cluster hex list).

    Main colour: among clusters of "saturated pixels" (S>0.28, 18%<V<85%) take the one
    with the highest weight x saturation; push it darker (V<=0.46, S>=0.32) — keep the
    photo's own hue, do not fade to grey;
    Secondary colour: the cluster farthest in hue from the main colour and with weight >=6%,
    pushed deeper (S x 0.92 / V x 0.78) — both colours are dark-toned, for the "not 50/50"
    biased gradient (see bg_ground).
    When override is #RRGGBB, the main colour is taken directly (secondary still chosen
    from the original's clusters).
    """
    im = src.convert("RGB")
    hh = max(2, int(round(220 * im.height / im.width)))
    flat = np.asarray(im.resize((220, hh), Image.BILINEAR), np.float32).reshape(-1, 3)
    f01 = flat / 255.0
    mx, mn = f01.max(1), f01.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    m = (sat > 0.28) & (mx > 0.18) & (mx < 0.85)
    pool = flat[m] if int(m.sum()) >= 60 else flat
    c, w = _kmeans(pool, min(4, len(pool)), seed=seed)
    palette = [rgb_hex(ci) for ci in c]
    if override and override != "auto":
        base = np.array([int(override[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
        h, s, v = rgb2hsv(base)
    else:
        score = w * np.array([rgb2hsv(ci)[1] for ci in c], np.float32)
        h, s, v = rgb2hsv(c[int(score.argmax())])
        base = hsv2rgb(h, min(0.62, max(0.32, s * 1.15)), min(0.46, max(0.30, v * 0.74)))
    j, dh_max = None, -1.0
    for k in range(len(c)):
        hk = rgb2hsv(c[k])[0]
        dh = abs(hk - h) % 360.0
        dh = min(dh, 360.0 - dh)
        if w[k] >= 0.06 and dh > dh_max:
            j, dh_max = k, dh
    if j is not None and dh_max >= 20.0:
        h2, s2, v2 = rgb2hsv(c[j])
        second = hsv2rgb(h2, min(0.52, max(0.28, s2 * 0.92)), min(0.38, max(0.28, v2 * 0.78)))
    else:
        second = hsv2rgb(h, min(0.60, s * 0.85), min(0.40, max(0.30, v * 0.95)))
    return base, second, palette


def bg_ground(base, second, seed, size=(W, H), grad="diag", vignette=0.0):
    """Ground = biased two-colour gradient (main colour takes the large area, secondary slants in
    from the lower edge) — smooth, no speckle, no texture overlaid.

    Rationale: text and info concentrate at the bottom -> secondary slants in from the lower edge,
    heavier right than left (avoids the dense left text column; the title band stays on the main
    colour, where big gold type has the steadiest contrast); the upper subject area keeps a solid
    main-colour ground (consistent figure/ground). Transition uses smoothstep, not 50/50 (u below
    threshold is all main colour); only 0.8 sigma jitter to prevent banding.
    grad="diag" = slants in from the lower-right (u=0.62y+0.38x); grad="up" = vertical from the
    bottom edge (u=0.88y+0.12x). vignette>0 lightly darkens the four edges to draw the eye to the
    central subject.
    """
    w, h = size
    rng = np.random.default_rng(seed + 977)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yn, xn = yy / (h - 1), xx / (w - 1)
    if grad == "up":
        u = 0.88 * yn + 0.12 * xn
        t = np.clip((u - 0.56) / 0.38, 0.0, 1.0)
    else:
        u = 0.62 * yn + 0.38 * xn       # 0 = top edge -> 1 = lower-right edge
        t = np.clip((u - 0.52) / 0.42, 0.0, 1.0)
    t = (t * t * (3.0 - 2.0 * t))[..., None]
    arr = (np.asarray(base, np.float32)[None, None, :] * (1.0 - t)
           + np.asarray(second, np.float32)[None, None, :] * t)
    arr += rng.normal(0, 0.8, (h, w, 1)).astype(np.float32)
    if vignette > 0:
        rr = np.sqrt(((xn - 0.5) * 2) ** 2 + ((yn - 0.5) * 2) ** 2) / 1.414
        arr *= (1.0 - float(vignette) * rr ** 2)[..., None]
    return np.clip(arr, 0, 255)


def pop_subject(img, amount):
    """Light subject saturation + contrast boost (alpha unchanged) — makes the subject stand out
    more on a dark ground (0.2-0.3 recommended)."""
    r, g, b, aa = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    sc = hsv.getchannel("S").point(lambda v: min(255, int(v * (1.0 + 0.35 * amount))))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), sc, hsv.getchannel("V"))).convert("RGB")
    arr = np.asarray(rgb, np.float32)
    arr = np.clip((arr - 128.0) * (1.0 + 0.22 * amount) + 128.0, 0, 255)
    out = Image.fromarray(arr.astype(np.uint8), "RGB")
    return Image.merge("RGBA", (*out.split(), aa))


def paint_subject(img, amount):
    """Subject "repaint": denoise smoothing -> saturation/lift boost -> contrast -> colour-layer
    quantisation.

    Push the real-photo subject toward an illustration/hand-drawn "high saturation, vivid colour,
    clean blocks" look (the brocade ribbon of the reference poster has exactly this feel);
    amount 0-1 (0.6 gives a blocky painted feel).
    """
    r, g, b, aa = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = rgb.filter(ImageFilter.MedianFilter(3))                 # 1) denoise: smooth photo noise, cleaner blocks
    hsv = rgb.convert("HSV")
    sc = hsv.getchannel("S").point(lambda v: min(255, int(v * (1.0 + 0.90 * amount))))
    vc = hsv.getchannel("V").point(lambda v: min(255, int(v * (1.0 + 0.10 * amount))))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), sc, vc)).convert("RGB")
    arr = np.asarray(rgb, np.float32)                              # 2) contrast
    arr = np.clip((arr - 128.0) * (1.0 + 0.30 * amount) + 128.0, 0, 255)
    rgb = Image.fromarray(arr.astype(np.uint8), "RGB")
    if amount >= 0.45:                                             # 3) colour-layer quantisation: hand-drawn block feel
        colors = max(40, int(round(88 - 48 * amount)))
        rgb = rgb.quantize(colors=colors, method=Image.MEDIANCUT,
                           dither=Image.Dither.NONE).convert("RGB")
    return Image.merge("RGBA", (*rgb.split(), aa))


def lift_subject(img, amount):
    """Subject lift (keep hue/saturation, V x (1+amount); alpha unchanged)."""
    r, g, b, aa = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    v = hsv.getchannel("V").point(lambda x: min(255, int(x * (1.0 + amount))))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), hsv.getchannel("S"), v)).convert("RGB")
    return Image.merge("RGBA", (*rgb.split(), aa))


# ---------------------------------------------------------------------------
# Background window: framing -> duotone -> mask
# ---------------------------------------------------------------------------
def crop_window(src, focus, aspect, zoom):
    sw, sh = src.size
    hh = sh / max(0.2, float(zoom))
    ww = hh * aspect
    if ww > sw:
        ww = float(sw)
        hh = ww / aspect
    if hh > sh:
        hh = float(sh)
        ww = hh * aspect
    cx, cy = focus[0] * sw, focus[1] * sh
    x0 = min(max(cx - ww / 2.0, 0.0), sw - ww)
    y0 = min(max(cy - hh / 2.0, 0.0), sh - hh)
    return [round(x0), round(y0), round(x0 + ww), round(y0 + hh)]


def lens_bbox(bd, pad=40.0):
    cx, cy = bd["cx"] * W, bd["cy"] * H
    rx, ry = bd["rx"] * W, bd["ry"] * H
    return [cx - rx - pad, cy - ry - pad, cx + rx + pad, cy + ry + pad]


def lens_mask(bd, bbox, feather=FEATHER):
    bx0, by0, bx1, by1 = bbox
    bw, bh = int(round(bx1 - bx0)), int(round(by1 - by0))
    ss = 2
    big = Image.new("L", (bw * ss, bh * ss), 0)
    d = ImageDraw.Draw(big)
    cx, cy = (bd["cx"] * W - bx0) * ss, (bd["cy"] * H - by0) * ss
    rx, ry = bd["rx"] * W * ss, bd["ry"] * H * ss
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    m = big.resize((bw, bh), Image.LANCZOS)
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather / 2.0))
        m = m.point(lambda v: min(255, int(v * 1.28)))
    return m


def build_backdrop(src, bd, preset, chroma, focus, wash=0.32, blur=0.0):
    """Original -> background-window RGBA (framing -> duotone -> chroma -> soft focus -> blend toward
    paper colour -> mask) and its bbox."""
    bbox = lens_bbox(bd)
    bx0, by0 = bbox[0], bbox[1]
    bw, bh = int(round(bbox[2] - bx0)), int(round(bbox[3] - by0))
    crop = crop_window(src, focus, bw / bh, bd.get("zoom", 1.4))
    sub = src.crop(crop).resize((bw, bh), Image.LANCZOS)
    plate = sub.point(build_lut(preset)).convert("RGB")

    if chroma > 0:
        hsv = sub.convert("HSV")
        sat = np.asarray(hsv.getchannel("S"), np.float32) / 255.0
        g = np.asarray(sub.convert("L"), np.float32) / 255.0
        w = (chroma * np.clip(sat * 2.2, 0.0, 1.0) * np.clip(1.5 - 1.1 * g, 0.2, 1.0))[..., None]
        duo = np.asarray(plate, np.float32)
        org = np.asarray(sub, np.float32)
        mx = duo * (1.0 - w) + org * w
        gray = mx.mean(axis=2, keepdims=True)
        mx = gray + (mx - gray) * 1.12
        plate = Image.fromarray(np.clip(mx, 0, 255).astype(np.uint8))

    if blur > 0:  # soft focus: push the background back to a "colour field", separating it from the sharp subject
        plate = plate.filter(ImageFilter.GaussianBlur(blur))

    if wash > 0:  # blend toward paper colour: make the window a "faded print", not a see-through photo
        paper = rgb_of(preset["paper"])
        mx = np.asarray(plate, np.float32) * (1.0 - wash) + paper * wash
        plate = Image.fromarray(np.clip(mx, 0, 255).astype(np.uint8))

    mask = lens_mask(bd, bbox)
    rgba = plate.convert("RGBA")
    rgba.putalpha(mask)
    return rgba, [int(round(bx0)), int(round(by0))], crop


def _clip(dst_shape, pos, size):
    x0, y0 = pos
    nw, nh = size
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(dst_shape[1], x0 + nw), min(dst_shape[0], y0 + nh)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    return (cx0, cy0, cx1, cy1, cx0 - x0, cy0 - y0)


def composite(arr, rgba, pos, mode="over"):
    clip = _clip(arr.shape, pos, rgba.size)
    if not clip:
        return
    cx0, cy0, cx1, cy1, sx0, sy0 = clip
    p = np.asarray(rgba.convert("RGB"), np.float32)[sy0:sy0 + (cy1 - cy0), sx0:sx0 + (cx1 - cx0)]
    a = np.asarray(rgba.getchannel("A"), np.float32)[sy0:sy0 + (cy1 - cy0),
                                                      sx0:sx0 + (cx1 - cx0)][..., None] / 255.0
    dst = arr[cy0:cy1, cx0:cx1]
    src = dst * p / 255.0 if mode == "multiply" else p
    arr[cy0:cy1, cx0:cx1] = dst * (1.0 - a) + src * a


# ---------------------------------------------------------------------------
# Subject metrics and layout selection (requirement 1: auto-pick composition)
# ---------------------------------------------------------------------------
def subject_metrics(subj):
    a = np.asarray(subj.getchannel("A"), np.float32)
    ys, xs = np.where(a > 8.0)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    w, h = x1 - x0, y1 - y0
    sub = a[y0:y1, x0:x1]
    total = float(sub.sum())
    mass_cx = float((sub * np.arange(w)[None, :]).sum() / total / max(1, w)) if total else 0.5
    return {"aspect": w / h, "mass_cx": mass_cx, "bbox": [x0, y0, x1, y1]}


def pick_layout(m):
    if m["aspect"] >= 1.18:
        return "hero-top"
    if m["aspect"] <= 0.80:
        return "hero-right" if m["mass_cx"] > 0.50 else "hero-left"
    return "hero-centre"


def subject_rect(subj_bbox, spec, scale):
    """Compute the subject's rect (px) on the canvas from the layout anchor."""
    x0, y0, x1, y1 = subj_bbox
    w, h = (x1 - x0) * scale, (y1 - y0) * scale
    cx = spec["cx"] * W
    left = cx - w / 2.0
    if "top" in spec:
        top = spec["top"] * H
    else:
        top = spec["bottom"] * H - h
    return [left, top, w, h]


def fit_scale(subj_bbox, spec):
    w, h = subj_bbox[2] - subj_bbox[0], subj_bbox[3] - subj_bbox[1]
    if spec["mode"] == "width":
        return min(spec["target"] * W / w, spec["cap"] * H / h)
    return min(spec["target"] * H / h, spec["cap"] * W / w)


# ---------------------------------------------------------------------------
# Machine checks (downsample to 1/Q for computation)
# ---------------------------------------------------------------------------
def _small_alpha(img, q=Q):
    img = img.convert("L")
    return np.asarray(img.resize((max(1, img.size[0] // q), max(1, img.size[1] // q)),
                                 Image.BILINEAR), np.float32) / 255.0


def _paste(canvas, arr, pos):
    x, y = int(round(pos[0] / Q)), int(round(pos[1] / Q))
    h, w = arr.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.shape[1], x + w), min(canvas.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1],
                                      arr[y0 - y:y1 - y, x0 - x:x1 - x])


def checks(sub_c, bd_rgba, bd_pos, rect, text_zone):
    cw, ch = W // Q, H // Q
    a_sub = np.zeros((ch, cw), np.float32)
    a_bd = np.zeros((ch, cw), np.float32)
    sub_l = sub_c.getchannel("A").resize(
        (max(1, int(round(rect[2] / Q))), max(1, int(round(rect[3] / Q)))), Image.BILINEAR)
    _paste(a_sub, np.asarray(sub_l, np.float32) / 255.0, (rect[0], rect[1]))
    _paste(a_bd, _small_alpha(bd_rgba.getchannel("A")), bd_pos)

    zx0, zy0 = int(text_zone[0] * W / Q), int(text_zone[1] * H / Q)
    zx1, zy1 = int(text_zone[2] * W / Q), int(text_zone[3] * H / Q)
    zone = (slice(zy0, zy1), slice(zx0, zx1))
    z_area = max(1, (zy1 - zy0) * (zx1 - zx0))
    ov_sub = float((a_sub[zone] > 0.10).sum()) / z_area
    ov_bd = float((a_bd[zone] > 0.12).sum()) / z_area
    covered = (a_sub > 0.04) | (a_bd > 0.12)
    blank = float(1.0 - covered.mean())

    in_canvas = (rect[0] >= -1 and rect[1] >= -1 and
                 rect[0] + rect[2] <= W + 1 and rect[1] + rect[3] <= H + 1)
    return {"subject_text_overlap": round(ov_sub, 4), "backdrop_text_overlap": round(ov_bd, 4),
            "blank_ratio": round(blank, 4), "subject_in_canvas": bool(in_canvas)}


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="background stylisation + automatic composition -> bg.png + plan.json")
    ap.add_argument("--source", required=True, help="original photo")
    ap.add_argument("--subject", required=True, help="transparent-background subject PNG (produced by cutout.py)")
    ap.add_argument("--preset", default="azure-gold",
                    help="preset name: English slug (e.g. azure-gold) or Chinese name (e.g. 青金)")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--layout", default=None, choices=list(LAYOUTS.keys()))
    ap.add_argument("--focus", nargs=2, type=float, default=[0.5, 0.40],
                    help="background-window focus point (fractional coords in the original)")
    ap.add_argument("--chroma", type=float, default=0.55, help="duotone chroma retention 0-1")
    ap.add_argument("--wash", type=float, default=0.40, help="background-window wash toward paper colour 0-1 (higher = more like a faded print)")
    ap.add_argument("--bd-blur", type=float, default=10.0, help="background-window soft-focus radius (separates it from the sharp subject)")
    ap.add_argument("--bd-zoom", type=float, default=None, help="override the layout's background-window zoom")
    ap.add_argument("--subject-target", type=float, default=None,
                    help="override the layout's subject target size (fraction of canvas width/height; default from layout table)")
    ap.add_argument("--debug", default=None, help="draw the subject rect and text zone for visual inspection")
    ap.add_argument("--no-backdrop", action="store_true", help="do not place a background window (plain paper background, subject drops straight onto paper)")
    ap.add_argument("--bg-mode", choices=["window", "color"], default="window",
                    help="background treatment: window = original photo window (soft-focus + duotone); "
                         "color = extract main + secondary colour from original for a biased-gradient ground (no window)")
    ap.add_argument("--bg-color", default="auto",
                    help="color-mode main colour: auto = auto-extract, or #RRGGBB (secondary always extracted from original)")
    ap.add_argument("--bg-grad", choices=["diag", "up"], default="diag",
                    help="color-mode gradient direction: diag = diagonal from lower-right; up = vertical from bottom edge")
    ap.add_argument("--bg-vignette", type=float, default=0.0,
                    help="color-mode edge darkening 0-0.3 (focus the eye, lift the subject; not too large)")
    ap.add_argument("--bg-lift", type=float, default=0.0,
                    help="color-mode ground lift 0-0.4 (main/secondary V x (1+lift), hue/saturation unchanged)")
    ap.add_argument("--subject-pop", type=float, default=0.0,
                    help="subject saturation/contrast boost 0-0.5 (makes subject stand out on dark ground; 0.2-0.3 recommended)")
    ap.add_argument("--subject-paint", type=float, default=0.0,
                    help="subject repaint 0-1: denoise + saturation/lift boost + contrast + colour-layer quantisation (>=0.45 gives a hand-drawn block feel)")
    ap.add_argument("--subject-lift", type=float, default=0.0,
                    help="subject lift 0-0.4 (V x (1+lift), hue/saturation unchanged; pair with --subject-paint)")
    ap.add_argument("--shadow", type=float, default=0.0,
                    help="subject shadow strength 0-1 (0 = none; use 0.25-0.35 when subject/paper contrast is insufficient)")
    ap.add_argument("--shadow-blur", type=float, default=26.0, help="shadow blur radius (px)")
    ap.add_argument("--shadow-dy", type=float, default=20.0, help="shadow downward shift (px)")
    ap.add_argument("--reflection", type=float, default=0.0,
                    help="subject reflection strength 0-1 (0 = none; a fading mineral-colour reflection at the paper's lower edge, adds depth to the base image)")
    ap.add_argument("--reflection-blur", type=float, default=28.0, help="reflection blur radius (px)")
    ap.add_argument("--paper", default=None, help="override paper colour (hex, e.g. #E8DCC0)")
    ap.add_argument("--list-layouts", action="store_true")
    a = ap.parse_args()

    if a.list_layouts:
        for k, v in LAYOUTS.items():
            print(f"{k:12s} {v['when']}")
        return 0

    presets = load_presets()["presets"]
    key, preset = resolve_preset(presets, a.preset)
    if preset is None:
        opts = " | ".join(f"{k} ({v.get('zh', '')})" for k, v in presets.items())
        print(f"unknown preset: {a.preset} (available: {opts})", file=sys.stderr)
        return 2
    preset = dict(preset)
    if a.paper:
        preset["paper"] = a.paper

    src = Image.open(a.source).convert("RGB")
    subj = Image.open(a.subject).convert("RGBA")
    m = subject_metrics(subj)
    sub_c = subj.crop(tuple(m["bbox"]))     # crop to subject bbox: same frame of reference as rect and checks

    layout = a.layout or pick_layout(m)
    spec = dict(LAYOUTS[layout])
    spec["subject"] = dict(spec["subject"])
    if a.subject_target:
        spec["subject"]["target"] = a.subject_target
    reason = spec["reason"] + (" (--layout override)" if a.layout else " (auto-selected)")

    scale = fit_scale(m["bbox"], spec["subject"])
    rect = subject_rect(m["bbox"], spec["subject"], scale)
    for _ in range(3):
        if rect[0] >= 0 and rect[1] >= 0 and rect[0] + rect[2] <= W and rect[1] + rect[3] <= H:
            break
        rect[0] = min(max(rect[0], 0), W - rect[2])
        rect[1] = min(max(rect[1], 0), H - rect[3])

    bd = dict(spec["backdrop"]) if spec.get("backdrop") else None
    if a.no_backdrop:
        bd = None
    base_col, second_col, palette_cols = None, None, []
    if a.bg_mode == "color":          # colour-fill mode: no background window, extract main + secondary colour for a biased-gradient ground
        bd = None
        base_col, second_col, palette_cols = extract_bg_color(src, a.bg_color, seed=a.seed)
        if a.bg_lift > 0:             # lift the whole ground (hue/saturation unchanged)
            base_col = _lift_rgb(base_col, a.bg_lift)
            second_col = _lift_rgb(second_col, a.bg_lift)
    if a.bd_zoom and bd:
        bd["zoom"] = a.bd_zoom
    text_zone = spec["text_zone"]
    if bd:
        bd_rgba, bd_pos, crop = build_backdrop(src, bd, preset, a.chroma, a.focus, a.wash, a.bd_blur)
    else:
        bd_rgba, bd_pos, crop = Image.new("RGBA", (1, 1), (0, 0, 0, 0)), (0, 0), []
    ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)

    tries = 0
    while ck["subject_text_overlap"] > 0.02 and tries < 4:      # shrink subject in 0.92 steps
        tries += 1
        scale *= 0.92
        rect = subject_rect(m["bbox"], spec["subject"], scale)
        ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)
    tries_bd = 0
    while bd and ck["backdrop_text_overlap"] > 0.02 and tries_bd < 4:  # shrink background window the same way
        tries_bd += 1
        bd["rx"] *= 0.92
        bd["ry"] *= 0.92
        bd_rgba, bd_pos, crop = build_backdrop(src, bd, preset, a.chroma, a.focus, a.wash, a.bd_blur)
        ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)
    while bd and ck["blank_ratio"] < 0.40 and tries_bd < 6:            # insufficient negative space -> shrink window again
        tries_bd += 1
        bd["rx"] *= 0.94
        bd["ry"] *= 0.94
        bd_rgba, bd_pos, crop = build_backdrop(src, bd, preset, a.chroma, a.focus, a.wash, a.bd_blur)
        ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)

    ck["pass"] = (ck["subject_text_overlap"] <= 0.02 and ck["backdrop_text_overlap"] <= 0.02
                  and ck["blank_ratio"] >= 0.40 and ck["subject_in_canvas"])

    # composite: ground (paper / extracted-colour ground) -> background window (multiply) ->
    # reflection/shadow -> subject (over)
    arr = (bg_ground(base_col, second_col, a.seed, grad=a.bg_grad, vignette=a.bg_vignette)
           if a.bg_mode == "color" else make_ground(preset, a.seed))
    composite(arr, bd_rgba, bd_pos, mode="multiply")
    sub_s = sub_c.resize((max(1, int(round(rect[2]))), max(1, int(round(rect[3])))), Image.LANCZOS)
    if a.subject_pop > 0:     # subject emphasis: light saturation/contrast boost (stands out more on dark ground)
        sub_s = pop_subject(sub_s, a.subject_pop)
    if a.subject_paint > 0:   # subject repaint: saturation/lift boost + quantisation (vivid feel of the reference poster)
        sub_s = paint_subject(sub_s, a.subject_paint)
    if a.subject_lift > 0:    # subject lift (hue/saturation unchanged)
        sub_s = lift_subject(sub_s, a.subject_lift)
    sx, sy = int(round(rect[0])), int(round(rect[1]))
    if a.reflection > 0:      # reflection: flip, compress and re-blur the subject, fading down — a mineral-colour band under the paper's lower edge
        rw, rh = sub_s.size
        rl = sub_s.transpose(Image.FLIP_TOP_BOTTOM).resize(
            (rw, max(1, int(rh * 0.24))), Image.LANCZOS).filter(ImageFilter.GaussianBlur(a.reflection_blur))
        ra = np.asarray(rl.getchannel("A"), np.float32) / 255.0
        ramp = np.linspace(1.0, 0.0, ra.shape[0], dtype=np.float32)[:, None]
        rl.putalpha(Image.fromarray((ra * ramp * a.reflection * 255.0).astype(np.uint8)))
        composite(arr, rl, (sx, int(round(sy + rect[3] - 4))), mode="over")
    if a.shadow > 0:          # shadow: blur and shift the subject alpha down, separating it from the paper (shadow first, then subject)
        sa = sub_s.getchannel("A").filter(ImageFilter.GaussianBlur(a.shadow_blur))
        sa = sa.point(lambda v: int(v * a.shadow))
        sh_rgb = Image.new("RGB", sub_s.size, (40, 33, 25))
        composite(arr, Image.merge("RGBA", (*sh_rgb.split(), sa)),
                  (sx, int(round(rect[1] + a.shadow_dy))), mode="over")
    composite(arr, sub_s, (sx, sy), mode="over")
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    if a.debug:
        dbg = out.copy()
        d = ImageDraw.Draw(dbg, "RGBA")
        if bd:
            d.rectangle([bd["cx"] * W - bd["rx"] * W, bd["cy"] * H - bd["ry"] * H,
                         bd["cx"] * W + bd["rx"] * W, bd["cy"] * H + bd["ry"] * H],
                        outline=(0, 120, 220, 255), width=4)
        d.rectangle([rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]],
                    outline=(220, 40, 40, 255), width=5)
        d.rectangle([text_zone[0] * W, text_zone[1] * H, text_zone[2] * W, text_zone[3] * H],
                    outline=(30, 160, 60, 255), width=5, fill=(30, 160, 60, 40))
        os.makedirs(os.path.dirname(os.path.abspath(a.debug)) or ".", exist_ok=True)
        dbg.save(a.debug)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    out.save(a.out)

    plan = {
        "layout": layout, "layout_reason": reason,
        "subject": {"aspect": round(m["aspect"], 3), "mass_cx": round(m["mass_cx"], 3),
                    "rect_px": [int(round(v)) for v in rect], "pop": a.subject_pop,
                    "paint": a.subject_paint, "lift": a.subject_lift},
        "backdrop": ({"shape": "lens", "cx": round(bd["cx"], 3), "cy": round(bd["cy"], 3),
                      "rx": round(bd["rx"], 3), "ry": round(bd["ry"], 3),
                      "zoom": bd["zoom"], "focus": a.focus, "crop_px": crop,
                      "chroma": a.chroma, "wash": a.wash, "blur": a.bd_blur}
                     if bd else {"shape": "none"}),
        "text_zone": text_zone,
        "checks": ck,
        "shadow": ({"strength": a.shadow, "blur": a.shadow_blur, "dy": a.shadow_dy}
                   if a.shadow > 0 else None),
        "reflection": ({"strength": a.reflection, "blur": a.reflection_blur}
                       if a.reflection > 0 else None),
        "paper": {"preset": key, "seed": a.seed, "color": preset["paper"]},
        "background": ({"mode": "color", "base": rgb_hex(base_col), "second": rgb_hex(second_col),
                       "grad": a.bg_grad, "vignette": a.bg_vignette, "lift": a.bg_lift,
                       "source_palette": palette_cols}
                       if a.bg_mode == "color" else {"mode": "window" if bd else "paper"}),
    }
    if a.plan:
        os.makedirs(os.path.dirname(os.path.abspath(a.plan)) or ".", exist_ok=True)
        with open(a.plan, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

    if a.bg_mode == "color":
        print(f"[compose] ground gradient {rgb_hex(base_col)} -> {rgb_hex(second_col)}"
              f"({'bottom-up' if a.bg_grad == 'up' else 'diagonal from lower-right'}"
              f"{', edge darkening %.2f' % a.bg_vignette if a.bg_vignette > 0 else ''}; "
              f"extracted clusters {' / '.join(palette_cols)})")
    print(f"[compose] {a.out}  layout={layout}  {reason}")
    print(f"[compose] checks={json.dumps(ck, ensure_ascii=False)}")
    return 0 if ck["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
