#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
art_title.py —— 生成「艺术字」HTML 片段（大小错落 ／ 纵向拉长 ／ 高低错位 ／ 轻微旋转）

为什么需要它
------------
参考海报（非遗系列：竹编艺术／徽州灯彩／非遗文化之美／山高水长）的中文大标题
**不是端正排一行**，而是：

  ① **大小错落** —— 每个字字号都不同（0.85–1.2 倍），读起来有轻重节奏
  ② **纵向拉长** —— 个别字 `scaleY` 1.2–1.4，笔画显得挺拔
  ③ **高低错位** —— 字与字上下错开，像手写时笔势的起伏
  ④ **轻微旋转** —— ±2°–7°，打破"印刷体"的呆板

本脚本把这几项**程序化**分配到每个字上（seed 可复现），输出可直接粘进母版的
`<span style="--s:…;--sy:…;--dy:…;--rot:…">字</span>` 片段。
**字体不变**（仍是母版的书法体），只改效果。

母版侧需要配套的 CSS（三套母版已内置）：

  .art { display: flex; align-items: flex-start; letter-spacing: 0; }
  .art > span {
    display: inline-block;
    font-size: calc(1em * var(--s, 1));
    transform: translateY(var(--dy, 0)) rotate(var(--rot, 0deg)) scaleY(var(--sy, 1));
    transform-origin: 50% 82%;        /* 以字脚为支点：拉长时向上长，不顶破基线 */
  }
  .art.silhouette > span { color: transparent; -webkit-text-stroke: 3px var(--ink); }

用法
----
  python art_title.py --text "壁上万象" --style lively --seed 3
  python art_title.py --text "壁上万象" --style dramatic --seed 5 --silhouette
  python art_title.py --text "壁上" --style subtle          # 英文版用：效果很轻

  输出示例（一行，可直接替换母版里 `>壁上<` 的内容）：
  <span style="--s:1.12;--sy:1.18;--dy:-7px;--rot:-3.2deg">壁</span><span …>上</span>
"""

import argparse
import random
import sys

# 各档强度：(字号倍率, 纵向拉伸, 上下错位 px, 旋转 deg, 左右错位 px)
STYLES = {
    "subtle":   dict(s=(0.94, 1.06), sy=(1.00, 1.05), dy=(-4, 4),     rot=(-1.2, 1.2),  dx=(-8, 8)),
    "lively":   dict(s=(0.88, 1.14), sy=(1.00, 1.12), dy=(-10, 10),   rot=(-4.0, 4.0),  dx=(-18, 26)),
    "stretch":  dict(s=(0.96, 1.04), sy=(1.16, 1.38), dy=(-6, 6),     rot=(-2.0, 2.0),  dx=(-10, 10)),
    "dramatic": dict(s=(0.82, 1.22), sy=(1.05, 1.32), dy=(-16, 16),   rot=(-7.0, 7.0),  dx=(-26, 40)),
    # ★ 「正」档（2026-10-12 老大要的）：字要**端正**，只留极轻的呼吸感 ——
    #   不旋转（±0.5°）、不拉伸（sy 1.00–1.02）、不上下跳（dy ±2）、大小几乎一致。
    #   老大的话：「中文标题大字不够正，全是歪七扭八放的」。要"活"用 lively／dramatic，
    #   要"正"就用这一档；**间距靠容器的 letter-spacing 放大**（母版 `.tcol.art`）。
    "upright": dict(s=(0.985, 1.015), sy=(1.00, 1.02), dy=(-2, 2),   rot=(-0.5, 0.5),  dx=(-3, 3)),
}


def fmt(v, unit=""):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return s + unit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="标题文案（逐字生成 span）")
    ap.add_argument("--style", default="lively", choices=sorted(STYLES))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--orient", default="h", choices=["h", "v"],
                    help="排布方向：h＝横排一行（默认）／v＝**竖排字柱**（逐字向下，另加左右错位 --dx）")
    ap.add_argument("--silhouette", action="store_true", help="加 .silhouette 类（空心描边剪影）")
    ap.add_argument("--anchor", default=None, help="首字锚定模式：big|small|none（默认 none）")
    a = ap.parse_args()

    cfg = STYLES[a.style]
    rng = random.Random(a.seed)
    chars = [c for c in a.text if c.strip()]
    if not chars:
        print("", end="")
        return 0

    out = []
    for i, ch in enumerate(chars):
        s = rng.uniform(*cfg["s"])
        sy = rng.uniform(*cfg["sy"])
        dy = rng.uniform(*cfg["dy"])
        rot = rng.uniform(*cfg["rot"])
        # 竖排时**左右错位**才是主要的不规则来源（横排用不到，给 0 保持兼容）
        dx = rng.uniform(*cfg["dx"]) if a.orient == "v" else 0.0
        # 锚定：让首字（或末字）落在某个极端，避免整组"平均化"而不见落差
        if a.anchor == "big" and i == 0:
            s, sy = cfg["s"][1], cfg["sy"][1]
        elif a.anchor == "small" and i == 0:
            s, sy = cfg["s"][0], cfg["sy"][0]
        elif a.anchor == "big" and i == len(chars) - 1:
            s, sy = cfg["s"][1], cfg["sy"][1]
        out.append('<span style="--s:%s;--sy:%s;--dx:%spx;--dy:%spx;--rot:%sdeg">%s</span>'
                   % (fmt(s), fmt(sy), fmt(round(dx)), fmt(round(dy)), fmt(rot), ch))

    cls = "art silhouette" if a.silhouette else "art"
    # 只输出内层片段；调用方负责把它放进 <div class="…"> 里（母版用 class 控制）
    sys.stdout.write("".join(out))
    print("", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
