#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
auto_compose.py —— 背景艺术化 + 自动构图：原图 + 透明底主体 → 处理好的背景（bg.png）

photo-cutout-forge 的第 ③ 步（需求 ①③⑤ 的落点）：
  1. 先处理背景：原图经「取景（focus）→ 放大/缩小（zoom）→ 裁剪 → 双色调 →
     蒙版（lens 羽化椭圆）→ 正片叠底」成为纸面上的一扇「背景窗」；
  2. 主体（抠图 alpha）以 over 方式立于纸面，其余留白；
  3. 自动构图：读主体的宽高比与质量重心，自选四版式之一（hero-top/right/left/centre），
     并在 plan.json 写明中文理由；人可 --layout 覆盖；
  4. 内置 checks（主体×文字区、背景×文字区、留白率、落画），不过按 0.92 步缩重试；
  5. 只出背景，文字排版是母版（poster-cutout-master.html）的事——铁律「先背景后文字」。

另有 --bg-mode color：不叠背景窗，改从原图提取「主色＋副色」做偏置双色渐变底场
  （主色约 2/3，副色自下缘斜入；平滑无斑点）＋主体 over——纯色渐变底＋清晰主体＋书法字的
  路线（主色 --bg-color 可覆盖）。

视觉模型：纸面（make_ground）→ 背景窗（multiply）→ 主体（over）→（之后才是文字）

用法：
    python auto_compose.py --source src.png --subject cut\A.png --preset 青金 --seed 3 \
        --out out\bg.png --plan out\plan.json [--layout hero-top] [--debug out\debug.png]
    python auto_compose.py --list-layouts
"""

import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS_PATH = os.path.join(HERE, "..", "assets", "presets.json")
W, H = 1500, 1875          # 画布 4:5
Q = 4                      # 机检降采样倍率

# ---------------------------------------------------------------------------
# 四版式（起始参数；实测以 plan.json 的 checks 全过为准）
# ---------------------------------------------------------------------------
LAYOUTS = {
    "hero-top": {
        "when": "主体宽高比 ≥ 1.18（横向岛屿）",
        "reason": "主体横向展开，作横幅式上置岛屿，下方整片纸面承字",
        "backdrop": {"cx": 0.50, "cy": 0.335, "rx": 0.415, "ry": 0.265, "zoom": 2.8},
        "subject": {"mode": "width", "target": 0.72, "cap": 0.46, "cx": 0.50, "top": 0.115},
        "text_zone": [0.07, 0.62, 0.93, 0.97],
    },
    "hero-right": {
        "when": "宽高比 ≤ 0.80 且质量重心 x > 0.50",
        "reason": "主体竖长，作立柱式侧置；质量重心偏右，让出左侧整栏纸面",
        "backdrop": {"cx": 0.70, "cy": 0.45, "rx": 0.235, "ry": 0.30, "zoom": 1.5},
        "subject": {"mode": "height", "target": 0.52, "cap": 0.38, "cx": 0.775, "bottom": 0.84},
        "text_zone": [0.06, 0.12, 0.50, 0.92],
    },
    "hero-left": {
        "when": "宽高比 ≤ 0.80 且质量重心 x ≤ 0.50",
        "reason": "主体竖长，作立柱式侧置；质量重心偏左，让出右侧整栏纸面",
        "backdrop": {"cx": 0.30, "cy": 0.45, "rx": 0.235, "ry": 0.30, "zoom": 1.5},
        "subject": {"mode": "height", "target": 0.52, "cap": 0.38, "cx": 0.225, "bottom": 0.84},
        "text_zone": [0.50, 0.12, 0.94, 0.92],
    },
    "hero-centre": {
        "when": "其余（0.80–1.18，方正）",
        "reason": "主体方正，居中浮岛，四周留纸、下缘承字",
        "backdrop": {"cx": 0.50, "cy": 0.315, "rx": 0.40, "ry": 0.245, "zoom": 2.4},
        "subject": {"mode": "width", "target": 0.60, "cap": 0.42, "cx": 0.50, "top": 0.14},
        "text_zone": [0.07, 0.62, 0.93, 0.97],
    },
    "hero-band": {  # 满幅长卷：不自动选取（胆量较大），需 --layout hero-band 人工指定
        "when": "全景横幅（宽高比 ≥ 1.30）且要满幅长卷",
        "reason": "全景长卷满幅横贯，作壁上长卷；下缘整片纸面承字",
        "backdrop": None,
        "subject": {"mode": "width", "target": 1.0, "cap": 0.62, "cx": 0.50, "top": 0.030},
        "text_zone": [0.07, 0.635, 0.93, 0.98],
    },
}
FEATHER = 30.0


# ---------------------------------------------------------------------------
# 颜色 / 预设 / LUT / 纸面（与 cutout.py 同一套口径）
# ---------------------------------------------------------------------------
def rgb_of(hx):
    return np.array([int(hx[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def mix(a, b, t):
    return a * (1.0 - t) + b * t


def load_presets():
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_lut(preset, gamma=1.0):
    shadow, mid, light = rgb_of(preset["shadow"]), rgb_of(preset["mid"]), rgb_of(preset["light"])
    paper = rgb_of(preset["paper"])
    top = mix(paper, np.array([255.0, 255.0, 248.0], np.float32), 0.5)
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
                c = mix(c0, c1, min(1.0, max(0.0, u)))
                break
        lut.extend(int(round(float(v))) for v in c)
    return lut


def make_ground(preset, seed, size=(W, H)):
    """纸面：纸色 + 低频斑驳 + 细纹噪点 + 稀疏暗斑 + 四角轻压。"""
    w, h = size
    rng = np.random.default_rng(seed)
    arr = np.tile(rgb_of(preset["paper"]), (h, w, 1)).astype(np.float32)
    low = rng.normal(0, 1, (h // 28 + 2, w // 28 + 2)).astype(np.float32)
    mot = np.asarray(Image.fromarray(((low * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8))
                     .resize((w, h), Image.BICUBIC), np.float32) / 255.0 - 0.5
    arr += (mot * 10.0)[..., None]
    arr += rng.normal(0, float(preset.get("grain", 0.05)) * 255.0 * 0.5, (h, w, 1)).astype(np.float32)
    n = int(w * h * 0.00030)
    idx = rng.choice(w * h, size=n, replace=False)
    arr.reshape(-1, 3)[idx] *= 0.965
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.sqrt(((xx / w - 0.5) * 2) ** 2 + ((yy / h - 0.5) * 2) ** 2) / 1.414
    arr *= (1.0 - 0.05 * rr ** 2)[..., None]
    return np.clip(arr, 0, 255)


# ---------------------------------------------------------------------------
# 背景色填充（--bg-mode color）：从原图提取主色 → 深色底场＋织物肌理
# ---------------------------------------------------------------------------
def rgb_hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(max(0.0, min(255.0, float(v))))) for v in rgb)


def rgb2hsv(rgb):
    r, g, b = [float(v) / 255.0 for v in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d <= 1e-6:
        return 0.0, 0.0, mx
    if mx == r:
        h = ((g - b) / d) % 6.0
    elif mx == g:
        h = (b - r) / d + 2.0
    else:
        h = (r - g) / d + 4.0
    return h * 60.0, d / mx, mx


def hsv2rgb(h, s, v):
    i = int(h // 60.0) % 6
    f = h / 60.0 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]
    return np.array([r, g, b], np.float32) * 255.0


def _lift_rgb(col, amount):
    """提亮一个颜色（保持色相/饱和，V×(1+amount)）。"""
    h, s, v = rgb2hsv(col)
    return hsv2rgb(h, s, min(1.0, v * (1.0 + amount)))


def _kmeans(a, k=4, iters=14, seed=11):
    rng = np.random.default_rng(seed)
    c = a[rng.choice(len(a), k, replace=False)].copy()
    for _ in range(iters):
        lab = ((a[:, None, :] - c[None, :, :]) ** 2).sum(-1).argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                c[j] = a[m].mean(0)
    w = np.bincount(lab, minlength=k).astype(np.float32) / len(a)
    o = np.argsort(-w)
    return c[o], w[o]


def extract_bg_color(src, override="auto", seed=11):
    """原图 → (底场主色, 副色, 主色簇 hex 列表)。

    主色：取「饱和像素」（S>0.28、18%<V<85%）聚类里 权重×饱和度 最高的一簇，
    向深色压（V≤0.46、S≥0.32）——保留照片自身色相，不退成灰；
    副色：与主色色相距离最大、且权重 ≥6% 的簇，压得更沉（S×0.92／V×0.78）——
    两色同为深色系，供「非五五开」的偏置渐变（见 bg_ground）。
    override 传 #RRGGBB 时主色直接采用（副色仍从原图簇中选）。
    """
    im = src.convert("RGB")
    hh = max(2, int(round(220 * im.height / im.width)))
    flat = np.asarray(im.resize((220, hh), Image.BILINEAR), np.float32).reshape(-1, 3)
    f01 = flat / 255.0
    mx, mn = f01.max(1), f01.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    m = (sat > 0.28) & (mx > 0.18) & (mx < 0.85)
    pool = flat[m] if int(m.sum()) >= 60 else flat
    c, w = _kmeans(pool, min(4, len(pool)), seed=seed)
    palette = [rgb_hex(ci) for ci in c]
    if override and override != "auto":
        base = np.array([int(override[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
        h, s, v = rgb2hsv(base)
    else:
        score = w * np.array([rgb2hsv(ci)[1] for ci in c], np.float32)
        h, s, v = rgb2hsv(c[int(score.argmax())])
        base = hsv2rgb(h, min(0.62, max(0.32, s * 1.15)), min(0.46, max(0.30, v * 0.74)))
    j, dh_max = None, -1.0
    for k in range(len(c)):
        hk = rgb2hsv(c[k])[0]
        dh = abs(hk - h) % 360.0
        dh = min(dh, 360.0 - dh)
        if w[k] >= 0.06 and dh > dh_max:
            j, dh_max = k, dh
    if j is not None and dh_max >= 20.0:
        h2, s2, v2 = rgb2hsv(c[j])
        second = hsv2rgb(h2, min(0.52, max(0.28, s2 * 0.92)), min(0.38, max(0.28, v2 * 0.78)))
    else:
        second = hsv2rgb(h, min(0.60, s * 0.85), min(0.40, max(0.30, v * 0.95)))
    return base, second, palette


def bg_ground(base, second, seed, size=(W, H), grad="diag", vignette=0.0):
    """底场＝双色偏置渐变（主色占大面，副色自下缘进入）——平滑无斑点，不叠任何肌理。

    考量：文字与信息集中在下方 → 副色自下缘进入、右重左轻（避开左侧密排文字列，
    标题一带留在主色上，金色大字对比最稳）；上方主体区保持主色纯底（图底一致）。
    过渡用 smoothstep 缓入缓出、非五五开（u<临界值全为主色）；仅 0.8σ 抖动防色带。
    grad="diag"＝自右下角斜入（u=0.62y+0.38x）；grad="up"＝自下缘向上竖版（u=0.88y+0.12x）。
    vignette>0 时四缘轻压暗，把视线收拢到中部主体。
    """
    w, h = size
    rng = np.random.default_rng(seed + 977)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yn, xn = yy / (h - 1), xx / (w - 1)
    if grad == "up":
        u = 0.88 * yn + 0.12 * xn
        t = np.clip((u - 0.56) / 0.38, 0.0, 1.0)
    else:
        u = 0.62 * yn + 0.38 * xn       # 0＝上缘 → 1＝下缘右侧
        t = np.clip((u - 0.52) / 0.42, 0.0, 1.0)
    t = (t * t * (3.0 - 2.0 * t))[..., None]
    arr = (np.asarray(base, np.float32)[None, None, :] * (1.0 - t)
           + np.asarray(second, np.float32)[None, None, :] * t)
    arr += rng.normal(0, 0.8, (h, w, 1)).astype(np.float32)
    if vignette > 0:
        rr = np.sqrt(((xn - 0.5) * 2) ** 2 + ((yn - 0.5) * 2) ** 2) / 1.414
        arr *= (1.0 - float(vignette) * rr ** 2)[..., None]
    return np.clip(arr, 0, 255)


def pop_subject(img, amount):
    """主体轻提饱和＋对比（alpha 不动）——深底上让主体更「立」起来（0.2–0.3 为宜）。"""
    r, g, b, aa = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    sc = hsv.getchannel("S").point(lambda v: min(255, int(v * (1.0 + 0.35 * amount))))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), sc, hsv.getchannel("V"))).convert("RGB")
    arr = np.asarray(rgb, np.float32)
    arr = np.clip((arr - 128.0) * (1.0 + 0.22 * amount) + 128.0, 0, 255)
    out = Image.fromarray(arr.astype(np.uint8), "RGB")
    return Image.merge("RGBA", (*out.split(), aa))


def paint_subject(img, amount):
    """主体「重绘」：去噪平滑 → 提饱和/提亮 → 对比 → 色彩分层量化。

    把实拍主体往插画/手绘的「饱和度高、色彩鲜明、色块干净」方向推
    （参考海报的织锦缎带即此观感）；amount 0–1（0.6 起见量化块面感）。
    """
    r, g, b, aa = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = rgb.filter(ImageFilter.MedianFilter(3))                 # 1) 去噪：抹照片噪点，色块更整
    hsv = rgb.convert("HSV")
    sc = hsv.getchannel("S").point(lambda v: min(255, int(v * (1.0 + 0.90 * amount))))
    vc = hsv.getchannel("V").point(lambda v: min(255, int(v * (1.0 + 0.10 * amount))))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), sc, vc)).convert("RGB")
    arr = np.asarray(rgb, np.float32)                              # 2) 对比
    arr = np.clip((arr - 128.0) * (1.0 + 0.30 * amount) + 128.0, 0, 255)
    rgb = Image.fromarray(arr.astype(np.uint8), "RGB")
    if amount >= 0.45:                                             # 3) 色彩分层量化：手绘块面感
        colors = max(40, int(round(88 - 48 * amount)))
        rgb = rgb.quantize(colors=colors, method=Image.MEDIANCUT,
                           dither=Image.Dither.NONE).convert("RGB")
    return Image.merge("RGBA", (*rgb.split(), aa))


def lift_subject(img, amount):
    """主体提亮（保持色相/饱和，V×(1+amount)；alpha 不动）。"""
    r, g, b, aa = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    v = hsv.getchannel("V").point(lambda x: min(255, int(x * (1.0 + amount))))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), hsv.getchannel("S"), v)).convert("RGB")
    return Image.merge("RGBA", (*rgb.split(), aa))


# ---------------------------------------------------------------------------
# 背景窗：取景 → 双色调 → 蒙版
# ---------------------------------------------------------------------------
def crop_window(src, focus, aspect, zoom):
    sw, sh = src.size
    hh = sh / max(0.2, float(zoom))
    ww = hh * aspect
    if ww > sw:
        ww = float(sw)
        hh = ww / aspect
    if hh > sh:
        hh = float(sh)
        ww = hh * aspect
    cx, cy = focus[0] * sw, focus[1] * sh
    x0 = min(max(cx - ww / 2.0, 0.0), sw - ww)
    y0 = min(max(cy - hh / 2.0, 0.0), sh - hh)
    return [round(x0), round(y0), round(x0 + ww), round(y0 + hh)]


def lens_bbox(bd, pad=40.0):
    cx, cy = bd["cx"] * W, bd["cy"] * H
    rx, ry = bd["rx"] * W, bd["ry"] * H
    return [cx - rx - pad, cy - ry - pad, cx + rx + pad, cy + ry + pad]


def lens_mask(bd, bbox, feather=FEATHER):
    bx0, by0, bx1, by1 = bbox
    bw, bh = int(round(bx1 - bx0)), int(round(by1 - by0))
    ss = 2
    big = Image.new("L", (bw * ss, bh * ss), 0)
    d = ImageDraw.Draw(big)
    cx, cy = (bd["cx"] * W - bx0) * ss, (bd["cy"] * H - by0) * ss
    rx, ry = bd["rx"] * W * ss, bd["ry"] * H * ss
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    m = big.resize((bw, bh), Image.LANCZOS)
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather / 2.0))
        m = m.point(lambda v: min(255, int(v * 1.28)))
    return m


def build_backdrop(src, bd, preset, chroma, focus, wash=0.32, blur=0.0):
    """原图 → 背景窗 RGBA（取景 → 双色调 → 彩度 → 柔焦 → 向纸色融合 → 蒙版）及其 bbox。"""
    bbox = lens_bbox(bd)
    bx0, by0 = bbox[0], bbox[1]
    bw, bh = int(round(bbox[2] - bx0)), int(round(bbox[3] - by0))
    crop = crop_window(src, focus, bw / bh, bd.get("zoom", 1.4))
    sub = src.crop(crop).resize((bw, bh), Image.LANCZOS)
    plate = sub.point(build_lut(preset)).convert("RGB")

    if chroma > 0:
        hsv = sub.convert("HSV")
        sat = np.asarray(hsv.getchannel("S"), np.float32) / 255.0
        g = np.asarray(sub.convert("L"), np.float32) / 255.0
        w = (chroma * np.clip(sat * 2.2, 0.0, 1.0) * np.clip(1.5 - 1.1 * g, 0.2, 1.0))[..., None]
        duo = np.asarray(plate, np.float32)
        org = np.asarray(sub, np.float32)
        mx = duo * (1.0 - w) + org * w
        gray = mx.mean(axis=2, keepdims=True)
        mx = gray + (mx - gray) * 1.12
        plate = Image.fromarray(np.clip(mx, 0, 255).astype(np.uint8))

    if blur > 0:  # 柔焦：背景退成「色场」，与清晰主体拉开图底层级
        plate = plate.filter(ImageFilter.GaussianBlur(blur))

    if wash > 0:  # 向纸色融合：让窗成为「褪色印品」而非透出的照片
        paper = rgb_of(preset["paper"])
        mx = np.asarray(plate, np.float32) * (1.0 - wash) + paper * wash
        plate = Image.fromarray(np.clip(mx, 0, 255).astype(np.uint8))

    mask = lens_mask(bd, bbox)
    rgba = plate.convert("RGBA")
    rgba.putalpha(mask)
    return rgba, [int(round(bx0)), int(round(by0))], crop


def _clip(dst_shape, pos, size):
    x0, y0 = pos
    nw, nh = size
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(dst_shape[1], x0 + nw), min(dst_shape[0], y0 + nh)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    return (cx0, cy0, cx1, cy1, cx0 - x0, cy0 - y0)


def composite(arr, rgba, pos, mode="over"):
    clip = _clip(arr.shape, pos, rgba.size)
    if not clip:
        return
    cx0, cy0, cx1, cy1, sx0, sy0 = clip
    p = np.asarray(rgba.convert("RGB"), np.float32)[sy0:sy0 + (cy1 - cy0), sx0:sx0 + (cx1 - cx0)]
    a = np.asarray(rgba.getchannel("A"), np.float32)[sy0:sy0 + (cy1 - cy0),
                                                      sx0:sx0 + (cx1 - cx0)][..., None] / 255.0
    dst = arr[cy0:cy1, cx0:cx1]
    src = dst * p / 255.0 if mode == "multiply" else p
    arr[cy0:cy1, cx0:cx1] = dst * (1.0 - a) + src * a


# ---------------------------------------------------------------------------
# 主体度量与版式选择（需求 ①：自主选择构图）
# ---------------------------------------------------------------------------
def subject_metrics(subj):
    a = np.asarray(subj.getchannel("A"), np.float32)
    ys, xs = np.where(a > 8.0)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    w, h = x1 - x0, y1 - y0
    sub = a[y0:y1, x0:x1]
    total = float(sub.sum())
    mass_cx = float((sub * np.arange(w)[None, :]).sum() / total / max(1, w)) if total else 0.5
    return {"aspect": w / h, "mass_cx": mass_cx, "bbox": [x0, y0, x1, y1]}


def pick_layout(m):
    if m["aspect"] >= 1.18:
        return "hero-top"
    if m["aspect"] <= 0.80:
        return "hero-right" if m["mass_cx"] > 0.50 else "hero-left"
    return "hero-centre"


def subject_rect(subj_bbox, spec, scale):
    """按版式锚点算主体在画布中的 rect（px）。"""
    x0, y0, x1, y1 = subj_bbox
    w, h = (x1 - x0) * scale, (y1 - y0) * scale
    cx = spec["cx"] * W
    left = cx - w / 2.0
    if "top" in spec:
        top = spec["top"] * H
    else:
        top = spec["bottom"] * H - h
    return [left, top, w, h]


def fit_scale(subj_bbox, spec):
    w, h = subj_bbox[2] - subj_bbox[0], subj_bbox[3] - subj_bbox[1]
    if spec["mode"] == "width":
        return min(spec["target"] * W / w, spec["cap"] * H / h)
    return min(spec["target"] * H / h, spec["cap"] * W / w)


# ---------------------------------------------------------------------------
# 机检（降采样到 1/Q 计算）
# ---------------------------------------------------------------------------
def _small_alpha(img, q=Q):
    img = img.convert("L")
    return np.asarray(img.resize((max(1, img.size[0] // q), max(1, img.size[1] // q)),
                                 Image.BILINEAR), np.float32) / 255.0


def _paste(canvas, arr, pos):
    x, y = int(round(pos[0] / Q)), int(round(pos[1] / Q))
    h, w = arr.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.shape[1], x + w), min(canvas.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1],
                                      arr[y0 - y:y1 - y, x0 - x:x1 - x])


def checks(sub_c, bd_rgba, bd_pos, rect, text_zone):
    cw, ch = W // Q, H // Q
    a_sub = np.zeros((ch, cw), np.float32)
    a_bd = np.zeros((ch, cw), np.float32)
    sub_l = sub_c.getchannel("A").resize(
        (max(1, int(round(rect[2] / Q))), max(1, int(round(rect[3] / Q)))), Image.BILINEAR)
    _paste(a_sub, np.asarray(sub_l, np.float32) / 255.0, (rect[0], rect[1]))
    _paste(a_bd, _small_alpha(bd_rgba.getchannel("A")), bd_pos)

    zx0, zy0 = int(text_zone[0] * W / Q), int(text_zone[1] * H / Q)
    zx1, zy1 = int(text_zone[2] * W / Q), int(text_zone[3] * H / Q)
    zone = (slice(zy0, zy1), slice(zx0, zx1))
    z_area = max(1, (zy1 - zy0) * (zx1 - zx0))
    ov_sub = float((a_sub[zone] > 0.10).sum()) / z_area
    ov_bd = float((a_bd[zone] > 0.12).sum()) / z_area
    covered = (a_sub > 0.04) | (a_bd > 0.12)
    blank = float(1.0 - covered.mean())

    in_canvas = (rect[0] >= -1 and rect[1] >= -1 and
                 rect[0] + rect[2] <= W + 1 and rect[1] + rect[3] <= H + 1)
    return {"subject_text_overlap": round(ov_sub, 4), "backdrop_text_overlap": round(ov_bd, 4),
            "blank_ratio": round(blank, 4), "subject_in_canvas": bool(in_canvas)}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="背景艺术化 + 自动构图 → bg.png + plan.json")
    ap.add_argument("--source", required=True, help="原照片")
    ap.add_argument("--subject", required=True, help="透明底主体 PNG（cutout.py 产出）")
    ap.add_argument("--preset", default="青金")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--layout", default=None, choices=list(LAYOUTS.keys()))
    ap.add_argument("--focus", nargs=2, type=float, default=[0.5, 0.40],
                    help="背景窗取景对焦点（原图分数坐标）")
    ap.add_argument("--chroma", type=float, default=0.55, help="双色调彩度保留 0–1")
    ap.add_argument("--wash", type=float, default=0.40, help="背景窗向纸色融合 0–1（越大越像褪色印品）")
    ap.add_argument("--bd-blur", type=float, default=10.0, help="背景窗柔焦半径（与清晰主体拉开层级）")
    ap.add_argument("--bd-zoom", type=float, default=None, help="覆盖版式的背景窗放大倍率")
    ap.add_argument("--subject-target", type=float, default=None,
                    help="覆盖版式的主体目标尺寸（占画布宽/高比例，默认取版式表）")
    ap.add_argument("--debug", default=None, help="画出主体 rect 与文字区，供目检")
    ap.add_argument("--no-backdrop", action="store_true", help="不放背景窗（纯纸面背景，主体直接落纸）")
    ap.add_argument("--bg-mode", choices=["window", "color"], default="window",
                    help="背景处理方式：window=原图背景窗（柔焦＋双色调）；color=提取原图主色＋副色做偏置渐变底场（无窗）")
    ap.add_argument("--bg-color", default="auto",
                    help="color 模式主色：auto=自动提取，或 #RRGGBB 指定（副色始终从原图提取）")
    ap.add_argument("--bg-grad", choices=["diag", "up"], default="diag",
                    help="color 模式渐变方向：diag=自右下斜入；up=自下缘向上竖版")
    ap.add_argument("--bg-vignette", type=float, default=0.0,
                    help="color 模式四缘压暗 0–0.3（收拢视线、提主体；不宜过大）")
    ap.add_argument("--bg-lift", type=float, default=0.0,
                    help="color 模式底场提亮 0–0.4（主/副色 V×(1+lift)，色相饱和不变）")
    ap.add_argument("--subject-pop", type=float, default=0.0,
                    help="主体提饱和/对比 0–0.5（深底上让主体更立；0.2–0.3 为宜）")
    ap.add_argument("--subject-paint", type=float, default=0.0,
                    help="主体重绘 0–1：去噪平滑＋提饱和/提亮＋对比＋色彩分层量化（≥0.45 出手绘块面感）")
    ap.add_argument("--subject-lift", type=float, default=0.0,
                    help="主体提亮 0–0.4（V×(1+lift)，色相饱和不变；配 --subject-paint 用）")
    ap.add_argument("--shadow", type=float, default=0.0,
                    help="主体投影强度 0–1（0=无；主体与纸面对比不足时用 0.25–0.35）")
    ap.add_argument("--shadow-blur", type=float, default=26.0, help="投影模糊半径（px）")
    ap.add_argument("--shadow-dy", type=float, default=20.0, help="投影下移量（px）")
    ap.add_argument("--reflection", type=float, default=0.0,
                    help="主体倒影强度 0–1（0=无；纸面下缘接一道渐隐的矿彩倒影，给底图层次）")
    ap.add_argument("--reflection-blur", type=float, default=28.0, help="倒影模糊半径（px）")
    ap.add_argument("--paper", default=None, help="覆盖纸色（十六进制，如 #E8DCC0）")
    ap.add_argument("--list-layouts", action="store_true")
    a = ap.parse_args()

    if a.list_layouts:
        for k, v in LAYOUTS.items():
            print(f"{k:12s} {v['when']}")
        return 0

    presets = load_presets()["presets"]
    if a.preset not in presets:
        print(f"未知预设：{a.preset}（可选：{'、'.join(presets)}）", file=sys.stderr)
        return 2
    preset = dict(presets[a.preset])
    if a.paper:
        preset["paper"] = a.paper

    src = Image.open(a.source).convert("RGB")
    subj = Image.open(a.subject).convert("RGBA")
    m = subject_metrics(subj)
    sub_c = subj.crop(tuple(m["bbox"]))     # 裁到主体 bbox：rect 与 checks 同口径

    layout = a.layout or pick_layout(m)
    spec = dict(LAYOUTS[layout])
    spec["subject"] = dict(spec["subject"])
    if a.subject_target:
        spec["subject"]["target"] = a.subject_target
    reason = spec["reason"] + ("（--layout 指定）" if a.layout else "（自动判定）")

    scale = fit_scale(m["bbox"], spec["subject"])
    rect = subject_rect(m["bbox"], spec["subject"], scale)
    for _ in range(3):
        if rect[0] >= 0 and rect[1] >= 0 and rect[0] + rect[2] <= W and rect[1] + rect[3] <= H:
            break
        rect[0] = min(max(rect[0], 0), W - rect[2])
        rect[1] = min(max(rect[1], 0), H - rect[3])

    bd = dict(spec["backdrop"]) if spec.get("backdrop") else None
    if a.no_backdrop:
        bd = None
    base_col, second_col, palette_cols = None, None, []
    if a.bg_mode == "color":          # 颜色填充模式：不放背景窗，提取 主色＋副色 做偏置渐变底场
        bd = None
        base_col, second_col, palette_cols = extract_bg_color(src, a.bg_color, seed=a.seed)
        if a.bg_lift > 0:             # 底场整体提亮（色相/饱和不变）
            base_col = _lift_rgb(base_col, a.bg_lift)
            second_col = _lift_rgb(second_col, a.bg_lift)
    if a.bd_zoom and bd:
        bd["zoom"] = a.bd_zoom
    text_zone = spec["text_zone"]
    if bd:
        bd_rgba, bd_pos, crop = build_backdrop(src, bd, preset, a.chroma, a.focus, a.wash, a.bd_blur)
    else:
        bd_rgba, bd_pos, crop = Image.new("RGBA", (1, 1), (0, 0, 0, 0)), (0, 0), []
    ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)

    tries = 0
    while ck["subject_text_overlap"] > 0.02 and tries < 4:      # 主体按 0.92 步缩
        tries += 1
        scale *= 0.92
        rect = subject_rect(m["bbox"], spec["subject"], scale)
        ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)
    tries_bd = 0
    while bd and ck["backdrop_text_overlap"] > 0.02 and tries_bd < 4:  # 背景窗同样步缩
        tries_bd += 1
        bd["rx"] *= 0.92
        bd["ry"] *= 0.92
        bd_rgba, bd_pos, crop = build_backdrop(src, bd, preset, a.chroma, a.focus, a.wash, a.bd_blur)
        ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)
    while bd and ck["blank_ratio"] < 0.40 and tries_bd < 6:            # 留白不足 → 背景窗再缩
        tries_bd += 1
        bd["rx"] *= 0.94
        bd["ry"] *= 0.94
        bd_rgba, bd_pos, crop = build_backdrop(src, bd, preset, a.chroma, a.focus, a.wash, a.bd_blur)
        ck = checks(sub_c, bd_rgba, bd_pos, rect, text_zone)

    ck["pass"] = (ck["subject_text_overlap"] <= 0.02 and ck["backdrop_text_overlap"] <= 0.02
                  and ck["blank_ratio"] >= 0.40 and ck["subject_in_canvas"])

    # 合成：底场（纸面／提取色底场）→ 背景窗（multiply）→ 倒影/投影 → 主体（over）
    arr = (bg_ground(base_col, second_col, a.seed, grad=a.bg_grad, vignette=a.bg_vignette)
           if a.bg_mode == "color" else make_ground(preset, a.seed))
    composite(arr, bd_rgba, bd_pos, mode="multiply")
    sub_s = sub_c.resize((max(1, int(round(rect[2]))), max(1, int(round(rect[3])))), Image.LANCZOS)
    if a.subject_pop > 0:     # 主体突出：轻提饱和/对比（深底上更「立」）
        sub_s = pop_subject(sub_s, a.subject_pop)
    if a.subject_paint > 0:   # 主体重绘：提饱和/提亮＋量化（参考海报的鲜明观感）
        sub_s = paint_subject(sub_s, a.subject_paint)
    if a.subject_lift > 0:    # 主体提亮（色相/饱和不变）
        sub_s = lift_subject(sub_s, a.subject_lift)
    sx, sy = int(round(rect[0])), int(round(rect[1]))
    if a.reflection > 0:      # 倒影：主体翻转、压缩、重模糊，向下渐隐——给纸面下缘一段矿彩层次
        rw, rh = sub_s.size
        rl = sub_s.transpose(Image.FLIP_TOP_BOTTOM).resize(
            (rw, max(1, int(rh * 0.24))), Image.LANCZOS).filter(ImageFilter.GaussianBlur(a.reflection_blur))
        ra = np.asarray(rl.getchannel("A"), np.float32) / 255.0
        ramp = np.linspace(1.0, 0.0, ra.shape[0], dtype=np.float32)[:, None]
        rl.putalpha(Image.fromarray((ra * ramp * a.reflection * 255.0).astype(np.uint8)))
        composite(arr, rl, (sx, int(round(sy + rect[3] - 4))), mode="over")
    if a.shadow > 0:          # 投影：主体 alpha 模糊下移，拉开与纸面的对比（先影后主体）
        sa = sub_s.getchannel("A").filter(ImageFilter.GaussianBlur(a.shadow_blur))
        sa = sa.point(lambda v: int(v * a.shadow))
        sh_rgb = Image.new("RGB", sub_s.size, (40, 33, 25))
        composite(arr, Image.merge("RGBA", (*sh_rgb.split(), sa)),
                  (sx, int(round(rect[1] + a.shadow_dy))), mode="over")
    composite(arr, sub_s, (sx, sy), mode="over")
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    if a.debug:
        dbg = out.copy()
        d = ImageDraw.Draw(dbg, "RGBA")
        if bd:
            d.rectangle([bd["cx"] * W - bd["rx"] * W, bd["cy"] * H - bd["ry"] * H,
                         bd["cx"] * W + bd["rx"] * W, bd["cy"] * H + bd["ry"] * H],
                        outline=(0, 120, 220, 255), width=4)
        d.rectangle([rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]],
                    outline=(220, 40, 40, 255), width=5)
        d.rectangle([text_zone[0] * W, text_zone[1] * H, text_zone[2] * W, text_zone[3] * H],
                    outline=(30, 160, 60, 255), width=5, fill=(30, 160, 60, 40))
        os.makedirs(os.path.dirname(os.path.abspath(a.debug)) or ".", exist_ok=True)
        dbg.save(a.debug)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    out.save(a.out)

    plan = {
        "layout": layout, "layout_reason": reason,
        "subject": {"aspect": round(m["aspect"], 3), "mass_cx": round(m["mass_cx"], 3),
                    "rect_px": [int(round(v)) for v in rect], "pop": a.subject_pop,
                    "paint": a.subject_paint, "lift": a.subject_lift},
        "backdrop": ({"shape": "lens", "cx": round(bd["cx"], 3), "cy": round(bd["cy"], 3),
                      "rx": round(bd["rx"], 3), "ry": round(bd["ry"], 3),
                      "zoom": bd["zoom"], "focus": a.focus, "crop_px": crop,
                      "chroma": a.chroma, "wash": a.wash, "blur": a.bd_blur}
                     if bd else {"shape": "none"}),
        "text_zone": text_zone,
        "checks": ck,
        "shadow": ({"strength": a.shadow, "blur": a.shadow_blur, "dy": a.shadow_dy}
                   if a.shadow > 0 else None),
        "reflection": ({"strength": a.reflection, "blur": a.reflection_blur}
                       if a.reflection > 0 else None),
        "paper": {"preset": a.preset, "seed": a.seed, "color": preset["paper"]},
        "background": ({"mode": "color", "base": rgb_hex(base_col), "second": rgb_hex(second_col),
                       "grad": a.bg_grad, "vignette": a.bg_vignette, "lift": a.bg_lift,
                       "source_palette": palette_cols}
                       if a.bg_mode == "color" else {"mode": "window" if bd else "paper"}),
    }
    if a.plan:
        os.makedirs(os.path.dirname(os.path.abspath(a.plan)) or ".", exist_ok=True)
        with open(a.plan, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

    if a.bg_mode == "color":
        print(f"[compose] 底场渐变 {rgb_hex(base_col)} → {rgb_hex(second_col)}"
              f"（{'自下向上' if a.bg_grad == 'up' else '右下斜入'}"
              f"{'，四缘压暗 %.2f' % a.bg_vignette if a.bg_vignette > 0 else ''}；"
              f"提取簇 {'、'.join(palette_cols)}）")
    print(f"[compose] {a.out}  layout={layout}  {reason}")
    print(f"[compose] checks={json.dumps(ck, ensure_ascii=False)}")
    return 0 if ck["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())