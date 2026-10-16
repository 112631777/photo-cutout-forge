#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""kraft_full.py —— 「满幅铺底」：照片铺满整张画布，材质当纸纹叠上（第四条取形路线）

什么时候用
----------
前三条路线都在「开一块口子」（横带／竖窗／斜块）。但参考 06/07/10/11（竹编艺术／徽州灯彩／
非遗文化之美）走的是另一条路：**照片直接铺满整张画布**，文字压在照片上 ——
老大原话：「尽可能让海报铺满，像这几张一样」。

本脚本做三件事：
  ① **照片铺满**（cover 缩放 ＋ 取景偏移；不裁到主体、不留白边）
  ② **材质当纸纹**（材质的高频细节 ＋ 低频明暗，按 --overlay 叠上去）——
     照片因此"吃"到同一张纸／石的质地，和我们另外三条路线是同一种质感语言
  ③ **四缘压暗 ＋ 轻调色**（--vignette/--tone）—— 给压在上面的字留出可读底子

用法
----
  python kraft_full.py --photo src\scene.png --material src\material.jpg `
      --out out\bg.png --focus 0.5,0.52 --overlay 0.45 --vignette 0.30 --tone 0.18

依赖：Pillow + numpy（复用 kraft_tear 的材质工具）
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

import kraft_tear as kt
from torn_edge import noise2d

W, H = kt.W, kt.H


def parse_pair(s):
    a, b = s.split(",")
    return float(a), float(b)


def blur01(a01, r):
    im = Image.fromarray(np.clip(a01 * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser(description="满幅铺底（照片铺满 ＋ 材质当纸纹 ＋ 四缘压暗）")
    ap.add_argument("--photo", required=True)
    ap.add_argument("--material", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--focus", default="0.5,0.5", help="照片里哪一点对齐画布中心（0..1）")
    ap.add_argument("--scale", type=float, default=1.0, help="在 cover 基础上再放大（>1 更近）")
    ap.add_argument("--overlay", type=float, default=0.45,
                    help="材质当纸纹的强度：0＝照片原样，0.45＝明显同纸，1＝几乎被材质吃掉")
    ap.add_argument("--material-gain", type=float, default=0.0, help="材质保留原色增益（0＝按暗/亮端重上色）")
    ap.add_argument("--material-gamma", type=float, default=0.52, help="材质色阶 gamma")
    ap.add_argument("--material-dark", default="185,170,153")
    ap.add_argument("--material-light", default="241,229,214")
    ap.add_argument("--tone", type=float, default=0.18, help="向材质色调整体偏色（0＝不偏）")
    ap.add_argument("--vignette", type=float, default=0.30, help="四缘压暗（0＝不压）")
    ap.add_argument("--vignette-gamma", type=float, default=2.2, help="压暗的径向曲线（越大越贴边）")
    ap.add_argument("--scrim", default="",
                    help="★ 局部压暗（文字区 scrim），形如 \"x0,y0,x1,y1,强度,羽化px;…\"（可多块）。"
                         "满幅铺底时照片各处的明暗不受控，浅色字压在亮墙上必然挂 —— "
                         "参考 110/111 之所以能压浅字，是因为那块底子本来就暗；"
                         "实测本案左上幕墙 P95=158（线亮度），浅字 CR 只有 1.31，"
                         "需要把最亮处压到 ≤37（≈sRGB 105）才够 4.5:1。")
    ap.add_argument("--grain", type=float, default=0.22, help="颗粒（0＝无）")
    ap.add_argument("--brightness", type=float, default=1.0)
    ap.add_argument("--contrast", type=float, default=1.0)
    a = ap.parse_args()

    # ---- ① 照片铺满（cover ＋ 取景）----
    ph = Image.open(a.photo).convert("RGB")
    pw, phh = ph.size
    sc = max(W / pw, H / phh) * a.scale
    pw2, ph2 = int(round(pw * sc)), int(round(phh * sc))
    ph2im = ph.resize((pw2, ph2), Image.LANCZOS)
    fx, fy = parse_pair(a.focus)
    ox = int(round(fx * pw2 - W / 2))
    oy = int(round(fy * ph2 - H / 2))
    ox = int(np.clip(ox, 0, max(0, pw2 - W)))
    oy = int(np.clip(oy, 0, max(0, ph2 - H)))
    img = np.asarray(ph2im.crop((ox, oy, ox + W, oy + H)), np.float32)
    print("[kraft_full] 照片 %dx%d → cover ×%.3f → %dx%d ｜ 取景 (%d,%d) ｜ 铺满 %dx%d"
          % (pw, phh, sc, pw2, ph2, ox, oy, W, H))

    # ---- ② 材质当纸纹 ----
    if a.material and a.overlay > 0:
        if a.material_gain > 0:
            kraft = kt.photo_native(a.material, gain=a.material_gain, gamma=a.material_gamma)
        else:
            kraft = kt.photo_cover(a.material,
                                   dark=tuple(int(v) for v in a.material_dark.split(",")),
                                   light=tuple(int(v) for v in a.material_light.split(",")))
        lo = blur01(np.clip(kraft.mean(axis=2) / 255.0, 0, 1), 42)[..., None]      # 低频明暗
        hi = kt.photo_detail(a.material)[..., None]                                # 高频细节
        lo = 0.80 + 0.40 * lo                                                       # 围绕 1.0 摆动
        img = img * (1.0 - a.overlay) + (img * lo + hi * 1.6) * a.overlay
        print("       ② 材质纸纹 overlay=%.2f ｜ 低频明暗＋高频细节都已叠上" % a.overlay)

    # ---- ③ 调色 / 压暗 / 颗粒 ----
    if a.tone > 0 and a.material:
        mean_mat = kraft.reshape(-1, 3).mean(axis=0)
        mean_img = img.reshape(-1, 3).mean(axis=0)
        img = img * (1.0 - a.tone) + (img - mean_img + mean_mat) * a.tone
        print("       ③ 向材质色调偏色 tone=%.2f" % a.tone)
    if a.brightness != 1.0:
        img = img * a.brightness
    if a.contrast != 1.0:
        img = (img - 127.5) * a.contrast + 127.5
    if a.vignette > 0:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.414
        v = 1.0 - a.vignette * np.clip(r, 0, 1) ** a.vignette_gamma
        img = img * v[..., None]
        print("       ③ 四缘压暗 vignette=%.2f（gamma %.1f）" % (a.vignette, a.vignette_gamma))

    # ---- ③b 文字区 scrim：把文字所在的那几块底子压下去 ----
    if a.scrim:
        yy, xx = np.mgrid[0:H, 0:W]
        for k, part in enumerate(a.scrim.split(";")):
            part = part.strip()
            if not part:
                continue
            v = [float(t) for t in part.replace("，", ",").split(",")]
            x0, y0, x1, y1, strength = v[:5]
            feather = v[5] if len(v) > 5 else 80.0
            m = np.zeros((H, W), np.float32)
            m[int(max(0, y0)):int(min(H, y1)), int(max(0, x0)):int(min(W, x1))] = 1.0
            m = blur01(m, feather / 2.0)                 # 羽化 → 不留硬边
            img = img * (1.0 - strength * m[..., None])
            print("       ③b scrim#%d  (%d,%d)-(%d,%d) 强度 %.2f 羽化 %.0f"
                  % (k + 1, x0, y0, x1, y1, strength, feather))
    if a.grain > 0:
        g = noise2d(W, H, seed=11, octaves=4, base=10)[..., None]
        img = img * (1.0 + a.grain * 0.18 * g)

    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(a.out)
    arr = np.asarray(Image.open(a.out).convert("L")).astype(np.float32)
    print("       成品亮度：均值 %.0f ｜ P5 %.0f ｜ P95 %.0f" % (arr.mean(), np.percentile(arr, 5), np.percentile(arr, 95)))
    print("[kraft_full]", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
