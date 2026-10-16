# -*- coding: utf-8 -*-
"""Glow for the lower-left text zone (legibility backing on a dark ground): softly lift the lower-left of the background to keep WCAG contrast (background first, type second).

Metric (do not change): the gain is back-solved from the WCAG linear luminance p5
inside the probe rectangle --
  g = (target / p5)^(1/2.4) - 1 + 0.005, target defaults to 0.26 (above the 4.5:1 threshold for near-black ink).
  Note p5 must be the linear luminance (0-1); using sRGB 0-255 gives a wrong gain (hit this in practice).

Glow shape (lower-left): m = ss((y-cy)/fy) * (1 - ss((x-cx)/fx)), ss is smoothstep;
  pairs with dark-ground ink: --ink near-black (case #171009), labels dark brown.

Usage (case): probe = four rectangles in the lower-left text zone; gain auto-computed (case measured p5 0.139 -> g 0.303)
  python textzone_glow.py --bg bg.kraft.png --out bg.glow.png `
      --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"
"""
import argparse
import os

import numpy as np
from PIL import Image


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def linear_lum(a):
    """a: (H,W,3) sRGB 0-255 -> WCAG linear relative luminance (H,W) 0-1."""
    a01 = a / 255.0
    lin = np.where(a01 <= 0.04045, a01 / 12.92, ((a01 + 0.055) / 1.055) ** 2.4)
    return lin @ np.array((0.2126, 0.7152, 0.0722), np.float32)


def main():
    ap = argparse.ArgumentParser(description="Glow for the lower-left text zone (legibility backing on a dark ground)")
    ap.add_argument("--bg", required=True, help="input background PNG")
    ap.add_argument("--out", required=True)
    ap.add_argument("--zones", default="", help="probe rectangles y0,y1,x0,x1 separated by semicolons (for measuring p5)")
    ap.add_argument("--target", type=float, default=0.26, help="target linear luminance (at p5)")
    ap.add_argument("--gain", type=float, default=None, help="manually override the gain")
    ap.add_argument("--cy", type=float, default=860.0, help="glow y start")
    ap.add_argument("--fy", type=float, default=300.0, help="y feather width")
    ap.add_argument("--cx", type=float, default=1060.0, help="glow x right bound")
    ap.add_argument("--fx", type=float, default=340.0, help="x feather width")
    args = ap.parse_args()

    im = Image.open(args.bg).convert("RGB")
    a = np.asarray(im, np.float32)
    H, W, _ = a.shape

    if args.gain is None:
        if not args.zones:
            ap.error("auto gain needs --zones (probe rectangles) or a manual --gain")
        L = linear_lum(a)
        p5 = min(float(np.percentile(L[y0:y1, x0:x1], 5))
                 for y0, y1, x0, x1 in (tuple(int(v) for v in z.split(",")) for z in args.zones.split(";")))
        gain = (args.target / p5) ** (1 / 2.4) - 1.0 + 0.005
        print(f"       p5(linear) {p5:.4f} | gain {gain:.3f}")
    else:
        gain = args.gain

    y = np.arange(H, dtype=np.float32)[:, None]
    x = np.arange(W, dtype=np.float32)[None, :]
    m = (smoothstep((y - args.cy) / args.fy) * (1.0 - smoothstep((x - args.cx) / args.fx))).astype(np.float32)
    b = a * (1.0 + gain * m[..., None])
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).save(args.out)
    print("[textzone_glow]", args.out)


if __name__ == "__main__":
    main()
