"""Render the blog artboards to PNG with headless Chromium.

Runs the page in a real browser so the SVG + canvas field are drawn exactly as
authored, then screenshots each <section class="board"> at 2x device scale.

Usage:  python blog/render.py [board-id ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "artboards.html"
OUT = ROOT / "assets"
SCALE = 2


def main(wanted: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1500, "height": 1000},
            device_scale_factor=SCALE,
        )
        page.goto(SRC.as_uri())
        page.wait_for_timeout(600)
        boards = page.query_selector_all("section.board")
        for board in boards:
            bid = board.get_attribute("id")
            if wanted and bid not in wanted:
                continue
            shot = board.get_attribute("data-shot") or f"{bid}.png"
            path = OUT / shot
            board.screenshot(path=str(path))
            box = board.bounding_box()
            print(f"{bid:12s} {int(box['width'])}x{int(box['height'])} -> "
                  f"{path.name} ({int(box['width'])*SCALE}x{int(box['height'])*SCALE})")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
