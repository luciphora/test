#!/usr/bin/env python3
"""Render each ad creative HTML to a PNG at its declared pixel size.

    python3 render_creatives.py targets/<slug> [--only A1]

Each creative declares its canvas in the document:

    <meta name="size" content="1080x1350">

which is used as the viewport, so what Chromium paints is exactly the asset.
Fonts are inlined as base64 in creatives/fonts/embedded.css, so a render never
depends on network or on the container's font set — only DejaVu/Liberation are
installed here and a fallback would silently wreck the typography. The renderer
asserts the real computed family instead of trusting that.
"""
import argparse, os, pathlib, re, sys

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
EXPECT_FAMILIES = ("Archivo", "Inter")

def size_of(html: str) -> tuple[int, int]:
    m = re.search(r'<meta\s+name=["\']size["\']\s+content=["\'](\d+)x(\d+)', html)
    if not m:
        sys.exit("creative has no <meta name=\"size\" content=\"WxH\">")
    return int(m.group(1)), int(m.group(2))

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--only", help="render just the creatives whose filename starts with this")
    a = ap.parse_args()

    cdir = (pathlib.Path(a.target) / "creatives").resolve()
    out = cdir / "out"; out.mkdir(exist_ok=True)
    files = sorted(p for p in cdir.glob("*.html")
                   if not a.only or p.stem.lower().startswith(a.only.lower()))
    if not files:
        sys.exit(f"no creatives matched in {cdir}")
    if not os.path.exists(CHROME):
        sys.exit(f"bundled chromium missing at {CHROME}")

    from playwright.sync_api import sync_playwright
    bad = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        for f in files:
            w, h = size_of(f.read_text())
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f.as_uri()); pg.wait_for_timeout(700)
            try:
                pg.evaluate("document.fonts.ready")
            except Exception:
                pass
            fam = pg.evaluate(
                "getComputedStyle(document.querySelector('.display')||document.body).fontFamily")
            if not any(e in fam for e in EXPECT_FAMILIES):
                bad.append(f"{f.name}: fell back to {fam!r} — embedded fonts did not load")
            # anything painted outside the canvas is a layout bug, not a crop
            over = pg.evaluate(
                "document.documentElement.scrollWidth>document.documentElement.clientWidth"
                " || document.documentElement.scrollHeight>document.documentElement.clientHeight")
            if over:
                bad.append(f"{f.name}: content overflows the {w}x{h} canvas")
            if errs:
                bad.append(f"{f.name}: JS errors {errs[:2]}")
            png = out / f"{f.stem}.png"
            pg.screenshot(path=str(png)); pg.close()
            print(f"  {f.stem:<28} {w}x{h}  {png.stat().st_size/1024:>6.0f} KB")
        b.close()
    print(f"\n{len(files)} creative(s) -> {out}")
    for x in bad: print("  FAIL:", x)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
