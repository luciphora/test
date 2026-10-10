#!/usr/bin/env python3
"""Recover card stills for 17 Sep ads from the published 17 Sep page.

Ads Foreplay has since re-keyed or dropped come back from no pull with media, but
the 17 Sep report embedded a still for each of its 44 cards. Decode those into
thumbs_small/<id>.jpg (and under the new id when the ad was re-keyed).
"""
import re, base64, json, os, io

os.chdir(os.path.dirname(os.path.abspath(__file__)))
h = open("snapshots/report_2026-09-17.html", encoding="utf-8").read()
ads = json.load(open("ads.json"))
rekey = {a["was_id_0917"]: a["id"] for a in ads if a.get("was_id_0917")}
os.makedirs("thumbs_small", exist_ok=True)
n = 0
for m in re.finditer(r'<figure class="card">(.*?)</figure>', h, re.S):
    c = m.group(1)
    fid = re.search(r"ad=([A-Za-z0-9]+)", c).group(1)
    img = re.search(r'src="data:image/([a-z]+);base64,([A-Za-z0-9+/=]+)"', c)
    if not img:
        continue
    raw = base64.b64decode(img.group(2))
    if img.group(1) != "jpeg":
        from PIL import Image
        buf = io.BytesIO(); Image.open(io.BytesIO(raw)).convert("RGB").save(buf, "JPEG", quality=62); raw = buf.getvalue()
    for out_id in {fid, rekey.get(fid, fid)}:
        p = f"thumbs_small/{out_id}.jpg"
        if not os.path.exists(p):
            open(p, "wb").write(raw); n += 1
print(f"recovered {n} stills from the 17 Sep page")
