#!/usr/bin/env python3
"""Build the market-scan report. Different shape from a single-advertiser teardown:
one snapshot, many advertisers, so tenure carries the analysis and no delta exists."""
import json, base64, os, html, collections, statistics

ads = json.load(open("ads.json"))
tx  = [a for a in ads if a.get("full_transcription")]
esc = lambda s: html.escape(s or "")

def b64(aid):
    p = f"thumbs_small/{aid}.jpg"
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else None

def card(a):
    img = b64(a["id"])
    media = f'<img loading="lazy" src="{img}" alt="">' if img else '<div class="noimg">no still</div>'
    t = a.get("full_transcription") or ""
    return (f'<figure class="card"><a href="{esc(a.get("video") or a.get("foreplay_url") or "#")}" '
            f'target="_blank" rel="noopener">{media}</a><figcaption>'
            f'<span class="badge live">{a["days_running"]}d live</span>'
            f'<b>{esc(a["funnel"])}</b><span class="hook">{esc(a["hook"])}</span>'
            f'<p class="op">{esc(t[:120])}{"…" if len(t) > 120 else ""}</p>'
            f'<p class="lnk"><a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a> · '
            f'<a href="{esc(a.get("foreplay_url"))}" target="_blank" rel="noopener">foreplay</a></p>'
            f'</figcaption></figure>')

def bar(p, cls): return f'<div class="bar"><i class="{cls}" style="width:{min(p,100)}%"></i><span>{p}d</span></div>'

# --- advertisers -------------------------------------------------------------
byb = collections.defaultdict(list)
for a in ads: byb[a["funnel"]].append(a)
rows = sorted(byb.items(), key=lambda kv: -max(x["days_running"] for x in kv[1]))
mx_all = max(a["days_running"] for a in ads)
ADV_ROWS = "".join(
    f'<tr><td><code>{esc(k)}</code></td><td class="n">{len(v)}</td>'
    f'<td class="n big">{max(x["days_running"] for x in v)}d</td>'
    f'<td>{bar(round(100*statistics.median([x["days_running"] for x in v])/mx_all) or 1, "good" if statistics.median([x["days_running"] for x in v])>=45 else "mid" if statistics.median([x["days_running"] for x in v])>=20 else "bad")}</td>'
    f'<td class="n">{int(statistics.median([x["days_running"] for x in v]))}d</td></tr>'
    for k, v in rows)

# --- hook families by median tenure -----------------------------------------
byh = collections.defaultdict(list)
for a in tx:
    if a["hook"] != "Unclassified": byh[a["hook"]].append(a["days_running"])
hrows = sorted(byh.items(), key=lambda kv: -statistics.median(kv[1]))
mx_h = max(statistics.median(v) for _, v in hrows)
HOOK_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{len(v)}</td>'
    f'<td>{bar(round(100*statistics.median(v)/mx_h) or 1, "good" if statistics.median(v)>=70 else "mid" if statistics.median(v)>=30 else "bad")}</td>'
    f'<td class="n">{int(statistics.median(v))}d</td><td class="n">{max(v)}d</td></tr>'
    for k, v in hrows)

# --- tenure distribution ----------------------------------------------------
bands = [("300d+", 300, 10**9), ("100–299d", 100, 299), ("60–99d", 60, 99), ("30–59d", 30, 59), ("under 30d", 0, 29)]
BAND_ROWS = "".join(
    f'<tr><td>{lbl}</td><td class="n">{len([a for a in ads if lo <= a["days_running"] <= hi])}</td>'
    f'<td>{bar(round(100*len([a for a in ads if lo <= a["days_running"] <= hi])/len(ads)), "good" if lo>=60 else "bad")}</td></tr>'
    for lbl, lo, hi in bands)

TOP = "".join(card(a) for a in sorted([a for a in ads if a.get("full_transcription")],
                                      key=lambda a: -a["days_running"])[:18])
TX_BLOCKS = "".join(
    f'<article class="tx" data-v="{esc(a["vertical"])}" data-f="{esc(a["funnel"])}" data-s="live">'
    f'<header><span class="badge live">{a["days_running"]}d</span><b>{esc(a["funnel"])}</b>'
    f'<span class="hook">{esc(a["hook"])}</span>'
    f'<a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a></header>'
    f'<p>{esc(a["full_transcription"])}</p></article>'
    for a in sorted(tx, key=lambda a: -a["days_running"]))

vals = {
    "N_ADS": f"{len(ads):,}", "N_BRANDS": str(len({a.get("brand_id") for a in ads})), "N_TX": str(len(tx)),
    "MAX": str(mx_all), "N_60": str(len([a for a in ads if a["days_running"] >= 60])),
    "N_CLASS": str(sum(1 for a in tx if a["hook"] != "Unclassified")),
    "ADV_ROWS": ADV_ROWS, "HOOK_ROWS": HOOK_ROWS, "BAND_ROWS": BAND_ROWS,
    "TOP": TOP, "TX_BLOCKS": TX_BLOCKS, "TX_COUNT": str(len(tx)),
    "GUAR_MED": str(int(statistics.median(byh["Guarantee"]))) if "Guarantee" in byh else "?",
    "AUTO_N": str(sum(1 for a in tx if a["hook"] in ("AI / automation demo", "Mechanism walkthrough"))),
}
out = ("<title>Service-Business Ad Scan</title>\n<style>" + open("report.css").read() + "</style>\n"
       + open("report_body.html").read())
for k, v in vals.items(): out = out.replace("{{" + k + "}}", v)
out += "\n<script>" + open("report.js").read() + "</script>"
open("report.html", "w").write(out)
print(f"report.html  {os.path.getsize('report.html')/1e6:.2f} MB · {len(tx)} transcripts inline")
