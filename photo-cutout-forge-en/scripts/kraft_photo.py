# -*- coding: utf-8 -*-
r"""Torn-material-layer . Route B: the centre-seam window content uses the original photo directly
(whole frame fills the canvas width, aligned by wall-band rows), with background material pressed on top/bottom.

Input model (skill direction): one original image containing the subject (--photo, subject within frame) + one
material source image (--material, e.g. rock-wall material -- the closer its tone/texture matches the subject's
environment, the better) + a description of the subject (used for white-background candidate prompts; see
references\cutout-craft.md section 1, not handled by this script).

Shares the tear geometry with kraft_tear.py (contour arc x k + random torn edge, 20px tuck) -- only the window
content is replaced; the window holds a continuous real-photo image, so "material colour leaking into the mural"
(the structural problem of route A's k<1 compressed arc) never appears.

Two contour sources: ① AI silhouette candidate (default); ② photo-traced mask -- when the AI silhouette geometry
  disagrees with the real photo (multi-wing / U-shaped perspective), trace top/bot control points along the true
  boundary on the photo, interpolate a polyline into an alpha band mask of the same size as the photo, and feed it
  to --cutout; pair with --k 1.0 (tear = traced contour ± tear) --smooth 21 (preserve contour)
  --wall-top-row taking the traced top mean (see references\kraft-tear.md section 1.5).

Framing: --wall-top-row = the photo row aligned to the upper tear line (--top-edge, default 539).
  First locate ceiling/mural/floor boundaries via the per-row brightness profile, then render 2-3 candidates for
  human-eye selection:
  case (4202x5248 exhibition photo): ceiling lower bound ~ y1550; central cropped column mural band ~ y2600.
  Final: --zoom 1.45 --wall-top-row 1550 (window 486px, no black/ground showing through).

Usage (case parameters):
  python kraft_photo.py --cutout ..\cut\A2c.png --photo material\mural.original.png `
      --material material\rock.sand.png --zoom 1.45 --wall-top-row 1550 --out bg.rock.png
"""
import argparse
import os

import numpy as np
from PIL import Image

import kraft_tear as kt


def parse_color(s):
    return tuple(int(v) for v in s.split(","))


def main():
    ap = argparse.ArgumentParser(description="Torn-material-layer (window = original photo)")
    ap.add_argument("--cutout", required=True, help="Cutout subject PNG (RGBA, used only for the tear-contour arc)")
    ap.add_argument("--photo", required=True, help="Original photo (RGB, fills the tear window)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--material", "--kraft", default="", help="Background material photo (rock wall / kraft paper etc.; optional -- if omitted, a procedural texture is used)")
    ap.add_argument("--wall-top-row", type=float, default=1400.0, help="Photo row aligned to the upper tear line (framing)")
    ap.add_argument("--top-edge", type=float, default=539.0, help="Upper tear-line position (must match the geometry; default 539)")
    ap.add_argument("--zoom", type=float, default=1.0, help="Window content magnification (>1: contour and photo scale up together, centre-cropped on both sides, taller tear window)")
    ap.add_argument("--k", type=float, default=0.60, help="Tear-arc / contour-arc compression factor (->1 means the tear hugs the subject contour more)")
    ap.add_argument("--smooth", type=int, default=81, help="Contour smoothing window in px (smaller = more contour detail, larger = more hand-torn big wave)")
    ap.add_argument("--yA", type=float, default=540.0, help="Upper tear baseline mean (canvas y)")
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--paper-dark", default="185,170,153", help="Material tonal dark end R,G,B (default rock-wall tone)")
    ap.add_argument("--paper-light", default="241,229,214", help="Material tonal light end R,G,B (default rock-wall tone)")
    ap.add_argument("--material-gain", type=float, default=0.0, help="Keep material's original colour: overall gain multiplier (1.2≈lift by 20%%); 0 = off, recolour via --paper-dark/--paper-light")
    ap.add_argument("--material-gamma", type=float, default=1.0, help="Tonal curve when keeping original colour (<1 lifts shadows and keeps highlights, e.g. 0.52; !=1 also enables keep-original-colour)")
    ap.add_argument("--detail", type=float, default=4.0, help="Material detail high-pass overlay amount (when --material is given)")
    args = ap.parse_args()

    # Paper ground: compute the procedural texture first (keep the same random sequence as kraft_tear.build so the tear shape matches)
    rng = np.random.default_rng(args.seed)
    kraft = kt.paper(rng, kt.MATERIAL_DARK, kt.MATERIAL_LIGHT)
    if args.material:
        if args.material_gain > 0 or args.material_gamma != 1.0:
            # Keep original colour: no recolour, only tonal curve + overall gain (use when the material carries its own stains/cracks/mineral colours)
            kraft = kt.photo_native(args.material, gain=args.material_gain if args.material_gain > 0 else 1.0,
                                    gamma=args.material_gamma) \
                + kt.photo_detail(args.material)[..., None] * args.detail
        else:
            kraft = kt.photo_cover(args.material, dark=parse_color(args.paper_dark),
                                   light=parse_color(args.paper_light)) \
                + kt.photo_detail(args.material)[..., None] * args.detail
    canvas = kraft.copy()

    # ---- Contour and tear line (same as build(); when zoom>1, scale up then centre-crop to canvas width) ----
    sub = Image.open(args.cutout).convert("RGBA")
    sw, sh = sub.size
    zw = max(kt.W, int(round(kt.W * args.zoom)))
    s2 = sub.resize((zw, max(1, int(round(sh * zw / sw)))), Image.LANCZOS)
    if zw > kt.W:
        x0 = (zw - kt.W) // 2
        s2 = s2.crop((x0, 0, x0 + kt.W, s2.size[1]))
    sa = np.asarray(s2, np.float32)
    sh2 = sa.shape[0]
    vis = sa[..., 3] / 255.0 > 0.45
    top = np.argmax(vis, axis=0).astype(np.float32)
    bot = (sh2 - 1 - np.argmax(vis[::-1], axis=0)).astype(np.float32)
    none_c = ~vis.any(axis=0)
    if none_c.any():
        xs = np.arange(kt.W)
        top[none_c] = np.interp(xs[none_c], xs[~none_c], top[~none_c])
        bot[none_c] = np.interp(xs[none_c], xs[~none_c], bot[~none_c])
    top = kt.smooth1d(top, args.smooth)
    bot = kt.smooth1d(bot, args.smooth)
    mt, mb = float(top.mean()), float(bot.mean())
    e_top = args.yA + (top - mt) * args.k + kt.tear(rng, amp=10.0, n_spike=4)
    sy = int(round(float((e_top - top).min()) - 20.0))
    e_top = e_top.astype(np.float32)
    e_bot = (bot - mb) * args.k + kt.tear(rng, amp=10.0, n_spike=4)
    e_bot = (e_bot + (float(((sy + bot) - e_bot).min()) - 20.0)).astype(np.float32)
    print(f"       e_top {e_top.mean():.0f} | e_bot {e_bot.mean():.0f} | tuck_top {(e_top - (sy + top)).min():.0f} | tuck_bot {((sy + bot) - e_bot).min():.0f}")

    # ---- Original photo: fill the canvas width (centre-crop both sides after zoom scaling), align wall-band rows to the tear line ----
    ph = Image.open(args.photo).convert("RGB")
    pw, phh = ph.size
    sc = kt.W * args.zoom / pw
    ph2 = ph.resize((max(kt.W, int(round(pw * sc))), max(kt.H, int(round(phh * sc)))), Image.LANCZOS)
    x0 = (ph2.size[0] - kt.W) // 2
    pa = np.asarray(ph2, np.float32)[:, x0:x0 + kt.W]
    by = int(round(args.top_edge - args.wall_top_row * sc))    # canvas row = by + photo row * sc (by may be negative)
    y0c, y0p = max(0, by), max(0, -by)
    h_avail = min(kt.H - y0c, pa.shape[0] - y0p)
    canvas[y0c:y0c + h_avail] = pa[y0p:y0p + h_avail]
    print(f"       photo {pw}x{phh} | sc {sc:.3f} | visible {ph2.size[0]}x{ph2.size[1]} take x{x0}..{x0 + kt.W} | by {by} -> window({args.top_edge:.0f}-{e_bot.mean():.0f}) maps to photo rows {int((args.top_edge - by) / sc)}..{int((e_bot.mean() - by) / sc)}")

    # ---- Light tear shadow (same as build) ----
    yy = np.arange(kt.H, dtype=np.float32)[:, None]
    d = np.clip(yy - e_top[None, :], 0, None)
    amt = np.where(yy > e_top[None, :], np.exp(-d / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt[..., None]) + kt.SHADE[None, None, :] * amt[..., None]
    d2 = np.clip(e_bot[None, :] - yy, 0, None)
    amt2 = np.where(yy < e_bot[None, :], np.exp(-d2 / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt2[..., None]) + kt.SHADE[None, None, :] * amt2[..., None]

    # ---- Top paper / bottom paper over ----
    top_rgb, at = kt.paper_layer(rng, kraft, e_top, "top")
    canvas = top_rgb * at[..., None] + canvas * (1 - at[..., None])
    bot_rgb, ab = kt.paper_layer(rng, kraft, e_bot, "bot")
    canvas = bot_rgb * ab[..., None] + canvas * (1 - ab[..., None])

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(args.out)
    print("[kraft_photo]", args.out)


if __name__ == "__main__":
    main()
