#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""kraft_window.py -- "irregular vertical window": material fills the canvas, with an irregular vertical window cut to reveal the photo.

A third shape-extraction route, parallel to `kraft_photo.py` (horizontal tear band); added for case16 on 2026-10-11.

| route | mask semantics | visual effect | best for |
|---|---|---|---|
| `kraft_photo` | top/bottom edge of every **column** -> horizontal band | top / middle / bottom three sections | subject is wide and continuous; frame already split into top/bottom |
| `kraft_tear`  | same, window = cutout subject | same | subject has a concave outline |
| **`kraft_window`** | left/right edge of every **row** -> vertical window | **one irregular vertical patch** | **subject itself is a vertical mass** (display case + wall projection, standing figure, artefact...) |

Window alpha is taken straight from the mask (produced by `band_mask.py --orient v --shape vpatch`, already carrying fractal-noise irregular edges), then the photo is placed into the window via `--scale` / `--focus`, followed by **feathering + in-window shadow + bright rim** to avoid the false "pasted-on" edge.

Usage (case16 display case)
---------------------------
  python band_mask.py --w 1500 --h 1875 --orient v --shape vpatch --jitter 0.010 --out cut\win.png
  python kraft_window.py --win cut\win.png --photo src\scene.png --material src\material.jpg `
      --scale 2.13 --focus 0.617,0.5 --material-gamma 0.52 --out out\bg.png

Dependencies: Pillow + numpy
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

import kraft_tear as kt
from torn_edge import noise2d        # same scripts directory; reuses the 2D fractal noise

W, H = kt.W, kt.H


def parse_pair(s):
    a, b = s.split(",")
    return float(a), float(b)


def blur01(a01, r):
    """Gaussian blur on a 0..1 float image (via uint8, since PIL's F mode does not support GaussianBlur)."""
    if r <= 0:
        return a01
    im = Image.fromarray(np.clip(a01 * 255.0, 0, 255).astype(np.uint8))
    im = im.filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser(description="Irregular vertical window (material fills, photo shown through window)")
    ap.add_argument("--win", required=True, help="Window mask (RGBA; alpha>0.45 counts as inside the window)")
    ap.add_argument("--photo", required=True, help="Original photo (placed into the window)")
    ap.add_argument("--material", default="", help="Material source photo (rock wall / earth wall / paper...)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=2.0, help="Photo enlargement factor (canvas px / photo px)")
    ap.add_argument("--focus", default="0.5,0.5", help="Which point of the photo aligns to the window centroid (0..1 relative coords)")
    ap.add_argument("--feather", type=float, default=2.4, help="Window edge feather radius in px")
    ap.add_argument("--shadow", type=float, default=0.30, help="In-hole shadow strength (material cast onto the photo)")
    ap.add_argument("--rim", type=float, default=0.16, help="Outer bright rim strength (torn-edge fibre catching light)")
    # ---- texture trio (added 2026-10-11: lead feedback "cutout lacks texture") ----
    ap.add_argument("--seam", type=float, default=0.42,
                    help="Paper-thickness dark line: a thin dark ring hugging the edge (makes the material 'press' onto the photo, default 0.42)")
    ap.add_argument("--fiber", type=float, default=0.55,
                    help="Fibre overlap: material's high-frequency detail laid over the photo along the edge (default 0.55)")
    ap.add_argument("--grain", type=float, default=0.30,
                    help="Same-paper grain: let the photo take in the material's grain and colour (0 = photo pasted flat as-is, default 0.30)")
    ap.add_argument("--photo-lift", type=float, default=0.0, help="Window content lift amount (0..1; for dark material try 0.06)")
    ap.add_argument("--material-gain", type=float, default=0.0, help="Keep material's original colour: overall gain (0 = recolour via --material-dark/light)")
    ap.add_argument("--material-gamma", type=float, default=1.0, help="Material tonal gamma")
    ap.add_argument("--material-dark", default="185,170,153", help="Recolour dark end R,G,B")
    ap.add_argument("--material-light", default="241,229,214", help="Recolour light end R,G,B")
    ap.add_argument("--detail", type=float, default=0.06, help="Material detail (cracks / grain) strength")
    ap.add_argument("--plate", default="", help="Legibility plate (optional, overlaid on the text area; leave empty to skip)")
    a = ap.parse_args()

    # ---- 1) Material fills the canvas ----
    if a.material:
        if a.material_gain > 0 or a.material_gamma != 1.0:
            kraft = kt.photo_native(a.material,
                                    gain=a.material_gain if a.material_gain > 0 else 1.0,
                                    gamma=a.material_gamma) \
                + kt.photo_detail(a.material)[..., None] * a.detail
        else:
            kraft = kt.photo_cover(a.material,
                                   dark=tuple(int(v) for v in a.material_dark.split(",")),
                                   light=tuple(int(v) for v in a.material_light.split(","))) \
                + kt.photo_detail(a.material)[..., None] * a.detail
    else:
        # With no material, fall back to plain paper
        kraft = np.full((H, W, 3), 232.0, np.float32) \
            + np.random.default_rng(3).normal(0, 3.0, (H, W, 1)).astype(np.float32)
    canvas = kraft.copy()

    # ---- 2) Window alpha ----
    # ★ 2026-10-11: changed to **keep continuous alpha** (no longer a 0/1 hard cut) —
    #   the fibre fray produced by `torn_edge.py` lives in the 0.3–0.9 transition band,
    #   and the previous `> 0.45` binarisation discarded it entirely, so "no texture".
    wm = Image.open(a.win).convert("RGBA")
    if wm.size != (W, H):
        wm = wm.resize((W, H), Image.LANCZOS)
    a_soft = np.asarray(wm)[..., 3].astype(np.float32) / 255.0    # continuous
    a0 = (a_soft > 0.45).astype(np.float32)                       # used only for stats / centroid
    ys, xs = np.nonzero(a0)
    if ys.size == 0:
        print("Window mask is empty", file=sys.stderr)
        return 2
    cx, cy = float(xs.mean()), float(ys.mean())
    wmax = np.abs(a0.sum(axis=1)).max()      # max row width of window
    hspan = ys.max() - ys.min()
    print("[kraft_window] window centroid (%.0f, %.0f) | bbox %.0f×%.0f px | max row width %.0f"
          % (cx, cy, xs.max() - xs.min(), hspan, wmax))

    # ---- 3) Photo placement ----
    ph = Image.open(a.photo).convert("RGB")
    pw, phh = ph.size
    sc = a.scale
    ph2 = ph.resize((max(1, int(round(pw * sc))), max(1, int(round(phh * sc)))), Image.LANCZOS)
    pa = np.asarray(ph2, np.float32)
    fx, fy = parse_pair(a.focus)
    ox = int(round(cx - fx * pw * sc))
    oy = int(round(cy - fy * phh * sc))
    # Out-of-bounds areas use **edge clamping** (not black fill) — when the photo is shorter/narrower
    # than the window, the window edges won't show a black border; the outermost ring of pixels is just
    # extended (barely visible on dark material).
    # ⚠ Coordinate note: pa is the **already-scaled** photo, so canvas coords subtract the placement point
    #   directly (do NOT divide by scale again, or it shrinks a second time and the window shows a different
    #   region of the photo — case16 hit exactly this on the first try).
    photo = np.zeros((H, W, 3), np.float32)
    sx = np.clip(np.arange(W) - ox, 0, pa.shape[1] - 1)
    for yy in range(H):
        sy2 = int(np.clip(yy - oy, 0, pa.shape[0] - 1))
        photo[yy] = pa[sy2][sx]
    print("       photo %dx%d | scale %.3f -> %dx%d | placement (%d, %d)"
          % (pw, phh, sc, ph2.size[0], ph2.size[1], ox, oy))
    if a.photo_lift > 0:
        photo = photo + (255.0 - photo) * a.photo_lift

    # ---- 4) Composite: feathered window (uses **continuous alpha**, so the fray is preserved) ----
    af = blur01(a_soft, a.feather)
    canvas = canvas * (1.0 - af[..., None]) + photo * af[..., None]

    # ---- 4.5) ★ Texture trio (added 2026-10-11) ----
    # ① paper-thickness dark line: a thin dark ring hugging the edge — the material looks "pressed" onto
    #    the photo rather than pieced with it
    if a.seam > 0:
        tight = np.clip(a_soft - blur01(a_soft, 2.0), 0, 1)
        canvas = canvas * (1.0 - tight[..., None] * a.seam) \
            + kt.SHADE[None, None, :] * (tight[..., None] * a.seam)
        print("       ① paper-thickness dark line seam=%.2f" % a.seam)
    # ② fibre overlap: material's high-frequency detail laid over the photo along the edge (most visible at the fray)
    if a.fiber > 0:
        det = kt.photo_detail(a.material)[..., None] if a.material else 0.0
        fib = blur01(a_soft, 1.6) * (1.0 - a_soft)          # only on the outer ring of the edge
        canvas = canvas + (det * a.fiber) * fib[..., None]
        print("       ② fibre overlap fiber=%.2f" % a.fiber)
    # ③ same-paper grain: let the **photo inside the window** take in the material's low-frequency
    #    light/dark plus a fine grain, so it reads as "printed on the same sheet" rather than "a pasted-on image".
    if a.grain > 0:
        win = af[..., None]
        g = (0.5 + 0.5 * noise2d(W, H, seed=5, octaves=4, base=14))[..., None]     # 0..1 grain
        broad = blur01(np.clip(kraft.mean(axis=2) / 255.0, 0, 1), 40)[..., None] * 255.0
        canvas = canvas * (1 - 0.25 * a.grain * win) + broad * (0.25 * a.grain * win)
        canvas = canvas * (1 - 0.18 * a.grain * g * win) + (canvas * (0.88 + 0.24 * g)) * (0.18 * a.grain * g * win)
        print("       ③ same-paper grain grain=%.2f" % a.grain)

    # ---- 5) In-hole shadow (material edge cast onto photo) + outer bright rim (fibre catching light) ----
    if a.shadow > 0:
        inner = np.clip(a0 - blur01(a0, max(3.0, a.feather * 3.0)), 0, 1)
        canvas = canvas * (1.0 - inner[..., None] * a.shadow) \
            + kt.SHADE[None, None, :] * (inner[..., None] * a.shadow)
    if a.rim > 0:
        outer = np.clip(blur01(a0, max(2.0, a.feather * 1.6)) - a0, 0, 1)
        canvas = canvas + outer[..., None] * (a.rim * 90.0)      # grey lift of the bright rim

    # ---- 6) Optional legibility plate ----
    if a.plate and os.path.exists(a.plate):
        pl = np.asarray(Image.open(a.plate).convert("RGB").resize((W, H), Image.LANCZOS), np.float32)
        plm = np.asarray(Image.open(a.plate).convert("RGBA").resize((W, H), Image.LANCZOS), np.float32)[..., 3] / 255.0
        canvas = canvas * (1 - plm[..., None]) + pl * plm[..., None]

    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(a.out)
    print("[kraft_window]", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
