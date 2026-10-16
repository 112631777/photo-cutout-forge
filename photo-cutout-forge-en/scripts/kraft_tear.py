# -*- coding: utf-8 -*-
r"""Torn-material-layer renderer (route A): a full-bleed background material image
(rock wall / kraft paper or similar), torn along the subject's outline arc at the
top and bottom, with the subject revealed in the centre seam.

Input model (skill direction): one original image containing the subject
(--subject cutout version) + one material image (--material, e.g. a rock-wall
asset — the closer its tone/texture to the subject's environment, the better the
match) + a description of the subject (used for white-background candidate prompts,
see references\cutout-craft.md section 1; not handled by this script).

Visual model (order must not be swapped):
  full material layer -> subject drawn on the material (top edge hidden behind the
  upper material, bottom edge behind the lower material) -> light tear shadow ->
  upper material over (y <= e_top) -> lower material over (y >= e_bot) -> paper
  core white line + paper edge slight highlight

Tear geometry: tear baseline = subject outline arc x k (compression factor) + random
tear edge; edge auto-positioning: the paper edge must cover at least 20 px of the
subject (subject edge always hidden behind the material).

Two routes for the window content:
  A cutout subject (this script): --subject gives an RGBA cutout;
  B real photo (recommended, seamless inside the window): use kraft_photo.py.
  Note: when k<1 the tear arc is gentler than the outline, so material colour is
  inevitably sandwiched between the arc and the outline — to make the window
  "fully continuous" you must take route B.

Usage (case parameters as illustration; afterwards follow the master template for
type-setting + machine checks):
  python kraft_tear.py --subject ..\cut\A2c.png --material material\rock.sand.png `
      --zoom 1.45 --out bg.rock.a.png
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter

# Canvas size: default 1500x1875 (portrait, the historically finalised spec).
# NOTE added 2026-10-13: support overriding via the PF_W / PF_H environment
#   variables to fit non-0.8-ratio canvases (e.g. 16:9 landscape 1920x1080).
#   kraft_window / kraft_photo both read W/H from here, so just set the env vars
#   before calling this script; default behaviour is unchanged.
W = int(os.environ.get("PF_W", "1500"))
H = int(os.environ.get("PF_H", "1875"))
MATERIAL_DARK = (185, 170, 153)       # background material default dark-tone stop (rock.sand.png p2 end)
MATERIAL_LIGHT = (241, 229, 214)      # background material default light-tone stop (rock.sand.png p98 end)
SHADE = np.array((56, 45, 31), np.float32)
CORE = np.array((238, 230, 208), np.float32)


def parse_color(s):
    return tuple(int(v) for v in s.split(","))


def noise2(rng, h, w, sh, sw, blur=0.0):
    """Low-frequency noise field: sample at (sh,sw), upsample to (h,w), normalise to ~N(0,1)."""
    small = rng.normal(0.0, 1.0, (max(2, sh), max(2, sw))).astype(np.float32)
    u = np.clip(small * 40.0 + 128.0, 0, 255).astype(np.uint8)
    img = Image.fromarray(u).resize((w, h), Image.BICUBIC)
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    arr = (np.asarray(img, np.float32) - 128.0) / 40.0
    arr -= arr.mean()
    arr /= (arr.std() + 1e-6)
    return arr


def paper(rng, dark, light):
    """Procedural-texture safety net: low-contrast colour difference + fine mid-frequency
    + two-layer fine grain + vertical fibre + horizontal mesh + speckle (a crisp material feel)."""
    low = noise2(rng, H, W, H // 55, W // 55, 4)
    mid = noise2(rng, H, W, H // 18, W // 18, 0)
    g2 = noise2(rng, H, W, H // 2, W // 2, 0)
    grain = noise2(rng, H, W, H, W, 0)
    fibv = noise2(rng, H, W, H // 3, W, 0)
    fibh = noise2(rng, H, W, H, W // 4, 0)
    lum = np.clip(0.5 + (0.20 * low + 0.30 * mid + 0.16 * g2 + 0.12 * grain) * 0.44, 0, 1)
    d = np.array(dark, np.float32)
    l = np.array(light, np.float32)
    rgb = d[None, None, :] * (1 - lum[..., None]) + l[None, None, :] * lum[..., None]
    rgb += (fibv * 3.4 + fibh * 3.0 + g2 * 4.5 + grain * 8.5)[..., None]
    sp = rng.random((H, W)).astype(np.float32)
    rgb += np.where(sp < 0.00035, -26.0, 0.0)[..., None]
    rgb += np.where(sp > 0.99965, 22.0, 0.0)[..., None]
    return rgb


def _cover(path):
    """Material photo -> scale up uniformly to cover the canvas and centre-crop to (H,W)
    (mirror tiling was abandoned: it creates symmetric butterfly artefacts)."""
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    sc = max(W / sw, H / sh)
    im = im.resize((max(W, int(round(sw * sc))), max(H, int(round(sh * sc)))), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    y0, x0 = (a.shape[0] - H) // 2, (a.shape[1] - W) // 2
    return a[y0:y0 + H, x0:x0 + W]


def photo_cover(path, dark=MATERIAL_DARK, light=MATERIAL_LIGHT, flat_r=180.0):
    """Background material photo -> material layer (H,W,3) (recoloured version): cover + remove
    large-scale lighting + map onto the dark..light two-tone stops."""
    a = _cover(path)
    lum = a @ np.array((0.299, 0.587, 0.114), np.float32)
    blur = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(flat_r))
    lum = lum / (np.asarray(blur, np.float32) + 1e-6)          # remove large-scale lighting, keep folds / fibre
    lo, hi = np.percentile(lum, 2.0), np.percentile(lum, 98.0)
    t = np.clip((lum - lo) / (hi - lo + 1e-6), 0, 1)
    t = 0.5 + (t - 0.5) * 0.86                                  # suppress over-stretching, keep natural contrast
    d = np.array(dark, np.float32)
    l = np.array(light, np.float32)
    return d[None, None, :] * (1 - t[..., None]) + l[None, None, :] * t[..., None]


def photo_native(path, gain=1.0, gamma=1.0):
    """Background material photo -> material layer (H,W,3) (keep original colours): cover + tone curve
    (gamma<1 lifts shadows, protects highlights) + overall gain; no recolouring, no lighting
    removal — use it when the material already carries colour patches / cracks / mineral tints
    (e.g. weathered rock wall) so the original colour is preserved."""
    a = _cover(path)
    if gamma != 1.0:
        a = 255.0 * np.power(np.clip(a, 0, 255) / 255.0, gamma)
    return a * gain


def photo_detail(path, flat_r=16.0):
    """Material detail (high-pass): fibre + grain; after normalising, mirror-tile to the canvas
    (at detail scale the mirror seam is invisible)."""
    a = np.asarray(Image.open(path).convert("RGB"), np.float32)
    lum = a @ np.array((0.299, 0.587, 0.114), np.float32)
    blur = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(flat_r))
    hi = lum - np.asarray(blur, np.float32)
    hi /= (float(hi.std()) + 1e-6)
    sh, sw = hi.shape
    py, px = max(0, H - sh), max(0, W - sw)
    if py or px:
        hi = np.pad(hi, ((py // 2 + 1, py - py // 2 + 1), (px // 2 + 1, px - px // 2 + 1)), mode="reflect")
    y0, x0 = (hi.shape[0] - H) // 2, (hi.shape[1] - W) // 2
    return hi[y0:y0 + H, x0:x0 + W]


def tear(rng, amp=26.0, n_spike=6):
    """Tear-edge profile (length W): big wave + mid-scale undulation + high-frequency fine teeth
    + occasional fibre spikes."""
    big = np.convolve(rng.normal(0, 1, W).astype(np.float32), np.ones(220, np.float32) / 220, "same")
    big /= (np.abs(big).max() + 1e-6)
    t = np.convolve(rng.normal(0, 1, W).astype(np.float32), np.ones(48, np.float32) / 48, "same")
    t /= (np.abs(t).max() + 1e-6)
    prof = (big * amp * 0.75 + t * amp * 0.55).astype(np.float32)
    hi = np.convolve(rng.normal(0, 1, W).astype(np.float32), np.ones(5, np.float32) / 5, "same")
    prof += (hi * amp * 0.25).astype(np.float32)
    for _ in range(n_spike):
        i = int(rng.integers(10, W - 10))
        a, b = max(0, i - 7), min(W, i + 8)
        prof[a:b] += float(rng.normal(0, 1)) * amp * 1.4 * np.hanning(b - a).astype(np.float32)
    return prof


def feathered(mask):
    img = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    return np.asarray(img, np.float32) / 255.0


def paper_layer(rng, panel, edge, side, core_w=5.0):
    """Paper layer (with white core + slight paper-edge highlight): side='top' means paper is above
    edge; side='bot' means paper is below edge."""
    yy = np.arange(H, dtype=np.float32)[:, None]
    if side == "top":
        dc = np.clip(edge[None, :] - yy, 0, None)
        inside = (yy <= edge[None, :]).astype(np.float32)
    else:
        dc = np.clip(yy - edge[None, :], 0, None)
        inside = (yy >= edge[None, :]).astype(np.float32)
    core = np.clip(1 - dc / core_w, 0, 1) * inside
    rgb = panel * (1 - (core * 0.85)[..., None]) + CORE[None, None, :] * (core * 0.85)[..., None]
    glow = (np.clip(1 - dc / 9.0, 0, 1) * inside * 0.10)[..., None]
    rgb = rgb * (1 - glow) + np.array((255, 246, 228), np.float32)[None, None, :] * glow
    return rgb, feathered(inside)


def smooth1d(v, w):
    """1D moving average (edge padding), smoothing contour aliasing."""
    k = np.ones(w, np.float32) / w
    vp = np.pad(v, w // 2, mode="edge")
    return np.convolve(vp, k, "valid")[: len(v)].astype(np.float32)


def build(sub_img, k, yA, seed, tex=None, dark=MATERIAL_DARK, light=MATERIAL_LIGHT, zoom=1.0):
    rng = np.random.default_rng(seed)
    yy = np.arange(H, dtype=np.float32)[:, None]

    proc = paper(rng, dark, light)                   # procedural texture (also keeps the RNG sequence: tear shape reproducible)
    kraft = proc if tex is None else tex             # when material present, use the real material layer (same sheet top and bottom, continuous texture across the tear)
    canvas = kraft.copy()

    # subject scaling + visible outline (top/bottom edges where alpha>0.45): tear baseline =
    # outline arc x compression factor k
    # zoom>1: enlarge the whole thing first, then centre-crop to canvas width — bigger subject,
    # taller tear window (content cropped on both sides)
    sw, sh = sub_img.size
    zw = max(W, int(round(W * zoom)))
    sub = sub_img.resize((zw, max(1, int(round(sh * zw / sw)))), Image.LANCZOS)
    if zw > W:
        x0 = (zw - W) // 2
        sub = sub.crop((x0, 0, x0 + W, sub.size[1]))
    sa = np.asarray(sub, np.float32)
    sh2 = sa.shape[0]
    vis = sa[..., 3] / 255.0 > 0.45
    top = np.argmax(vis, axis=0).astype(np.float32)
    bot = (sh2 - 1 - np.argmax(vis[::-1], axis=0)).astype(np.float32)
    none_c = ~vis.any(axis=0)
    if none_c.any():
        xs = np.arange(W)
        top[none_c] = np.interp(xs[none_c], xs[~none_c], top[~none_c])
        bot[none_c] = np.interp(xs[none_c], xs[~none_c], bot[~none_c])
    top = smooth1d(top, 81)
    bot = smooth1d(bot, 81)
    mt = float(top.mean())
    mb = float(bot.mean())

    # tear line: mean sits on canvas yA, arc amplitude = outline arc x k
    # place the subject so the "paper edge over pattern" is exactly 20 px at its thinnest
    # (guarantees the pattern edge is always hidden under the paper)
    e_top = yA + (top - mt) * k + tear(rng, amp=10.0, n_spike=4)
    cov = e_top - top
    sy = int(round(float(cov.min()) - 20.0))
    e_top = e_top.astype(np.float32)
    e_bot = (bot - mb) * k + tear(rng, amp=10.0, n_spike=4)
    # correction: shift the whole thing to where "paper edge covers at least 20 px of the
    # pattern" (pattern bottom edge always hidden behind paper, paper edge as close to the outline as possible)
    e_bot = (e_bot + (float(((sy + bot) - e_bot).min()) - 20.0)).astype(np.float32)

    # draw the subject — top edge hidden behind upper paper, bottom edge behind lower paper
    y0, y1 = max(0, sy), min(H, sy + sh2)
    a = sa[y0 - sy:y1 - sy]
    # harden the semi-transparent soft edge: a wide soft edge (alpha 0.1-0.4) would let the
    # material layer bleed through the cutout and form muddy colour stains; tighten to a ~0.1
    # narrow transition band — solid subject keeps its colour, soft edge cleanly reveals the material
    m = a[..., 3:4] / 255.0
    alpha = np.clip((m - 0.42) / 0.10, 0, 1.0)
    canvas[y0:y1] = canvas[y0:y1] * (1 - alpha) + a[:, :, :3] * alpha

    # light tear shadow (narrow band, keeps the pattern's colour)
    d = np.clip(yy - e_top[None, :], 0, None)
    amt = np.where(yy > e_top[None, :], np.exp(-d / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt[..., None]) + SHADE[None, None, :] * amt[..., None]

    d2 = np.clip(e_bot[None, :] - yy, 0, None)
    amt2 = np.where(yy < e_bot[None, :], np.exp(-d2 / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt2[..., None]) + SHADE[None, None, :] * amt2[..., None]

    # upper material / lower material over (pattern below, material above)
    top_rgb, at = paper_layer(rng, kraft, e_top, "top")
    canvas = top_rgb * at[..., None] + canvas * (1 - at[..., None])
    bot_rgb, ab = paper_layer(rng, kraft, e_bot, "bot")
    canvas = bot_rgb * ab[..., None] + canvas * (1 - ab[..., None])

    print(f"       e_top {e_top.mean():.0f} | e_bot {e_bot.mean():.0f} | tuck_top {(e_top - (sy + top)).min():.0f} | tuck_bot {((sy + bot) - e_bot).min():.0f}")
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description="torn material layer (window = cutout subject)")
    ap.add_argument("--subject", required=True, help="cutout subject PNG (RGBA)")
    ap.add_argument("--out", required=True, help="output background PNG (1500x1875)")
    ap.add_argument("--material", "--kraft", default="", help="background material photo (rock wall / kraft paper or similar; optional, omit for procedural texture)")
    ap.add_argument("--k", type=float, default=0.60, help="tear arc amplitude / outline arc amplitude compression factor")
    ap.add_argument("--yA", type=float, default=540.0, help="upper tear baseline mean (canvas y)")
    ap.add_argument("--zoom", type=float, default=1.0, help="window content enlargement factor (>1: enlarge then centre-crop sides, taller tear window)")
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--paper-dark", default="185,170,153", help="material dark-tone stop R,G,B (default rock-wall tone)")
    ap.add_argument("--paper-light", default="241,229,214", help="material light-tone stop R,G,B (default rock-wall tone)")
    ap.add_argument("--material-gain", type=float, default=0.0, help="keep material's original colour: overall gain factor (1.2 ~ lift by a fifth); 0 = off, switch to --paper-dark/--paper-light recolouring")
    ap.add_argument("--material-gamma", type=float, default=1.0, help="tone curve when keeping original colour (<1 lifts shadows, protects highlights, e.g. 0.52; !=1 also enables keep-original-colour)")
    ap.add_argument("--detail", type=float, default=4.0, help="material detail high-pass overlay amount (when --material given)")
    args = ap.parse_args()

    sub = Image.open(args.subject).convert("RGBA")
    dark, light = parse_color(args.paper_dark), parse_color(args.paper_light)
    tex = None
    if args.material:
        # real material layer (full cover, no mirror artefacts) + material-native-scale detail
        # (stone grain / grain, mirror invisible)
        if args.material_gain > 0 or args.material_gamma != 1.0:
            # keep original colour: no recolouring, only tone curve + overall gain (use when the
            # material already carries colour patches / cracks / mineral tints)
            tex = photo_native(args.material, gain=args.material_gain if args.material_gain > 0 else 1.0,
                               gamma=args.material_gamma) + photo_detail(args.material)[..., None] * args.detail
        else:
            tex = photo_cover(args.material, dark=dark, light=light) + photo_detail(args.material)[..., None] * args.detail
    img = build(sub, args.k, args.yA, args.seed, tex, dark=dark, light=light, zoom=args.zoom)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    img.save(args.out)
    print("[kraft_tear]", args.out, "| k", args.k, "| yA", args.yA, "| zoom", args.zoom, "| seed", args.seed)


if __name__ == "__main__":
    main()
