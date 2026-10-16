#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
band_mask.py — generates the "tear-line band" mask (an alpha band image the same
size as the photo).

The tear line = the top/bottom edges of this band x k (kraft_tear / kraft_photo
compress it internally). So **the shape of this band directly decides what the
tear looks like**, and therefore how the image gets split into pieces.

Two typical shapes
------------------
  flat   "single straight band" — the top and bottom edges are nearly straight,
          with a slight arch. Stable and clean; but **it easily slices the image
          into top/middle/bottom thirds**, which feels mechanical.

  pinch  "centre pinched in, ends flared out" — the top edge dips in the middle,
          the bottom edge arches up in the middle; the band height forms a
          dumbbell. **The centre seam is narrow and the ends are wide**, giving
          the exposed content room to breathe and more sense of depth.

WARNING **Naturalness** (added after the 2026-10-11 feedback)
  Feeding only "centre-dip" control points yields a **left-right symmetric smooth
  arc** — it looks drawn, not torn (the lead's words: "this dumbbell shape is too
  regular, it has no natural feel"). A real tear has three traits: **asymmetric,
  multi-scale undulation, finely broken edges**. So this script layers **1D
  fractal noise** on top of the base curve (`--jitter`, multiple octaves,
  different seeds for the top/bottom edges), then leaves the final bit of fray to
  the built-in random tear inside kraft_photo.

WARNING Both the shape and the naturalness must be **analysed per source image** —
  you do not have to use pinch every time:
  - subject runs horizontally and the image already has top/bottom zones -> `flat` is tidier
  - subject is arched / embracing, or you want to break the thirds feel -> `pinch` adds depth
  - see references/kraft-tear.md "section 1.6 tear shaping"

Usage
-----
  # preset (pinch already = asymmetric base + fractal noise)
  python band_mask.py --w 1537 --h 1920 --shape pinch --jitter 0.012 --seed 7 --out cut\mask.png

  # fully custom control points (evenly spaced along the width; values are fractions of canvas height)
  python band_mask.py --w 1537 --h 1920 `
      --top "0.270,0.335,0.355,0.325,0.275" `
      --bottom "0.600,0.540,0.508,0.528,0.592" --jitter 0.010 --out cut\mask.png

Dependencies: Pillow + numpy
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

# Preset control points (fractions of canvas height, evenly spaced along the width)
PRESETS = {
    # single straight band: read off Dunhuang case13 (undulation only 26/42 px)
    "flat":  {"top":    [0.292, 0.277, 0.292],
              "bottom": [0.556, 0.532, 0.556]},
    # centre pinched, ends flared: 7 points; top and bottom edges are **deliberately
    # different** (avoids the dead feel of mirror symmetry).
    # The whole band sits high: the centre-seam bottom edge leaves enough lower
    # material area for type (left-text layout needs ~470 px of clean type height).
    "pinch": {"top":    [0.252, 0.290, 0.322, 0.332, 0.310, 0.275, 0.258],
              "bottom": [0.552, 0.524, 0.490, 0.476, 0.498, 0.530, 0.546]},
}

# ---- Vertical (--orient v) -------------------------------------------------
# Control points become "fractions of canvas **width**", distributed along the
# **height**; left / right are the window's left/right edges.
VPRESETS = {
    # vertical irregular window (vpatch): the window hugs the left-centre of the
    # image, with uneven width and deliberately different left/right edge shapes.
    # For material where "the subject is a vertical clump" (display case + its
    # reflection on the wall, standing figure, vessel ...), echoing the reference
    # poster's feel of "an irregular mural patch". Case: case16 display case.
    "vpatch": {"left":  [0.105, 0.088, 0.115, 0.096, 0.126, 0.100, 0.140],
               "right": [0.470, 0.492, 0.455, 0.500, 0.468, 0.486, 0.520]},
}

# ---- Diagonal (--rotate, added after 2026-10-11 feedback) -------------------
# "An axis-aligned rectangle placed in a poster looks ridiculous" — the impact of
# the reference poster comes from **one irregular diagonal band running from the
# upper-right to the lower-left** that splits the whole poster in two. Approach:
# first generate a horizontal band on an **enlarged square canvas**, then rotate
# the whole thing (PIL positive = counter-clockwise), finally centre-crop back to
# W x H.
# WARNING The band thickness is given as a fraction of the **enlarged canvas D**
#   (D = canvas diagonal length), NOT of W.
DPRESETS = {
    # diagonal band (a horizontal band rotated into a "/" — upper-right to lower-left)
    "diag": {"top":    [0.300, 0.268, 0.336, 0.296, 0.352, 0.286, 0.318],
             "bottom": [0.706, 0.742, 0.664, 0.716, 0.648, 0.752, 0.690]},
    # a thicker, more aggressive-edged version (occupies more of the image; the
    # reference poster's "split" feel is stronger)
    "diag-thick": {"top":    [0.238, 0.214, 0.286, 0.240, 0.302, 0.228, 0.262],
                   "bottom": [0.772, 0.806, 0.712, 0.776, 0.700, 0.812, 0.740]},
    # NOTE ends-wide, waist-pinched diagonal block (added after the lead's second
    #   2026-10-11 feedback): the reference poster's image is not an equal-width
    #   band but "a big block at upper-right -> pinched in the middle -> a big
    #   block at lower-left", leaving the centre as paper for the title. After
    #   rotation you get a "diagonal hourglass", with the two corners taken by the
    #   image and the centre free for type.
    #   Waist width pinned by measurement: **0.62D too wide** (covers 56.5%, no
    #   centre paper); **0.10D just right** (covers 39.2%, each of upper-left and
    #   lower-right gets a block of paper).
    "diag-pinch": {"top":    [0.190, 0.280, 0.410, 0.450, 0.400, 0.290, 0.180],
                   "bottom": [0.810, 0.720, 0.590, 0.550, 0.600, 0.710, 0.820]},
    # NOTE break-symmetry version (added after the lead's second 2026-10-11
    #   feedback): the previous `diag-pinch` had top/bottom edges as **mirror
    #   images** (bottom = 1 - top: 0.19/0.81, 0.28/0.72 ...), yielding a
    #   **centre-symmetric hourglass** — the lead: "the cutout is too centre
    #   symmetric, the pattern can be a bit more irregular". Break symmetry in
    #   three places together:
    #     1. **off-centre waist**: the thinnest point is not centred (thickness
    #        0.075 at 3/6, 0.165 at 2/6)
    #     2. **unequal ends**: left end 0.755 / right end 0.640 (no longer symmetric)
    #     3. **different waist depth**: top edge dips to 0.470, bottom edge arches
    #        to 0.545 (shallower arch)
    #   Plus `--jitter 0.014` (coarser than the usual 0.010) + a non-integer angle
    #   (e.g. 34 deg) to further de-regularise.
    "diag-rag": {"top":    [0.140, 0.300, 0.400, 0.445, 0.345, 0.235, 0.205],
                 "bottom": [0.895, 0.680, 0.565, 0.570, 0.660, 0.790, 0.845]},
}


def parse_pts(s):
    return [float(v) for v in s.replace("，", ",").split(",") if v.strip() != ""]


def smooth1d(arr, k):
    """Moving average (np.convolve; PIL's F mode has no GaussianBlur, do not use)."""
    k = int(k) | 1
    if k <= 1:
        return np.asarray(arr, np.float32)
    a = np.pad(np.asarray(arr, np.float32), k // 2, mode="edge")
    return np.convolve(a, np.ones(k, np.float32) / k, mode="valid")


def fractal_noise(n, seed=0, octaves=5, persist=0.52):
    """1D fractal noise (multiple octaves summed, range roughly +/-1).

    Used to add **multi-scale undulation** to the tear: low frequency gives the
    big wave, high frequency gives the fine fray. Pure sine or pure white noise
    both look wrong — the roughness of torn paper is "a little at every scale".
    """
    rng = np.random.default_rng(seed)
    out = np.zeros(n, np.float32)
    amp, total = 1.0, 0.0
    step = max(4, n // 5)                 # lowest frequency
    while octaves > 0 and step >= 2:
        k = max(2, n // step + 1)
        pts = rng.normal(0.0, 1.0, k)
        layer = np.interp(np.arange(n), np.linspace(0, n - 1, k), pts)
        layer = smooth1d(layer, step)
        out += layer * amp
        total += amp
        amp *= persist
        step = max(2, step // 2)
        octaves -= 1
    return out / max(total, 1e-6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, required=True, help="output width (= photo width)")
    ap.add_argument("--h", type=int, required=True, help="output height (= photo height)")
    ap.add_argument("--orient", default="h", choices=["h", "v"],
                    help="shape orientation: h = horizontal tear band (top/bottom edges per column) "
                         "/ v = **vertical irregular window** (left/right edges per row)")
    ap.add_argument("--shape", default=None, help="preset: h -> flat/pinch; v -> vpatch")
    ap.add_argument("--top", default=None, help="top edge (h) or **left edge** (v) control points, comma-separated")
    ap.add_argument("--bottom", default=None, help="bottom edge (h) or **right edge** (v) control points, comma-separated")
    ap.add_argument("--left", default=None, help="v only: left-edge control points (= alias of --top)")
    ap.add_argument("--right", default=None, help="v only: right-edge control points (= alias of --bottom)")
    ap.add_argument("--yspan", default=None,
                    help="v only: window's vertical span 'start,end' (fraction of canvas height, e.g. "
                         "0.26,0.76); omitted = full height. The two ends also get an irregular closure "
                         "(see --end-jitter)")
    ap.add_argument("--end-jitter", type=float, default=0.022,
                    help="v only: irregular amount of the window's **top/bottom** closure (fraction of canvas height)")
    ap.add_argument("--rotate", type=float, default=0.0,
                    help="rotate the whole shape by this many degrees (PIL positive = counter-clockwise). "
                         "When non-zero it is generated on a **square canvas of diagonal length** then "
                         "centre-cropped back to WxH — used to make a **diagonal irregular block running "
                         "from upper-right to lower-left** (pair with --shape diag / diag-thick)")
    ap.add_argument("--smooth", type=int, default=81, help="base curve smoothing kernel (px, odd)")
    ap.add_argument("--jitter", type=float, default=0.012,
                    help="fractal noise amount: h = fraction of canvas height; v = **fraction of canvas "
                         "width**. 0 = off, degenerates to a smooth arc")
    ap.add_argument("--seed", type=int, default=7, help="noise seed (sides use seed / seed+101)")
    ap.add_argument("--ink", default="58,42,30", help="fill colour (placeholder only; alpha is what is used)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    vertical = a.orient == "v"
    # diagonal mode: generate a horizontal band on a "square canvas of diagonal
    # length", then rotate + centre-crop back
    diagonal = abs(a.rotate) > 1e-6
    if a.shape is None:
        a.shape = "vpatch" if vertical else ("diag" if diagonal else "pinch")

    if diagonal:
        D = int(np.ceil(np.hypot(a.w, a.h))) + 4
        CW, CH = D, D                    # generation canvas
        table = DPRESETS
        vertical = False                 # diagonal always uses the horizontal-band mechanism (then rotated)
    else:
        CW, CH = a.w, a.h
        table = VPRESETS if vertical else PRESETS

    t_arg = a.left if (vertical and a.left) else a.top
    b_arg = a.right if (vertical and a.right) else a.bottom
    key = "left" if vertical else "top"
    key2 = "right" if vertical else "bottom"
    if a.shape not in table and not (t_arg and b_arg):
        print("unknown preset %s (available: %s)" % (a.shape, "/".join(sorted(table))), file=sys.stderr)
        return 2
    t_ctl = parse_pts(t_arg) if t_arg else table[a.shape][key]
    b_ctl = parse_pts(b_arg) if b_arg else table[a.shape][key2]
    if len(t_ctl) < 2 or len(t_ctl) != len(b_ctl):
        print("need >=2 control points and equal count on both sides", file=sys.stderr)
        return 2

    if vertical:
        # interpolate along height; control point values are "fractions of canvas
        # width"; noise amount computed from width
        span, along = CW, CH
        xs = np.linspace(0, CH - 1, CH)
        cx = np.linspace(0, CH - 1, len(t_ctl))
        amp_ref = CW
    else:
        span, along = CH, CW
        xs = np.linspace(0, CW - 1, CW)
        cx = np.linspace(0, CW - 1, len(t_ctl))
        amp_ref = CH

    t = smooth1d(np.interp(xs, cx, np.array(t_ctl, np.float32) * span), a.smooth)
    b = smooth1d(np.interp(xs, cx, np.array(b_ctl, np.float32) * span), a.smooth)

    if a.jitter > 0:
        amp = a.jitter * amp_ref
        t = t + fractal_noise(along, seed=a.seed) * amp           # different seeds on the two sides -> not mirrored
        b = b + fractal_noise(along, seed=a.seed + 101) * amp

    b = np.maximum(b, t + 12.0)                                   # curves must not cross

    m = np.zeros((CH, CW), np.uint8)
    if vertical:
        x0 = np.clip(np.round(t).astype(int), 0, CW - 1)
        x1 = np.clip(np.round(b).astype(int), 0, CW - 1)
        if a.yspan:
            ya, yb = [float(v) for v in a.yspan.replace("，", ",").split(",")]
            # WARNING bug fix 2026-10-13: with --yspan the old code iterated
            #   `for x in range(CW)` but indexed `x1[x]` (x0/x1 are indexed by
            #   **row** length CH, so they must be indexed by y) -> IndexError on
            #   a canvas wider than tall (1920x1080 landscape always crashes; the
            #   1500x1875 portrait survived only because CW=1500 < CH=1875).
            #   Correct semantics: window = "per-column x vertical range ytop[x]..ybot[x]"
            #   intersect "per-row y horizontal range x0[y]..x1[y]".
            ytop = ya * CH + fractal_noise(CW, seed=a.seed + 7) * (a.end_jitter * CH)
            ybot = yb * CH + fractal_noise(CW, seed=a.seed + 9) * (a.end_jitter * CH)
            x0f, x1f = x0.astype(np.float32), x1.astype(np.float32)
            for y in range(CH):
                if x1f[y] <= x0f[y]:
                    continue
                lo, hi = int(x0f[y]), int(x1f[y])
                # on this row, does column x's vertical range cover y
                cols = np.arange(lo, min(hi + 1, CW))
                if cols.size == 0:
                    continue
                ok = (ytop[cols] <= y) & (y <= ybot[cols])
                m[y, cols[ok]] = 255
        else:
            for y in range(CH):
                if x1[y] > x0[y]:
                    m[y, x0[y]:x1[y] + 1] = 255
    else:
        y0 = np.clip(np.round(t).astype(int), 0, CH - 1)
        y1 = np.clip(np.round(b).astype(int), 0, CH - 1)
        for x in range(CW):
            if y1[x] > y0[x]:
                m[y0[x]:y1[x] + 1, x] = 255

    # ---- diagonal: rotate then centre-crop back to W x H ----
    if diagonal:
        mi = Image.fromarray(m).rotate(a.rotate, resample=Image.BICUBIC, fillcolor=0)
        ma = np.asarray(mi)
        ox, oy = (CW - a.w) // 2, (CH - a.h) // 2
        m = (ma[oy:oy + a.h, ox:ox + a.w] > 128).astype(np.uint8) * 255
        # prove the orientation with the four-corner coverage (print it, do not rely on the eye)
        q = min(a.w, a.h) // 4
        corners = {
            "top-left": m[:q, :q].mean() / 255, "top-right": m[:q, -q:].mean() / 255,
            "bottom-left": m[-q:, :q].mean() / 255, "bottom-right": m[-q:, -q:].mean() / 255,
        }
        print("            corner coverage: " + "  ".join("%s %.0f%%" % (k, v * 100)
                                                          for k, v in corners.items())
              + " (diagonal band should be high at 'top-right / bottom-left')")

    fill = tuple(int(v) for v in a.ink.split(","))
    rgba = Image.new("RGB", (a.w, a.h), fill).convert("RGBA")
    rgba.putalpha(Image.fromarray(m))
    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    rgba.save(a.out)

    band = b - t
    q = along // 4
    asym_t = abs((t[q] - t[0]) - (t[along - 1 - q] - t[along - 1]))   # >0 means not mirrored
    asym_b = abs((b[q] - b[0]) - (b[along - 1 - q] - b[along - 1]))
    orient_name = "diagonal irregular block" if diagonal else ("vertical window" if vertical else "horizontal tear band")
    print("[band_mask] %s  %dx%d  %s  shape=%s  jitter=%.3f seed=%d %s"
          % (a.out, a.w, a.h, orient_name, a.shape if not t_arg else "custom", a.jitter, a.seed,
             "" if a.jitter > 0 else " (no noise = smooth arc)"))
    print("            band width: left %.0f | 1/4 %.0f | mid %.0f | 3/4 %.0f | right %.0f px"
          % (band[0], band[q], band[along // 2], band[3 * q], band[-1]))
    print("            %s %.0f->%.0f->%.0f | %s %.0f->%.0f->%.0f | asymmetry %.0f/%.0f px"
          % ("left edge" if vertical else "top edge", t[0], t[along // 2], t[-1],
             "right edge" if vertical else "bottom edge", b[0], b[along // 2], b[-1], asym_t, asym_b))
    if diagonal:
        print("            rotate %.1f deg (counter-clockwise positive) | canvas %dx%d -> centre-crop %dx%d"
              % (a.rotate, CW, CH, a.w, a.h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
