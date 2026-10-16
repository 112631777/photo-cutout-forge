# -*- coding: utf-8 -*-
r"""撕开素材层 · B 路线：中缝窗口内容直接用实拍原图（整幅铺满画布宽、按墙带行对位），背景素材压上/下。

输入模型（skill 方向）：一张含主体物的原图（--photo，主体带在画内）＋一张材质素材图（--material，
如岩壁素材——色调/质感越贴近主体环境越契合）＋对主体物的描述（用于白底候选提示词，见
references\cutout-craft.md §①，不经过本脚本）。

与 kraft_tear.py 共用撕口几何（轮廓弧×k＋随机撕边、压边 20px）——只替换窗口内容；
窗口内是连续实拍画面，不会出现「素材色夹入壁画」（A 路线 k<1 压缩弧的结构性问题）。

轮廓源两条路：① AI 剪影候选（默认）；② 照片描线 mask —— AI 剪影几何与实拍不符（多翼/U 形透视）时，
  在照片上按真实边界描 top/bot 控制点、折线插值成与照片同尺寸的 alpha 带状 mask 喂 --cutout；
  配 --k 1.0（撕口＝描线轮廓 ±tear）--smooth 21（保轮廓）--wall-top-row 取描线 top 均值（见 references\kraft-tear.md §1.5）。

取景：--wall-top-row = 照片中对齐到上撕口线（--top-edge，默认 539）的原图行。
  先按行亮度剖面定位天花/壁画/地面边界，再渲染 2-3 个候选目检挑选：
  案例（4202x5248 展览实拍）：天花下界约 y1550；中心裁剪列壁画带到约 y2600。
  定稿取 --zoom 1.45 --wall-top-row 1550（窗口 486px、无露黑/露地）。

用法（案例参数）：
  python kraft_photo.py --cutout ..\cut\A2c.png --photo material\mural.original.png `
      --material material\rock.sand.png --zoom 1.45 --wall-top-row 1550 --out bg.rock.png
"""
import argparse
import os

import numpy as np
from PIL import Image

import kraft_tear as kt


def parse_color(s):
    return tuple(int(v) for v in s.split(","))


def main():
    ap = argparse.ArgumentParser(description="撕开素材层（窗口＝实拍原图）")
    ap.add_argument("--cutout", required=True, help="抠图主体 PNG（RGBA，仅用于撕口轮廓弧）")
    ap.add_argument("--photo", required=True, help="实拍原图（RGB，填满撕口窗口）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--material", "--kraft", default="", help="背景素材照片（岩壁/牛皮纸等相关素材；可选，不给则程序纹理）")
    ap.add_argument("--wall-top-row", type=float, default=1400.0, help="照片中对齐到上撕口线的行（取景）")
    ap.add_argument("--top-edge", type=float, default=539.0, help="上撕口线位置（须与几何一致；默认 539）")
    ap.add_argument("--zoom", type=float, default=1.0, help="窗口内容放大倍率（>1：轮廓与照片同步放大居中裁两侧，撕口窗口更高）")
    ap.add_argument("--k", type=float, default=0.60, help="撕口弧幅 / 轮廓弧幅 压缩系数（→1 撕口越贴主体轮廓）")
    ap.add_argument("--smooth", type=int, default=81, help="轮廓平滑窗口 px（越小越保轮廓细节，越大越像手撕大波浪）")
    ap.add_argument("--yA", type=float, default=540.0, help="上撕口基线均值（画布 y）")
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--paper-dark", default="185,170,153", help="素材色阶暗端 R,G,B（默认岩壁调）")
    ap.add_argument("--paper-light", default="241,229,214", help="素材色阶亮端 R,G,B（默认岩壁调）")
    ap.add_argument("--material-gain", type=float, default=0.0, help="保留素材原色：整体增益倍率（1.2≈提亮两成）；0＝关闭，改为 --paper-dark/--paper-light 重上色")
    ap.add_argument("--material-gamma", type=float, default=1.0, help="保留素材原色时的色阶曲线（<1 提暗部保亮部，如 0.52；≠1 也启用保留原色）")
    ap.add_argument("--detail", type=float, default=4.0, help="素材细部高通叠加幅度（有 --material 时）")
    args = ap.parse_args()

    # 纸面：程序纹理先算（保持与 kraft_tear.build 相同的随机序列，撕口形状一致）
    rng = np.random.default_rng(args.seed)
    kraft = kt.paper(rng, kt.MATERIAL_DARK, kt.MATERIAL_LIGHT)
    if args.material:
        if args.material_gain > 0 or args.material_gamma != 1.0:
            # 保留原色：不重上色，仅色阶曲线＋整体增益（素材自带色斑/裂纹/矿物色时用）
            kraft = kt.photo_native(args.material, gain=args.material_gain if args.material_gain > 0 else 1.0,
                                    gamma=args.material_gamma) \
                + kt.photo_detail(args.material)[..., None] * args.detail
        else:
            kraft = kt.photo_cover(args.material, dark=parse_color(args.paper_dark),
                                   light=parse_color(args.paper_light)) \
                + kt.photo_detail(args.material)[..., None] * args.detail
    canvas = kraft.copy()

    # ---- 轮廓与撕口线（与 build() 相同；zoom>1 放大后居中裁到画布宽）----
    sub = Image.open(args.cutout).convert("RGBA")
    sw, sh = sub.size
    zw = max(kt.W, int(round(kt.W * args.zoom)))
    s2 = sub.resize((zw, max(1, int(round(sh * zw / sw)))), Image.LANCZOS)
    if zw > kt.W:
        x0 = (zw - kt.W) // 2
        s2 = s2.crop((x0, 0, x0 + kt.W, s2.size[1]))
    sa = np.asarray(s2, np.float32)
    sh2 = sa.shape[0]
    vis = sa[..., 3] / 255.0 > 0.45
    top = np.argmax(vis, axis=0).astype(np.float32)
    bot = (sh2 - 1 - np.argmax(vis[::-1], axis=0)).astype(np.float32)
    none_c = ~vis.any(axis=0)
    if none_c.any():
        xs = np.arange(kt.W)
        top[none_c] = np.interp(xs[none_c], xs[~none_c], top[~none_c])
        bot[none_c] = np.interp(xs[none_c], xs[~none_c], bot[~none_c])
    top = kt.smooth1d(top, args.smooth)
    bot = kt.smooth1d(bot, args.smooth)
    mt, mb = float(top.mean()), float(bot.mean())
    e_top = args.yA + (top - mt) * args.k + kt.tear(rng, amp=10.0, n_spike=4)
    sy = int(round(float((e_top - top).min()) - 20.0))
    e_top = e_top.astype(np.float32)
    e_bot = (bot - mb) * args.k + kt.tear(rng, amp=10.0, n_spike=4)
    e_bot = (e_bot + (float(((sy + bot) - e_bot).min()) - 20.0)).astype(np.float32)
    print(f"       e_top {e_top.mean():.0f} | e_bot {e_bot.mean():.0f} | tuck_top {(e_top - (sy + top)).min():.0f} | tuck_bot {((sy + bot) - e_bot).min():.0f}")

    # ---- 实拍原图：铺满画布宽（zoom 放大后居中裁两侧），墙带行对位撕口线 ----
    ph = Image.open(args.photo).convert("RGB")
    pw, phh = ph.size
    sc = kt.W * args.zoom / pw
    ph2 = ph.resize((max(kt.W, int(round(pw * sc))), max(kt.H, int(round(phh * sc)))), Image.LANCZOS)
    x0 = (ph2.size[0] - kt.W) // 2
    pa = np.asarray(ph2, np.float32)[:, x0:x0 + kt.W]
    by = int(round(args.top_edge - args.wall_top_row * sc))    # 画布行 = by + 照片行×sc（by 可为负）
    y0c, y0p = max(0, by), max(0, -by)
    h_avail = min(kt.H - y0c, pa.shape[0] - y0p)
    canvas[y0c:y0c + h_avail] = pa[y0p:y0p + h_avail]
    print(f"       photo {pw}x{phh} | sc {sc:.3f} | 可见 {ph2.size[0]}x{ph2.size[1]} 取 x{x0}..{x0 + kt.W} | by {by} -> 窗口({args.top_edge:.0f}-{e_bot.mean():.0f})对应照片行 {int((args.top_edge - by) / sc)}..{int((e_bot.mean() - by) / sc)}")

    # ---- 撕口轻投影（同 build）----
    yy = np.arange(kt.H, dtype=np.float32)[:, None]
    d = np.clip(yy - e_top[None, :], 0, None)
    amt = np.where(yy > e_top[None, :], np.exp(-d / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt[..., None]) + kt.SHADE[None, None, :] * amt[..., None]
    d2 = np.clip(e_bot[None, :] - yy, 0, None)
    amt2 = np.where(yy < e_bot[None, :], np.exp(-d2 / 7.0) * 0.24, 0.0)
    canvas = canvas * (1 - amt2[..., None]) + kt.SHADE[None, None, :] * amt2[..., None]

    # ---- 上纸 / 下纸 over ----
    top_rgb, at = kt.paper_layer(rng, kraft, e_top, "top")
    canvas = top_rgb * at[..., None] + canvas * (1 - at[..., None])
    bot_rgb, ab = kt.paper_layer(rng, kraft, e_bot, "bot")
    canvas = bot_rgb * ab[..., None] + canvas * (1 - ab[..., None])

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(args.out)
    print("[kraft_photo]", args.out)


if __name__ == "__main__":
    main()