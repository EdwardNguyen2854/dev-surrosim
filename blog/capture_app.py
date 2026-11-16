"""Capture product screenshots from a running SurroSim app.

Start the service first (the registries that exist in this checkout):

    python -m surrosim serve --port 8013 \
        --registry models/scalar/v2_reviewed_candidate \
        --field-model models/gnn/v2_normalized_candidate

then run this script. Screenshots go to blog/assets/ at 2x.

The shots show finished work, so the script drives each page (start the job,
wait for it, then capture) instead of snapshotting an empty form.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets"
BASE = "http://127.0.0.1:8013"

FULL = {"width": 1440, "height": 960}


def shot(page: Page, name: str, full_page: bool = True, clip: dict | None = None) -> None:
    path = OUT / name
    page.screenshot(path=str(path), full_page=full_page, clip=clip)
    print(f"  {name}")


def open_page(page: Page, route: str) -> None:
    page.goto(f"{BASE}{route}", wait_until="networkidle")
    page.wait_for_timeout(2200)


def capture_explorer(page: Page) -> None:
    open_page(page, "/")
    shot(page, "fig-09-app-explorer.png")


def capture_field(page: Page) -> None:
    open_page(page, "/field")
    page.get_by_role("button", name="Predict field").first.click()
    page.wait_for_timeout(30000)
    shot(page, "fig-10-app-field.png")


def capture_optimization(page: Page) -> None:
    open_page(page, "/optimize")
    page.get_by_role("button", name="Run optimization").first.click()
    page.wait_for_timeout(60000)
    shot(page, "fig-11-app-optimization.png")


def capture_verify(page: Page) -> None:
    open_page(page, "/verify")
    page.get_by_role("button", name="Run CalculiX verification").first.click()
    page.wait_for_timeout(45000)
    box = page.evaluate(
        """() => {
            let best = null;
            document.querySelectorAll('div,section,article').forEach(e => {
                const t = (e.textContent || '').toLowerCase();
                if (t.includes('comparison against calculix') && t.includes('solver runtime')) {
                    const r = e.getBoundingClientRect();
                    if (r.width > 500 && (!best || r.height < best.h)) {
                        best = {x: r.x, y: r.y, w: r.width, h: r.height};
                    }
                }
            });
            return best;
        }"""
    )
    if not box:
        raise RuntimeError("verification comparison panel not found")
    shot(page, "fig-12-app-fea-verify.png", full_page=False,
         clip={"x": box["x"] - 16, "y": box["y"] - 16,
               "width": box["w"] + 32, "height": box["h"] + 46})


CAPTURES = {
    "explorer": capture_explorer,
    "field": capture_field,
    "optimization": capture_optimization,
    "verify": capture_verify,
}


def main(wanted: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    names = wanted or list(CAPTURES)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=FULL, device_scale_factor=2)
        for name in names:
            print(name)
            CAPTURES[name](page)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
