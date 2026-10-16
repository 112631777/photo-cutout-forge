#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
motif_band.py — motif band: subject -> motif tiles -> flattening -> S-shaped ribbon layout

The "motif band" route of photo-cutout-forge (another skeleton for an exhibition
key visual; reference: the Vietnam silk exhibition):
  1. Sampling: score every candidate inside the subject's alpha by "saturation x
     pattern-structure", greedily pick N non-overlapping tiles whose hues are
     pulled apart (only take regions where the whole alpha ~= 255, so no cutout
     soft edges leak in);
  2. Flattening: strong denoise -> saturation boost -> contrast boost -> limited
     colour quantisation — turning real photographic texture into clean colour
     blocks (a mineral-pigment feel);
  3. Banding: a white S-shaped ribbon (constant band width, soft shadow, both ends
     spilling off the canvas), tiles laid along the curve, each micro-rotated with
     the tangent (clamped +/-7 deg), plus a small name tag above each tile (by
     default auto-assigned from the tile's dominant colour to a Dunhuang mineral
     pigment name; override with --labels).

Usage:
    python motif_band.py --source cut\A2c.png --out band\band.demo.png \
        --count 5 --colors 14 --seed 3
    python motif_band.py --list-pigments
"""

import argparse
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from auto_compose import rgb2hsv, hsv2rgb, rgb_of, rgb_hex   # same dir, reuse colour tools

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(HERE, "..", "assets", "fonts")
W, H = 1500, 1875          # canvas 4:5 (same format as the master template)
SS = 2                     # supersampling factor

# Dunhuang mineral pigment names (sorted by hue; Yuebai/Dai judged specially by lightness)
# Qingjin (青金) = deep blue (near 215 deg), Shiqing (石青) = bright blue (near 207 deg) — same family, named by depth
PIGMENTS = [("朱砂", 8.0), ("赭石", 26.0), ("藤黄", 48.0), ("石绿", 142.0),
            ("松石绿", 170.0), ("石青", 207.0), ("青金", 215.0), ("藏青", 236.0),
            ("绛紫", 312.0)]

BAND_RGB = (253, 252, 248)          # ribbon paper white
TAG_RGB = (70, 64, 52)              # name-tag ink colour


# ---------------------------------------------------------------------------
# 1. Sampling: pick "patterned, coloured" tiles inside the subject
# ---------------------------------------------------------------------------
def _work_image(src, width=900):
    sw, sh = src.size
    r = width / sw
    return src.resize((int(round(sw * r)), int(round(sh * r))), Image.BILINEAR), r


def dominant_key(rgb_img, k=6, share=0.10):
    """Motif tile -> dominant colour: among quantised modes whose share >= share,
    the one with the highest "saturation x share".

    Take "the most salient colour", not "the largest-share colour": on a
    multi-colour mixed tile the largest-share colour is often a grey transition
    tone that points the name tag at a colour not actually prominent on the
    image; looking at saturation alone would favour small-area high-saturation
    specks. Saturation x share balances "area" and "prominence", closest to the
    first impression the eye gets from a tile. The same criterion is also used for
    "near-colour down-weighting" and for naming the tag, keeping sampling and
    labels consistent.
    """
    sw, sh = rgb_img.size
    small = rgb_img.resize((96, max(2, int(round(96 * sh / sw)))), Image.BILINEAR)
    q = small.quantize(colors=k, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    cols = q.convert("RGB").getcolors(maxcolors=1 << 20)
    total = float(sum(c for c, _ in cols))
    doms = [(c, rgb) for c, rgb in cols if c / total >= share] or [max(cols)]
    return np.asarray(max(doms, key=lambda t: rgb2hsv(np.asarray(t[1], np.float32))[1]
                          * (t[0] / total))[1], np.float32)


def _tile_key(rgb_img, aspect, sat, con, small_w=72):
    """Candidate's "band dominant colour": first compress to a small sample using
    the same flattening criterion, then take the dominant colour (for down-weighting)."""
    return dominant_key(flatten_tile(rgb_img, 6,
                                     (small_w, max(2, int(round(small_w / aspect)))),
                                     sat=sat, con=con))


def pick_tiles(src, count, aspect, tile_src_w, sat=1.50, con=1.28, debug=False):
    """Pick count tiles inside the subject's alpha.

    Score = (0.25 + 0.75 * mean saturation) * (0.30 + 0.70 * normalised luminance
    std-dev): there must be both colour and pattern undulation; after each pick,
    "near-colour down-weighting" is applied to the remaining candidates (RGB
    distance of the dominant colour), keeping the set of tiles chromatically
    pulled apart (covering the wall's mineral spectrum). The down-weighted colour
    uses the tile's dominant colour under the "same flattening criterion" — raw
    pixels are mostly dirty-brick coloured (near gold-brown); only after the
    flattening saturation boost does the true cinnabar show, so "nearness" must be
    judged by the final on-band colour.
    """
    # The subject test is built at "full resolution" (sharp, unaffected by scaling
    # bleed): if alpha is a soft "paint concentration" mask (A2c type) it is not
    # reliable, so uniformly judge "outside" by "near pure white and alpha ~= 0"
    # (cutouts are often made on a white background); sampling only uses RGB (the
    # painting's own colours).
    full = np.asarray(src.convert("RGB"), np.float32)
    fa = np.asarray(src.getchannel("A"), np.float32)
    inside_full = ((fa >= 1.0) | (full.min(2) <= 232.0)).astype(np.uint8) * 255
    del full, fa

    work, r = _work_image(src)
    arr = np.asarray(work.convert("RGB"), np.float32)
    cover = np.asarray(Image.fromarray(inside_full, "L").resize(work.size, Image.BILINEAR),
                       np.float32) / 255.0           # per-working-pixel "inside-subject coverage" 0-1
    mx = arr.max(2)
    mn = arr.min(2)
    satmap = np.where(mx > 1.0, (mx - mn) / np.maximum(mx, 1.0), 0.0)
    lum = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114

    tw = max(8, int(round(tile_src_w * r)))
    th = max(8, int(round(tw / aspect)))
    sw, sh = work.size
    step = max(6, int(round(tw * 0.33)))
    cands = []
    for y0 in range(0, max(1, sh - th) + 1, step):
        for x0 in range(0, max(1, sw - tw) + 1, step):
            if cover[y0:y0 + th, x0:x0 + tw].shape != (th, tw):
                continue
            if float(cover[y0:y0 + th, x0:x0 + tw].mean()) < 0.99:    # whole tile falls inside the subject
                continue
            s_m = float(satmap[y0:y0 + th, x0:x0 + tw].mean())
            l_t = lum[y0:y0 + th, x0:x0 + tw]
            col = arr[y0:y0 + th, x0:x0 + tw].reshape(-1, 3).mean(0)
            key = _tile_key(Image.fromarray(arr[y0:y0 + th, x0:x0 + tw].astype(np.uint8), "RGB"),
                            aspect, sat, con)
            score = (0.25 + 0.75 * s_m) * (0.30 + 0.70 * min(1.0, float(l_t.std()) / 40.0))
            cands.append({"x": x0, "y": y0, "score": score, "col": col, "key": key})
    print(f"[motif] {len(cands)} valid candidates inside subject (sampling {tw}x{th} working pixels)")
    if not cands:
        raise SystemExit("[motif] no fully-opaque tile found inside the subject: use a different source or a smaller sampling size")

    avail = list(cands)
    picked = []
    gx, gy = tw * 0.30, th * 0.30
    for _ in range(count):
        if not avail:
            break
        avail.sort(key=lambda c: -c["score"])
        if debug:
            top = " | ".join(f"{c['score']:.3f}·{rgb_hex(c['key'])}·({c['x']},{c['y']})"
                             for c in avail[:10])
            print(f"[motif.debug] round {len(picked)+1} top 10: {top}")
        best = avail[0]
        picked.append(best)
        print(f"[motif] pick {len(picked)}: {best['score']:.3f} dominant={rgb_hex(best['key'])}"
              f" @working-pixel({best['x']},{best['y']})")
        rest = []
        for c in avail[1:]:
            if not (c["x"] + tw + gx <= best["x"] or c["x"] >= best["x"] + tw + gx or
                    c["y"] + th + gy <= best["y"] or c["y"] >= best["y"] + th + gy):
                continue                                    # overlaps a picked tile -> drop
            # down-weight "near-colour" to already-picked: use RGB distance (with
            # lightness) of the "dominant saturated colour", so gold (32 deg) and
            # cinnabar (15 deg) are not mistaken for the same hue by pure hue, and
            # grey mean-tone colours are not over-penalised
            dd = float(np.linalg.norm(c["key"] - best["key"]))
            c = dict(c)
            c["score"] *= (1.0 - 0.60 * math.exp(-((dd / 64.0) ** 2)))
            rest.append(c)
        avail = rest

    out = []
    for c in picked:
        x0 = max(0, int(round(c["x"] / r)))
        y0 = max(0, int(round(c["y"] / r)))
        x1 = min(src.size[0], int(round((c["x"] + tw) / r)))
        y1 = min(src.size[1], int(round((c["y"] + th) / r)))
        out.append({"rect": [x0, y0, x1, y1], "col": c["col"], "score": c["score"]})
    return out


# ---------------------------------------------------------------------------
# 2. Flattening: strong denoise -> saturation/contrast boost -> limited quantisation
# ---------------------------------------------------------------------------
def flatten_tile(rgb, colors, display_size, sat=1.85, con=1.28):
    """Real photographic texture -> clean colour blocks (quantise at display size,
    so block edges are sharpest)."""
    rgb = rgb.filter(ImageFilter.MedianFilter(5))
    hsv = rgb.convert("HSV")
    s = hsv.getchannel("S").point(lambda v: min(255, int(v * sat)))
    v = hsv.getchannel("V").point(lambda v: min(255, int(v * 1.08)))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), s, v)).convert("RGB")
    a = np.asarray(rgb, np.float32)
    a = np.clip((a - 128.0) * con + 128.0, 0, 255)
    rgb = Image.fromarray(a.astype(np.uint8), "RGB")
    rgb = rgb.resize(display_size, Image.LANCZOS)
    return rgb.quantize(colors=colors, method=Image.MEDIANCUT,
                        dither=Image.Dither.NONE).convert("RGB")


def name_for(key_rgb, used):
    """Tile dominant colour -> mineral pigment name (first-come-first-served;
    Yuebai/Dai judged specially by lightness)."""
    h, s, v = rgb2hsv(np.asarray(key_rgb, np.float32))
    if s < 0.25 and v > 0.80:
        nm = "月白"
    elif v < 0.24 and s < 0.30:
        nm = "黛"
    else:
        cand = [(m, min(abs(h - hc), 360.0 - abs(h - hc)))
                for m, hc in PIGMENTS if m not in used]
        if not cand:
            cand = [(m, min(abs(h - hc), 360.0 - abs(h - hc))) for m, hc in PIGMENTS]
        nm = min(cand, key=lambda t: t[1])[0]
    used.add(nm)
    return nm


# ---------------------------------------------------------------------------
# 3. Banding: ground gradient + S-shaped ribbon + tiles/tags onto the band
# ---------------------------------------------------------------------------
def band_colors(src, top_override, bottom_override, hue_override=None):
    """Take the dominant hue from the subject -> two colours: light ground (top) +
    dominant colour (bottom)."""
    r, g, b, a = src.split()
    comp = Image.new("RGB", src.size, (243, 237, 226))
    comp.paste(src.convert("RGB"), (0, 0), a)
    small = comp.resize((260, max(2, int(260 * src.size[1] / src.size[0]))), Image.BILINEAR)
    arr = np.asarray(small, np.float32) / 255.0
    mx = arr.max(2)
    mn = arr.min(2)
    d = mx - mn
    ok = (d > 1e-4) & (mx > 0.15)
    r_, g_, b_ = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros_like(mx)
    ir = ok & (mx == r_)
    ig = ok & (mx == g_) & ~ir
    ib = ok & ~ir & ~ig
    hue[ir] = ((g_[ir] - b_[ir]) / d[ir]) % 6.0
    hue[ig] = (b_[ig] - r_[ig]) / d[ig] + 2.0
    hue[ib] = (r_[ib] - g_[ib]) / d[ib] + 4.0
    hue = (hue * 60.0) % 360.0
    sat = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    hist, edges = np.histogram(hue.ravel(), bins=12, range=(0, 360),
                               weights=(sat * ok).ravel())
    hp = (edges[hist.argmax()] + 15.0) % 360.0
    if hue_override is not None:
        hp = float(hue_override) % 360.0
    top = hsv2rgb(hp, 0.16, 0.93) if top_override is None else rgb_of(top_override)
    bot = hsv2rgb(hp, 0.50, 0.62) if bottom_override is None else rgb_of(bottom_override)
    return top, bot, hp


def bg_gradient(top, bottom, size, seed=7):
    """Smooth diagonal gradient (light top-left, dominant bottom-right), only 0.8 sigma
    jitter to prevent banding — zero texture."""
    w, h = size
    rng = np.random.default_rng(seed + 313)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = 0.62 * (yy / (h - 1)) + 0.38 * (xx / (w - 1))
    t = np.clip((u - 0.18) / 0.82, 0.0, 1.0)
    t = (t * t * (3.0 - 2.0 * t))[..., None]
    arr = top[None, None, :] * (1.0 - t) + bottom[None, None, :] * t
    arr += rng.normal(0, 0.8, (h, w, 1)).astype(np.float32)
    return np.clip(arr, 0, 255)


def band_alpha(size, band_w, amp, cycles, phase):
    """S-shaped ribbon alpha: x_c(t) = 0.5 + amp * sin(2*pi*(cycles*t + phase)),
    constant band width."""
    w, h = size
    xs = np.arange(w, dtype=np.float32)[None, :]
    t = np.arange(h, dtype=np.float32)[:, None] / h
    xc = (0.5 + amp * np.sin(2.0 * math.pi * (cycles * t + phase))) * w
    half = band_w * w / 2.0
    m = (np.abs(xs - xc) <= half).astype(np.uint8) * 255
    return Image.fromarray(m, "L").filter(ImageFilter.GaussianBlur(2.5))


def curve_x(t, amp, cycles, phase):
    return 0.5 + amp * math.sin(2.0 * math.pi * (cycles * t + phase))


def curve_angle(t, amp, cycles, phase, canvas_h):
    dx = amp * W * 2.0 * math.pi * cycles * math.cos(2.0 * math.pi * (cycles * t + phase))
    return math.degrees(math.atan2(dx, canvas_h))


def blit_shadow(canvas, alpha, pos, blur, opacity, color=(32, 34, 40)):
    """Composite the (small-size) alpha onto the canvas at pos, blur it, then use it
    as a shadow colour block."""
    w, h = canvas.size
    m = Image.new("L", (w, h), 0)
    m.paste(alpha.filter(ImageFilter.GaussianBlur(blur)), pos)
    m = m.point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", (w, h), color + (0,))
    sh.putalpha(m)
    canvas.alpha_composite(sh)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="motif band: subject -> flattened tiles -> S-shaped ribbon")
    ap.add_argument("--source", required=True, help="subject PNG (RGBA cutout recommended; RGB treated as fully usable)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=5, help="number of tiles")
    ap.add_argument("--colors", type=int, default=14, help="flattening colour count")
    ap.add_argument("--tile-w", type=float, default=0.14, help="tile display width (x canvas width)")
    ap.add_argument("--tile-aspect", type=float, default=0.80, help="tile width / height")
    ap.add_argument("--sat", type=float, default=1.50, help="flattening saturation boost (1 = unchanged)")
    ap.add_argument("--con", type=float, default=1.28, help="flattening contrast boost (1 = unchanged)")
    ap.add_argument("--band-w", type=float, default=0.40, help="ribbon band width (x canvas width)")
    ap.add_argument("--amp", type=float, default=0.175, help="S-curve swing (x canvas width)")
    ap.add_argument("--cycles", type=float, default=0.90, help="S-curve cycle count")
    ap.add_argument("--phase", type=float, default=-0.30, help="S-curve phase")
    ap.add_argument("--flip-x", action="store_true",
                    help="mirror the ribbon left-right (this case: after mirroring the band exits bottom-right, "
                         "leaving the lower-left free for the title zone)")
    ap.add_argument("--bg-hue", type=float, default=None,
                    help="ground hue override (deg, 0-360; default auto-extracted from subject; this case the "
                         "gold wall dominates so it picks up a warm gold)")
    ap.add_argument("--labels", nargs="*", default=None, help="name-tag text (overrides auto mineral-pigment names)")
    ap.add_argument("--bg-color", default=None, help="ground bottom-edge dominant colour #RRGGBB (default auto)")
    ap.add_argument("--bg-color2", default=None, help="ground top-edge light colour #RRGGBB (default auto)")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--debug-picks", action="store_true", help="print top 10 candidates per round (for tuning samples)")
    ap.add_argument("--list-pigments", action="store_true")
    a = ap.parse_args()
    if a.list_pigments:
        print("Mineral pigment names: " + "  ".join(f"{m}({h:g}°)" for m, h in PIGMENTS) + "  Yuebai  Dai")
        return 0

    src = Image.open(a.source).convert("RGBA")
    tile_src_w = int(round(a.tile_w * W * 1.6))          # source-domain sampling width (~1.6x display, sharp at display size)
    picks = pick_tiles(src, a.count, a.tile_aspect, tile_src_w,
                       sat=a.sat, con=a.con, debug=a.debug_picks)

    tw_d = a.tile_w * W
    th_d = tw_d / a.tile_aspect
    tiles = []
    used = set()
    for i, p in enumerate(picks):
        crop = src.crop(tuple(p["rect"]))
        flat = flatten_tile(crop.convert("RGB"), a.colors,
                            (int(round(tw_d * SS)), int(round(th_d * SS))),
                            sat=a.sat, con=a.con)
        key = dominant_key(flat)                      # dominant saturated colour -> naming basis
        if a.labels and i < len(a.labels):
            label = a.labels[i]
        else:
            label = name_for(key, used)
        tiles.append({"img": flat.convert("RGBA"), "label": label, "key": key})
        print(f"[motif] tile{i+1}: rect={p['rect']} dominant={rgb_hex(key)} tag '{label}'")

    top, bot, hp = band_colors(src, a.bg_color, a.bg_color2, a.bg_hue)
    print(f"[motif] ground: dominant hue {hp:g}° -> top edge {rgb_hex(top)} / bottom edge {rgb_hex(bot)}")

    canvas = Image.fromarray(
        bg_gradient(top, bot, (W * SS, H * SS), a.seed).astype(np.uint8)).convert("RGBA")

    amp_eff = -a.amp if a.flip_x else a.amp                   # mirror = negative swing (same criterion as the others)
    alpha = band_alpha((W * SS, H * SS), a.band_w, amp_eff, a.cycles, a.phase)
    blit_shadow(canvas, alpha, (0, int(0.016 * H * SS)), 34, 0.30)       # ribbon shadow
    band = Image.new("RGBA", canvas.size, BAND_RGB + (0,))
    band.putalpha(alpha)
    canvas.alpha_composite(band)

    n = len(tiles)
    for i, tl in enumerate(tiles):
        t = 0.055 + (i + 0.5) * (0.945 - 0.055) / n
        cx = curve_x(t, amp_eff, a.cycles, a.phase) * W * SS
        cy = t * H * SS
        ang = max(-7.0, min(7.0, curve_angle(t, amp_eff, a.cycles, a.phase, H)))
        rot = tl["img"].rotate(-ang, expand=True, resample=Image.BICUBIC)
        pos = (int(round(cx - rot.size[0] / 2.0)), int(round(cy - rot.size[1] / 2.0)))
        blit_shadow(canvas, rot.getchannel("A"), (pos[0] + 3 * SS, pos[1] + 6 * SS),
                    12, 0.24)                                            # tile shadow
        canvas.paste(rot, pos, rot)
        tl["pos"] = pos
        tl["rot"] = rot.size

    try:
        font = ImageFont.truetype(os.path.join(FONTS_DIR, "MaShanZheng-Regular.ttf"), 30 * SS)
    except OSError:
        font = None
    if font is not None:
        d = ImageDraw.Draw(canvas)
        for tl in tiles:
            x = tl["pos"][0] + 2
            y = tl["pos"][1] - 76                                     # name tag sits just above the tile (in the gap between tiles)
            d.text((x, y), tl["label"], font=font, fill=TAG_RGB + (255,))

    out = canvas.convert("RGB").resize((W, H), Image.LANCZOS)
    d2 = os.path.dirname(os.path.abspath(a.out))
    if d2 and not os.path.isdir(d2):
        os.makedirs(d2, exist_ok=True)
    out.save(a.out)
    print(f"[motif] {n} tiles -> ribbon -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
