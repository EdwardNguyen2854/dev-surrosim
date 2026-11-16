"""Record the animated SurroSim clip and encode it for the web.

Playwright records the live page to WebM, then the bundled ffmpeg transcodes
to H.264 MP4 (widely embeddable) and a trimmed WebM.

Usage:  python blog/record_video.py
"""
from __future__ import annotations

import glob
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "race.html"
OUT = ROOT / "assets"
TMP = ROOT / ".video"
SECONDS = 10.6


def find_ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    base = Path.home() / "AppData" / "Local" / "ms-playwright"
    hits = sorted(glob.glob(str(base / "ffmpeg-*" / "ffmpeg*.exe")))
    return hits[-1] if hits else None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(TMP),
            record_video_size={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        page = ctx.new_page()
        page.goto(SRC.as_uri())
        page.wait_for_timeout(int(SECONDS * 1000))
        page.close()
        ctx.close()
        browser.close()

    webm = next(TMP.glob("*.webm"))
    raw = OUT / "race-raw.webm"
    shutil.copy(webm, raw)

    ff = find_ffmpeg()
    if not ff:
        print("ffmpeg not found; kept", raw)
        return 1

    mp4 = OUT / "fig-08-solver-vs-surrogate.mp4"
    subprocess.run(
        [ff, "-y", "-i", str(raw), "-an",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)],
        check=True, capture_output=True,
    )
    webm_out = OUT / "fig-08-solver-vs-surrogate.webm"
    subprocess.run(
        [ff, "-y", "-i", str(raw), "-an", "-c:v", "libvpx-vp9", "-crf", "34",
         "-b:v", "0", "-row-mt", "1", str(webm_out)],
        check=True, capture_output=True,
    )
    raw.unlink()
    shutil.rmtree(TMP, ignore_errors=True)
    for f in (mp4, webm_out):
        print(f"{f.name}: {f.stat().st_size / 1024:.0f} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
