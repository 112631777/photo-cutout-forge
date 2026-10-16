#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_png.py -- HTML master template to PNG deliverable (headless browser)

Screenshot with the system's built-in Edge / Chrome headless mode; no Playwright.
It can also export "QA data": the bounding boxes and computed styles of text
elements (used by check_contrast.py).

WARNING: viewport compensation (fixed on 2026-10-10 after testing; do not remove)
  In headless=new mode, --window-size is the "outer window size", and the actual
  viewport is smaller (tested on local Edge 135: 21x91 CSS px less at scale=2,
  24x93 at scale=1). The screenshot is output at window-size x scale, so the page
  only renders up to the viewport, and the body background shows in the
  bottom-right -- the master body is dark #17130E, so the deliverable gets a black
  edge at bottom-right. Machine checks cannot catch this (check_contrast only looks
  at text rectangles); it can only be found by human-eye inspection or pixel
  auditing. Fix: when screenshotting, enlarge window-size by PAD so the viewport is
  larger than .stage, then crop back to the design size (the master .stage is the
  first child of body, at the top-left of the page (0,0)). Before cropping, verify
  the screenshot is not smaller than the target, to avoid silent errors.

Usage:
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

# Viewport compensation margin (CSS px). The window chrome is about 21x91 in
# tests; we give 5x+ here to leave headroom for different Edge/Chrome versions
# and DPI. Better to overshoot then crop than to undershoot.
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
    """Give a full 90s timeout: after PAD the window is larger and screenshots
    slower; 40s would occasionally time out (hit this in practice)."""
    profile = tempfile.mkdtemp(prefix="pf-profile-")
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={profile}", *args]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _ensure_dir(path):
    """Auto-create the output directory if missing (recipients often run the
    example directly, before the directory exists)."""
    if not path:
        return
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


# Relative resource references: <img src>, <script src>, <source src>, CSS url(...) (incl. @font-face)
_REF_PATTERNS = [
    re.compile(r'<(?:\w+)[^>]*?\ssrc\s*=\s*["\']([^"\']+)["\']', re.I),
    re.compile(r'url\(\s*["\']?([^"\'\s]+)["\']?\s*\)', re.I),
]
_SKIP_PREFIX = ("http://", "https://", "//", "data:", "mailto:", "#", "blob:", "javascript:")


def check_assets(html):
    """Pre-render preflight: check whether the **relative-path** resources referenced
    in the HTML all exist (resolved relative to the HTML's directory).

    Why this must be checked: when `<img src="logo.svg">` points to a missing file,
    the headless browser **does not error** -- it only draws a broken-image icon (or
    nothing) in the deliverable -- and the machine check (which only looks at text
    rectangles) cannot catch it either. Hit this in practice on 2026-10-14: the
    master was under `layouts/` while logo.svg was only copied to `src/`, so the
    LOGO in both poster versions was a broken image, and a full round of QA missed it.
    Returns the list of missing files (empty = all present).
    """
    base = os.path.dirname(os.path.abspath(html))
    try:
        text = open(html, encoding="utf-8").read()
    except OSError:
        return []
    seen, missing = set(), []
    for pat in _REF_PATTERNS:
        for ref in pat.findall(text):
            ref = ref.strip()
            if not ref or ref.lower().startswith(_SKIP_PREFIX):
                continue
            ref = ref.split("?")[0].split("#")[0]
            if not ref:
                continue
            key = ref.replace("\\", "/")
            if key in seen:
                continue
            seen.add(key)
            p = os.path.normpath(os.path.join(base, ref))
            if not os.path.exists(p):
                missing.append(ref)
    return missing


def shot(browser, html, out, w, h, scale, query=""):
    _ensure_dir(out)
    _run(browser, [f"--window-size={w + PAD},{h + PAD}", f"--force-device-scale-factor={scale}",
                   "--virtual-time-budget=4000", "--run-all-compositor-stages-before-draw",
                   f"--screenshot={os.path.abspath(out)}", to_file_url(html) + query])
    if not os.path.exists(out):
        raise RuntimeError(f"screenshot failed: {out} was not generated (browser: {browser})")
    # Crop back to design size: stage is at the page top-left; PAD guarantees the
    # viewport is larger than stage
    tw, th = w * scale, h * scale
    im = Image.open(out)
    if im.width < tw or im.height < th:
        raise RuntimeError(
            f"screenshot {im.size} is smaller than target {tw}x{th}: insufficient viewport margin (PAD={PAD})."
            f"Increase PAD -- in headless=new, --window-size only frames the window; the viewport is smaller.")
    if im.size != (tw, th):
        im.crop((0, 0, tw, th)).save(out)
    return out


def dump_boxes(browser, html, w, h, out_json, query=""):
    """Read the text-element rectangles written by the master's QA instrument
    (<script id='pf-boxes'>)."""
    _ensure_dir(out_json)
    r = _run(browser, [f"--window-size={w + PAD},{h + PAD}", "--virtual-time-budget=4000",
                       "--dump-dom", to_file_url(html) + query])
    dom = r.stdout.decode("utf-8", "replace")
    m = re.search(r'<script type="application/json" id="pf-boxes">(.*?)</script>', dom, re.S)
    if not m:
        raise RuntimeError("QA data not obtained: is the pf-boxes instrument script missing from the master?")
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
    ap.add_argument("--qa-bg", default=None, help="Also capture a 'hidden-text-layer' image for the contrast machine check")
    ap.add_argument("--boxes", default=None, help="Export the JSON of text-element rectangles and styles")
    ap.add_argument("--query", default="",
                    help="Query string appended to the file:// URL (e.g. ?lang=en or ?theme=deep) -- "
                         "shared by the deliverable image, the QA background image, and the text-box export, to keep the same language/theme")
    a = ap.parse_args()

    browser = find_browser()
    if not browser:
        print("Edge / Chrome not found. Set the POSTER_FORGE_BROWSER environment variable to the browser path.", file=sys.stderr)
        return 2
    # WARNING pre-render asset preflight: missing assets silently produce a
    # "broken image + alt text" that the machine check cannot catch (hit 2026-10-14)
    missing = check_assets(a.html)
    if missing:
        print("FAIL: pre-render preflight failed: the HTML references resources that do not "
              "exist (resolved relative to %s):"
              % os.path.dirname(os.path.abspath(a.html)), file=sys.stderr)
        for m in missing:
            print("    - %s" % m, file=sys.stderr)
        print("  Tip: copy the assets (logo / fonts / background images) to the HTML's "
              "**same directory or a subdirectory**, or fix the relative src path. Missing "
              "assets do not make the browser throw an error -- it only draws a broken image.",
              file=sys.stderr)
        return 2
    q = a.query
    if q and not q.startswith("?"):
        q = "?" + q
    if "pf-qa" in q:
        print("WARNING --query must not include pf-qa (it is appended by --qa-bg itself)", file=sys.stderr)
        return 2
    shot(browser, a.html, a.out, a.w, a.h, a.scale, query=q)
    print(f"[render] {a.out}")
    if a.qa_bg:
        sep = "&" if q else "?"
        shot(browser, a.html, a.qa_bg, a.w, a.h, a.scale, query=f"{q}{sep}pf-qa=bg")
        print(f"[render] {a.qa_bg} (text layer hidden)")
    if a.boxes:
        data = dump_boxes(browser, a.html, a.w, a.h, a.boxes, query=q)
        print(f"[render] {a.boxes} ({len(data)} text elements)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
