# -*- coding: utf-8 -*-
"""左下文字区光晕（深底排字护读）：背景左侧下部柔和提亮，保 WCAG 对比（先背景、后文字）。

口径（不可改）：增益由「探针矩形内的 WCAG 线性亮度 p5」反推——
  g = (target / p5)^(1/2.4) - 1 + 0.005，target 默认 0.26（近黑墨字 4.5:1 门槛之上）。
  注意 p5 必须是「线性亮度（0-1）」，用 sRGB 0-255 算会得到错误增益（实测踩坑）。

光晕形状（左下角）：m = ss((y-cy)/fy) * (1 - ss((x-cx)/fx))，ss 为 smoothstep；
  深底墨字配套：--ink 系近黑（案例 #171009），标签深棕。

用法（案例）：探针＝左下文字区四段矩形；自动算增益（案例实测 p5 0.139 → g 0.303）
  python textzone_glow.py --bg bg.kraft.png --out bg.glow.png `
      --zones "1150,1230,105,620;1240,1560,105,1050;1560,1770,105,950;1770,1835,105,460"
"""
import argparse
import os

import numpy as np
from PIL import Image


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def linear_lum(a):
    """a: (H,W,3) sRGB 0-255 → WCAG 线性相对亮度 (H,W) 0-1。"""
    a01 = a / 255.0
    lin = np.where(a01 <= 0.04045, a01 / 12.92, ((a01 + 0.055) / 1.055) ** 2.4)
    return lin @ np.array((0.2126, 0.7152, 0.0722), np.float32)


def main():
    ap = argparse.ArgumentParser(description="左下文字区光晕（深底排字护读）")
    ap.add_argument("--bg", required=True, help="输入背景 PNG")
    ap.add_argument("--out", required=True)
    ap.add_argument("--zones", default="", help="探针矩形 y0,y1,x0,x1 分号分隔（测 p5 用）")
    ap.add_argument("--target", type=float, default=0.26, help="目标线性亮度（p5 处）")
    ap.add_argument("--gain", type=float, default=None, help="手动覆盖增益")
    ap.add_argument("--cy", type=float, default=860.0, help="光晕 y 起点")
    ap.add_argument("--fy", type=float, default=300.0, help="y 羽化宽度")
    ap.add_argument("--cx", type=float, default=1060.0, help="光晕 x 右界")
    ap.add_argument("--fx", type=float, default=340.0, help="x 羽化宽度")
    args = ap.parse_args()

    im = Image.open(args.bg).convert("RGB")
    a = np.asarray(im, np.float32)
    H, W, _ = a.shape

    if args.gain is None:
        if not args.zones:
            ap.error("自动增益需 --zones（探针矩形）或手动 --gain")
        L = linear_lum(a)
        p5 = min(float(np.percentile(L[y0:y1, x0:x1], 5))
                 for y0, y1, x0, x1 in (tuple(int(v) for v in z.split(",")) for z in args.zones.split(";")))
        gain = (args.target / p5) ** (1 / 2.4) - 1.0 + 0.005
        print(f"       p5(linear) {p5:.4f} | gain {gain:.3f}")
    else:
        gain = args.gain

    y = np.arange(H, dtype=np.float32)[:, None]
    x = np.arange(W, dtype=np.float32)[None, :]
    m = (smoothstep((y - args.cy) / args.fy) * (1.0 - smoothstep((x - args.cx) / args.fx))).astype(np.float32)
    b = a * (1.0 + gain * m[..., None])
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).save(args.out)
    print("[textzone_glow]", args.out)


if __name__ == "__main__":
    main()