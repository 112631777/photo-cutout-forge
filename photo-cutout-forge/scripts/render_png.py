#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_png.py —— HTML 母版 → PNG 成品（无头浏览器）

用系统自带的 Edge / Chrome 无头模式截图，不装 Playwright。
同时可导出「QA 数据」：文字元素的外接矩形与计算样式（供 check_contrast.py 使用）。

⚠ 视口补偿（2026-10-10 实测修复，勿删）
  headless=new 模式下 `--window-size` 是「窗口外尺寸」，**实际视口比它小**
  （本机 Edge 135 实测：scale=2 时少 21×91 CSS px，scale=1 时少 24×93）。
  截图按 window-size × scale 输出，于是页面只渲染到视口为止，
  **右下露出 body 底色** —— 母版 body 是深色 #17130E，成品右下就成了一条黑边。
  此缺陷机检抓不到（check_contrast 只看文字矩形），只能靠目检或像素审计发现。
  对策：截图时把 window-size 加大 PAD，让视口大于 .stage，再裁回设计尺寸
  （母版 .stage 是 body 首个子元素，位于页面左上角 (0,0)）。
  裁切前校验截图不小于目标尺寸，避免静默出错。

用法：
    python render_png.py --html poster.zh.html --out out/poster.zh.png --scale 2
    python render_png.py --html poster.zh.html --out out/poster.zh.png --scale 2 \
        --qa-bg out/poster.zh.bg.png --boxes out/poster.zh.boxes.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

# 视口补偿余量（CSS px）。实测窗口装饰约 21×91，这里给足 5 倍以上，留余量给
# 不同 Edge/Chrome 版本与 DPI。宁可多截再裁，不可少截。
PAD = 160

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge",
]
PATH_NAMES = ["chrome", "google-chrome", "chromium", "chromium-browser", "msedge", "microsoft-edge"]


def find_browser():
    env = os.environ.get("POSTER_FORGE_BROWSER")
    if env and os.path.exists(env):
        return env
    for p in BROWSER_CANDIDATES:
        if os.path.exists(p):
            return p
    for name in PATH_NAMES:
        p = shutil.which(name)
        if p:
            return p
    return None


def to_file_url(path):
    path = os.path.abspath(path).replace("\\", "/")
    return "file:///" + path.lstrip("/") if path.startswith("/") else "file:///" + path


def _run(browser, args, timeout=90):
    """timeout 给足 90s：PAD 之后窗口更大、截图更慢，40s 会偶发超时（实测踩过）。"""
    profile = tempfile.mkdtemp(prefix="pf-profile-")
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={profile}", *args]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _ensure_dir(path):
    """输出目录不存在时自动创建（收包的人常直接跑示例，目录可能还没建）。"""
    if not path:
        return
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def shot(browser, html, out, w, h, scale, query=""):
    _ensure_dir(out)
    _run(browser, [f"--window-size={w + PAD},{h + PAD}", f"--force-device-scale-factor={scale}",
                   "--virtual-time-budget=4000", "--run-all-compositor-stages-before-draw",
                   f"--screenshot={os.path.abspath(out)}", to_file_url(html) + query])
    if not os.path.exists(out):
        raise RuntimeError(f"截图失败：{out} 未生成（浏览器：{browser}）")
    # 裁回设计尺寸：stage 位于页面左上角，视口已由 PAD 保证大于 stage
    tw, th = w * scale, h * scale
    im = Image.open(out)
    if im.width < tw or im.height < th:
        raise RuntimeError(
            f"截图 {im.size} 小于目标 {tw}x{th}：视口余量不足（PAD={PAD}）。"
            f"请增大 PAD —— headless=new 的 --window-size 只框住窗口，视口会更小。")
    if im.size != (tw, th):
        im.crop((0, 0, tw, th)).save(out)
    return out


def dump_boxes(browser, html, w, h, out_json, query=""):
    """取页面里由母版 QA 仪器写出的文字元素矩形（<script id='pf-boxes'>）。"""
    _ensure_dir(out_json)
    r = _run(browser, [f"--window-size={w + PAD},{h + PAD}", "--virtual-time-budget=4000",
                       "--dump-dom", to_file_url(html) + query])
    dom = r.stdout.decode("utf-8", "replace")
    m = re.search(r'<script type="application/json" id="pf-boxes">(.*?)</script>', dom, re.S)
    if not m:
        raise RuntimeError("未取到 QA 数据：母版里是否缺少 pf-boxes 仪器脚本？")
    data = json.loads(m.group(1))
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1500)
    ap.add_argument("--h", type=int, default=1875)
    ap.add_argument("--scale", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--qa-bg", default=None, help="再截一张「隐藏文字层」的图，用于对比度机检")
    ap.add_argument("--boxes", default=None, help="导出文字元素矩形与样式的 JSON")
    ap.add_argument("--query", default="",
                    help="附加到 file:// URL 的查询串（如 ?lang=en 或 ?theme=deep）——"
                         "成品图、QA 背景图、文字盒导出三处共用，保证同语言/同主题")
    a = ap.parse_args()

    browser = find_browser()
    if not browser:
        print("找不到 Edge / Chrome。可设环境变量 POSTER_FORGE_BROWSER 指定浏览器路径。", file=sys.stderr)
        return 2
    q = a.query
    if q and not q.startswith("?"):
        q = "?" + q
    if "pf-qa" in q:
        print("⚠ --query 不要带 pf-qa（它由 --qa-bg 自行追加）", file=sys.stderr)
        return 2
    shot(browser, a.html, a.out, a.w, a.h, a.scale, query=q)
    print(f"[render] {a.out}")
    if a.qa_bg:
        sep = "&" if q else "?"
        shot(browser, a.html, a.qa_bg, a.w, a.h, a.scale, query=f"{q}{sep}pf-qa=bg")
        print(f"[render] {a.qa_bg}（文字层隐藏）")
    if a.boxes:
        data = dump_boxes(browser, a.html, a.w, a.h, a.boxes, query=q)
        print(f"[render] {a.boxes}（{len(data)} 个文字元素）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
