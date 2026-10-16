#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""torn_edge.py -- turn a "smooth shape" into a **2D torn edge** (multi-scale + bite marks + fibre fray)

Why it is needed (2026-10-11 lead feedback)
-------------------------------------------
`band_mask.py`'s shape extraction is **1D extrusion**: a horizontal band is "one top/bottom edge per column",
a vertical window is "one left/right edge per row". Even with `--jitter` fractal noise, it is essentially
**one smooth curve + jitter** — zoomed in it looks "cut with a wavy knife", not "torn".
The lead's exact words: "the cutout motif is still too regular, it lacks a natural feel".

A real torn edge is irregular at **three scales** at once:

| scale | phenomenon | this script's approach |
|---|---|---|
| large (tens of px) | notches, bulges — the whole shape drifts | **2D fractal-noise displacement**: push the boundary along its normal by `--edge` ratio |
| medium (a few to tens of px) | chunks **bitten off** | `--bites` random circular bite marks (random sample centres along the boundary) |
| small (1–3 px) | **fibre fray**: semi-transparent filaments poking in/out | `--fray` high-frequency noise -> alpha lands in the 0.3–0.9 transition band |

⭐ Key: **keep continuous alpha** (no 0/1 binarisation) — `kraft_window.py` blends this fray into the photo,
so the paper's fibres really "cover" the image; this step is the source of "texture".

Usage
-----
  python torn_edge.py --mask cut\win.png --out cut\win.torn.png `
      --edge 0.016 --bites 9 --bite-size 0.055 --fray 0.22 --seed 3

  # For a more "torn" look: raise edge/bites/bite-size/fray together; for clean: lower them or set 0
Dependencies: Pillow + numpy
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter


# ---------------------------------------------------------------- utilities


def noise2d(w, h, seed=0, octaves=5, persist=0.55, base=8):
    """2D fractal value noise (multi-octave), range about -1..1.

    Method: each octave generates a small random grid, then bilinear-upscales it to the target size and
    adds it in — same origin as the 1D version in band_mask, but **different in 2D**,
    so the boundary gets pushed in every direction (that is "tearing" rather than "cutting").
    """
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total, step = 1.0, 0.0, max(3, base)
    while octaves > 0 and step >= 2:
        gw, gh = max(2, w // step + 1), max(2, h // step + 1)
        g = rng.normal(0.0, 1.0, (gh, gw)).astype(np.float32)
        layer = np.asarray(Image.fromarray(g, mode="F").resize((w, h), Image.BILINEAR), np.float32)
        out += layer * amp
        total += amp
        amp *= persist
        step = max(2, step // 2)
        octaves -= 1
    n = out / max(total, 1e-6)
    return np.clip(n / max(np.abs(n).max(), 1e-6), -1.0, 1.0)


def blur(a01, r):
    if r <= 0:
        return a01
    im = Image.fromarray(np.clip(a01 * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


# ---------------------------------------------------------------- main flow


def main():
    ap = argparse.ArgumentParser(description="Smooth shape -> 2D torn edge (multi-scale + bite marks + fray)")
    ap.add_argument("--mask", required=True, help="Input mask (RGBA, uses alpha)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--edge", type=float, default=0.018,
                    help="[large scale] boundary displacement magnitude (ratio of short canvas side, 0.01≈1%% of short side; default 0.018)")
    ap.add_argument("--edge-scale", type=float, default=26.0,
                    help="[large scale] smoothing radius of the displacement in px (larger = more 'bulge', smaller = more 'jagged')")
    ap.add_argument("--bites", type=int, default=8, help="[medium scale] number of bite marks (0 = none)")
    ap.add_argument("--bite-size", type=float, default=0.05,
                    help="[medium scale] bite radius (ratio of short canvas side)")
    ap.add_argument("--bite-depth", type=float, default=0.55,
                    help="[medium scale] distance of bite centre from the boundary (x radius; smaller = deeper bite)")
    ap.add_argument("--fray", type=float, default=0.55,
                    help="[small scale] fibre-fray strength (alpha jitter amplitude, 0 = hard edge; 0.5≈visible filaments)")
    ap.add_argument("--fray-px", type=float, default=3.0, help="Effective width of the fibre fray in px")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--plate", default="", help="Optional: also write the edge alpha back to this path (for debugging)")
    a = ap.parse_args()

    im = Image.open(a.mask).convert("RGBA")
    W, H = im.size
    arr = np.asarray(im).astype(np.float32)
    b = (arr[..., 3] > 127).astype(np.float32)          # binarised interior
    short = min(W, H)
    print("[torn_edge] %dx%d | edge %.3f (≈%.0fpx) bites %d×r%.0fpx fray %.2f"
          % (W, H, a.edge, a.edge * short, a.bites, a.bite_size * short, a.fray))

    # ---- ① Large scale: 2D fractal noise pushes the boundary along its normal ----
    # blur builds a 0..1 ramp near the boundary; after adding noise we re-threshold at 0.5,
    # displacement ≈ noise amplitude × ramp width -> controlled by --edge / --edge-scale.
    # ⚠⚠ **Only allow flipping inside the boundary band**: the first version added noise to the whole image,
    #    so anywhere in the solid area where noise dropped below threshold, speckles were bitten out in the
    #    middle of the image (the real screenshot showed a row of white dots).
    if a.edge > 0:
        ramp = blur(b, a.edge_scale)
        band = np.abs(ramp - 0.5) < 0.34            # only inside the ramp band can edges flip
        n = noise2d(W, H, seed=a.seed, octaves=5, base=10)
        disp = (a.edge * short) / max(a.edge_scale, 1e-6)
        flipped = (ramp + n * disp > 0.5).astype(np.float32)
        b = np.where(band, flipped, b)
        print("            ① large-scale displacement (equivalent ±%.0fpx, only in ramp band)" % (a.edge * short))

    # ---- ② Medium scale: bite off a few chunks from the **outside** along the boundary ----
    # ⚠⚠ The bite centre MUST be placed on the **outside** (pushed along the outward normal by r×depth),
    #    so the bite connects to the outer edge and forms a concave notch; the first version put the centre
    #    on the boundary and offset it the wrong way, leaving **floating material discs** in the middle
    #    of the image (hit this pitfall in practice).
    if a.bites > 0:
        rb = blur(b, 3.0)
        gyy, gxx = np.gradient(rb)
        inner_edge = (b > 0.5) & (rb < 0.90)        # the ring hugging the inner side of the edge
        ys, xs = np.nonzero(inner_edge)
        if ys.size:
            rng = np.random.default_rng(a.seed + 17)
            yy, xx = np.mgrid[0:H, 0:W]
            done = 0
            for i in range(a.bites):
                k = int(rng.integers(0, ys.size))
                cy, cx = float(ys[k]), float(xs[k])
                r = a.bite_size * short * rng.uniform(0.55, 1.45)
                gy, gx = float(gyy[ys[k], xs[k]]), float(gxx[ys[k], xs[k]])
                norm = float(np.hypot(gy, gx)) + 1e-6
                # outward normal = -gradient direction (gradient points to the inner side where b grows)
                cy -= gy / norm * r * a.bite_depth * rng.uniform(0.5, 1.3)
                cx -= gx / norm * r * a.bite_depth * rng.uniform(0.5, 1.3)
                # ★ Use **random ellipses** (random aspect ratio and orientation) instead of perfect circles:
                #    perfect circles produce a row of identical notches, which just looks "too regular" (the first version did that).
                ang = rng.uniform(0.0, np.pi)
                ca, sa = float(np.cos(ang)), float(np.sin(ang))
                ra = r * rng.uniform(0.70, 1.55)
                rb2 = r * rng.uniform(0.40, 0.95)
                dx, dy = xx - cx, yy - cy
                u = (dx * ca + dy * sa) / ra
                v = (-dx * sa + dy * ca) / rb2
                m = (u * u + v * v) < 1.0
                if not m.any():
                    continue
                b[m] = 0.0
                done += 1
            print("            ② bite marks done (%d places, random ellipses, all bitten from outside)" % done)

    # ---- ③ Small scale: fibre fray (continuous alpha, no binarisation) ----
    if a.fray > 0:
        n_hi = noise2d(W, H, seed=a.seed + 41, octaves=3, persist=0.6, base=3)
        inside = blur(b, a.fray_px) * b                   # band decaying outward from inside
        outside = (1.0 - b) * blur(b, a.fray_px * 1.6)    # band decaying inward from outside
        a_final = np.clip(b + n_hi * a.fray * (inside - outside), 0.0, 1.0)
        print("            ③ fibre fray done (transition-band alpha 0.3–0.9)")
    else:
        a_final = b

    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = arr[..., 0], arr[..., 1], arr[..., 2]
    out[..., 3] = np.clip(a_final * 255.0, 0, 255).astype(np.uint8)
    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    Image.fromarray(out).save(a.out)

    inside_frac = float((a_final > 0.45).mean())
    fringe = float(((a_final > 0.15) & (a_final < 0.85)).mean())
    print("            coverage %.1f%% | transition band (fray) %.2f%% of pixels"
          % (inside_frac * 100, fringe * 100))
    print("[torn_edge]", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
