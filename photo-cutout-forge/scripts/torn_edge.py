#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""torn_edge.py —— 把「光滑取形」变成**二维撕裂边缘**（多尺度 ＋ 咬痕 ＋ 纤维毛边）

为什么需要它（2026-10-11 老大反馈）
----------------------------------
`band_mask.py` 的取形是**一维挤出**的：横带是「每列一个上下缘」、竖窗是「每行一个左右缘」，
即使叠了 `--jitter` 分形噪声，本质仍是**一条光滑曲线＋抖动** —— 放大看就是"用刀切得有波浪"，
不是"撕出来的"。老大原话：「抠图图案还是太规整了，缺乏自然感」。

真实的撕裂边缘在**三个尺度**上同时不规则：

| 尺度 | 现象 | 本脚本做法 |
|---|---|---|
| 大（数十 px） | 缺口、鼓包 —— 形状整体走偏 | **2D 分形噪声位移**：把边界沿法向推动 `--edge` 比例 |
| 中（数 px～十数 px） | 一块块**被咬掉**的碎口 | `--bites` 个随机圆弧咬痕（沿边界随机取样心） |
| 小（1–3 px） | **纤维毛边**：半透明的细丝伸出／缩进 | `--fray` 高频噪声 → alpha 落在 0.3–0.9 的过渡带 |

⭐ 关键：**保留连续 alpha**（不做 0/1 二值化）——`kraft_window.py` 会用它把毛边
混进照片，于是纸的纤维真的"盖"在画面上，这一步是"质感"的来源。

用法
----
  python torn_edge.py --mask cut\win.png --out cut\win.torn.png `
      --edge 0.016 --bites 9 --bite-size 0.055 --fray 0.22 --seed 3

  # 想更"烂"：edge/bites/bite-size/fray 一起加大；想干净：都调小或设 0
依赖：Pillow + numpy
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter


# ---------------------------------------------------------------- 工具


def noise2d(w, h, seed=0, octaves=5, persist=0.55, base=8):
    """二维分形值噪声（多八度），值域约 −1..1。

    做法：每层生成一个很小的随机网格，再用双线性放大到目标尺寸后叠加 ——
    和 band_mask 里的 1D 版本同源，但**在二维上都不一样**，
    所以边界会被推向各个方向（这才是"撕"而不是"切"）。
    """
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total, step = 1.0, 0.0, max(3, base)
    while octaves > 0 and step >= 2:
        gw, gh = max(2, w // step + 1), max(2, h // step + 1)
        g = rng.normal(0.0, 1.0, (gh, gw)).astype(np.float32)
        layer = np.asarray(Image.fromarray(g, mode="F").resize((w, h), Image.BILINEAR), np.float32)
        out += layer * amp
        total += amp
        amp *= persist
        step = max(2, step // 2)
        octaves -= 1
    n = out / max(total, 1e-6)
    return np.clip(n / max(np.abs(n).max(), 1e-6), -1.0, 1.0)


def blur(a01, r):
    if r <= 0:
        return a01
    im = Image.fromarray(np.clip(a01 * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


# ---------------------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser(description="光滑取形 → 二维撕裂边缘（多尺度＋咬痕＋毛边）")
    ap.add_argument("--mask", required=True, help="输入 mask（RGBA，用 alpha）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--edge", type=float, default=0.018,
                    help="【大尺度】边界位移幅度（画布短边比例，0.01≈短边 1%%；默认 0.018）")
    ap.add_argument("--edge-scale", type=float, default=26.0,
                    help="【大尺度】位移的平滑半径 px（越大越「鼓包」、越小越「锯齿」）")
    ap.add_argument("--bites", type=int, default=8, help="【中尺度】咬痕数量（0＝不要）")
    ap.add_argument("--bite-size", type=float, default=0.05,
                    help="【中尺度】咬痕半径（画布短边比例）")
    ap.add_argument("--bite-depth", type=float, default=0.55,
                    help="【中尺度】咬痕中心离边界的距离（×半径；越小咬得越深）")
    ap.add_argument("--fray", type=float, default=0.55,
                    help="【小尺度】纤维毛边强度（alpha 抖动幅度，0＝硬边；0.5≈可见细丝）")
    ap.add_argument("--fray-px", type=float, default=3.0, help="纤维毛边的作用宽度 px")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--plate", default="", help="可选：把边缘 alpha 也写回该路径（调试用）")
    a = ap.parse_args()

    im = Image.open(a.mask).convert("RGBA")
    W, H = im.size
    arr = np.asarray(im).astype(np.float32)
    b = (arr[..., 3] > 127).astype(np.float32)          # 二值内部
    short = min(W, H)
    print("[torn_edge] %dx%d ｜ edge %.3f（≈%.0fpx）bites %d×r%.0fpx fray %.2f"
          % (W, H, a.edge, a.edge * short, a.bites, a.bite_size * short, a.fray))

    # ---- ① 大尺度：2D 分形噪声沿法向推动边界 ----
    # 边界附近由 blur 造出一条 0..1 的坡；叠加噪声后重新按 0.5 取阈值，
    # 位移量 ≈ 噪声幅度 × 坡宽 → 用 --edge / --edge-scale 控制。
    # ⚠⚠ **只在边界带内允许翻转**：第一版把噪声加到整张图上，
    #    实心区里噪声一旦低于阈值就在画面中间咬出麻点（实测截图里一排白点）。
    if a.edge > 0:
        ramp = blur(b, a.edge_scale)
        band = np.abs(ramp - 0.5) < 0.34            # 只有坡带内才可能翻边
        n = noise2d(W, H, seed=a.seed, octaves=5, base=10)
        disp = (a.edge * short) / max(a.edge_scale, 1e-6)
        flipped = (ramp + n * disp > 0.5).astype(np.float32)
        b = np.where(band, flipped, b)
        print("            ① 大尺度位移（等效 ±%.0fpx，仅坡带内生效）" % (a.edge * short))

    # ---- ② 中尺度：从**外侧**沿边界啃掉若干块 ----
    # ⚠⚠ 咬痕的圆心必须放在**外侧**（沿外法向推 r×depth），
    #    这样咬口与外缘连通、形成凹缺；第一版圆心取在边界上、再按错方向偏移，
    #    结果在画面中央留下一个个**浮空的材质圆斑**（实测踩过）。
    if a.bites > 0:
        rb = blur(b, 3.0)
        gyy, gxx = np.gradient(rb)
        inner_edge = (b > 0.5) & (rb < 0.90)        # 贴边内侧的一圈
        ys, xs = np.nonzero(inner_edge)
        if ys.size:
            rng = np.random.default_rng(a.seed + 17)
            yy, xx = np.mgrid[0:H, 0:W]
            done = 0
            for i in range(a.bites):
                k = int(rng.integers(0, ys.size))
                cy, cx = float(ys[k]), float(xs[k])
                r = a.bite_size * short * rng.uniform(0.55, 1.45)
                gy, gx = float(gyy[ys[k], xs[k]]), float(gxx[ys[k], xs[k]])
                norm = float(np.hypot(gy, gx)) + 1e-6
                # 外法向 = −梯度方向（梯度指向 b 增大的内侧）
                cy -= gy / norm * r * a.bite_depth * rng.uniform(0.5, 1.3)
                cx -= gx / norm * r * a.bite_depth * rng.uniform(0.5, 1.3)
                # ★ 用**随机椭圆**（长宽比与朝向都随机）而不是正圆：
                #   正圆咬出来是一排同款圆缺，反而"规整"（第一版就是那样）。
                ang = rng.uniform(0.0, np.pi)
                ca, sa = float(np.cos(ang)), float(np.sin(ang))
                ra = r * rng.uniform(0.70, 1.55)
                rb2 = r * rng.uniform(0.40, 0.95)
                dx, dy = xx - cx, yy - cy
                u = (dx * ca + dy * sa) / ra
                v = (-dx * sa + dy * ca) / rb2
                m = (u * u + v * v) < 1.0
                if not m.any():
                    continue
                b[m] = 0.0
                done += 1
            print("            ② 咬痕完成（%d 处，随机椭圆、均从外侧啃入）" % done)

    # ---- ③ 小尺度：纤维毛边（连续 alpha，不二值化）----
    if a.fray > 0:
        n_hi = noise2d(W, H, seed=a.seed + 41, octaves=3, persist=0.6, base=3)
        inside = blur(b, a.fray_px) * b                   # 由内向外衰减的带
        outside = (1.0 - b) * blur(b, a.fray_px * 1.6)    # 由外向内衰减的带
        a_final = np.clip(b + n_hi * a.fray * (inside - outside), 0.0, 1.0)
        print("            ③ 纤维毛边完成（过渡带 alpha 0.3–0.9）")
    else:
        a_final = b

    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = arr[..., 0], arr[..., 1], arr[..., 2]
    out[..., 3] = np.clip(a_final * 255.0, 0, 255).astype(np.uint8)
    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    Image.fromarray(out).save(a.out)

    inside_frac = float((a_final > 0.45).mean())
    fringe = float(((a_final > 0.15) & (a_final < 0.85)).mean())
    print("            覆盖 %.1f%% ｜ 过渡带（毛边）占 %.2f%% 像素"
          % (inside_frac * 100, fringe * 100))
    print("[torn_edge]", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
