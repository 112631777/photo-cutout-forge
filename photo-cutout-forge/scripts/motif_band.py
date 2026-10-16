#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
motif_band.py —— 纹样图带：主体 → 纹样切片 → 平面化 → S 形飘带排布

photo-cutout-forge 的「图带」路线（展览主视觉的另一种骨架，参考：越南丝绸展）：
  ① 取样：在主体 alpha 内按「饱和度 × 图案结构度」打分，逐枚贪心挑选
     N 枚互不重叠、色相彼此拉开的纹样切片（只取整幅 alpha≈255 的区域，
     杜绝抠图软边出镜）；
  ② 平面化：强去噪 → 提饱和 → 提对比 → 限色量化 —— 实拍肌理化为一格格
     干净色块（矿物色质感）；
  ③ 排带：白色 S 形飘带（恒定带宽、软投影、两端溢出画布），切片沿曲线逐一
     上带、随切线微转（钳 ±7°），每片上方一枚小字名签（默认按切片主色自动
     分配敦煌矿物色名，可用 --labels 覆盖）。

用法：
    python motif_band.py --source cut\A2c.png --out band\band.demo.png \
        --count 5 --colors 14 --seed 3
    python motif_band.py --list-pigments
"""

import argparse
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from auto_compose import rgb2hsv, hsv2rgb, rgb_of, rgb_hex   # 同目录，复用色彩工具

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(HERE, "..", "assets", "fonts")
W, H = 1500, 1875          # 画布 4:5（与母版同制式）
SS = 2                     # 超采样倍率

# 敦煌矿物色名（按色相归位；月白/黛按明度特判）
# 青金＝深蓝（近 215°）、石青＝亮蓝（近 207°）——同族按深浅分名
PIGMENTS = [("朱砂", 8.0), ("赭石", 26.0), ("藤黄", 48.0), ("石绿", 142.0),
            ("松石绿", 170.0), ("石青", 207.0), ("青金", 215.0), ("藏青", 236.0),
            ("绛紫", 312.0)]

BAND_RGB = (253, 252, 248)          # 飘带纸白
TAG_RGB = (70, 64, 52)              # 名签墨色


# ---------------------------------------------------------------------------
# ① 取样：主体内挑「有花纹、有颜色」的切片
# ---------------------------------------------------------------------------
def _work_image(src, width=900):
    sw, sh = src.size
    r = width / sw
    return src.resize((int(round(sw * r)), int(round(sh * r))), Image.BILINEAR), r


def dominant_key(rgb_img, k=6, share=0.10):
    """纹样切片 → 主导色：占比 ≥share 的量化模式色中「饱和×占比」最大者。

    取「最显著的颜色」而非「最大占比色」：多色混片的最大占比色常是灰调过渡
    色，会让名签指向画面上并不显眼的颜色；若只看饱和度又会偏袒小面积高饱和
    点缀。饱和×占比兼顾「面积」与「显色」，最接近肉眼看片时的第一印象。
    同一口径也用于「近似色降权」与名签命名，保证取样与标签一致。
    """
    sw, sh = rgb_img.size
    small = rgb_img.resize((96, max(2, int(round(96 * sh / sw)))), Image.BILINEAR)
    q = small.quantize(colors=k, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    cols = q.convert("RGB").getcolors(maxcolors=1 << 20)
    total = float(sum(c for c, _ in cols))
    doms = [(c, rgb) for c, rgb in cols if c / total >= share] or [max(cols)]
    return np.asarray(max(doms, key=lambda t: rgb2hsv(np.asarray(t[1], np.float32))[1]
                          * (t[0] / total))[1], np.float32)


def _tile_key(rgb_img, aspect, sat, con, small_w=72):
    """候选的「带上主色」：按平面化同口径先压成小样，再取主导色（供降权用）。"""
    return dominant_key(flatten_tile(rgb_img, 6,
                                     (small_w, max(2, int(round(small_w / aspect)))),
                                     sat=sat, con=con))


def pick_tiles(src, count, aspect, tile_src_w, sat=1.50, con=1.28, debug=False):
    """在主体 alpha 内挑 count 枚切片。

    评分＝(0.25+0.75·平均饱和)·(0.30+0.70·明度标准差归一)：
    既要有颜色、又要有花纹起伏；逐枚选取后对剩余候选做「近似色降权」
    （主导色的 RGB 距离），保证一组切片色彩彼此拉开（覆盖壁面的矿物色谱）。
    降权色取「同平面化口径」的切片主色——原始像素的红多为污砖色（近金棕），
    平面化提饱和后才显出真朱砂，必须按带上最终颜色判「近似」。
    """
    # 主体判据在「全分辨率」上构建（锐利、不受缩放渗色影响）：
    # alpha 若为「颜料浓度」软遮罩（A2c 型）并不可靠，统一按
    # 「近纯白且 alpha≈0」判外部（抠图常以白底作图）；取样只用 RGB（画作本体颜色）。
    full = np.asarray(src.convert("RGB"), np.float32)
    fa = np.asarray(src.getchannel("A"), np.float32)
    inside_full = ((fa >= 1.0) | (full.min(2) <= 232.0)).astype(np.uint8) * 255
    del full, fa

    work, r = _work_image(src)
    arr = np.asarray(work.convert("RGB"), np.float32)
    cover = np.asarray(Image.fromarray(inside_full, "L").resize(work.size, Image.BILINEAR),
                       np.float32) / 255.0           # 每工作像素的「主体内覆盖率」0–1
    mx = arr.max(2)
    mn = arr.min(2)
    satmap = np.where(mx > 1.0, (mx - mn) / np.maximum(mx, 1.0), 0.0)
    lum = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114

    tw = max(8, int(round(tile_src_w * r)))
    th = max(8, int(round(tw / aspect)))
    sw, sh = work.size
    step = max(6, int(round(tw * 0.33)))
    cands = []
    for y0 in range(0, max(1, sh - th) + 1, step):
        for x0 in range(0, max(1, sw - tw) + 1, step):
            if cover[y0:y0 + th, x0:x0 + tw].shape != (th, tw):
                continue
            if float(cover[y0:y0 + th, x0:x0 + tw].mean()) < 0.99:    # 整幅落在主体内
                continue
            s_m = float(satmap[y0:y0 + th, x0:x0 + tw].mean())
            l_t = lum[y0:y0 + th, x0:x0 + tw]
            col = arr[y0:y0 + th, x0:x0 + tw].reshape(-1, 3).mean(0)
            key = _tile_key(Image.fromarray(arr[y0:y0 + th, x0:x0 + tw].astype(np.uint8), "RGB"),
                            aspect, sat, con)
            score = (0.25 + 0.75 * s_m) * (0.30 + 0.70 * min(1.0, float(l_t.std()) / 40.0))
            cands.append({"x": x0, "y": y0, "score": score, "col": col, "key": key})
    print(f"[motif] 主体内合格候选 {len(cands)} 枚（取样 {tw}×{th} 工作像素）")
    if not cands:
        raise SystemExit("[motif] 主体内找不到全幅不透明的切片：请换源或减小取样尺寸")

    avail = list(cands)
    picked = []
    gx, gy = tw * 0.30, th * 0.30
    for _ in range(count):
        if not avail:
            break
        avail.sort(key=lambda c: -c["score"])
        if debug:
            top = " | ".join(f"{c['score']:.3f}·{rgb_hex(c['key'])}·({c['x']},{c['y']})"
                             for c in avail[:10])
            print(f"[motif.debug] 第{len(picked)+1}轮前10：{top}")
        best = avail[0]
        picked.append(best)
        print(f"[motif] 选{len(picked)}: {best['score']:.3f} 主导色={rgb_hex(best['key'])}"
              f" @工作像素({best['x']},{best['y']})")
        rest = []
        for c in avail[1:]:
            if not (c["x"] + tw + gx <= best["x"] or c["x"] >= best["x"] + tw + gx or
                    c["y"] + th + gy <= best["y"] or c["y"] >= best["y"] + th + gy):
                continue                                    # 与已选重叠 → 剔除
            # 与已选「近似色」降权：用「主导饱和色」的 RGB 距离（含明度），
            # 避免金(32°)与朱砂(15°)按纯色相被误判为同类，也避免被灰调均值色重罚
            dd = float(np.linalg.norm(c["key"] - best["key"]))
            c = dict(c)
            c["score"] *= (1.0 - 0.60 * math.exp(-((dd / 64.0) ** 2)))
            rest.append(c)
        avail = rest

    out = []
    for c in picked:
        x0 = max(0, int(round(c["x"] / r)))
        y0 = max(0, int(round(c["y"] / r)))
        x1 = min(src.size[0], int(round((c["x"] + tw) / r)))
        y1 = min(src.size[1], int(round((c["y"] + th) / r)))
        out.append({"rect": [x0, y0, x1, y1], "col": c["col"], "score": c["score"]})
    return out


# ---------------------------------------------------------------------------
# ② 平面化：强去噪 → 提饱和/对比 → 限色量化
# ---------------------------------------------------------------------------
def flatten_tile(rgb, colors, display_size, sat=1.85, con=1.28):
    """实拍肌理 → 干净色块（在显示尺寸上量化，色块边沿最锐）。"""
    rgb = rgb.filter(ImageFilter.MedianFilter(5))
    hsv = rgb.convert("HSV")
    s = hsv.getchannel("S").point(lambda v: min(255, int(v * sat)))
    v = hsv.getchannel("V").point(lambda v: min(255, int(v * 1.08)))
    rgb = Image.merge("HSV", (hsv.getchannel("H"), s, v)).convert("RGB")
    a = np.asarray(rgb, np.float32)
    a = np.clip((a - 128.0) * con + 128.0, 0, 255)
    rgb = Image.fromarray(a.astype(np.uint8), "RGB")
    rgb = rgb.resize(display_size, Image.LANCZOS)
    return rgb.quantize(colors=colors, method=Image.MEDIANCUT,
                        dither=Image.Dither.NONE).convert("RGB")


def name_for(key_rgb, used):
    """切片主色 → 矿物色名（先到先得；月白/黛按明度特判）。"""
    h, s, v = rgb2hsv(np.asarray(key_rgb, np.float32))
    if s < 0.25 and v > 0.80:
        nm = "月白"
    elif v < 0.24 and s < 0.30:
        nm = "黛"
    else:
        cand = [(m, min(abs(h - hc), 360.0 - abs(h - hc)))
                for m, hc in PIGMENTS if m not in used]
        if not cand:
            cand = [(m, min(abs(h - hc), 360.0 - abs(h - hc))) for m, hc in PIGMENTS]
        nm = min(cand, key=lambda t: t[1])[0]
    used.add(nm)
    return nm


# ---------------------------------------------------------------------------
# ③ 排带：底场渐变 + S 形飘带 + 切片/名签上带
# ---------------------------------------------------------------------------
def band_colors(src, top_override, bottom_override, hue_override=None):
    """从主体取主色相 → 淡底（上）+ 主色（下）两色。"""
    r, g, b, a = src.split()
    comp = Image.new("RGB", src.size, (243, 237, 226))
    comp.paste(src.convert("RGB"), (0, 0), a)
    small = comp.resize((260, max(2, int(260 * src.size[1] / src.size[0]))), Image.BILINEAR)
    arr = np.asarray(small, np.float32) / 255.0
    mx = arr.max(2)
    mn = arr.min(2)
    d = mx - mn
    ok = (d > 1e-4) & (mx > 0.15)
    r_, g_, b_ = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros_like(mx)
    ir = ok & (mx == r_)
    ig = ok & (mx == g_) & ~ir
    ib = ok & ~ir & ~ig
    hue[ir] = ((g_[ir] - b_[ir]) / d[ir]) % 6.0
    hue[ig] = (b_[ig] - r_[ig]) / d[ig] + 2.0
    hue[ib] = (r_[ib] - g_[ib]) / d[ib] + 4.0
    hue = (hue * 60.0) % 360.0
    sat = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    hist, edges = np.histogram(hue.ravel(), bins=12, range=(0, 360),
                               weights=(sat * ok).ravel())
    hp = (edges[hist.argmax()] + 15.0) % 360.0
    if hue_override is not None:
        hp = float(hue_override) % 360.0
    top = hsv2rgb(hp, 0.16, 0.93) if top_override is None else rgb_of(top_override)
    bot = hsv2rgb(hp, 0.50, 0.62) if bottom_override is None else rgb_of(bottom_override)
    return top, bot, hp


def bg_gradient(top, bottom, size, seed=7):
    """平滑对角渐变（左上淡、右下主色），仅 0.8σ 抖动防色带——零肌理。"""
    w, h = size
    rng = np.random.default_rng(seed + 313)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = 0.62 * (yy / (h - 1)) + 0.38 * (xx / (w - 1))
    t = np.clip((u - 0.18) / 0.82, 0.0, 1.0)
    t = (t * t * (3.0 - 2.0 * t))[..., None]
    arr = top[None, None, :] * (1.0 - t) + bottom[None, None, :] * t
    arr += rng.normal(0, 0.8, (h, w, 1)).astype(np.float32)
    return np.clip(arr, 0, 255)


def band_alpha(size, band_w, amp, cycles, phase):
    """S 形飘带 alpha：x_c(t)=0.5+amp·sin(2π(cycles·t+phase))，恒定带宽。"""
    w, h = size
    xs = np.arange(w, dtype=np.float32)[None, :]
    t = np.arange(h, dtype=np.float32)[:, None] / h
    xc = (0.5 + amp * np.sin(2.0 * math.pi * (cycles * t + phase))) * w
    half = band_w * w / 2.0
    m = (np.abs(xs - xc) <= half).astype(np.uint8) * 255
    return Image.fromarray(m, "L").filter(ImageFilter.GaussianBlur(2.5))


def curve_x(t, amp, cycles, phase):
    return 0.5 + amp * math.sin(2.0 * math.pi * (cycles * t + phase))


def curve_angle(t, amp, cycles, phase, canvas_h):
    dx = amp * W * 2.0 * math.pi * cycles * math.cos(2.0 * math.pi * (cycles * t + phase))
    return math.degrees(math.atan2(dx, canvas_h))


def blit_shadow(canvas, alpha, pos, blur, opacity, color=(32, 34, 40)):
    """把（小尺寸）alpha 贴到画布 pos 处，模糊后作为投影色块复合。"""
    w, h = canvas.size
    m = Image.new("L", (w, h), 0)
    m.paste(alpha.filter(ImageFilter.GaussianBlur(blur)), pos)
    m = m.point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", (w, h), color + (0,))
    sh.putalpha(m)
    canvas.alpha_composite(sh)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="纹样图带：主体 → 平面化切片 → S 形飘带")
    ap.add_argument("--source", required=True, help="主体 PNG（建议 RGBA 抠图；RGB 视为整幅可用）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=5, help="切片数")
    ap.add_argument("--colors", type=int, default=14, help="平面化限色数")
    ap.add_argument("--tile-w", type=float, default=0.14, help="切片显示宽（×画布宽）")
    ap.add_argument("--tile-aspect", type=float, default=0.80, help="切片宽/高")
    ap.add_argument("--sat", type=float, default=1.50, help="平面化提饱和倍率（1＝不动）")
    ap.add_argument("--con", type=float, default=1.28, help="平面化对比倍率（1＝不动）")
    ap.add_argument("--band-w", type=float, default=0.40, help="飘带带宽（×画布宽）")
    ap.add_argument("--amp", type=float, default=0.175, help="S 曲线摆幅（×画布宽）")
    ap.add_argument("--cycles", type=float, default=0.90, help="S 曲线周期数")
    ap.add_argument("--phase", type=float, default=-0.30, help="S 曲线相位")
    ap.add_argument("--flip-x", action="store_true",
                    help="飘带左右镜像（本案例：镜像后带子自右下出画，左下留出标题区）")
    ap.add_argument("--bg-hue", type=float, default=None,
                    help="底场色相覆盖（度，0–360；默认从主体自动提取，本案例金壁占优会取到暖金）")
    ap.add_argument("--labels", nargs="*", default=None, help="名签文字（覆盖自动矿物色名）")
    ap.add_argument("--bg-color", default=None, help="底场下缘主色 #RRGGBB（默认自动提取）")
    ap.add_argument("--bg-color2", default=None, help="底场上缘淡色 #RRGGBB（默认自动）")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--debug-picks", action="store_true", help="逐轮打印候选前 10 名（调样本用）")
    ap.add_argument("--list-pigments", action="store_true")
    a = ap.parse_args()
    if a.list_pigments:
        print("矿物色名表：" + "  ".join(f"{m}({h:g}°)" for m, h in PIGMENTS) + "  月白  黛")
        return 0

    src = Image.open(a.source).convert("RGBA")
    tile_src_w = int(round(a.tile_w * W * 1.6))          # 源域取样宽（约显示 1.6 倍，缩到显示尺寸即锐）
    picks = pick_tiles(src, a.count, a.tile_aspect, tile_src_w,
                       sat=a.sat, con=a.con, debug=a.debug_picks)

    tw_d = a.tile_w * W
    th_d = tw_d / a.tile_aspect
    tiles = []
    used = set()
    for i, p in enumerate(picks):
        crop = src.crop(tuple(p["rect"]))
        flat = flatten_tile(crop.convert("RGB"), a.colors,
                            (int(round(tw_d * SS)), int(round(th_d * SS))),
                            sat=a.sat, con=a.con)
        key = dominant_key(flat)                      # 主导饱和色 → 命名依据
        if a.labels and i < len(a.labels):
            label = a.labels[i]
        else:
            label = name_for(key, used)
        tiles.append({"img": flat.convert("RGBA"), "label": label, "key": key})
        print(f"[motif] 切片{i+1}: rect={p['rect']} 主导色={rgb_hex(key)} 名签「{label}」")

    top, bot, hp = band_colors(src, a.bg_color, a.bg_color2, a.bg_hue)
    print(f"[motif] 底场：主色相 {hp:g}° → 上缘 {rgb_hex(top)} / 下缘 {rgb_hex(bot)}")

    canvas = Image.fromarray(
        bg_gradient(top, bot, (W * SS, H * SS), a.seed).astype(np.uint8)).convert("RGBA")

    amp_eff = -a.amp if a.flip_x else a.amp                   # 镜像＝负摆幅（三者同口径）
    alpha = band_alpha((W * SS, H * SS), a.band_w, amp_eff, a.cycles, a.phase)
    blit_shadow(canvas, alpha, (0, int(0.016 * H * SS)), 34, 0.30)       # 飘带投影
    band = Image.new("RGBA", canvas.size, BAND_RGB + (0,))
    band.putalpha(alpha)
    canvas.alpha_composite(band)

    n = len(tiles)
    for i, tl in enumerate(tiles):
        t = 0.055 + (i + 0.5) * (0.945 - 0.055) / n
        cx = curve_x(t, amp_eff, a.cycles, a.phase) * W * SS
        cy = t * H * SS
        ang = max(-7.0, min(7.0, curve_angle(t, amp_eff, a.cycles, a.phase, H)))
        rot = tl["img"].rotate(-ang, expand=True, resample=Image.BICUBIC)
        pos = (int(round(cx - rot.size[0] / 2.0)), int(round(cy - rot.size[1] / 2.0)))
        blit_shadow(canvas, rot.getchannel("A"), (pos[0] + 3 * SS, pos[1] + 6 * SS),
                    12, 0.24)                                            # 切片投影
        canvas.paste(rot, pos, rot)
        tl["pos"] = pos
        tl["rot"] = rot.size

    try:
        font = ImageFont.truetype(os.path.join(FONTS_DIR, "MaShanZheng-Regular.ttf"), 30 * SS)
    except OSError:
        font = None
    if font is not None:
        d = ImageDraw.Draw(canvas)
        for tl in tiles:
            x = tl["pos"][0] + 2
            y = tl["pos"][1] - 76                                     # 名签贴本片正上方（落在片间空隙）
            d.text((x, y), tl["label"], font=font, fill=TAG_RGB + (255,))

    out = canvas.convert("RGB").resize((W, H), Image.LANCZOS)
    d2 = os.path.dirname(os.path.abspath(a.out))
    if d2 and not os.path.isdir(d2):
        os.makedirs(d2, exist_ok=True)
    out.save(a.out)
    print(f"[motif] {n} 片 → 飘带 → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())