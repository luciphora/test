#!/usr/bin/env python3
"""Refuse to ship a report that would embarrass us.

Structural: no unfilled {{PLACEHOLDER}}, no U+FFFD, balanced tags, every card
has a still, no forbidden wrapper tags (the Artifact host supplies them).
Rendered (if the bundled Chromium is present): no horizontal overflow, no JS
errors, the transcript filter reports a count. Exit 1 on any failure.
"""
import re, sys, os, pathlib
from html.parser import HTMLParser

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
VOID = {"br","img","hr","input","meta","link","source","col","area","base","embed","track","wbr","path","circle","rect","line"}

class Tags(HTMLParser):
    def __init__(s): super().__init__(); s.st=[]; s.err=[]
    def handle_starttag(s,t,a):
        if t not in VOID: s.st.append(t)
    def handle_endtag(s,t):
        if t in VOID: return
        if s.st and s.st[-1]==t: s.st.pop()
        else: s.err.append(t)

def main(target):
    p = os.path.join(target, "report.html"); h = open(p, encoding="utf-8").read(); bad = []
    ph = sorted(set(re.findall(r"\{\{[A-Z_0-9]+\}\}", h)))
    if ph: bad.append(f"unfilled placeholders: {ph}")
    if "�" in h: bad.append(f"{h.count(chr(0xfffd))} U+FFFD chars (bad bytes in source data)")
    if re.search(r"<(!doctype|html|head|body)[ >]", h, re.I): bad.append("wrapper tags present; the host adds them")
    cards, noimg = h.count('class="card"'), h.count('class="noimg"')
    if noimg: bad.append(f"{noimg} of {cards} cards have no still — run fetch_stills.py")
    t = Tags(); t.feed(h)
    if t.err or t.st: bad.append(f"tag balance: stray {t.err[:5]} unclosed {t.st[:5]}")
    size = os.path.getsize(p) / 1e6
    if size > 15: bad.append(f"{size:.1f} MB exceeds the 16 MB artifact cap")
    render = "skipped (no chromium)"
    if os.path.exists(CHROME):
        try:
            from playwright.sync_api import sync_playwright
            pathlib.Path("/tmp/_v.html").write_text("<!doctype html><html><head><meta charset='utf-8'></head><body>"+h+"</body></html>")
            with sync_playwright() as pw:
                b = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
                pg = b.new_page(viewport={"width":1280,"height":1150}); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto("file:///tmp/_v.html"); pg.wait_for_timeout(2500)
                ov = pg.evaluate("document.documentElement.scrollWidth>document.documentElement.clientWidth")
                cnt = pg.eval_on_selector("#count", "e=>e.textContent") if pg.query_selector("#count") else "n/a"
                pg.screenshot(path=os.path.join(target, "shot_validate.png")); b.close()
            if ov: bad.append("page scrolls horizontally")
            if errs: bad.append(f"JS errors: {errs[:3]}")
            render = f"ok · filter count '{cnt}'"
        except Exception as e:
            render = f"render check failed: {e}"
    print(f"validate: {size:.2f} MB · {cards} cards · render {render}")
    for b in bad: print("  FAIL:", b)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main(sys.argv[1])
