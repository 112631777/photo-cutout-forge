#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
text_contrast.py -- text/ground contrast diagnosis + legibility-plate generation

Why it is needed
----------------
check_contrast.py uses the metric "the darkest 5% single pixels (dark text) /
brightest 5% (light text) inside the glyph box" -- this is a conservative
compliance line, guaranteeing "still readable in the worst case". But it does
NOT equal the visual impression: material backgrounds (earthen wall / rock face
/ torn paper) are mottled in light and shade; the P5 passes, yet what the eye
sees is "black text lost in a busy ground of bright and dark patches" -- this
is the user feedback "the text and the ground are too close in colour".

This script adds two more metrics:

  1. Median metric cr_p50: contrast of the ink colour vs the background median
     -- corresponds to "overall impression".
  2. Busyness std: standard deviation of luminance inside the glyph box --
     corresponds to "how busy the ground is".
     When std is high, even if contrast is enough the text "smears into the
     texture", and needs an outline or a plate.

Then it gives actionable advice based on the diagnosis, and optionally
generates a legibility plate (--plate): locally lifts (dark text) or darkens
(light text) the ink colour hue-preserving within the text area, with a
large-radius feather that blends naturally into the material.

Usage
-----
  # diagnosis only
  python text_contrast.py --bg out/poster.bg.png --boxes out/poster.boxes.json

  # write the legibility plate to out/bg.png (for re-rendering; save the original first)
  python text_contrast.py --bg out/poster.bg.png --boxes out/poster.boxes.json \
      --plate out/bg.png --report out/text-contrast.json

Dependencies: Pillow + numpy
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE_W = 1500.0          # Master template design canvas width (coordinate system for boxes)
BUSY_STD = 26.0          # If the luminance std inside a glyph box exceeds this -> flag "busy ground", suggest outline/plate
MIN_EDGE_CR = 3.6        # Minimum acceptable value for the median metric (below it = visually clearly insufficient)


def _lin_lut():
    lut = []
    for i in range(256):
        c = i / 255.0
        lut.append((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) * 255.0)
    return lut


LUT = _lin_lut()


def rel_lum(rgb):
    r, g, b = rgb
    return 0.2126 * (LUT[r] / 255.0) + 0.7152 * (LUT[g] / 255.0) + 0.0722 * (LUT[b] / 255.0)


def parse_color(css):
    css = css.strip()
    if css.startswith("rgb"):
        parts = css[css.index("(") + 1:css.index(")")].replace("%", "").split(",")
        return tuple(int(float(p)) for p in parts[:3])
    if css.startswith("#"):
        return tuple(int(css[i:i + 2], 16) for i in (1, 3, 5))
    return (0, 0, 0)


def lum_image(rgb_im):
    from PIL import ImageChops
    r, g, b = rgb_im.split()
    r = r.point(LUT).point(lambda v: v * 0.2126)
    g = g.point(LUT).point(lambda v: v * 0.7152)
    b = b.point(LUT).point(lambda v: v * 0.0722)
    return ImageChops.add(ImageChops.add(r, g), b)


def cr(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def frame_stats(bg_lut, box, inset=0.14):
    x, y, w, h = box
    dx = max(2, int(w * inset)); dy = max(2, int(h * inset))
    x0, y0, x1, y1 = x + dx, y + dy, x + w - dx, y + h - dy
    if x1 <= x0 or y1 <= y0:
        x0, y0, x1, y1 = x, y, x + max(1, w), y + max(1, h)
    hist = bg_lut.crop((x0, y0, x1, y1)).histogram()
    total = sum(hist)
    if total == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    def pct(p):
        acc = 0
        for i, c in enumerate(hist):
            acc += c
            if acc / total >= p:
                return i / 255.0
        return 1.0
    mean = sum(i * c for i, c in enumerate(hist)) / total / 255.0
    var = sum(((i / 255.0) - mean) ** 2 * c for i, c in enumerate(hist)) / total
    return pct(0.05), pct(0.50), pct(0.95), mean, var ** 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True, help="PNG rendered from the hidden-text layer (same as check_contrast's --bg)")
    ap.add_argument("--boxes", required=True)
    ap.add_argument("--ink", default=None, help="Set a single ink colour; if omitted, use each box's computed colour from the boxes file")
    ap.add_argument("--plate", default=None, help="Output the legibility plate image (re-render after overwriting the new bg.png)")
    ap.add_argument("--report", default=None, help="Diagnostic report JSON")
    ap.add_argument("--pad", type=int, default=44, help="Pixels the plate expands beyond the glyph box (design coordinates)")
    ap.add_argument("--strength", type=float, default=0.15, help="Plate strength (lift/darken amount)")
    ap.add_argument("--canvas", type=float, default=None)
    a = ap.parse_args()

    boxes = json.load(open(a.boxes, encoding="utf-8"))
    bg = Image.open(a.bg).convert("RGB")
    scale = bg.size[0] / (a.canvas or BASE_W)
    bg_lut = lum_image(bg)

    report = {"bg": os.path.abspath(a.bg), "busy_std_threshold": BUSY_STD,
              "min_edge_cr": MIN_EDGE_CR, "items": []}
    need_plate = False
    n_busy = 0

    for b in boxes:
        x = int(round(b["x"] * scale)); y = int(round(b["y"] * scale))
        w = int(round(b["w"] * scale)); h = int(round(b["h"] * scale))
        p5, p50, p95, mean, std = frame_stats(bg_lut, (x, y, w, h))
        t_rgb = parse_color(a.ink) if a.ink else parse_color(b.get("color", "rgb(0,0,0)"))
        lt = rel_lum(t_rgb)
        cr_p5 = cr(lt, p5)      # machine-check metric (worst case)
        cr_p50 = cr(lt, p50)    # visual metric (overall impression)
        cr_mean = cr(lt, mean)
        busy = (std * 255) >= BUSY_STD

        advice = []
        if cr_p50 < MIN_EDGE_CR:
            advice.append("Visual contrast insufficient (median metric %.2f) -> ink needs to go one step darker/lighter" % cr_p50)
            need_plate = True
        if busy:
            advice.append("Busy ground (std %.0f) -> add a light outline / increase weight" % (std * 255))
            n_busy += 1
        if cr_p5 < 4.5:
            advice.append("Darkest area insufficient (P5 metric %.2f) -> a legibility plate is required" % cr_p5)
            need_plate = True
        if not advice:
            advice.append("pass")

        report["items"].append({
            "role": b.get("role"), "text": (b.get("text") or "")[:40],
            "font_size": round(b.get("fontSize", 0), 1),
            "ink": "#%02X%02X%02X" % t_rgb,
            "bg_p5": round(p5 * 255, 1), "bg_p50": round(p50 * 255, 1),
            "bg_p95": round(p95 * 255, 1), "bg_std": round(std * 255, 1),
            "cr_p5": round(cr_p5, 2), "cr_p50": round(cr_p50, 2), "cr_mean": round(cr_mean, 2),
            "busy": busy, "advice": advice,
        })

    worst_vis = min(i["cr_p50"] for i in report["items"]) if report["items"] else 0
    report["worst_visual_cr"] = round(worst_vis, 2)
    report["busy_count"] = n_busy
    report["need_plate"] = need_plate

    for i in report["items"]:
        flag = "OK " if (i["cr_p50"] >= MIN_EDGE_CR and not i["busy"]) else "NOTE"
        print("[%s] %-10s CR(dark) %5.2f  CR(median) %5.2f  std %4.0f  %s"
              % (flag, i["role"], i["cr_p5"], i["cr_p50"], i["bg_std"], " / ".join(i["advice"])))
    print("[text_contrast] worst visual contrast %.2f ; busy ground %d items ; plate recommended: %s"
          % (worst_vis, n_busy, "yes" if need_plate else "no"))

    # ---------------- legibility plate ----------------
    if a.plate:
        W, H = bg.size
        mask = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(mask)
        pad = int(a.pad * scale)
        for b in boxes:
            x = int(round(b["x"] * scale)); y = int(round(b["y"] * scale))
            w = int(round(b["w"] * scale)); h = int(round(b["h"] * scale))
            d.rectangle([x - pad, y - pad, x + w + pad, y + h + pad], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(pad * 0.62))

        arr = np.asarray(bg).astype(np.float32) / 255.0
        mk = (np.asarray(mask).astype(np.float32) / 255.0)[..., None]

        # Dark text -> lift plate; light text -> darken plate. Use a
        # "preserve-hue value V" approach to avoid washing out the material
        # by direct multiplication.
        lts = [rel_lum(parse_color(a.ink) if a.ink else parse_color(b.get("color", "rgb(0,0,0)")))
               for b in boxes]
        dark_text = (sum(lts) / max(1, len(lts))) < 0.18
        k = (1.0 + mk * a.strength) if dark_text else (1.0 - mk * a.strength)
        mx = arr.max(axis=2, keepdims=True)
        sc = np.where(mx > 1e-6, np.clip(mx * k, 0.0, 1.0) / np.maximum(mx, 1e-6), 1.0)
        out = np.clip(arr * sc, 0, 1)
        Image.fromarray((out * 255).astype(np.uint8)).save(a.plate)
        # change-amount audit
        delta = (np.abs(out - arr).mean(axis=2) * 255)
        print("[text_contrast] plate written to %s (%s, strength %.2f, max local change %.0f, mean change over whole image %.2f)"
              % (a.plate, "lift" if dark_text else "darken", a.strength,
                 delta.max(), delta.mean()))

    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        json.dump(report, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[text_contrast] report -> %s" % a.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
