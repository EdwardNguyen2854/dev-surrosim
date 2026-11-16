"""Render the blog post to a preview page and screenshot it.

A quick way to check the reading experience — image scale, captions, heading
rhythm — without standing up the real site.

    python blog/preview.py            # writes blog/.preview/post.html + shots
"""
from __future__ import annotations

from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "introducing-surrosim.md"
OUT = ROOT / ".preview"

CSS = """
:root{--paper:#FBFAF7;--ink:#14181C;--ink2:#525C66;--rule:#DDE0DC;--accent:#1B4A6E}
*{box-sizing:border-box}
body{margin:0;background:#EDEEEA;font-family:"Segoe UI",Arial,sans-serif;color:var(--ink)}
article{max-width:760px;margin:0 auto;padding:64px 32px 120px;background:var(--paper);
        min-height:100vh;box-shadow:0 0 0 1px rgba(0,0,0,.05)}
h1{font-family:"Bahnschrift","Segoe UI Semibold",sans-serif;font-weight:600;
   font-size:44px;line-height:1.08;letter-spacing:-.6px;margin:0 0 18px}
h2{font-family:"Bahnschrift","Segoe UI Semibold",sans-serif;font-weight:600;
   font-size:27px;letter-spacing:-.3px;margin:56px 0 16px}
p,li{font-size:17.5px;line-height:1.66;color:#22282E}
p{margin:0 0 20px}
strong{font-weight:650}
em{color:var(--ink2)}
blockquote{margin:0 0 22px;padding:14px 20px;border-left:2px solid var(--accent);
           background:#F3F5F2;font-family:"Cascadia Mono",Consolas,monospace;font-size:15px}
blockquote p{margin:0;font:inherit;font-size:15px;color:var(--accent)}
img,video{display:block;width:100%;height:auto;margin:30px 0 10px;border:1px solid var(--rule);
          background:#fff}
p > em:only-child{display:block;font-size:13.5px;line-height:1.5;color:var(--ink2);
                  margin:-2px 0 34px;padding-left:2px}
ol,ul{margin:0 0 20px;padding-left:24px}
li{margin:0 0 10px}
code{font-family:"Cascadia Mono",Consolas,monospace;font-size:.88em;
     background:#EFF1EE;padding:1px 5px;border-radius:3px}
pre{background:#182028;color:#DDE3E6;padding:18px 20px;border-radius:3px;overflow:auto;
    font-size:13px;line-height:1.6;margin:0 0 24px}
pre code{background:none;color:inherit;padding:0}
hr{border:0;border-top:1px solid var(--rule);margin:48px 0 28px}
a{color:var(--accent)}
article > p:nth-of-type(1){font-size:19px;line-height:1.5;color:#2A3138;margin-bottom:8px}
"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    body = markdown.markdown(SRC.read_text(encoding="utf-8"), extensions=["extra"])
    html = (f"<!doctype html><meta charset='utf-8'><base href='../'>"
            f"<style>{CSS}</style><article>{body}</article>")
    page_path = OUT / "post.html"
    page_path.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 1400},
                                device_scale_factor=1)
        page.goto(page_path.as_uri())
        page.wait_for_timeout(1200)
        total = page.evaluate("document.body.scrollHeight")
        print(f"page height {total}px")
        for i, y in enumerate((0, 1300, 2900, total - 1500)):
            page.evaluate(f"window.scrollTo(0, {max(0, y)})")
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"shot{i + 1}.png"))
        browser.close()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
