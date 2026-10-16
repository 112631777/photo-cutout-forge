#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""pick_ink.py —— 从画面里取「占比最大的深色」当字色（2026-10-12 老大要的）

为什么需要它
------------
默认墨色是固定的 `#17130E`（近黑）。但画面本身有主色调时（本案壁画是群青／赭石／墨绿），
**字色取自画面里占比最大的那档深色**会更和谐 —— 老大原话：
「可以给 Skill 加上**提取画面中占比最大的深色**去给字体加一个颜色，会更和谐」。

做法（三步，都不依赖第三方库）
----------------------------
1. 亮度排序，取**最暗的 N%**（`--dark-pct`，默认 18%）的像素；
2. 对这些暗像素做 **8×8×8 三维直方图**，取最重的若干格算加权均值 ——
   比"直接平均"稳：直接平均会被零散的噪点拉灰，直方图取的是**有体量的那一簇**；
3. **保底变暗**：取样出的颜色往往还不够深（压在浅材质上要 4.5:1），
   按 WCAG 相对亮度把颜色往黑压，直到 `L ≤ --max-lum`（默认 0.045，≈ CR 4.5:1 的常用上限）。

用法
----
  python pick_ink.py --image out\bg.png                       # 直接打印两个 hex
  python pick_ink.py --image out\bg.png --dark-pct 14 --json out\ink.json
  python pick_ink.py --image src\scene.png --region 0,0,1537,1100

输出：`ink`（主字色）、`ink2`（次级，提亮 12%，用于 tagline 这类）
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image


def rel_lum(rgb):
    """WCAG 相对亮度（0..1），rgb 为 0-255。"""
    c = np.asarray(rgb, np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def darken_to(rgb, max_lum, keep_hue=True):
    """把颜色往黑压，直到相对亮度 ≤ max_lum（尽量保色相：整体缩放）。"""
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
    ap = argparse.ArgumentParser(description="取画面里占比最大的深色当字色")
    ap.add_argument("--image", required=True)
    ap.add_argument("--region", default="", help="只看某块区域 x0,y0,x1,y1（默认整幅）")
    ap.add_argument("--dark-pct", type=float, default=18.0,
                    help="取最暗的百分比参与统计（默认 18%%；太大→偏灰，太小→偏噪点）")
    ap.add_argument("--bins", type=int, default=8, help="三维直方图每维格数（默认 8）")
    ap.add_argument("--top-bins", type=int, default=3, help="取最重的几格算加权均值（默认 3）")
    ap.add_argument("--max-lum", type=float, default=0.045,
                    help="保底：把字色压到相对亮度 ≤ 此值（默认 0.045 ≈ 4.5:1 上限）")
    ap.add_argument("--json", default=None, help="可选：把结果写成 json 供 run 脚本读取")
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
        print("暗部像素太少，请调大 --dark-pct", file=sys.stderr)
        return 2

    # 三维直方图 → 最重的若干格
    b = max(2, a.bins)
    idx = np.clip((dark / 256.0 * b).astype(int), 0, b - 1)
    flat = idx[:, 0] * b * b + idx[:, 1] * b + idx[:, 2]
    cnt = np.bincount(flat, minlength=b ** 3)
    top = np.argsort(cnt)[::-1][:max(1, a.top_bins)]
    w = cnt[top].astype(np.float32)
    w = w / max(w.sum(), 1e-6)
    sel = np.isin(flat, top)
    dom = dark[sel].mean(axis=0)
    # 用格心加权再修正一次（格心比格内均值更稳）
    centers = np.stack([(top // (b * b)), (top // b) % b, top % b], axis=1).astype(np.float32)
    center_rgb = (centers + 0.5) / b * 256.0
    dom = (center_rgb * w[:, None]).sum(axis=0) * 0.5 + dom * 0.5

    ink = darken_to(dom, a.max_lum)
    ink2 = np.clip(ink * 1.12 + 6, 0, 255)          # 次级：略提亮，仍够深
    res = {"ink": "#%02X%02X%02X" % tuple(int(round(v)) for v in ink),
           "ink2": "#%02X%02X%02X" % tuple(int(round(v)) for v in ink2),
           "dominant_dark_raw": "#%02X%02X%02X" % tuple(int(round(v)) for v in dom),
           "ink_rel_lum": round(rel_lum(ink), 4),
           "ink2_rel_lum": round(rel_lum(ink2), 4),
           "dark_pixels": int(dark.shape[0])}
    print("[pick_ink] %s（暗部 %.0f%% ｜ 取样 %d 像素）" % (a.image, a.dark_pct, dark.shape[0]))
    print("        画面主深色（原始）%s  → 保底压暗后 ink=%s（L=%.4f）｜ ink2=%s（L=%.4f）"
          % (res["dominant_dark_raw"], res["ink"], res["ink_rel_lum"],
             res["ink2"], res["ink2_rel_lum"]))
    if a.json:
        d = os.path.dirname(os.path.abspath(a.json))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print("        已写", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
