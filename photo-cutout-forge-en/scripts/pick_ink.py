#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""pick_ink.py -- take the "largest-area dark colour" from the image as the ink colour (requested by the boss on 2026-10-12)

Why it is needed
----------------
The default ink is a fixed #17130E (near-black). But when the image itself has a
dominant tone (here the mural is ultramarine / ochre / dark green), taking the ink
colour from the largest-area dark tone in the image is more harmonious -- the
boss's words: "add to the Skill a way to extract the largest-area dark colour from
the image and give the font a colour; it will be more harmonious."

Approach (three steps, no third-party libraries)
------------------------------------------------
1. Sort by luminance, take the darkest N% of pixels (--dark-pct, default 18%);
2. Build an 8x8x8 3D histogram over these dark pixels, take the heaviest bins for
   a weighted mean -- more stable than "direct averaging": direct averaging gets
   pulled grey by stray noise; the histogram takes the substantial cluster;
3. Fallback darkening: the sampled colour is often not dark enough (needs 4.5:1 on
   a light material), push the colour toward black by WCAG relative luminance
   until L <= --max-lum (default 0.045, ~ the common ceiling for CR 4.5:1).

Usage
----
  python pick_ink.py --image out\bg.png                       # print the two hex values directly
  python pick_ink.py --image out\bg.png --dark-pct 14 --json out\ink.json
  python pick_ink.py --image src\scene.png --region 0,0,1537,1100

Output: ink (primary ink colour), ink2 (secondary, lifted 12%, for taglines and the like)
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image


def rel_lum(rgb):
    """WCAG relative luminance (0..1); rgb is 0-255."""
    c = np.asarray(rgb, np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def darken_to(rgb, max_lum, keep_hue=True):
    """Push the colour toward black until relative luminance <= max_lum
    (preserve hue as much as possible: scale uniformly)."""
    rgb = np.asarray(rgb, np.float32)
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        cur = rgb * mid if keep_hue else rgb - (255 - rgb) * 0
        if rel_lum(np.clip(cur, 0, 255)) > max_lum:
            hi = mid
        else:
            lo = mid
    return np.clip(rgb * lo, 0, 255)


def main():
    ap = argparse.ArgumentParser(description="take the largest-area dark colour from the image as the ink colour")
    ap.add_argument("--image", required=True)
    ap.add_argument("--region", default="", help="only look at a region x0,y0,x1,y1 (default whole image)")
    ap.add_argument("--dark-pct", type=float, default=18.0,
                    help="percentage of darkest pixels to include in statistics (default 18%%; too large -> greyish, too small -> noisy)")
    ap.add_argument("--bins", type=int, default=8, help="histogram bins per dimension (default 8)")
    ap.add_argument("--top-bins", type=int, default=3, help="number of heaviest bins for the weighted mean (default 3)")
    ap.add_argument("--max-lum", type=float, default=0.045,
                    help="fallback: push the ink colour to relative luminance <= this value (default 0.045 ~ 4.5:1 ceiling)")
    ap.add_argument("--json", default=None, help="optional: write the result as JSON for run scripts to read")
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    if a.region:
        v = [int(q) for q in a.region.replace("，", ",").split(",")]
        im = im.crop((v[0], v[1], v[2], v[3]))
    im = im.resize((min(480, im.width), max(1, int(im.height * min(480, im.width) / im.width))), Image.LANCZOS)
    arr = np.asarray(im).astype(np.float32)
    lum = arr.mean(axis=2)
    thr = np.percentile(lum, a.dark_pct)
    dark = arr[lum <= thr]
    if dark.shape[0] < 50:
        print("too few dark pixels; raise --dark-pct", file=sys.stderr)
        return 2

    # 3D histogram -> heaviest bins
    b = max(2, a.bins)
    idx = np.clip((dark / 256.0 * b).astype(int), 0, b - 1)
    flat = idx[:, 0] * b * b + idx[:, 1] * b + idx[:, 2]
    cnt = np.bincount(flat, minlength=b ** 3)
    top = np.argsort(cnt)[::-1][:max(1, a.top_bins)]
    w = cnt[top].astype(np.float32)
    w = w / max(w.sum(), 1e-6)
    sel = np.isin(flat, top)
    dom = dark[sel].mean(axis=0)
    # Correct once more with the bin centre weighted (bin centre is more stable than the in-bin mean)
    centers = np.stack([(top // (b * b)), (top // b) % b, top % b], axis=1).astype(np.float32)
    center_rgb = (centers + 0.5) / b * 256.0
    dom = (center_rgb * w[:, None]).sum(axis=0) * 0.5 + dom * 0.5

    ink = darken_to(dom, a.max_lum)
    ink2 = np.clip(ink * 1.12 + 6, 0, 255)          # secondary: slightly lifted, still dark enough
    res = {"ink": "#%02X%02X%02X" % tuple(int(round(v)) for v in ink),
           "ink2": "#%02X%02X%02X" % tuple(int(round(v)) for v in ink2),
           "dominant_dark_raw": "#%02X%02X%02X" % tuple(int(round(v)) for v in dom),
           "ink_rel_lum": round(rel_lum(ink), 4),
           "ink2_rel_lum": round(rel_lum(ink2), 4),
           "dark_pixels": int(dark.shape[0])}
    print("[pick_ink] %s (dark portion %.0f%% | sampled %d pixels)" % (a.image, a.dark_pct, dark.shape[0]))
    print("        dominant dark colour (raw) %s  -> after fallback darkening ink=%s (L=%.4f) | ink2=%s (L=%.4f)"
          % (res["dominant_dark_raw"], res["ink"], res["ink_rel_lum"],
             res["ink2"], res["ink2_rel_lum"]))
    if a.json:
        d = os.path.dirname(os.path.abspath(a.json))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print("        written", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
