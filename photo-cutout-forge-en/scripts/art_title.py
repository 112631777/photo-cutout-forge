#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
art_title.py -- generate "art lettering" HTML fragments (varied sizes / vertical stretch / vertical offset / slight rotation)

Why it is needed
----------------
The Chinese main titles of the reference posters (intangible-heritage series:
bamboo weaving / Huizhou lanterns / the beauty of ICH / lofty mountains and long
rivers) are NOT set in one neat row; instead:

  1. Varied sizes -- each character has a different font size (0.85-1.2x),
     giving a rhythmic light/heavy feel
  2. Vertical stretch -- some characters scaleY 1.2-1.4, making strokes look upright
  3. Vertical offset -- characters shift up and down, like the rise and fall of handwriting
  4. Slight rotation -- +/-2 to 7 degrees, breaking the rigidity of "typeface" setting

This script assigns these procedurally to each character (seed reproducible),
output can be pasted straight into the master's
<span style="--s:...;--sy:...;--dy:...;--rot:...">char</span> fragment.
The font stays unchanged (still the master's calligraphic face); only the effect changes.

The master needs matching CSS (built into the three master templates):

  .art { display: flex; align-items: flex-start; letter-spacing: 0; }
  .art > span {
    display: inline-block;
    font-size: calc(1em * var(--s, 1));
    transform: translateY(var(--dy, 0)) rotate(var(--rot, 0deg)) scaleY(var(--sy, 1));
    transform-origin: 50% 82%;        /* pivot at the character foot: grows upward when stretched, does not break the baseline */
  }
  .art.silhouette > span { color: transparent; -webkit-text-stroke: 3px var(--ink); }

Usage
----
  python art_title.py --text "壁上万象" --style lively --seed 3
  python art_title.py --text "壁上万象" --style dramatic --seed 5 --silhouette
  python art_title.py --text "壁上" --style subtle          # for the EN edition: very light effect

  Example output (one line, can directly replace the content of `>壁上<` in the master):
  <span style="--s:1.12;--sy:1.18;--dy:-7px;--rot:-3.2deg">壁</span><span ...>上</span>
"""

import argparse
import random
import sys

# Per-style intensities: (font-size multiplier, vertical stretch, vertical offset px, rotation deg, horizontal offset px)
STYLES = {
    "subtle":   dict(s=(0.94, 1.06), sy=(1.00, 1.05), dy=(-4, 4),     rot=(-1.2, 1.2),  dx=(-8, 8)),
    "lively":   dict(s=(0.88, 1.14), sy=(1.00, 1.12), dy=(-10, 10),   rot=(-4.0, 4.0),  dx=(-18, 26)),
    "stretch":  dict(s=(0.96, 1.04), sy=(1.16, 1.38), dy=(-6, 6),     rot=(-2.0, 2.0),  dx=(-10, 10)),
    "dramatic": dict(s=(0.82, 1.22), sy=(1.05, 1.32), dy=(-16, 16),   rot=(-7.0, 7.0),  dx=(-26, 40)),
    # The "upright" style (requested by the boss on 2026-10-12): the characters must be upright, leaving only a very light breathing room --
    #   no rotation (+/-0.5 deg), no stretch (sy 1.00-1.02), no vertical jump (dy +/-2), sizes nearly identical.
    #   The boss said: "the large Chinese title characters are not upright enough; they are all set askew". Use lively / dramatic for "lively",
    #   use this style for "upright"; spacing relies on enlarging the container's letter-spacing (master `.tcol.art`).
    "upright": dict(s=(0.985, 1.015), sy=(1.00, 1.02), dy=(-2, 2),   rot=(-0.5, 0.5),  dx=(-3, 3)),
}


def fmt(v, unit=""):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return s + unit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="title text (generate a span per character)")
    ap.add_argument("--style", default="lively", choices=sorted(STYLES))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--orient", default="h", choices=["h", "v"],
                    help="layout direction: h = one horizontal row (default) / v = vertical character column (top to bottom, with extra horizontal offset --dx)")
    ap.add_argument("--silhouette", action="store_true", help="add the .silhouette class (hollow outline silhouette)")
    ap.add_argument("--anchor", default=None, help="first-character anchor mode: big|small|none (default none)")
    a = ap.parse_args()

    cfg = STYLES[a.style]
    rng = random.Random(a.seed)
    chars = [c for c in a.text if c.strip()]
    if not chars:
        print("", end="")
        return 0

    out = []
    for i, ch in enumerate(chars):
        s = rng.uniform(*cfg["s"])
        sy = rng.uniform(*cfg["sy"])
        dy = rng.uniform(*cfg["dy"])
        rot = rng.uniform(*cfg["rot"])
        # In vertical layout, the horizontal offset is the main source of
        # irregularity (unused in horizontal; set to 0 for compatibility)
        dx = rng.uniform(*cfg["dx"]) if a.orient == "v" else 0.0
        # Anchoring: pin the first (or last) character to an extreme, so the
        # whole group does not "average out" and lose contrast
        if a.anchor == "big" and i == 0:
            s, sy = cfg["s"][1], cfg["sy"][1]
        elif a.anchor == "small" and i == 0:
            s, sy = cfg["s"][0], cfg["sy"][0]
        elif a.anchor == "big" and i == len(chars) - 1:
            s, sy = cfg["s"][1], cfg["sy"][1]
        out.append('<span style="--s:%s;--sy:%s;--dx:%spx;--dy:%spx;--rot:%sdeg">%s</span>'
                   % (fmt(s), fmt(sy), fmt(round(dx)), fmt(round(dy)), fmt(rot), ch))

    cls = "art silhouette" if a.silhouette else "art"
    # Only output the inner fragment; the caller is responsible for placing it
    # inside <div class="..."> (the master controls via class)
    sys.stdout.write("".join(out))
    print("", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
