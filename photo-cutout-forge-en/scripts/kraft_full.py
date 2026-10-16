#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""kraft_full.py -- "full-bleed ground": the photo fills the whole canvas, with the material used as a paper
grain overlaid on top (the fourth shape-extraction route).

When to use
-----------
The first three routes all "open a hole" (horizontal band / vertical window / diagonal block). But references
06/07/10/11 (bamboo-weave art / Huizhou lantern / the beauty of intangible cultural heritage) take a different
path: **the photo fills the whole canvas directly**, with type pressed on top of it --
the lead's exact words: "make the poster fill as much as possible, like these ones".

This script does three things:
  ① **Photo fills** (cover scaling + framing offset; no cropping into the subject, no blank border)
  ② **Material as paper grain** (the material's high-frequency detail + low-frequency light/dark, overlaid via
     --overlay) -- the photo thus "takes in" the same paper/stone texture, speaking the same texture language
     as our other three routes
  ③ **Four-edge darkening + light colour grade** (--vignette/--tone) -- leaving a legible base for the type on top

Usage
-----
  python kraft_full.py --photo src\scene.png --material src\material.jpg `
      --out out\bg.png --focus 0.5,0.52 --overlay 0.45 --vignette 0.30 --tone 0.18

Dependencies: Pillow + numpy (reuses kraft_tear's material utilities)
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

import kraft_tear as kt
from torn_edge import noise2d

W, H = kt.W, kt.H


def parse_pair(s):
    a, b = s.split(",")
    return float(a), float(b)


def blur01(a01, r):
    im = Image.fromarray(np.clip(a01 * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser(description="Full-bleed ground (photo fills + material as paper grain + four-edge darkening)")
    ap.add_argument("--photo", required=True)
    ap.add_argument("--material", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--focus", default="0.5,0.5", help="Which point of the photo aligns to the canvas centre (0..1)")
    ap.add_argument("--scale", type=float, default=1.0, help="Scale further on top of cover (>1 = closer)")
    ap.add_argument("--overlay", type=float, default=0.45,
                    help="Strength of material as paper grain: 0 = photo as-is, 0.45 = clearly same-paper, 1 = almost swallowed by material")
    ap.add_argument("--material-gain", type=float, default=0.0, help="Material keep-original-colour gain (0 = recolour by dark/light ends)")
    ap.add_argument("--material-gamma", type=float, default=0.52, help="Material tonal gamma")
    ap.add_argument("--material-dark", default="185,170,153")
    ap.add_argument("--material-light", default="241,229,214")
    ap.add_argument("--tone", type=float, default=0.18, help="Overall colour shift toward the material tone (0 = no shift)")
    ap.add_argument("--vignette", type=float, default=0.30, help="Four-edge darkening (0 = none)")
    ap.add_argument("--vignette-gamma", type=float, default=2.2, help="Radial curve of the darkening (larger = hugs the edge more)")
    ap.add_argument("--scrim", default="",
                    help="★ Local darkening (text-area scrim), format like \"x0,y0,x1,y1,strength,featherpx;…\" (multiple blocks allowed)."
                         "With full-bleed ground the photo's light/dark is uncontrolled, so light type on a bright wall will inevitably fail -- "
                         "references 110/111 could hold light type only because that patch was already dark; "
                         "in this case the top-left curtain wall measured P95=158 (line luminance), light type CR was only 1.31, "
                         "and the brightest spot had to be pushed down to <=37 (≈sRGB 105) to reach 4.5:1.")
    ap.add_argument("--grain", type=float, default=0.22, help="Grain (0 = none)")
    ap.add_argument("--brightness", type=float, default=1.0)
    ap.add_argument("--contrast", type=float, default=1.0)
    a = ap.parse_args()

    # ---- ① Photo fills (cover + framing) ----
    ph = Image.open(a.photo).convert("RGB")
    pw, phh = ph.size
    sc = max(W / pw, H / phh) * a.scale
    pw2, ph2 = int(round(pw * sc)), int(round(phh * sc))
    ph2im = ph.resize((pw2, ph2), Image.LANCZOS)
    fx, fy = parse_pair(a.focus)
    ox = int(round(fx * pw2 - W / 2))
    oy = int(round(fy * ph2 - H / 2))
    ox = int(np.clip(ox, 0, max(0, pw2 - W)))
    oy = int(np.clip(oy, 0, max(0, ph2 - H)))
    img = np.asarray(ph2im.crop((ox, oy, ox + W, oy + H)), np.float32)
    print("[kraft_full] photo %dx%d -> cover ×%.3f -> %dx%d | framing (%d,%d) | fills %dx%d"
          % (pw, phh, sc, pw2, ph2, ox, oy, W, H))

    # ---- ② Material as paper grain ----
    if a.material and a.overlay > 0:
        if a.material_gain > 0:
            kraft = kt.photo_native(a.material, gain=a.material_gain, gamma=a.material_gamma)
        else:
            kraft = kt.photo_cover(a.material,
                                   dark=tuple(int(v) for v in a.material_dark.split(",")),
                                   light=tuple(int(v) for v in a.material_light.split(",")))
        lo = blur01(np.clip(kraft.mean(axis=2) / 255.0, 0, 1), 42)[..., None]      # low-frequency light/dark
        hi = kt.photo_detail(a.material)[..., None]                                # high-frequency detail
        lo = 0.80 + 0.40 * lo                                                       # swings around 1.0
        img = img * (1.0 - a.overlay) + (img * lo + hi * 1.6) * a.overlay
        print("       ② material paper grain overlay=%.2f | low-frequency light/dark + high-frequency detail both applied" % a.overlay)

    # ---- ③ Colour grade / darken / grain ----
    if a.tone > 0 and a.material:
        mean_mat = kraft.reshape(-1, 3).mean(axis=0)
        mean_img = img.reshape(-1, 3).mean(axis=0)
        img = img * (1.0 - a.tone) + (img - mean_img + mean_mat) * a.tone
        print("       ③ colour shift toward material tone tone=%.2f" % a.tone)
    if a.brightness != 1.0:
        img = img * a.brightness
    if a.contrast != 1.0:
        img = (img - 127.5) * a.contrast + 127.5
    if a.vignette > 0:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.414
        v = 1.0 - a.vignette * np.clip(r, 0, 1) ** a.vignette_gamma
        img = img * v[..., None]
        print("       ③ four-edge darkening vignette=%.2f (gamma %.1f)" % (a.vignette, a.vignette_gamma))

    # ---- ③b Text-area scrim: push down the base under the type ----
    if a.scrim:
        yy, xx = np.mgrid[0:H, 0:W]
        for k, part in enumerate(a.scrim.split(";")):
            part = part.strip()
            if not part:
                continue
            v = [float(t) for t in part.replace("，", ",").split(",")]
            x0, y0, x1, y1, strength = v[:5]
            feather = v[5] if len(v) > 5 else 80.0
            m = np.zeros((H, W), np.float32)
            m[int(max(0, y0)):int(min(H, y1)), int(max(0, x0)):int(min(W, x1))] = 1.0
            m = blur01(m, feather / 2.0)                 # feather -> no hard edge
            img = img * (1.0 - strength * m[..., None])
            print("       ③b scrim#%d  (%d,%d)-(%d,%d) strength %.2f feather %.0f"
                  % (k + 1, x0, y0, x1, y1, strength, feather))
    if a.grain > 0:
        g = noise2d(W, H, seed=11, octaves=4, base=10)[..., None]
        img = img * (1.0 + a.grain * 0.18 * g)

    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(a.out)
    arr = np.asarray(Image.open(a.out).convert("L")).astype(np.float32)
    print("       final luminance: mean %.0f | P5 %.0f | P95 %.0f" % (arr.mean(), np.percentile(arr, 5), np.percentile(arr, 95)))
    print("[kraft_full]", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
