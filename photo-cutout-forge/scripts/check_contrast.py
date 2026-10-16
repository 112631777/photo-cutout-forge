#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_contrast.py —— 可读性机检（WCAG 对比度），返回码可直接接流程

口径（不可改，改了要和 analyze 类脚本同步）：
  背景亮度取「文字矩形内**单像素 P95**（浅字）/ P5（深字）」——
  不能用均值。均值会把局部高光平均掉，导致「报告说可读、实际糊掉」。

输入：
  --boxes    render_png.py 导出的文字元素 JSON
  --full     成品 PNG（用于报告，可选）
  --bg       「隐藏文字层」渲染的 PNG（对比度的背景参照，必需）
  --json     输出报告路径（可选）
  --canvas   成品画布宽度（默认取 bg 图宽度），用于换算字号门槛

判据：
  字号 ≥ 48px @1500 画布宽 → 大字号，门槛 3.0 : 1；其余 4.5 : 1
  另附：溢出标记（文字是否超出容器）、背景杂度（矩形内亮度标准差）

返回码：0 = 全部达标；1 = 存在不达标项
依赖：Pillow
"""

import argparse
import json
import os
import sys

from PIL import Image

BASE_W = 1500.0
LARGE_PX = 48.0          # @1500 画布宽 的大字号分界
LARGE_RATIO = 3.0
NORMAL_RATIO = 4.5


def _lin_lut():
    """sRGB 亮度（0-255）→ 相对亮度 的查表。"""
    lut = []
    for i in range(256):
        c = i / 255.0
        lut.append((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) * 255.0)
    return lut


LUT = _lin_lut()


def _rel_lum(rgb):
    """WCAG 相对亮度（0-1），rgb 为 0-255。"""
    r, g, b = rgb
    return 0.2126 * (LUT[r] / 255.0) + 0.7152 * (LUT[g] / 255.0) + 0.0722 * (LUT[b] / 255.0)


def _lum_image(rgb_im):
    """把 RGB 图转成 WCAG 相对亮度图（0-255 编码），供直方图取分位。"""
    r, g, b = rgb_im.split()
    from PIL import ImageChops
    r = r.point(LUT).point(lambda v: v * 0.2126)
    g = g.point(LUT).point(lambda v: v * 0.7152)
    b = b.point(LUT).point(lambda v: v * 0.0722)
    return ImageChops.add(ImageChops.add(r, g), b)


def contrast_ratio(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _bg_stats(im_gray_lut, box, inset=0.14):
    """返回矩形内的背景 (P5, P50, P95, mean, std)。

    inset：取样区域向内收缩的比例。**不可设为 0**：元素边缘常带圆角、
    描边或抗锯齿，会把「按钮外的暗角」算成文字背景，造成误判。
    """
    x, y, w, h = box
    dx = max(2, int(w * inset))
    dy = max(2, int(h * inset))
    x0, y0 = x + dx, y + dy
    x1, y1 = x + w - dx, y + h - dy
    if x1 <= x0 or y1 <= y0:
        x0, y0, x1, y1 = x, y, x + max(1, w), y + max(1, h)
    crop = im_gray_lut.crop((x0, y0, x1, y1))
    hist = crop.histogram()                      # 256 bins（线性亮度已映射到 0-255）
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


def parse_color(css):
    css = css.strip()
    if css.startswith("rgb"):
        parts = css[css.index("(") + 1:css.index(")")].replace("%", "").split(",")
        return tuple(int(float(p)) for p in parts[:3])
    return (255, 255, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boxes", required=True)
    ap.add_argument("--bg", required=True)
    ap.add_argument("--full", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--canvas", type=float, default=None, help="画布 CSS 宽度（默认 1500）")
    a = ap.parse_args()

    with open(a.boxes, encoding="utf-8") as f:
        boxes = json.load(f)
    bg = Image.open(a.bg).convert("RGB")
    scale = bg.size[0] / (a.canvas or BASE_W)
    canvas_w = a.canvas or BASE_W
    # 线性亮度图（WCAG 口径）
    bg_lut = _lum_image(bg)

    report = {"bg_image": os.path.abspath(a.bg), "canvas_width": canvas_w,
              "threshold_rule": f"大字号(≥{int(LARGE_PX)}px @{int(canvas_w)}) {LARGE_RATIO}:1，其余 {NORMAL_RATIO}:1",
              "pixel_rule": "背景亮度取矩形内单像素 P95（浅字）/ P5（深字），非均值",
              "items": []}
    fails = []
    for b in boxes:
        x = int(round(b["x"] * scale))
        y = int(round(b["y"] * scale))
        w = int(round(b["w"] * scale))
        h = int(round(b["h"] * scale))
        p5, p50, p95, mean, std = _bg_stats(bg_lut, (x, y, w, h))
        t_rgb = parse_color(b.get("color", "rgb(255,255,255)"))
        l_text = _rel_lum(t_rgb)
        worst = p95 if l_text >= p50 else p5
        ratio = contrast_ratio(l_text, worst)
        large = b.get("fontSize", 0) >= LARGE_PX * canvas_w / BASE_W
        need = LARGE_RATIO if large else NORMAL_RATIO
        ok = ratio + 1e-9 >= need
        item = {
            "role": b.get("role"), "text": (b.get("text") or "")[:40],
            "font_size": round(b.get("fontSize", 0), 1), "large_text": large,
            "text_color": "#%02X%02X%02X" % t_rgb,
            "bg_p5": round(p5 * 255, 1), "bg_p50": round(p50 * 255, 1), "bg_p95": round(p95 * 255, 1),
            "bg_std": round(std * 255, 1), "contrast": round(ratio, 2), "required": need,
            "pass": ok, "overflow_x": b.get("overflowX", False), "overflow_y": b.get("overflowY", False),
        }
        report["items"].append(item)
        if not ok:
            fails.append(item["role"])
        if item["overflow_x"] or item["overflow_y"]:
            fails.append(item["role"] + "(溢出)")

    report["pass"] = not fails
    report["failed_roles"] = fails
    out = a.json or os.path.splitext(a.bg)[0] + ".readability.json"
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    for it in report["items"]:
        flag = "OK " if it["pass"] else "FAIL"
        print(f"[{flag}] {it['role']:<14} {it['contrast']:>5.2f} (需 {it['required']})  "
              f"字号 {it['font_size']:>5.1f}  bgP95 {it['bg_p95']:>5.1f}  {it['text'][:24]}")
    print(f"[check_contrast] {'全部达标' if report['pass'] else '存在不达标：' + ', '.join(fails)}  -> {out}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())