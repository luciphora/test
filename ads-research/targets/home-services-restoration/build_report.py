#!/usr/bin/env python3
"""Build the home-services / restoration category report.

One snapshot, 21 advertisers, three segments that must not be pooled. Every
figure in the prose is a {{PLACEHOLDER}} filled here — nothing typed by hand.
CUT is derived from snapshots.json, never hardcoded.
"""
import json, base64, os, html, re, datetime, collections, statistics
import taxonomy as T

ads = json.load(open("ads.json"))
SNAP = json.load(open("snapshots.json"))[-1]
NOW  = datetime.date(*map(int, SNAP.split("-")))
CUT  = (NOW - datetime.timedelta(days=90)).isoformat()
esc  = lambda s: html.escape(s or "")

def full(a):
    return " ".join((a.get(f) or "") for f in ("headline", "description", "full_transcription"))

for a in ads:
    a["brand"]   = T.brand(a)
    a["seg"]     = T.segment(a)
    a["region"]  = T.region(a)
    blob = full(a).lower()
    a["vert"] = next((n for n, p in T.VERTICALS if re.search(p, blob)), "General")

live  = [a for a in ads if a.get("live") is True]
svc   = [a for a in ads if a["seg"] in ("duct_carpet", "restoration")]
dc    = [a for a in ads if a["seg"] == "duct_carpet"]
rest  = [a for a in ads if a["seg"] == "restoration"]
prod  = [a for a in ads if a["seg"] == "product"]
tx    = [a for a in ads if (a.get("full_transcription") or "").strip()]

def med(xs): return int(statistics.median(xs)) if xs else 0
def livep(g): return [a for a in g if a.get("live") is True]
def b64(aid):
    p = f"thumbs_small/{aid}.jpg"
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else None
def dstr(g):
    return f'{max(a["days_running"] for a in g)}d' if g else "—"
def bar(p, cls): return f'<div class="bar"><i class="{cls}" style="width:{max(min(int(p),100),1)}%"></i></div>'

def card(a):
    img = b64(a["id"])
    media = f'<img loading="lazy" src="{img}" alt="">' if img else '<div class="noimg">no still</div>'
    t = " ".join((a.get("full_transcription") or "").split())
    badge = (f'<span class="badge live">{a["days_running"]}d live</span>' if a.get("live")
             else '<span class="badge">not live</span>')
    return (f'<figure class="card"><a href="{esc(a.get("video") or a.get("foreplay_url") or "#")}" '
            f'target="_blank" rel="noopener">{media}</a><figcaption>{badge}'
            f'<b>{esc(a["brand"])}</b><span class="hook">{esc(a["vert"])} · {esc(a["hook"])}</span>'
            f'<p class="op">{esc(t[:130])}{"…" if len(t) > 130 else ""}</p>'
            f'<p class="lnk"><a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a> · '
            f'<a href="{esc(a.get("foreplay_url"))}" target="_blank" rel="noopener">foreplay</a></p>'
            f'</figcaption></figure>')

# --- segments ---------------------------------------------------------------
SEG_ROWS = "".join(
    f'<tr><td><b>{lbl}</b><span class="sub">{note}</span></td><td class="n">{len(g)}</td>'
    f'<td class="n">{len(livep(g))}</td>'
    f'<td>{bar(100*len(livep(g))/len(g), "good" if len(livep(g))/len(g) >= .25 else "bad")}</td>'
    f'<td class="n big">{round(100*len(livep(g))/len(g))}%</td>'
    f'<td class="n">{dstr(livep(g))}</td></tr>'
    for lbl, g, note in [("Duct &amp; carpet", dc, "sells a scheduled, discountable clean"),
                         ("Restoration", rest, "sells emergency mitigation")])
# Product was pulled live-only as a contrast set, so it has no meaningful live rate
# and must not sit in the same table implying 100% survival.
SEG_ROWS += (f'<tr class="muted"><td><b>DTC product</b><span class="sub">contrast set — live ads only, '
             f'so no live rate</span></td><td class="n">{len(prod)}</td><td class="n">{len(prod)}</td>'
             f'<td></td><td class="n">n/a</td>'
             f'<td class="n">{max([a["days_running"] for a in prod], default=0)}d</td></tr>')

# --- vertical channel viability (the headline table) -------------------------
byv = collections.defaultdict(list)
for a in svc: byv[a["vert"]].append(a)
vrows = sorted(byv.items(), key=lambda kv: -len(livep(kv[1])))
VERT_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{len(v)}</td><td class="n">{len(livep(v))}</td>'
    f'<td>{bar(100*len(livep(v))/len(v), "good" if len(livep(v))/len(v) >= .25 else "mid" if len(livep(v))/len(v) >= .05 else "bad")}</td>'
    f'<td class="n big">{round(100*len(livep(v))/len(v))}%</td>'
    f'<td class="n">{str(max([a["days_running"] for a in livep(v)], default=0)) + "d" if livep(v) else "—"}</td></tr>'
    for k, v in vrows)

# --- advertisers -------------------------------------------------------------
byb = collections.defaultdict(list)
for a in svc: byb[a["brand"]].append(a)
def adv_flag(v):
    return ' <span class="sub">Ireland</span>' if v[0]["region"] != "US" else ""

ADV_ROWS = "".join(
    f'<tr><td>{esc(k)}{adv_flag(v)}</td>'
    f'<td class="n">{"duct/carpet" if v[0]["seg"] == "duct_carpet" else "restoration"}</td>'
    f'<td class="n">{len(v)}</td><td class="n">{len(livep(v)) or "—"}</td>'
    f'<td class="n big">{str(max([x["days_running"] for x in livep(v)], default=0)) + "d" if livep(v) else "—"}</td></tr>'
    for k, v in sorted(byb.items(), key=lambda kv: (-len(livep(kv[1])), -len(kv[1]))))

# --- funnel, the operational split ------------------------------------------
def funrows(group):
    c = collections.Counter(a["funnel"] for a in group); n = sum(c.values())
    return "".join(
        f'<tr><td><code>{esc(k)}</code></td><td class="n">{v}</td>'
        f'<td>{bar(100*v/n, "good" if k == "booking_page" else "mid")}</td>'
        f'<td class="n">{round(100*v/n)}%</td></tr>' for k, v in c.most_common())
FUN_DC, FUN_REST = funrows(dc), funrows(rest)

def ctarows(group):
    c = collections.Counter(a.get("cta_type") or "—" for a in group); n = sum(c.values())
    return "".join(f'<tr><td><code>{esc(k)}</code></td><td class="n">{v}</td><td class="n">{round(100*v/n)}%</td></tr>'
                   for k, v in c.most_common(6))
CTA_DC, CTA_REST = ctarows(dc), ctarows(rest)

# --- price ladder ------------------------------------------------------------
# Order matters. "not a $99 cheap sweep" is a competitor naming the coupon price
# as the thing they are NOT — the opposite of quoting it, so it is tested first.
ROLE = [("anti-anchor", r"(not a|not the|isn'?t a|more than a|never a|beyond a)\s*$"),
        ("saving",      r"(sav(e|ings?)|off|discount|was|down from|reg(ularly)?)\D{0,20}$"),
        ("price",       r"(just|only|for|at|starting|special|solo por|por solo)\D{0,14}$")]
FIG = collections.defaultdict(collections.Counter)
for a in dc:
    blob = full(a)
    for m in re.finditer(r"\$\s?([0-9][0-9,]{1,5})(?![0-9])", blob):
        amt = m.group(1).replace(",", "")
        before = blob[max(0, m.start()-36):m.start()].lower()
        after  = blob[m.end():m.end()+14].lower()
        role = next((r for r, p in ROLE if re.search(p, before)), None)
        if role is None and re.match(r"\s*(off\b|savings?\b)", after): role = "saving"
        FIG[amt][role or "unlabelled"] += 1
tot = lambda k: sum(FIG[k].values())
prow = [k for k in sorted(FIG, key=lambda k: -tot(k)) if tot(k) >= 15][:8]
top_n = tot(prow[0]) if prow else 1
def role_cell(k):
    mc = FIG[k].most_common()
    lead, n = mc[0]
    if n / tot(k) >= 0.7 or len(mc) == 1:
        return esc(lead)
    parts = [f"{r} {c}" for r, c in mc if c / tot(k) >= 0.15]
    return f'<span class="sub">{esc(" · ".join(parts))}</span>'

PRICE_ROWS = "".join(
    f'<tr><td class="big">${int(k):,}</td><td>{role_cell(k)}</td>'
    f'<td class="n">{tot(k)}</td>'
    f'<td>{bar(100*tot(k)/top_n, "good" if FIG[k].most_common(1)[0][0] == "price" else "mid")}</td></tr>'
    for k in prow)
N_ANTI = sum(FIG[k]["anti-anchor"] for k in FIG)

# --- hooks (spoken) and themes (body copy) ----------------------------------
hk = collections.Counter(a["hook"] for a in tx if a["hook"] not in ("Unclassified", "junk"))
mx = hk.most_common(1)[0][1] if hk else 1
HOOK_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{v}</td><td>{bar(100*v/mx, "good" if v >= 30 else "mid" if v >= 10 else "bad")}</td>'
    f'<td class="n">{len([a for a in tx if a["hook"] == k and a.get("live")]) or "—"}</td></tr>'
    for k, v in hk.most_common())

th = collections.Counter()
for a in svc:
    for t in T.theme(a): th[t] += 1
mxt = th.most_common(1)[0][1] if th else 1
THEME_ROWS = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{v}</td><td>{bar(100*v/mxt, "good" if v >= 30 else "mid")}</td>'
    f'<td class="n">{round(100*v/len(svc))}%</td></tr>' for k, v in th.most_common())

# --- seasonality -------------------------------------------------------------
mon = collections.Counter()
for a in svc:
    d = a.get("started_date")
    if d: mon[d[5:7]] += 1
MONTHS = ["01","02","03","04","05","06","07","08","09","10","11","12"]
NAMES = dict(zip(MONTHS, "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()))
mxm = max(mon.values()) if mon else 1
SEASON_ROWS = "".join(
    f'<tr><td>{NAMES[m]}</td><td class="n">{mon.get(m,0)}</td>'
    f'<td>{bar(100*mon.get(m,0)/mxm, "good" if mon.get(m,0) >= mxm*0.6 else "mid")}</td></tr>' for m in MONTHS)

# --- gallery + transcripts ---------------------------------------------------
# A card shows its opening line, so an ASR-blank clip ("Thanks for watching!")
# makes a poor card however long it has run. Readable openers first.
readable = lambda a: (a.get("full_transcription") or "").strip() and a["hook"] != "junk"
feat = sorted([a for a in svc if a.get("live") and readable(a)], key=lambda a: -a["days_running"])
feat += [a for a in sorted(svc, key=lambda a: -a["days_running"]) if a not in feat and readable(a)]
feat += [a for a in sorted(svc, key=lambda a: -a["days_running"])
         if a not in feat and (a.get("full_transcription") or "").strip()]
TOP = "".join(card(a) for a in feat[:18])

def tx_badge(a):
    return (f'<span class="badge live">{a["days_running"]}d</span>' if a.get("live")
            else '<span class="badge">not live</span>')
TX_BLOCKS = "".join(
    f'<article class="tx" data-v="{esc(a["seg"])}" data-f="{esc(a["funnel"])}" '
    f'data-s="{"live" if a.get("live") else "dead"}">'
    f'<header>{tx_badge(a)}<b>{esc(a["brand"])}</b>'
    f'<span class="hook">{esc(a["vert"])} · {esc(a["hook"])}</span>'
    f'<a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a></header>'
    f'<p>{esc(" ".join(a["full_transcription"].split()))}</p></article>'
    for a in sorted(tx, key=lambda a: (not a.get("live"), -a["days_running"])))

pct = lambda a, b: round(100*a/b) if b else 0
mold = byv.get("Mold", []); water = byv.get("Water damage", [])
carpet = byv.get("Carpet", []); duct = byv.get("Air duct", [])
dc_book = collections.Counter(a["funnel"] for a in dc)["booking_page"]
r_book  = collections.Counter(a["funnel"] for a in rest)["booking_page"]

vals = {
    "N_ADS": f"{len(ads):,}", "N_BRANDS": str(len({a["brand"] for a in ads})), "N_TX": str(len(tx)),
    "N_LIVE": str(len(live)), "SNAP": SNAP,
    "N_DC": str(len(dc)), "N_DC_LIVE": str(len(livep(dc))), "PCT_DC_LIVE": str(pct(len(livep(dc)), len(dc))),
    "N_REST": str(len(rest)), "N_REST_LIVE": str(len(livep(rest))), "PCT_REST_LIVE": str(pct(len(livep(rest)), len(rest))),
    "REST_DEEPEST": str(max([a["days_running"] for a in livep(rest)], default=0)),
    "DC_DEEPEST": str(max([a["days_running"] for a in livep(dc)], default=0)),
    "N_PROD": str(len(prod)),
    "N_MOLD": str(len(mold)), "N_MOLD_LIVE": str(len(livep(mold))),
    "N_WATER": str(len(water)), "N_WATER_LIVE": str(len(livep(water))),
    "WATER_DEEPEST": str(max([a["days_running"] for a in livep(water)], default=0)),
    "N_CARPET": str(len(carpet)), "PCT_CARPET_LIVE": str(pct(len(livep(carpet)), len(carpet))),
    "N_DUCT": str(len(duct)), "PCT_DUCT_LIVE": str(pct(len(livep(duct)), len(duct))),
    "DC_BOOK": str(dc_book), "PCT_DC_BOOK": str(pct(dc_book, len(dc))),
    "R_BOOK": str(r_book), "PCT_R_BOOK": str(pct(r_book, len(rest))),
    "N_GUAR": str(th["Guarantee"]), "N_COST": str(th["Cost reframe"]),
    "N_REPL": str(th["Replace vs restore"]), "N_REF": str(th["Referral partner"]),
    "N_FIRST": str(th["First-time gate"]), "N_SEASON": str(th["Seasonal"]),
    "TOP_HOOK": esc(hk.most_common(1)[0][0]), "TOP_HOOK_N": str(hk.most_common(1)[0][1]),
    "N_CLASS": str(sum(hk.values())),
    "PCT_CLASS": str(pct(sum(hk.values()), len([a for a in tx if a["hook"] != "junk"]))),
    "N_JUNK": str(sum(1 for a in tx if a["hook"] == "junk")), "N_ANTI": str(N_ANTI),
    "SEG_ROWS": SEG_ROWS, "VERT_ROWS": VERT_ROWS, "ADV_ROWS": ADV_ROWS,
    "FUN_DC": FUN_DC, "FUN_REST": FUN_REST, "CTA_DC": CTA_DC, "CTA_REST": CTA_REST,
    "PRICE_ROWS": PRICE_ROWS, "HOOK_ROWS": HOOK_ROWS, "THEME_ROWS": THEME_ROWS,
    "SEASON_ROWS": SEASON_ROWS, "TOP": TOP, "TX_BLOCKS": TX_BLOCKS, "TX_COUNT": str(len(tx)),
}
out = ("<title>Restoration Ad Scan</title>\n<style>" + open("report.css").read() + "</style>\n"
       + open("report_body.html").read())
for k, v in vals.items(): out = out.replace("{{" + k + "}}", v)
out += "\n<script>" + open("report.js").read() + "</script>"
open("report.html", "w").write(out)
print(f"report.html  {os.path.getsize('report.html')/1e6:.2f} MB · {len(tx)} transcripts inline")
