#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""kraft_window.py —— 「竖向不规则开窗」：材质铺满，开一块**不规则竖向窗**露出照片

与 `kraft_photo.py`（横向撕口带）并列的第三条取形路线，2026-10-11 为 case16 加：

| 路线 | mask 语义 | 画面效果 | 适合 |
|---|---|---|---|
| `kraft_photo` | 每**列**的上下缘 → 横带 | 上／中／下三段 | 主体横向连贯、画面已分上下 |
| `kraft_tear`  | 同上，窗口＝抠图主体 | 同上 | 主体有凹口轮廓 |
| **`kraft_window`** | 每**行**的左右缘 → 竖窗 | **一块不规则竖向贴片** | **主体本身是竖向一团**（展示柜＋墙面投影、立像、器物…） |

窗口 alpha 直接取 mask（`band_mask.py --orient v --shape vpatch` 生成，已带分形噪声的不规则边），
把照片按 `--scale`／`--focus` 填进窗口，再做**羽化 ＋ 窗内投影 ＋ 洞口亮边**，
避免"照片贴上去"的假边。

用法（case16 展示柜）
--------------------
  python band_mask.py --w 1500 --h 1875 --orient v --shape vpatch --jitter 0.010 --out cut\win.png
  python kraft_window.py --win cut\win.png --photo src\scene.png --material src\material.jpg `
      --scale 2.13 --focus 0.617,0.5 --material-gamma 0.52 --out out\bg.png

依赖：Pillow + numpy
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

import kraft_tear as kt
from torn_edge import noise2d        # 同一个 scripts 目录；二维分形噪声复用

W, H = kt.W, kt.H


def parse_pair(s):
    a, b = s.split(",")
    return float(a), float(b)


def blur01(a01, r):
    """对 0..1 的 float 图做高斯模糊（走 uint8，PIL 的 F 模式不支持 GaussianBlur）。"""
    if r <= 0:
        return a01
    im = Image.fromarray(np.clip(a01 * 255.0, 0, 255).astype(np.uint8))
    im = im.filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser(description="竖向不规则开窗（材质铺满，窗口露照片）")
    ap.add_argument("--win", required=True, help="窗口 mask（RGBA；alpha>0.45 视为窗口内）")
    ap.add_argument("--photo", required=True, help="实拍原图（填进窗口）")
    ap.add_argument("--material", default="", help="材质素材照片（岩壁／土墙／纸…）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=2.0, help="照片放大倍率（px 画布 / px 照片）")
    ap.add_argument("--focus", default="0.5,0.5", help="照片里哪一点对准窗口质心（0..1 相对坐标）")
    ap.add_argument("--feather", type=float, default=2.4, help="窗口边羽化半径 px")
    ap.add_argument("--shadow", type=float, default=0.30, help="洞口内投影强度（材质投到照片上）")
    ap.add_argument("--rim", type=float, default=0.16, help="洞口外亮边强度（撕口纤维受光）")
    # ---- 质感三件套（2026-10-11 加：老大反馈「抠图后缺乏质感」）----
    ap.add_argument("--seam", type=float, default=0.42,
                    help="纸厚度暗线：紧贴边缘的一条窄暗环（让材质「压」在照片上，默认 0.42）")
    ap.add_argument("--fiber", type=float, default=0.55,
                    help="纤维搭边：材质的高频细节沿边缘盖到照片上（默认 0.55）")
    ap.add_argument("--grain", type=float, default=0.30,
                    help="同纸颗粒：让照片吃进材质的颗粒与色（0＝照片原样平贴，默认 0.30）")
    ap.add_argument("--photo-lift", type=float, default=0.0, help="窗口内容提亮量（0..1，暗素材可给 0.06）")
    ap.add_argument("--material-gain", type=float, default=0.0, help="材质保留原色：整体增益（0＝用 --material-dark/light 重上色）")
    ap.add_argument("--material-gamma", type=float, default=1.0, help="材质色阶 gamma")
    ap.add_argument("--material-dark", default="185,170,153", help="重上色暗端 R,G,B")
    ap.add_argument("--material-light", default="241,229,214", help="重上色亮端 R,G,B")
    ap.add_argument("--detail", type=float, default=0.06, help="材质细节（裂纹／颗粒）强度")
    ap.add_argument("--plate", default="", help="护读底衬（可选，叠加在文字区；留空不用）")
    a = ap.parse_args()

    # ---- 1) 材质铺满画布 ----
    if a.material:
        if a.material_gain > 0 or a.material_gamma != 1.0:
            kraft = kt.photo_native(a.material,
                                    gain=a.material_gain if a.material_gain > 0 else 1.0,
                                    gamma=a.material_gamma) \
                + kt.photo_detail(a.material)[..., None] * a.detail
        else:
            kraft = kt.photo_cover(a.material,
                                   dark=tuple(int(v) for v in a.material_dark.split(",")),
                                   light=tuple(int(v) for v in a.material_light.split(","))) \
                + kt.photo_detail(a.material)[..., None] * a.detail
    else:
        # 无材质时退化成素纸
        kraft = np.full((H, W, 3), 232.0, np.float32) \
            + np.random.default_rng(3).normal(0, 3.0, (H, W, 1)).astype(np.float32)
    canvas = kraft.copy()

    # ---- 2) 窗口 alpha ----
    # ★ 2026-10-11：改为**保留连续 alpha**（不再一刀切 0/1）——
    #   `torn_edge.py` 生成的纤维毛边就是靠 0.3–0.9 的过渡带体现的，
    #   之前这里 `> 0.45` 二值化会把它整条丢掉，于是"没有质感"。
    wm = Image.open(a.win).convert("RGBA")
    if wm.size != (W, H):
        wm = wm.resize((W, H), Image.LANCZOS)
    a_soft = np.asarray(wm)[..., 3].astype(np.float32) / 255.0    # 连续
    a0 = (a_soft > 0.45).astype(np.float32)                       # 仅用于统计/质心
    ys, xs = np.nonzero(a0)
    if ys.size == 0:
        print("窗口 mask 是空的", file=sys.stderr)
        return 2
    cx, cy = float(xs.mean()), float(ys.mean())
    wmax = np.abs(a0.sum(axis=1)).max()      # 窗最大行宽
    hspan = ys.max() - ys.min()
    print("[kraft_window] 窗口质心 (%.0f, %.0f) ｜ 外接 %.0f×%.0f px ｜ 最大行宽 %.0f"
          % (cx, cy, xs.max() - xs.min(), hspan, wmax))

    # ---- 3) 照片落位 ----
    ph = Image.open(a.photo).convert("RGB")
    pw, phh = ph.size
    sc = a.scale
    ph2 = ph.resize((max(1, int(round(pw * sc))), max(1, int(round(phh * sc)))), Image.LANCZOS)
    pa = np.asarray(ph2, np.float32)
    fx, fy = parse_pair(a.focus)
    ox = int(round(cx - fx * pw * sc))
    oy = int(round(cy - fy * phh * sc))
    # 越界处用**边缘钳制**（而不是补黑）——照片比窗口矮/窄时，窗口边缘不会露黑边，
    # 只是把最外一圈像素延展出去（暗素材上几乎看不出）。
    # ⚠ 坐标换算：pa 是**已放大**的照片，画布坐标直接减去落点即可（不要再除以 scale，
    #   否则会二次缩小、窗口显示到照片的另一片区域 —— case16 第一次就栽在这）。
    photo = np.zeros((H, W, 3), np.float32)
    sx = np.clip(np.arange(W) - ox, 0, pa.shape[1] - 1)
    for yy in range(H):
        sy2 = int(np.clip(yy - oy, 0, pa.shape[0] - 1))
        photo[yy] = pa[sy2][sx]
    print("       照片 %dx%d ｜ scale %.3f → %dx%d ｜ 落点 (%d, %d)"
          % (pw, phh, sc, ph2.size[0], ph2.size[1], ox, oy))
    if a.photo_lift > 0:
        photo = photo + (255.0 - photo) * a.photo_lift

    # ---- 4) 合成：羽化开窗（用**连续 alpha**，毛边因此得以保留）----
    af = blur01(a_soft, a.feather)
    canvas = canvas * (1.0 - af[..., None]) + photo * af[..., None]

    # ---- 4.5) ★ 质感三件套（2026-10-11 加）----
    # ① 纸厚度暗线：紧贴边缘的窄暗环 —— 材质像"压"在照片上，而不是和它拼在一起
    if a.seam > 0:
        tight = np.clip(a_soft - blur01(a_soft, 2.0), 0, 1)
        canvas = canvas * (1.0 - tight[..., None] * a.seam) \
            + kt.SHADE[None, None, :] * (tight[..., None] * a.seam)
        print("       ① 纸厚度暗线 seam=%.2f" % a.seam)
    # ② 纤维搭边：材质的高频细节沿边缘盖到照片上（毛边处最明显）
    if a.fiber > 0:
        det = kt.photo_detail(a.material)[..., None] if a.material else 0.0
        fib = blur01(a_soft, 1.6) * (1.0 - a_soft)          # 只在边缘外侧一圈
        canvas = canvas + (det * a.fiber) * fib[..., None]
        print("       ② 纤维搭边 fiber=%.2f" % a.fiber)
    # ③ 同纸颗粒：让**窗口里的照片**吃进材质的低频明暗 ＋ 一层细颗粒，
    #    于是它看起来是"印在同一张纸上"，而不是"贴上去的一张图"。
    if a.grain > 0:
        win = af[..., None]
        g = (0.5 + 0.5 * noise2d(W, H, seed=5, octaves=4, base=14))[..., None]     # 0..1 颗粒
        broad = blur01(np.clip(kraft.mean(axis=2) / 255.0, 0, 1), 40)[..., None] * 255.0
        canvas = canvas * (1 - 0.25 * a.grain * win) + broad * (0.25 * a.grain * win)
        canvas = canvas * (1 - 0.18 * a.grain * g * win) + (canvas * (0.88 + 0.24 * g)) * (0.18 * a.grain * g * win)
        print("       ③ 同纸颗粒 grain=%.2f" % a.grain)

    # ---- 5) 洞口内投影（材质边缘投到照片上）＋ 外亮边（纤维受光）----
    if a.shadow > 0:
        inner = np.clip(a0 - blur01(a0, max(3.0, a.feather * 3.0)), 0, 1)
        canvas = canvas * (1.0 - inner[..., None] * a.shadow) \
            + kt.SHADE[None, None, :] * (inner[..., None] * a.shadow)
    if a.rim > 0:
        outer = np.clip(blur01(a0, max(2.0, a.feather * 1.6)) - a0, 0, 1)
        canvas = canvas + outer[..., None] * (a.rim * 90.0)      # 亮边抬升的灰阶量

    # ---- 6) 可选护读底衬 ----
    if a.plate and os.path.exists(a.plate):
        pl = np.asarray(Image.open(a.plate).convert("RGB").resize((W, H), Image.LANCZOS), np.float32)
        plm = np.asarray(Image.open(a.plate).convert("RGBA").resize((W, H), Image.LANCZOS), np.float32)[..., 3] / 255.0
        canvas = canvas * (1 - plm[..., None]) + pl * plm[..., None]

    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(a.out)
    print("[kraft_window]", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
