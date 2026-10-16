#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
board.py —— 多图网格拼版（默认 3 列），用来做「范式选择板」与案例归档图。

Gate A / Gate B 需要一眼看全：九种构图、多个背景变体。
标签用马善政毛笔楷书渲染（assets/fonts/MaShanZheng-Regular.ttf）。

用法：
    python board.py --inputs nine/bg.居中式.png nine/bg.对角线.png ... \
        --labels 居中式 对角线 ... --cols 3 --width 460 --out nine/board.png
"""

import argparse
import os

from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "fonts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--labels", nargs="*", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--width", type=int, default=460, help="每格图片宽度（像素）")
    ap.add_argument("--gap", type=int, default=24)
    ap.add_argument("--bg", default="#EDE7D8")
    a = ap.parse_args()

    ims = [Image.open(p).convert("RGB") for p in a.inputs]
    scaled = [im.resize((a.width, int(im.size[1] * a.width / im.size[0])),
                        Image.LANCZOS) for im in ims]
    cellh = max(im.size[1] for im in scaled)
    cols = max(1, a.cols)
    rows = (len(scaled) + cols - 1) // cols

    font = None
    fp = os.path.join(FONTS_DIR, "MaShanZheng-Regular.ttf")
    if a.labels and os.path.exists(fp):
        font = ImageFont.truetype(fp, 44)
    lh = 58 if font else 0

    cw, ch = a.width + a.gap, cellh + lh + a.gap
    canvas = Image.new("RGB", (a.gap + cols * cw, a.gap + rows * ch), a.bg)
    d = ImageDraw.Draw(canvas)
    for i, im in enumerate(scaled):
        r, c = divmod(i, cols)
        x, y = a.gap + c * cw, a.gap + r * ch
        canvas.paste(im, (x, y))
        if font and a.labels and i < len(a.labels):
            bbox = d.textbbox((0, 0), a.labels[i], font=font)
            d.text((x + (a.width - (bbox[2] - bbox[0])) / 2.0, y + cellh + 4),
                   a.labels[i], font=font, fill="#3A342A")
    d2 = os.path.dirname(os.path.abspath(a.out))
    if d2 and not os.path.isdir(d2):
        os.makedirs(d2, exist_ok=True)
    canvas.save(a.out)
    print(f"[board] {len(scaled)} 图 × {cols} 列 -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())