#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
cutout.py —— AI 白底素材 → 透明底主体 PNG（alpha）

photo-cutout-forge 的第 ② 步：把「纯白底抠图素材」变成可信的透明底主体，
供 auto_compose.py 上纸。只依赖 PIL + numpy。

链：白底素材 → 亮度→alpha 公式 → 去噪门控 → 收边/柔边 → 裁边留白 → 模式着色

alpha 公式（实测）：
    a = clip((white − L) / (white − floor), 0, 1) ** gamma
    默认 white=255, floor=36, gamma=0.92。
    white 可用 --auto-white 从四周边缘中位亮度自动估（米黄底素材如双色平涂版）。

模式：
    color   保留原色（全彩抠图素材）
    ink     单色剪影（--ink，默认 #2A231A）
    duotone 预设 LUT 平涂 + 彩度保留（--preset，默认青金）

用法：
    python cutout.py --image cand\A.png --out cut\A.png --mode color --trim --pad 16
    python cutout.py --image cand\B.png --out cut\B.png --mode ink --trim --pad 16
    python cutout.py --image cand\C.png --out cut\C.png --mode color --auto-white --trim
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS_PATH = os.path.join(HERE, "..", "assets", "presets.json")

# 去噪门控参数
SPEC_THRESH = 0.28   # 二值化门槛：之下视为背景
SPEC_STRONG = 0.55   # 强信号门槛：之上无条件保留（保护细/薄结构）


def rgb_of(hx):
    return np.array([int(hx[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def load_presets():
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_lut(preset, gamma=1.0):
    """四段 LUT：明度 → 暗/中/亮/纸（与 auto_compose 的双色调一致）。"""
    shadow, mid, light = rgb_of(preset["shadow"]), rgb_of(preset["mid"]), rgb_of(preset["light"])
    paper = rgb_of(preset["paper"])
    top = paper * 0.5 + np.array([255.0, 255.0, 248.0], np.float32) * 0.5
    pts = [(0.0, shadow), (0.45, mid), (0.82, light), (1.0, top)]
    lut = []
    for i in range(256):
        t = (i / 255.0) ** (1.0 / gamma)
        c = pts[-1][1]
        for j in range(len(pts) - 1):
            a0, c0 = pts[j]
            a1, c1 = pts[j + 1]
            if t <= a1 or j == len(pts) - 2:
                u = 0.0 if a1 == a0 else (t - a0) / (a1 - a0)
                u = min(1.0, max(0.0, u))
                c = c0 * (1.0 - u) + c1 * u
                break
        lut.extend(int(round(float(v))) for v in c)
    return lut


def auto_white(img):
    """从四周边缘条带估背景亮度（中位）：米黄底素材（如双色平涂版）用。"""
    a = np.asarray(img.convert("L"), np.float32)
    h, w = a.shape
    m = max(2, int(round(min(h, w) * 0.03)))
    edge = np.concatenate([a[:m].ravel(), a[-m:].ravel(), a[:, :m].ravel(), a[:, -m:].ravel()])
    return float(np.median(edge))


def alpha_from_luma(img, white, floor, gamma):
    L = np.asarray(img.convert("L"), np.float32)
    a = np.clip((white - L) / max(1.0, white - floor), 0.0, 1.0) ** gamma
    return a


def despeckle(a, k):
    """去噪门控：开运算除小斑点，强信号区无条件保留（护住细条纹/薄纱）。

    gate = open(bin(a>SPEC_THRESH), k) ∪ bin(a>SPEC_STRONG)
    """
    if k <= 1:
        return a
    b = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    spec = b.point(lambda v: 255 if v >= SPEC_THRESH * 255 else 0)
    strong = b.point(lambda v: 255 if v >= SPEC_STRONG * 255 else 0)
    gate = spec.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    gate = Image.fromarray(np.maximum(np.asarray(gate), np.asarray(strong)))
    return a * (np.asarray(gate, np.float32) / 255.0)


def apply_mode(img, a, mode, ink, preset):
    if mode == "color":
        return img.convert("RGB")
    if mode == "ink":
        col = rgb_of(ink)
        arr = np.tile(col, (img.size[1], img.size[0], 1)).astype(np.float32)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if mode == "duotone":
        duo = np.asarray(img.point(build_lut(preset["presets"][preset] if "presets" in preset else preset)),
                         np.float32)
        hsv = img.convert("HSV")
        sat = np.asarray(hsv.getchannel("S"), np.float32) / 255.0
        g = np.asarray(img.convert("L"), np.float32) / 255.0
        w = (0.45 * np.clip(sat * 2.2, 0.0, 1.0) * np.clip(1.5 - 1.1 * g, 0.2, 1.0))[..., None]
        orig = np.asarray(img, np.float32)
        mixed = duo * (1.0 - w) + orig * w
        gray = mixed.mean(axis=2, keepdims=True)
        mixed = gray + (mixed - gray) * 1.12
        return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8))
    raise ValueError(f"未知模式：{mode}")


def main():
    ap = argparse.ArgumentParser(description="白底素材 → 透明底主体 PNG")
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="color", choices=["color", "ink", "duotone"])
    ap.add_argument("--ink", default="#2A231A", help="ink 模式剪影色")
    ap.add_argument("--preset", default="青金", help="duotone 模式预设名")
    ap.add_argument("--white", type=float, default=255.0, help="背景亮度参考（纯白=255）")
    ap.add_argument("--auto-white", action="store_true", help="从边缘条带自动估背景亮度")
    ap.add_argument("--floor", type=float, default=36.0, help="全不透明处的亮度下限")
    ap.add_argument("--gamma", type=float, default=0.92)
    ap.add_argument("--shrink", type=int, default=0, help="收边像素（除白边，1–2 常用）")
    ap.add_argument("--feather", type=float, default=0.8, help="柔边半径（0 关）")
    ap.add_argument("--despeckle", type=int, default=5, help="去噪门控核尺寸（0 关）")
    ap.add_argument("--trim", action="store_true", help="裁到主体 bbox")
    ap.add_argument("--pad", type=int, default=16, help="裁边后保留的透明边")
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    white = auto_white(img) if a.auto_white else a.white
    alpha = alpha_from_luma(img, white, a.floor, a.gamma)
    alpha = despeckle(alpha, a.despeckle)

    alpha_img = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8))
    if a.shrink > 0:
        k = a.shrink * 2 + 1
        alpha_img = alpha_img.filter(ImageFilter.MinFilter(k))
    if a.feather > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(a.feather))

    rgb = apply_mode(img, alpha, a.mode, a.ink, load_presets())
    out = rgb.convert("RGBA")
    out.putalpha(alpha_img)

    if a.trim:
        arr = np.asarray(alpha_img, np.float32)
        ys, xs = np.where(arr > 6.0)
        if len(xs):
            p = a.pad
            box = (max(0, int(xs.min()) - p), max(0, int(ys.min()) - p),
                   min(out.size[0], int(xs.max()) + 1 + p), min(out.size[1], int(ys.max()) + 1 + p))
            out = out.crop(box)

    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    out.save(a.out)

    ov = float((np.asarray(out.getchannel("A"), np.float32) > 128).mean())
    print(f"[cutout] {a.out}  {out.size[0]}x{out.size[1]}  mode={a.mode}  "
          f"white={white:.0f} floor={a.floor:.0f} 主体占比={ov:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())