#!/usr/bin/env python3
"""Build the ceramic-coating category report.

One snapshot, twenty advertisers, three segments that must not be pooled.
Tenure carries the analysis; there is no delta. Every figure in the prose is a
{{PLACEHOLDER}} filled from ads.json here — nothing is typed by hand.
"""
import json, base64, os, html, re, collections, statistics
import taxonomy as T

ads = json.load(open("ads.json"))
tx  = [a for a in ads if (a.get("full_transcription") or "").strip()]
esc = lambda s: html.escape(s or "")

for a in ads:
    a["brand"]   = T.brand(a)
    a["segment"] = T.segment(a)

live   = [a for a in ads if a.get("live") is True]
svc    = [a for a in ads if a["segment"] == "service"]
prod   = [a for a in ads if a["segment"] == "product"]
fran   = [a for a in ads if a["segment"] == "franchise"]
svc_live = [a for a in svc if a.get("live") is True]

def med(xs): return int(statistics.median(xs)) if xs else 0
def b64(aid):
    p = f"thumbs_small/{aid}.jpg"
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else None
def bar(p, cls): return f'<div class="bar"><i class="{cls}" style="width:{max(min(p,100),1)}%"></i></div>'

def card(a):
    img = b64(a["id"])
    media = f'<img loading="lazy" src="{img}" alt="">' if img else '<div class="noimg">no still</div>'
    t = (a.get("full_transcription") or "").strip()
    badge = (f'<span class="badge live">{a["days_running"]}d live</span>' if a.get("live")
             else '<span class="badge">not live</span>')
    return (f'<figure class="card"><a href="{esc(a.get("video") or a.get("foreplay_url") or "#")}" '
            f'target="_blank" rel="noopener">{media}</a><figcaption>{badge}'
            f'<b>{esc(a["brand"])}</b><span class="hook">{esc(a["hook"])} · {esc(a["funnel"])}</span>'
            f'<p class="op">{esc(" ".join(t.split())[:130])}{"…" if len(t) > 130 else ""}</p>'
            f'<p class="lnk"><a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a> · '
            f'<a href="{esc(a.get("foreplay_url"))}" target="_blank" rel="noopener">foreplay</a></p>'
            f'</figcaption></figure>')

# --- segment table -----------------------------------------------------------
SEG_ROWS = "".join(
    f'<tr><td><b>{lbl}</b><span class="sub">{note}</span></td><td class="n">{len(g)}</td>'
    f'<td class="n">{len([a for a in g if a.get("live")])}</td>'
    f'<td class="n">{med([a["days_running"] for a in g if a.get("live")]) or "—"}d</td>'
    f'<td class="n big">{max([a["days_running"] for a in g if a.get("live")], default=0)}d</td></tr>'
    for lbl, g, note in [("Service", svc, "sells an appointment"),
                         ("Product", prod, "sells a bottle"),
                         ("Franchise", fran, "sells a territory")])

# --- advertisers, service only ----------------------------------------------
byb = collections.defaultdict(list)
for a in svc: byb[a["brand"]].append(a)
arows = sorted(byb.items(), key=lambda kv: (-max((x["days_running"] for x in kv[1] if x.get("live")), default=0), -len(kv[1])))
ADV_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{len(v)}</td>'
    f'<td class="n">{len([x for x in v if x.get("live")]) or "—"}</td>'
    f'<td class="n big">{max((x["days_running"] for x in v if x.get("live")), default=0) or "—"}{"d" if any(x.get("live") for x in v) else ""}</td>'
    f'<td class="n">{len([x for x in v if x.get("started_date","") >= "2026-07-13"])}</td></tr>'
    for k, v in arows)

# --- hook families, service, live tenure ------------------------------------
byh = collections.defaultdict(list)
for a in svc:
    if a["hook"] not in ("Unclassified", "junk"): byh[a["hook"]].append(a)
hrows = sorted(byh.items(), key=lambda kv: -len(kv[1]))
mx_h = max((len(v) for _, v in hrows), default=1)
HOOK_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{len(v)}</td>'
    f'<td>{bar(round(100*len(v)/mx_h), "good" if len(v)>=100 else "mid" if len(v)>=30 else "bad")}</td>'
    f'<td class="n">{len([x for x in v if x.get("live")]) or "—"}</td>'
    f'<td class="n">{med([x["days_running"] for x in v if x.get("live")]) or "—"}</td></tr>'
    for k, v in hrows)

# --- funnels, service --------------------------------------------------------
byf = collections.Counter(a["funnel"] for a in svc)
FUN_ROWS = "".join(
    f'<tr><td><code>{esc(k)}</code></td><td class="n">{v}</td>'
    f'<td>{bar(round(100*v/len(svc)), "good" if k=="capture_page" else "mid")}</td>'
    f'<td class="n">{round(100*v/len(svc))}%</td></tr>'
    for k, v in byf.most_common())

# --- offer architecture ------------------------------------------------------
def count_in(pat, group, fields=("description", "headline", "full_transcription")):
    n = 0
    for a in group:
        blob = " ".join((a.get(f) or "") for f in fields)
        if re.search(pat, blob, re.I): n += 1
    return n

# Each dollar figure is classified by the words around it, because the biggest
# numbers in this category's copy are not prices: they are the saving and the
# value of the free add-ons.
ROLE_PAT = [
    ("saving",     r"(sav(e|ings?)|off|discount|down from|was)\D{0,24}$"),
    ("bonus value", r"(free|add-?ons?|value|bonus|included|throwing in)\D{0,24}$"),
    ("price",      r"(just|only|for|at|starting|regularly|package|from)\D{0,16}$"),
]
FIG = collections.defaultdict(collections.Counter)
for a in svc:
    blob = " ".join((a.get(f) or "") for f in ("description", "headline", "full_transcription"))
    for m in re.finditer(r"\$\s?([0-9][0-9,]{2,6})(?![0-9])", blob):
        amt = m.group(1).replace(",", "")
        before = blob[max(0, m.start()-40):m.start()].lower()
        role = next((r for r, p in ROLE_PAT if re.search(p, before)), "unlabelled")
        FIG[amt][role] += 1

def total(amt): return sum(FIG[amt].values())
prow = sorted(FIG, key=lambda k: -total(k))[:8]
top_n = total(prow[0])
PRICE_ROWS = "".join(
    f'<tr><td class="big">${int(k):,}</td>'
    f'<td>{esc(FIG[k].most_common(1)[0][0])}</td>'
    f'<td class="n">{total(k)}</td>'
    f'<td>{bar(round(100*total(k)/top_n), "good" if FIG[k].most_common(1)[0][0]=="price" else "mid")}</td></tr>'
    for k in prow)

BONUS = [("free interior detail",   r"free\s+interior\s+detail"),
         ("free windshield coating", r"free\s+windshield\s+(ceramic\s+)?coat"),
         ("free wheel coating",      r"free\s+wheel\s+(ceramic\s+)?coat"),
         ("lifetime warranty",       r"lifetime\s+warranty"),
         ("free carpet shampoo",     r"free\s+carpet\s+shampoo")]
brow = sorted(((lbl, count_in(p, svc)) for lbl, p in BONUS), key=lambda kv: -kv[1])
BONUS_ROWS = "".join(
    f'<tr><td>{esc(lbl)}</td><td class="n">{n}</td>'
    f'<td>{bar(round(100*n/max(brow[0][1],1)), "good" if n>=200 else "mid" if n>=20 else "bad")}</td></tr>'
    for lbl, n in brow)

n_50off = count_in(r"50\s?%\s*off", svc)
n_anyoff = count_in(r"\d{1,2}\s?%\s*off", svc)

# --- retargeting probe -------------------------------------------------------
n_dpa = len([a for a in ads if (a.get("display_format") or "").lower() == "dpa"])
n_dpa_svc = len([a for a in svc if (a.get("display_format") or "").lower() == "dpa"])

# --- new money ---------------------------------------------------------------
CUT = "2026-07-13"          # 60 days before the snapshot
new60 = [a for a in svc if (a.get("started_date") or "") >= CUT]
new60_on = len([a for a in new60 if a["funnel"] == "on_platform"])
newhook = collections.Counter(a["hook"] for a in new60 if a["hook"] not in ("Unclassified", "junk"))
NEW_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{v}</td>'
    f'<td>{bar(round(100*v/newhook.most_common(1)[0][1]), "good" if v>=100 else "mid" if v>=20 else "bad")}</td>'
    f'<td class="n">{round(100*v/len(new60))}%</td></tr>'
    for k, v in newhook.most_common(8))

# --- gallery + transcript browser -------------------------------------------
feat = sorted([a for a in svc if a.get("live") and (a.get("full_transcription") or "").strip()],
              key=lambda a: -a["days_running"])
feat += [a for a in sorted(svc, key=lambda a: -a["days_running"])
         if a not in feat and (a.get("full_transcription") or "").strip()]
TOP = "".join(card(a) for a in feat[:18])

def tx_badge(a):
    return (f'<span class="badge live">{a["days_running"]}d</span>' if a.get("live")
            else '<span class="badge">not live</span>')

TX_BLOCKS = "".join(
    f'<article class="tx" data-v="{esc(a["segment"])}" data-f="{esc(a["funnel"])}" '
    f'data-s="{"live" if a.get("live") else "dead"}">'
    f'<header>{tx_badge(a)}'
    f'<b>{esc(a["brand"])}</b><span class="hook">{esc(a["hook"])}</span>'
    f'<a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a></header>'
    f'<p>{esc(" ".join(a["full_transcription"].split()))}</p></article>'
    for a in sorted(tx, key=lambda a: (not a.get("live"), -a["days_running"])))

vals = {
    "N_ADS": f"{len(ads):,}", "N_BRANDS": str(len({a["brand"] for a in ads})),
    "N_TX": str(len(tx)), "N_LIVE": str(len(live)),
    "N_SVC": f"{len(svc):,}", "N_SVC_LIVE": str(len(svc_live)),
    "SVC_MED": str(med([a["days_running"] for a in svc_live])),
    "SVC_MAX": str(max(a["days_running"] for a in svc_live)),
    "N_PROD": str(len(prod)), "N_FRAN": str(len(fran)),
    "PROD_MED": str(med([a["days_running"] for a in prod if a.get("live")])),
    "N_ONPLAT": str(byf["on_platform"]), "PCT_ONPLAT": str(round(100*byf["on_platform"]/len(svc))),
    "N_CAPTURE": str(byf["capture_page"]), "PCT_CAPTURE": str(round(100*byf["capture_page"]/len(svc))),
    "N_DPA": str(n_dpa), "N_DPA_SVC": str(n_dpa_svc),
    "N_50OFF": str(n_50off), "N_ANYOFF": str(n_anyoff),
    "N_NEW60": str(len(new60)), "N_NEW60_ON": str(new60_on),
    "PCT_NEW60_ON": str(round(100*new60_on/len(new60))),
    "TOP_HOOK": esc(newhook.most_common(1)[0][0]), "TOP_HOOK_N": str(newhook.most_common(1)[0][1]),
    "HN_ADS": str(len(byb["Huracan Nero Luxury Auto Spa"])),
    "HN_LIVE": str(len([a for a in byb["Huracan Nero Luxury Auto Spa"] if a.get("live")])),
    "HN_NEW": str(len([a for a in byb["Huracan Nero Luxury Auto Spa"] if (a.get("started_date") or "") >= CUT])),
    "N_CLASS": str(sum(1 for a in tx if a["hook"] not in ("Unclassified", "junk"))),
    "PCT_CLASS": str(round(100*sum(1 for a in tx if a["hook"] not in ("Unclassified","junk"))
                           / max(len([a for a in tx if a["hook"] != "junk"]), 1))),
    "N_JUNK": str(sum(1 for a in tx if a["hook"] == "junk")),
    "SEG_ROWS": SEG_ROWS, "ADV_ROWS": ADV_ROWS, "HOOK_ROWS": HOOK_ROWS,
    "FUN_ROWS": FUN_ROWS, "PRICE_ROWS": PRICE_ROWS, "BONUS_ROWS": BONUS_ROWS,
    "NEW_ROWS": NEW_ROWS, "TOP": TOP, "TX_BLOCKS": TX_BLOCKS, "TX_COUNT": str(len(tx)),
}
out = ("<title>Ceramic Coating Ad Scan</title>\n<style>" + open("report.css").read() + "</style>\n"
       + open("report_body.html").read())
for k, v in vals.items(): out = out.replace("{{" + k + "}}", v)
out += "\n<script>" + open("report.js").read() + "</script>"
open("report.html", "w").write(out)
print(f"report.html  {os.path.getsize('report.html')/1e6:.2f} MB · {len(tx)} transcripts inline")
