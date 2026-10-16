#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
band_mask.py —— 生成「撕口轮廓带」mask（与照片同尺寸的 alpha 带状图）

撕口线 = 这条带的上下缘 × k（kraft_tear / kraft_photo 内做压缩）。
所以**这条带的形状直接决定撕口长什么样**，进而决定画面被切成几块。

两种典型形态
------------
  flat   「一字型横带」——上下缘基本平直、微微拱起。
         稳、干净；但**容易把画面切成上／中／下三等分**，生硬割裂。

  pinch  「中间凹陷、两端扩张」——上缘中间下凹、下缘中间上拱，带高呈哑铃形。
         **中缝中间窄、两端宽**，露出的内容有呼吸变化，层次感更强。

⚠ **自然感**（2026-10-11 老大反馈后补）
  只给「中间凹」的控制点，做出来是一条**左右对称的光滑弧** —— 一看就是画出来的，
  不像撕出来的（老大原话：「这种哑铃型又太过规整了，没有一种自然感」）。
  真实撕口有三个特征：**不对称、多尺度起伏、边缘细碎**。
  所以本脚本在基准曲线之上叠加 **1D 分形噪声**（`--jitter`，多八度、
  上下缘用不同 seed），再交给 kraft_photo 内建的随机 tear 去补最后一点细碎感。

⚠ 形态与自然度都要**按素材具体分析**，不是每次都必须用 pinch：
  - 主体横向连贯、画面已有上下分区 → `flat` 更整齐
  - 主体呈弧形／环抱，或需要打破三分感 → `pinch` 更有层次
  - 详见 references/kraft-tear.md「§1.6 撕口取形」

用法
----
  # 预设（pinch 已是不对称基准 + 分形噪声）
  python band_mask.py --w 1537 --h 1920 --shape pinch --jitter 0.012 --seed 7 --out cut\mask.png

  # 完全自定义控制点（沿宽度均匀分布，值为画布高的比例）
  python band_mask.py --w 1537 --h 1920 `
      --top "0.270,0.335,0.355,0.325,0.275" `
      --bottom "0.600,0.540,0.508,0.528,0.592" --jitter 0.010 --out cut\mask.png

依赖：Pillow + numpy
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

# 预设控制点（画布高的比例，沿宽度均匀分布）
PRESETS = {
    # 一字型横带：敦煌 case13 实测读数（起伏仅 26/42px）
    "flat":  {"top":    [0.292, 0.277, 0.292],
              "bottom": [0.556, 0.532, 0.556]},
    # 中间凹陷两端扩张：7 点；上下缘形状**故意不同**（避免镜像对称的死板感）。
    # 整条带偏上：中缝下缘留出足够的下部素材区承字（左文版式要 ~470px 的净落字高）。
    "pinch": {"top":    [0.252, 0.290, 0.322, 0.332, 0.310, 0.275, 0.258],
              "bottom": [0.552, 0.524, 0.490, 0.476, 0.498, 0.530, 0.546]},
}

# ---- 竖向（--orient v）----------------------------------------------------
# 控制点改为「画布**宽**的比例」，沿**高度**分布；left／right 是窗的左右缘。
VPRESETS = {
    # 竖向不规则开窗（vpatch）：窗贴在画面左中，宽窄起伏、左右缘形状故意不同。
    # 用于「主体是竖向一团」的素材（展示柜＋墙上的倒影、立像、器物……），
    # 学参考海报那种「一块不规则壁画贴片」的感觉。案例：case16 展示柜。
    "vpatch": {"left":  [0.105, 0.088, 0.115, 0.096, 0.126, 0.100, 0.140],
               "right": [0.470, 0.492, 0.455, 0.500, 0.468, 0.486, 0.520]},
}

# ---- 斜向（--rotate，2026-10-11 老大反馈后加）--------------------------------
# 「轴对齐的矩形块放在海报里太滑稽」——参考海报的震撼来自**一条从右上贯到左下**的
# 不规则斜带，把整张海报劈成两半。做法：先在**放大的正方画布**上按横向带生成，
# 再整体旋转（PIL 逆时针为正），最后中心裁回 W×H。
# ⚠ 带厚按**放大画布 D** 的比例给（D ＝ 画布对角线长），不是按 W。
DPRESETS = {
    # 斜带（横向带旋转后成「/」向，即右上→左下）
    "diag": {"top":    [0.300, 0.268, 0.336, 0.296, 0.352, 0.286, 0.318],
             "bottom": [0.706, 0.742, 0.664, 0.716, 0.648, 0.752, 0.690]},
    # 更厚、边缘更横冲直撞的一版（占画面更多，参考海报那种"劈开"感更强）
    "diag-thick": {"top":    [0.238, 0.214, 0.286, 0.240, 0.302, 0.228, 0.262],
                   "bottom": [0.772, 0.806, 0.712, 0.776, 0.700, 0.812, 0.740]},
    # ★ 两端宽、中间收腰的斜向块（2026-10-11 老大第二轮反馈后加）：
    #   参考海报的图不是一条等宽带，而是「右上角一大块 → 中间收窄 → 左下角一大块」，
    #   中央留出纸面给标题。旋转后即得「斜向沙漏」，两个角被图占住、中央可排字。
    #   腰宽实测定档：**0.62D 太宽**（覆盖 56.5%，中央没纸面）；
    #   **0.10D 刚好**（覆盖 39.2%，左上＋右下各得一块纸面）。
    "diag-pinch": {"top":    [0.190, 0.280, 0.410, 0.450, 0.400, 0.290, 0.180],
                   "bottom": [0.810, 0.720, 0.590, 0.550, 0.600, 0.710, 0.820]},
    # ★★ 破对称版（2026-10-11 老大第二轮反馈后加）：
    #   上一版 `diag-pinch` 的上下缘互为**镜像**（bottom = 1 − top：0.19/0.81、0.28/0.72…），
    #   结果是一条**中心对称的沙漏** —— 老大原话「抠图太过中心对称了，图案可以更不规则一点」。
    #   破对称三处一起动：
    #     ① **腰位偏心**：最细处不在正中（thickness 在 3/6 处 0.075，2/6 处 0.165）
    #     ② **两端不等宽**：左端 0.755 ／ 右端 0.640（不再对称）
    #     ③ **腰深不同**：上缘下探 0.470、下缘上拱 0.545（下拱得浅）
    #   另配 `--jitter 0.014`（比常规 0.010 更粗）＋非整数角度（如 34°）进一步去规整。
    "diag-rag": {"top":    [0.140, 0.300, 0.400, 0.445, 0.345, 0.235, 0.205],
                 "bottom": [0.895, 0.680, 0.565, 0.570, 0.660, 0.790, 0.845]},
}


def parse_pts(s):
    return [float(v) for v in s.replace("，", ",").split(",") if v.strip() != ""]


def smooth1d(arr, k):
    """滑动平均（np.convolve；PIL 的 F 模式不支持 GaussianBlur，别用）。"""
    k = int(k) | 1
    if k <= 1:
        return np.asarray(arr, np.float32)
    a = np.pad(np.asarray(arr, np.float32), k // 2, mode="edge")
    return np.convolve(a, np.ones(k, np.float32) / k, mode="valid")


def fractal_noise(n, seed=0, octaves=5, persist=0.52):
    """1D 分形噪声（多八度随机叠加，值域约 ±1）。

    用来给撕口加**多尺度起伏**：低频给大波形、高频给细碎边。
    只叠正弦或只加白噪声都不像 —— 撕纸的粗糙度是「每个尺度都有一点」。
    """
    rng = np.random.default_rng(seed)
    out = np.zeros(n, np.float32)
    amp, total = 1.0, 0.0
    step = max(4, n // 5)                 # 最低频
    while octaves > 0 and step >= 2:
        k = max(2, n // step + 1)
        pts = rng.normal(0.0, 1.0, k)
        layer = np.interp(np.arange(n), np.linspace(0, n - 1, k), pts)
        layer = smooth1d(layer, step)
        out += layer * amp
        total += amp
        amp *= persist
        step = max(2, step // 2)
        octaves -= 1
    return out / max(total, 1e-6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, required=True, help="输出宽（＝照片宽）")
    ap.add_argument("--h", type=int, required=True, help="输出高（＝照片高）")
    ap.add_argument("--orient", default="h", choices=["h", "v"],
                    help="取形方向：h＝横向撕口带（每列上下缘）／v＝**竖向不规则开窗**（每行左右缘）")
    ap.add_argument("--shape", default=None, help="预设：h→flat/pinch；v→vpatch")
    ap.add_argument("--top", default=None, help="上缘（h）或**左缘**（v）控制点，逗号分隔")
    ap.add_argument("--bottom", default=None, help="下缘（h）或**右缘**（v）控制点，逗号分隔")
    ap.add_argument("--left", default=None, help="v 专用：左缘控制点（＝--top 的别名）")
    ap.add_argument("--right", default=None, help="v 专用：右缘控制点（＝--bottom 的别名）")
    ap.add_argument("--yspan", default=None,
                    help="v 专用：窗口的纵向范围「起,止」（画布高比例，如 0.26,0.76）；"
                         "不给＝贯穿全高。两端也做不规则收口（见 --end-jitter）")
    ap.add_argument("--end-jitter", type=float, default=0.022,
                    help="v 专用：窗口**上下端**收口的不规则幅度（画布高比例）")
    ap.add_argument("--rotate", type=float, default=0.0,
                    help="把整条取形**旋转**这么多度（PIL 逆时针为正）。非 0 时会在"
                         "「对角线长度的正方画布」上生成再中心裁回 W×H —— 用来做"
                         "**从右上贯到左下**的斜向不规则块（配 --shape diag／diag-thick）")
    ap.add_argument("--smooth", type=int, default=81, help="基准曲线平滑核（px，奇数）")
    ap.add_argument("--jitter", type=float, default=0.012,
                    help="分形噪声幅度：h＝画布高比例；v＝**画布宽比例**。0＝关闭，退化成光滑弧")
    ap.add_argument("--seed", type=int, default=7, help="噪声种子（两侧用 seed / seed+101）")
    ap.add_argument("--ink", default="58,42,30", help="填充色（仅占位，alpha 才被使用）")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    vertical = a.orient == "v"
    # 斜向模式：在「对角线长度的正方画布」上按横向带生成，最后旋转＋中心裁回
    diagonal = abs(a.rotate) > 1e-6
    if a.shape is None:
        a.shape = "vpatch" if vertical else ("diag" if diagonal else "pinch")

    if diagonal:
        D = int(np.ceil(np.hypot(a.w, a.h))) + 4
        CW, CH = D, D                    # 生成画布
        table = DPRESETS
        vertical = False                 # 斜向一律用横向带的机制（再旋转）
    else:
        CW, CH = a.w, a.h
        table = VPRESETS if vertical else PRESETS

    t_arg = a.left if (vertical and a.left) else a.top
    b_arg = a.right if (vertical and a.right) else a.bottom
    key = "left" if vertical else "top"
    key2 = "right" if vertical else "bottom"
    if a.shape not in table and not (t_arg and b_arg):
        print("未知预设 %s（可用：%s）" % (a.shape, "/".join(sorted(table))), file=sys.stderr)
        return 2
    t_ctl = parse_pts(t_arg) if t_arg else table[a.shape][key]
    b_ctl = parse_pts(b_arg) if b_arg else table[a.shape][key2]
    if len(t_ctl) < 2 or len(t_ctl) != len(b_ctl):
        print("控制点需≥2 个且两侧数量一致", file=sys.stderr)
        return 2

    if vertical:
        # 沿高度插值；控制点值是「画布宽的比例」；噪声幅度按宽算
        span, along = CW, CH
        xs = np.linspace(0, CH - 1, CH)
        cx = np.linspace(0, CH - 1, len(t_ctl))
        amp_ref = CW
    else:
        span, along = CH, CW
        xs = np.linspace(0, CW - 1, CW)
        cx = np.linspace(0, CW - 1, len(t_ctl))
        amp_ref = CH

    t = smooth1d(np.interp(xs, cx, np.array(t_ctl, np.float32) * span), a.smooth)
    b = smooth1d(np.interp(xs, cx, np.array(b_ctl, np.float32) * span), a.smooth)

    if a.jitter > 0:
        amp = a.jitter * amp_ref
        t = t + fractal_noise(along, seed=a.seed) * amp           # 两侧不同种子 → 不镜像
        b = b + fractal_noise(along, seed=a.seed + 101) * amp

    b = np.maximum(b, t + 12.0)                                   # 曲线不许交叉

    m = np.zeros((CH, CW), np.uint8)
    if vertical:
        x0 = np.clip(np.round(t).astype(int), 0, CW - 1)
        x1 = np.clip(np.round(b).astype(int), 0, CW - 1)
        if a.yspan:
            ya, yb = [float(v) for v in a.yspan.replace("，", ",").split(",")]
            ytop = ya * CH + fractal_noise(CW, seed=a.seed + 7) * (a.end_jitter * CH)
            ybot = yb * CH + fractal_noise(CW, seed=a.seed + 9) * (a.end_jitter * CH)
            for x in range(CW):
                if x1[x] <= x0[x]:
                    continue
                ya_x = int(np.clip(round(ytop[x]), 0, CH - 1))
                yb_x = int(np.clip(round(ybot[x]), ya_x + 1, CH))
                m[ya_x:yb_x, x0[x]:x1[x] + 1] = 255
        else:
            for y in range(CH):
                if x1[y] > x0[y]:
                    m[y, x0[y]:x1[y] + 1] = 255
    else:
        y0 = np.clip(np.round(t).astype(int), 0, CH - 1)
        y1 = np.clip(np.round(b).astype(int), 0, CH - 1)
        for x in range(CW):
            if y1[x] > y0[x]:
                m[y0[x]:y1[x] + 1, x] = 255

    # ---- 斜向：旋转后中心裁回 W×H ----
    if diagonal:
        mi = Image.fromarray(m).rotate(a.rotate, resample=Image.BICUBIC, fillcolor=0)
        ma = np.asarray(mi)
        ox, oy = (CW - a.w) // 2, (CH - a.h) // 2
        m = (ma[oy:oy + a.h, ox:ox + a.w] > 128).astype(np.uint8) * 255
        # 用四角覆盖率自证方向（打印出来看，不靠眼睛）
        q = min(a.w, a.h) // 4
        corners = {
            "左上": m[:q, :q].mean() / 255, "右上": m[:q, -q:].mean() / 255,
            "左下": m[-q:, :q].mean() / 255, "右下": m[-q:, -q:].mean() / 255,
        }
        print("            四角覆盖率：" + "  ".join("%s %.0f%%" % (k, v * 100)
                                                    for k, v in corners.items())
              + "（斜带应为「右上／左下」高）")

    fill = tuple(int(v) for v in a.ink.split(","))
    rgba = Image.new("RGB", (a.w, a.h), fill).convert("RGBA")
    rgba.putalpha(Image.fromarray(m))
    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    rgba.save(a.out)

    band = b - t
    q = along // 4
    asym_t = abs((t[q] - t[0]) - (t[along - 1 - q] - t[along - 1]))   # >0 说明不是镜像
    asym_b = abs((b[q] - b[0]) - (b[along - 1 - q] - b[along - 1]))
    orient_name = "斜向不规则块" if diagonal else ("竖向开窗" if vertical else "横向撕口带")
    print("[band_mask] %s  %dx%d  %s  shape=%s  jitter=%.3f seed=%d %s"
          % (a.out, a.w, a.h, orient_name, a.shape if not t_arg else "custom", a.jitter, a.seed,
             "" if a.jitter > 0 else "（无噪声＝光滑弧）"))
    print("            取形带宽：左 %.0f ｜ ¼ %.0f ｜ 中 %.0f ｜ ¾ %.0f ｜ 右 %.0f  px"
          % (band[0], band[q], band[along // 2], band[3 * q], band[-1]))
    print("            %s %.0f→%.0f→%.0f ｜ %s %.0f→%.0f→%.0f ｜ 不对称 %.0f/%.0f px"
          % ("左缘" if vertical else "上缘", t[0], t[along // 2], t[-1],
             "右缘" if vertical else "下缘", b[0], b[along // 2], b[-1], asym_t, asym_b))
    if diagonal:
        print("            旋转 %.1f°（逆时针为正）｜ 生成画布 %dx%d → 中心裁回 %dx%d"
              % (a.rotate, CW, CH, a.w, a.h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
