# -*- coding: utf-8 -*-
r"""撕开素材层渲染器（A 路线）：整幅背景素材图（岩壁/牛皮纸等相关素材），上下撕口沿主体轮廓弧撕开，中缝露出一条主体。

输入模型（skill 方向）：一张含主体物的原图（--subject 抠图版）＋一张材质素材图（--material，
如岩壁素材——色调/质感越贴近主体环境越契合）＋对主体物的描述（用于白底候选提示词，见
references\cutout-craft.md §①，不经过本脚本）。

视觉模型（先后不可换）：
  整幅素材层 → 主体画在素材上（上缘藏于上素材后、下缘藏于下素材后）→ 撕口轻投影
    → 上素材 over（y≤e_top）→ 下素材 over（y≥e_bot）→ 纸芯白线＋纸边微高光

撕口几何：撕口基线 = 主体轮廓弧 × k（压缩系数）＋ 随机撕边；
  压边自动定位：纸边最少压住主体 20px（主体边缘始终藏在素材后）。

窗口内容两条路线：
  A 抠图主体（本脚本）：--subject 给 RGBA 抠图；
  B 实拍原图（推荐，窗口内连续无缝）：用 kraft_photo.py。
  注意：k<1 时撕口弧比轮廓平缓，弧与轮廓之间必然夹出素材色——要「窗口完全连续」必须走 B。

用法（案例参数示意；后续照常走母版排字＋机检）：
  python kraft_tear.py --subject ..\cut\A2c.png --material material\rock.sand.png `
      --zoom 1.45 --out bg.rock.a.png
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter

W, H = 1500, 1875
MATERIAL_DARK = (185, 170, 153)       # 背景素材默认色阶暗端（岩壁 rock.sand.png p2 端）
MATERIAL_LIGHT = (241, 229, 214)      # 背景素材默认色阶亮端（岩壁 rock.sand.png p98 端）
SHADE = np.array((56, 45, 31), np.float32)
CORE = np.array((238, 230, 208), np.float32)


def parse_color(s):
    return tuple(int(v) for v in s.split(","))


def noise2(rng, h, w, sh, sw, blur=0.0):
    """低频噪声场：从 (sh,sw) 采样上采样到 (h,w)，标准化到 ~N(0,1)。"""
    small = rng.normal(0.0, 1.0, (max(2, sh), max(2, sw))).astype(np.float32)
    u = np.clip(small * 40.0 + 128.0, 0, 255).astype(np.uint8)
    img = Image.fromarray(u).resize((w, h), Image.BICUBIC)
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    arr = (np.asarray(img, np.float32) - 128.0) / 40.0
    arr -= arr.mean()
    arr /= (arr.std() + 1e-6)
    return arr


def paper(rng, dark, light):
    """程序纹理兜底：低对比色差＋细密中频＋双层细颗粒＋竖纤维＋横网纹＋杂点（清晰素材感）。"""
    low = noise2(rng, H, W, H // 55, W // 55, 4)
    mid = noise2(rng, H, W, H // 18, W // 18, 0)
    g2 = noise2(rng, H, W, H // 2, W // 2, 0)
    grain = noise2(rng, H, W, H, W, 0)
    fibv = noise2(rng, H, W, H // 3, W, 0)
    fibh = noise2(rng, H, W, H, W // 4, 0)
    lum = np.clip(0.5 + (0.20 * low + 0.30 * mid + 0.16 * g2 + 0.12 * grain) * 0.44, 0, 1)
    d = np.array(dark, np.float32)
    l = np.array(light, np.float32)
    rgb = d[None, None, :] * (1 - lum[..., None]) + l[None, None, :] * lum[..., None]
    rgb += (fibv * 3.4 + fibh * 3.0 + g2 * 4.5 + grain * 8.5)[..., None]
    sp = rng.random((H, W)).astype(np.float32)
    rgb += np.where(sp < 0.00035, -26.0, 0.0)[..., None]
    rgb += np.where(sp > 0.99965, 22.0, 0.0)[..., None]
    return rgb


def _cover(path):
    """素材照片 → 整幅等比放大盖满画布并居中裁到 (H,W)（镜像平铺会形成对称蝶形伪影，弃用）。"""
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    sc = max(W / sw, H / sh)
    im = im.resize((max(W, int(round(sw * sc))), max(H, int(round(sh * sc)))), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    y0, x0 = (a.shape[0] - H) // 2, (a.shape[1] - W) // 2
    return a[y0:y0 + H, x0:x0 + W]


def photo_cover(path, dark=MATERIAL_DARK, light=MATERIAL_LIGHT, flat_r=180.0):
    """背景素材照片 → 素材层 (H,W,3)（重上色版）：盖满＋去大尺度光照＋映射到 dark..light 两色阶。"""
    a = _cover(path)
    lum = a @ np.array((0.299, 0.587, 0.114), np.float32)
    blur = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(flat_r))
    lum = lum / (np.asarray(blur, np.float32) + 1e-6)          # 去大尺度光照，保留褶皱/纤维
    lo, hi = np.percentile(lum, 2.0), np.percentile(lum, 98.0)
    t = np.clip((lum - lo) / (hi - lo + 1e-6), 0, 1)
    t = 0.5 + (t - 0.5) * 0.86                                  # 抑制过度拉伸，保持自然对比
    d = np.array(dark, np.float32)
    l = np.array(light, np.float32)
    return d[None, None, :] * (1 - t[..., None]) + l[None, None, :] * t[..., None]


def photo_native(path, gain=1.0, gamma=1.0):
    """背景素材照片 → 素材层 (H,W,3)（保留原色版）：盖满＋色阶曲线（gamma<1 提暗部保亮部）＋整体增益，
    不重上色、不去光照——素材自带色斑/裂纹/矿物色（如风化岩壁）时用它，保住原始颜色。"""
    a = _cover(path)
    if gamma != 1.0:
        a = 255.0 * np.power(np.clip(a, 0, 255) / 255.0, gamma)
    return a * gain


def photo_detail(path, flat_r=16.0):
    """素材细部（高通）：纤维＋颗粒；标准化后镜像平铺至画布（细部尺度下镜像无可见接缝）。"""
    a = np.asarray(Image.open(path).convert("RGB"), np.float32)
    lum = a @ np.array((0.299, 0.587, 0.114), np.float32)
    blur = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(flat_r))
    hi = lum - np.asarray(blur, np.float32)
    hi /= (float(hi.std()) + 1e-6)
    sh, sw = hi.shape
    py, px = max(0, H - sh), max(0, W - sw)
    if py or px:
        hi = np.pad(hi, ((py // 2 + 1, py - py // 2 + 1), (px // 2 + 1, px - px // 2 + 1)), mode="reflect")
    y0, x0 = (hi.shape[0] - H) // 2, (hi.shape[1] - W) // 2
    return hi[y0:y0 + H, x0:x0 + W]


def tear(rng, amp=26.0, n_spike=6):
    """撕边轮廓（长度 W）：大波浪＋中尺度起伏＋高频细齿＋偶发纤维尖刺。"""
    big = np.convolve(rng.normal(0, 1, W).astype(np.float32), np.ones(220, np.float32) / 220, "same")
    big /= (np.abs(big).max() + 1e-6)
    t = np.convolve(rng.normal(0, 1, W).astype(np.float32), np.ones(48, np.float32) / 48, "same")
    t /= (np.abs(t).max() + 1e-6)
    prof = (big * amp * 0.75 + t * amp * 0.55).astype(np.float32)
    hi = np.convolve(rng.normal(0, 1, W).astype(np.float32), np.ones(5, np.float32) / 5, "same")
    prof += (hi * amp * 0.25).astype(np.float32)
    for _ in range(n_spike):
        i = int(rng.integers(10, W - 10))
        a, b = max(0, i - 7), min(W, i + 8)
        prof[a:b] += float(rng.normal(0, 1)) * amp * 1.4 * np.hanning(b - a).astype(np.float32)
    return prof


def feathered(mask):
    img = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    return np.asarray(img, np.float32) / 255.0


def paper_layer(rng, panel, edge, side, core_w=5.0):
    """纸层（含白芯＋纸边微高光）：side='top' 纸在 edge 之上；side='bot' 纸在 edge 之下。"""
    yy = np.arange(H, dtype=np.float32)[:, None]
    if side == "top":
        dc = np.clip(edge[None, :] - yy, 0, None)
        inside = (yy <= edge[None, :]).astype(np.float32)
    else:
        dc = np.clip(yy - edge[None, :], 0, None)
        inside = (yy >= edge[None, :]).astype(np.float32)
    core = np.clip(1 - dc / core_w, 0, 1) * inside
    rgb = panel * (1 - (core * 0.85)[..., None]) + CORE[None, None, :] * (core * 0.85)[..., None]
    glow = (np.clip(1 - dc / 9.0, 0, 1) * inside * 0.10)[..., None]
    rgb = rgb * (1 - glow) + np.array((255, 246, 228), np.float32)[None, None, :] * glow
    return rgb, feathered(inside)


def smooth1d(v, w):
    """一维滑动均值（edge 填充），抚平轮廓锯齿。"""
    k = np.ones(w, np.float32) / w
    vp = np.pad(v, w // 2, mode="edge")
    return np.convolve(vp, k, "valid")[: len(v)].astype(np.float32)


def build(sub_img, k, yA, seed, tex=None, dark=MATERIAL_DARK, light=MATERIAL_LIGHT, zoom=1.0):
    rng = np.random.default_rng(seed)
    yy = np.arange(H, dtype=np.float32)[:, None]

    proc = paper(rng, dark, light)                   # 程序纹理（同时保持随机数序列：撕口形状可复现）
    kraft = proc if tex is None else tex             # 有素材时用真实素材层（上下同一张，撕口两侧纹理连续）
    canvas = kraft.copy()

    # 主体缩放＋可见轮廓（alpha>0.45 的上下缘）：撕口基线 = 轮廓弧 × 压缩系数 k
    # zoom>1：先放大整幅再居中裁到画布宽——主体更大、撕口窗口更高（内容两侧被裁）
    sw, sh = sub_img.size
    zw = max(W, int(round(W * zoom)))
    sub = sub_img.resize((zw, max(1, int(round(sh * zw / sw)))), Image.LANCZOS)
    if zw > W:
        x0 = (zw - W) // 2
        sub = sub.crop((x0, 0, x0 + W, sub.size[1]))
    sa = np.asarray(sub, np.float32)
    sh2 = sa.shape[0]
    vis = sa[..., 3] / 255.0 > 0.45
    top = np.argmax(vis, axis=0).astype(np.float32)
    bot = (sh2 - 1 - np.argmax(vis[::-1], axis=0)).astype(np.float32)
    none_c = ~vis.any(axis=0)
    if none_c.any():
        xs = np.arange(W)
        top[none_c] = np.interp(xs[none_c], xs[~none_c], top[~none_c])
        bot[none_c] = np.interp(xs[none_c], xs[~none_c], bot[~none_c])
    top = smooth1d(top, 81)
    bot = smooth1d(bot, 81)
    mt = float(top.mean())
    mb = float(bot.mean())

    # 撕口线：均值位于 yA 的画布上，弧幅 = 轮廓弧 × k
    # 主体放置使「纸边覆盖图案」最薄处恰好 20px（保证图案边缘始终藏在纸下）
    e_top = yA + (top - mt) * k + tear(rng, amp=10.0, n_spike=4)
    cov = e_top - top
    sy = int(round(float(cov.min()) - 20.0))
    e_top = e_top.astype(np.float32)
    e_bot = (bot - mb) * k + tear(rng, amp=10.0, n_spike=4)
    # 校正：整体位移至「纸边最少压住图案 20px」处（图案下缘始终藏在纸后，纸边尽量贴轮廓）
    e_bot = (e_bot + (float(((sy + bot) - e_bot).min()) - 20.0)).astype(np.float32)

    # 画主体——上缘藏于上纸后、下缘藏于下纸后
    y0, y1 = max(0, sy), min(H, sy + sh2)
    a = sa[y0 - sy:y1 - sy]
    # 半透明软边收硬：宽软边（alpha 0.1-0.4）会让素材层从抠图里透出来形成渗色泥斑；
    # 收成约 0.1 宽的窄过渡带——实心主体保持原色，软边处干净露出素材层
    m = a[..., 3:4] / 255.0
    alpha = np.clip((m - 0.42) / 0.10, 0, 1.0)
    canvas[y0:y1] = canvas[y0:y1] * (1 - alpha) + a[:, :, :3] * alpha

    # 撕口轻投影（窄带，让图案保持原色）
    d = np.clip(yy - e_top[None, :], 0, None)
    amt = np.where(yy > e_top[None, :], np.exp(-d / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt[..., None]) + SHADE[None, None, :] * amt[..., None]

    d2 = np.clip(e_bot[None, :] - yy, 0, None)
    amt2 = np.where(yy < e_bot[None, :], np.exp(-d2 / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt2[..., None]) + SHADE[None, None, :] * amt2[..., None]

    # 上素材 / 下素材 over（图案在下、素材在上）
    top_rgb, at = paper_layer(rng, kraft, e_top, "top")
    canvas = top_rgb * at[..., None] + canvas * (1 - at[..., None])
    bot_rgb, ab = paper_layer(rng, kraft, e_bot, "bot")
    canvas = bot_rgb * ab[..., None] + canvas * (1 - ab[..., None])

    print(f"       e_top {e_top.mean():.0f} | e_bot {e_bot.mean():.0f} | tuck_top {(e_top - (sy + top)).min():.0f} | tuck_bot {((sy + bot) - e_bot).min():.0f}")
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description="撕开素材层（窗口＝抠图主体）")
    ap.add_argument("--subject", required=True, help="抠图主体 PNG（RGBA）")
    ap.add_argument("--out", required=True, help="输出背景 PNG（1500x1875）")
    ap.add_argument("--material", "--kraft", default="", help="背景素材照片（岩壁/牛皮纸等相关素材；可选，不给则程序纹理）")
    ap.add_argument("--k", type=float, default=0.60, help="撕口弧幅 / 轮廓弧幅 压缩系数")
    ap.add_argument("--yA", type=float, default=540.0, help="上撕口基线均值（画布 y）")
    ap.add_argument("--zoom", type=float, default=1.0, help="窗口内容放大倍率（>1：放大后居中裁两侧，撕口窗口更高）")
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--paper-dark", default="185,170,153", help="素材色阶暗端 R,G,B（默认岩壁调）")
    ap.add_argument("--paper-light", default="241,229,214", help="素材色阶亮端 R,G,B（默认岩壁调）")
    ap.add_argument("--material-gain", type=float, default=0.0, help="保留素材原色：整体增益倍率（1.2≈提亮两成）；0＝关闭，改为 --paper-dark/--paper-light 重上色")
    ap.add_argument("--material-gamma", type=float, default=1.0, help="保留素材原色时的色阶曲线（<1 提暗部保亮部，如 0.52；≠1 也启用保留原色）")
    ap.add_argument("--detail", type=float, default=4.0, help="素材细部高通叠加幅度（有 --material 时）")
    args = ap.parse_args()

    sub = Image.open(args.subject).convert("RGBA")
    dark, light = parse_color(args.paper_dark), parse_color(args.paper_light)
    tex = None
    if args.material:
        # 真实素材层（整幅盖满，无镜像伪影）＋素材原生尺度细部（石理/颗粒，镜像不可见）
        if args.material_gain > 0 or args.material_gamma != 1.0:
            # 保留原色：不重上色，仅色阶曲线＋整体增益（素材自带色斑/裂纹/矿物色时用）
            tex = photo_native(args.material, gain=args.material_gain if args.material_gain > 0 else 1.0,
                               gamma=args.material_gamma) + photo_detail(args.material)[..., None] * args.detail
        else:
            tex = photo_cover(args.material, dark=dark, light=light) + photo_detail(args.material)[..., None] * args.detail
    img = build(sub, args.k, args.yA, args.seed, tex, dark=dark, light=light, zoom=args.zoom)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    img.save(args.out)
    print("[kraft_tear]", args.out, "| k", args.k, "| yA", args.yA, "| zoom", args.zoom, "| seed", args.seed)


if __name__ == "__main__":
    main()