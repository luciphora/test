#!/usr/bin/env python3
"""Render each ad creative HTML to a PNG at its declared pixel size.

    python3 render_creatives.py targets/<slug> [--only A1]
    python3 render_creatives.py targets/<slug> --sizes 1080x1350,1080x1080,1080x1920

Each creative declares its canvas in the document:

    <meta name="size" content="1080x1350">

which is used as the viewport, so what Chromium paints is exactly the asset.
Fonts are inlined as base64 in creatives/fonts/embedded.css, so a render never
depends on network or on the container's font set — only DejaVu/Liberation are
installed here and a fallback would silently wreck the typography. The renderer
asserts the real computed family instead of trusting that.

With --sizes, one creative renders at several aspect ratios. Rather than keeping
a file per ratio — which would put three copies of every sentence in the repo and
let them drift the first time a word changes — the ratio is stamped onto the root
element as data-ar (4x5 / 1x1 / 9x16) before the document runs, and each creative
carries small :root[data-ar=...] override blocks. Copy lives in exactly one place;
only spacing and type sizes differ between cuts.
"""
import argparse, os, pathlib, re, sys

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
EXPECT_FAMILIES = ("Archivo", "Inter")

# Named by the ratio rather than the pixel size so a creative's CSS reads as a
# design decision ("on square, drop the photo band") and not as a magic number.
AR_NAME = {(4, 5): "4x5", (1, 1): "1x1", (9, 16): "9x16"}

def size_of(html: str) -> tuple[int, int]:
    m = re.search(r'<meta\s+name=["\']size["\']\s+content=["\'](\d+)x(\d+)', html)
    if not m:
        sys.exit("creative has no <meta name=\"size\" content=\"WxH\">")
    return int(m.group(1)), int(m.group(2))

def ar_of(w: int, h: int) -> str:
    from math import gcd
    g = gcd(w, h)
    key = (w // g, h // g)
    if key not in AR_NAME:
        sys.exit(f"{w}x{h} is not one of the supported ratios {sorted(AR_NAME.values())}")
    return AR_NAME[key]

def base_name(stem: str) -> str:
    """Filenames already end in their native size; swap it rather than stack a second one."""
    return re.sub(r"-\d+x\d+$", "", stem)

def parse_sizes(spec: str) -> list[tuple[int, int]]:
    out = []
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)x(\d+)\s*", part)
        if not m:
            sys.exit(f"--sizes wants WxH[,WxH...], got {part!r}")
        out.append((int(m.group(1)), int(m.group(2))))
    return out

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--only", help="render just the creatives whose filename starts with this")
    ap.add_argument("--sizes", help="comma-separated WxH list; default is each file's own "
                                    "<meta name=\"size\">")
    a = ap.parse_args()
    sizes = parse_sizes(a.sizes) if a.sizes else None

    cdir = (pathlib.Path(a.target) / "creatives").resolve()
    out = cdir / "out"; out.mkdir(exist_ok=True)
    files = sorted(p for p in cdir.glob("*.html")
                   if not a.only or p.stem.lower().startswith(a.only.lower()))
    if not files:
        sys.exit(f"no creatives matched in {cdir}")
    if not os.path.exists(CHROME):
        sys.exit(f"bundled chromium missing at {CHROME}")

    from playwright.sync_api import sync_playwright
    bad = []; shots = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        for f in files:
            native = size_of(f.read_text())
            for w, h in (sizes or [native]):
                ar = ar_of(w, h)
                pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(f.as_uri())
                # after the document exists but before the screenshot: the style change
                # reflows synchronously, and we still wait below for fonts and images
                pg.evaluate("ar => document.documentElement.setAttribute('data-ar', ar)", ar)
                pg.wait_for_timeout(700)
                try:
                    pg.evaluate("document.fonts.ready")
                except Exception:
                    pass
                tag = f"{f.name} @{ar}"
                fam = pg.evaluate("getComputedStyle("
                                  "document.querySelector('.display')||document.body).fontFamily")
                if not any(e in fam for e in EXPECT_FAMILIES):
                    bad.append(f"{tag}: fell back to {fam!r} — embedded fonts did not load")
                # Content pushed outside the canvas is a layout bug, not a crop — and
                # .ad sets overflow:hidden, so an overrunning footer is clipped away
                # silently and the document never scrolls. Walk the normal flow instead
                # and name what busts the frame. Absolutely positioned layers are skipped
                # on purpose: a full-bleed photo is meant to overhang (A3 over-scales its
                # wallpaper by 8%), and flagging that would train us to ignore this check.
                over = pg.evaluate("""([w, h]) => {
                    for (const e of document.body.querySelectorAll('*')) {
                        const p = getComputedStyle(e).position;
                        if (p === 'absolute' || p === 'fixed') continue;
                        const r = e.getBoundingClientRect();
                        if (!r.width || !r.height) continue;
                        if (r.bottom > h + 1 || r.top < -1 || r.right > w + 1 || r.left < -1)
                            return `${e.className || e.tagName} at `
                                 + `${r.top.toFixed(0)}..${r.bottom.toFixed(0)}`;
                    }
                    return '';
                }""", [w, h])
                if over:
                    bad.append(f"{tag}: content overflows the {w}x{h} canvas — {over}")
                if errs:
                    bad.append(f"{tag}: JS errors {errs[:2]}")
                stem = f.stem if not sizes else f"{base_name(f.stem)}-{w}x{h}"
                png = out / f"{stem}.png"
                pg.screenshot(path=str(png)); pg.close(); shots += 1
                print(f"  {stem:<40} {w}x{h}  {png.stat().st_size/1024:>6.0f} KB")
        b.close()
    print(f"\n{shots} render(s) from {len(files)} creative(s) -> {out}")
    for x in bad: print("  FAIL:", x)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
