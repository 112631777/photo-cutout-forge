#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
cutout.py -- AI white-background source image to transparent-background subject PNG (alpha)

Step 2 of photo-cutout-forge: turn a "pure-white-background cutout source" into a
trustworthy transparent-background subject, to be placed on paper by
auto_compose.py. Only depends on PIL + numpy.

Pipeline: white-background source -> luminance-to-alpha formula -> despeckle
gating -> edge shrink / feather -> trim with negative space -> mode colouring

alpha formula (tested):
    a = clip((white - L) / (white - floor), 0, 1) ** gamma
    default white=255, floor=36, gamma=0.92.
    white can be auto-estimated from the median edge luminance via --auto-white
    (for cream-background sources such as flat duotone versions).

Modes:
    color   keep original colours (full-colour cutout source)
    ink     monochrome silhouette (--ink, default #2A231A)
    duotone preset-LUT flat colour + chroma preserved (--preset, default azure-gold)

Usage:
    python cutout.py --image cand\A.png --out cut\A.png --mode color --trim --pad 16
    python cutout.py --image cand\B.png --out cut\B.png --mode ink --trim --pad 16
    python cutout.py --image cand\C.png --out cut\C.png --mode color --auto-white --trim
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS_PATH = os.path.join(HERE, "..", "assets", "presets.json")

# Despeckle gating parameters
SPEC_THRESH = 0.28   # Binarisation threshold: below it is treated as background
SPEC_STRONG = 0.55   # Strong-signal threshold: above it is kept unconditionally (protects thin/delicate structures)


def rgb_of(hx):
    return np.array([int(hx[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


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
    """Four-segment LUT: luminance to dark/mid/light/paper (matches auto_compose's duotone)."""
    shadow, mid, light = rgb_of(preset["shadow"]), rgb_of(preset["mid"]), rgb_of(preset["light"])
    paper = rgb_of(preset["paper"])
    top = paper * 0.5 + np.array([255.0, 255.0, 248.0], np.float32) * 0.5
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
                u = min(1.0, max(0.0, u))
                c = c0 * (1.0 - u) + c1 * u
                break
        lut.extend(int(round(float(v))) for v in c)
    return lut


def auto_white(img):
    """Estimate background luminance (median) from the edge bands on all four
    sides: for cream-background sources (e.g. flat duotone versions)."""
    a = np.asarray(img.convert("L"), np.float32)
    h, w = a.shape
    m = max(2, int(round(min(h, w) * 0.03)))
    edge = np.concatenate([a[:m].ravel(), a[-m:].ravel(), a[:, :m].ravel(), a[:, -m:].ravel()])
    return float(np.median(edge))


def alpha_from_luma(img, white, floor, gamma):
    L = np.asarray(img.convert("L"), np.float32)
    a = np.clip((white - L) / max(1.0, white - floor), 0.0, 1.0) ** gamma
    return a


def despeckle(a, k):
    """Despeckle gating: opening removes small speckles; strong-signal areas are
    kept unconditionally (protects fine stripes / sheer fabric).

    gate = open(bin(a>SPEC_THRESH), k) ∪ bin(a>SPEC_STRONG)
    """
    if k <= 1:
        return a
    b = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    spec = b.point(lambda v: 255 if v >= SPEC_THRESH * 255 else 0)
    strong = b.point(lambda v: 255 if v >= SPEC_STRONG * 255 else 0)
    gate = spec.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    gate = Image.fromarray(np.maximum(np.asarray(gate), np.asarray(strong)))
    return a * (np.asarray(gate, np.float32) / 255.0)


def apply_mode(img, a, mode, ink, preset, preset_name=None):
    if mode == "color":
        return img.convert("RGB")
    if mode == "ink":
        col = rgb_of(ink)
        arr = np.tile(col, (img.size[1], img.size[0], 1)).astype(np.float32)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if mode == "duotone":
        if preset_name is None:
            raise ValueError("duotone mode requires --preset")
        _, pentry = resolve_preset(preset["presets"], preset_name)
        if pentry is None:
            raise ValueError(f"unknown preset: {preset_name}")
        duo = np.asarray(img.point(build_lut(pentry)), np.float32)
        hsv = img.convert("HSV")
        sat = np.asarray(hsv.getchannel("S"), np.float32) / 255.0
        g = np.asarray(img.convert("L"), np.float32) / 255.0
        w = (0.45 * np.clip(sat * 2.2, 0.0, 1.0) * np.clip(1.5 - 1.1 * g, 0.2, 1.0))[..., None]
        orig = np.asarray(img, np.float32)
        mixed = duo * (1.0 - w) + orig * w
        gray = mixed.mean(axis=2, keepdims=True)
        mixed = gray + (mixed - gray) * 1.12
        return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8))
    raise ValueError(f"unknown mode: {mode}")


def main():
    ap = argparse.ArgumentParser(description="White-background source to transparent-background subject PNG")
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="color", choices=["color", "ink", "duotone"])
    ap.add_argument("--ink", default="#2A231A", help="ink-mode silhouette colour")
    ap.add_argument("--preset", default="azure-gold", help="duotone-mode preset name (English slug or Chinese name)")
    ap.add_argument("--white", type=float, default=255.0, help="background luminance reference (pure white = 255)")
    ap.add_argument("--auto-white", action="store_true", help="auto-estimate background luminance from the edge bands")
    ap.add_argument("--floor", type=float, default=36.0, help="luminance floor for fully opaque areas")
    ap.add_argument("--gamma", type=float, default=0.92)
    ap.add_argument("--shrink", type=int, default=0, help="edge-shrink pixels (removes white fringe; 1-2 typical)")
    ap.add_argument("--feather", type=float, default=0.8, help="feather radius (0 disables)")
    ap.add_argument("--despeckle", type=int, default=5, help="despeckle gating kernel size (0 disables)")
    ap.add_argument("--trim", action="store_true", help="crop to the subject bounding box")
    ap.add_argument("--pad", type=int, default=16, help="transparent margin kept after cropping")
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    white = auto_white(img) if a.auto_white else a.white
    alpha = alpha_from_luma(img, white, a.floor, a.gamma)
    alpha = despeckle(alpha, a.despeckle)

    alpha_img = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8))
    if a.shrink > 0:
        k = a.shrink * 2 + 1
        alpha_img = alpha_img.filter(ImageFilter.MinFilter(k))
    if a.feather > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(a.feather))

    rgb = apply_mode(img, alpha, a.mode, a.ink, load_presets(), a.preset)
    out = rgb.convert("RGBA")
    out.putalpha(alpha_img)

    if a.trim:
        arr = np.asarray(alpha_img, np.float32)
        ys, xs = np.where(arr > 6.0)
        if len(xs):
            p = a.pad
            box = (max(0, int(xs.min()) - p), max(0, int(ys.min()) - p),
                   min(out.size[0], int(xs.max()) + 1 + p), min(out.size[1], int(ys.max()) + 1 + p))
            out = out.crop(box)

    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    out.save(a.out)

    ov = float((np.asarray(out.getchannel("A"), np.float32) > 128).mean())
    print(f"[cutout] {a.out}  {out.size[0]}x{out.size[1]}  mode={a.mode}  "
          f"white={white:.0f} floor={a.floor:.0f}  subject ratio={ov:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
