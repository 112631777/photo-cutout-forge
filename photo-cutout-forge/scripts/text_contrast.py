#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
text_contrast.py —— 文字／底板对比度诊断 + 护读底衬生成

为什么需要它
------------
`check_contrast.py` 的口径是「字框内**最暗 5% 的单像素**（深字）／最亮 5%（浅字）」——
这是**保守的合规线**，保证"最坏情况下也读得出来"。但它**不等于视觉感受**：
材质背景（土墙／岩壁／撕纸）明暗斑驳，P5 过线了，眼睛看到的却是
「黑字混在深一块浅一块的花底里」——这就是用户反馈的「文字和底板颜色太相近」。

本脚本补两个口径：

  ① **中位口径** `cr_p50`：字色 vs 背景**中位数**的对比度 —— 对应"整体观感"。
  ② **杂度** `std`：字框内亮度的标准差 —— 对应"底子花不花"。
     std 高时即使对比度够，字也会"糊进纹理里"，需要**描边**或**底衬**。

然后按诊断结果给出可执行建议，并可选 **生成护读底衬**（`--plate`）：
在文字区做局部**保色相提亮**（深字）或压暗（浅字），大半径羽化自然融入材质。

用法
----
  # 只看诊断
  python text_contrast.py --bg out/poster.bg.png --boxes out/poster.boxes.json

  # 生成护读底衬到 out/bg.png（供重新渲染用；原图请先另存）
  python text_contrast.py --bg out/poster.bg.png --boxes out/poster.boxes.json \
      --plate out/bg.png --report out/text-contrast.json

依赖：Pillow + numpy
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE_W = 1500.0          # 母版设计画布宽（boxes 的坐标系）
BUSY_STD = 26.0          # 字框内亮度 std 超过它 → 判「底子花」，建议描边/底衬
MIN_EDGE_CR = 3.6        # 中位口径的最低接受值（低于它＝视觉上明显不够）


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
    ap.add_argument("--bg", required=True, help="「隐藏文字层」渲染的 PNG（同 check_contrast 的 --bg）")
    ap.add_argument("--boxes", required=True)
    ap.add_argument("--ink", default=None, help="统一指定字色；不给则逐个用 boxes 里的 computed color")
    ap.add_argument("--plate", default=None, help="输出护读底衬图（覆盖为新的 bg.png 后重新渲染）")
    ap.add_argument("--report", default=None, help="诊断报告 JSON")
    ap.add_argument("--pad", type=int, default=44, help="底衬相对字框外扩的像素（设计坐标）")
    ap.add_argument("--strength", type=float, default=0.15, help="底衬强度（提亮/压暗幅度）")
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
        cr_p5 = cr(lt, p5)      # 机检口径（最坏情况）
        cr_p50 = cr(lt, p50)    # 视觉口径（整体观感）
        cr_mean = cr(lt, mean)
        busy = (std * 255) >= BUSY_STD

        advice = []
        if cr_p50 < MIN_EDGE_CR:
            advice.append("视觉对比不足（中位口径 %.2f）→ 字色需再深/再浅一档" % cr_p50)
            need_plate = True
        if busy:
            advice.append("底子花（std %.0f）→ 加浅色描边 / 加字重" % (std * 255))
            n_busy += 1
        if cr_p5 < 4.5:
            advice.append("最暗处不足（P5 口径 %.2f）→ 必须加护读底衬" % cr_p5)
            need_plate = True
        if not advice:
            advice.append("达标")

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
        flag = "OK " if (i["cr_p50"] >= MIN_EDGE_CR and not i["busy"]) else "注意"
        print("[%s] %-10s CR(最暗) %5.2f  CR(中位) %5.2f  std %4.0f  %s"
              % (flag, i["role"], i["cr_p5"], i["cr_p50"], i["bg_std"], " / ".join(i["advice"])))
    print("[text_contrast] 最差视觉对比 %.2f ；底子花 %d 项 ；建议底衬 %s"
          % (worst_vis, n_busy, "是" if need_plate else "否"))

    # ---------------- 护读底衬 ----------------
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

        # 深字 → 提亮底衬；浅字 → 压暗底衬。用「保色相刻度 V」的做法，
        # 避免直接乘算把材质洗白。
        lts = [rel_lum(parse_color(a.ink) if a.ink else parse_color(b.get("color", "rgb(0,0,0)")))
               for b in boxes]
        dark_text = (sum(lts) / max(1, len(lts))) < 0.18
        k = (1.0 + mk * a.strength) if dark_text else (1.0 - mk * a.strength)
        mx = arr.max(axis=2, keepdims=True)
        sc = np.where(mx > 1e-6, np.clip(mx * k, 0.0, 1.0) / np.maximum(mx, 1e-6), 1.0)
        out = np.clip(arr * sc, 0, 1)
        Image.fromarray((out * 255).astype(np.uint8)).save(a.plate)
        # 变化量审计
        delta = (np.abs(out - arr).mean(axis=2) * 255)
        print("[text_contrast] 底衬已写出 %s（%s，强度 %.2f，最大局部变化 %.0f，全图均值变化 %.2f）"
              % (a.plate, "提亮" if dark_text else "压暗", a.strength,
                 delta.max(), delta.mean()))

    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        json.dump(report, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[text_contrast] 报告 -> %s" % a.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
