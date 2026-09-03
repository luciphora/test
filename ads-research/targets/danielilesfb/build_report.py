#!/usr/bin/env python3
"""Render the Viral Coach teardown as one self-contained HTML page."""
import json, base64, os, html, collections, statistics

ads = json.load(open("ads.json"))
live = [a for a in ads if a.get("live") is True]
SNAPS = ["2026-08-25", "2026-09-01", "2026-09-03"]
SNAP, NOW = SNAPS[-2], SNAPS[-1]

def b64(aid):
    p = f"thumbs_small/{aid}.jpg"
    if not os.path.exists(p): return None
    return "data:image/jpeg;base64," + base64.b64encode(open(p,"rb").read()).decode()

def esc(s): return html.escape(s or "")

def card(a, show_days=True):
    img = b64(a["id"])
    days = (f'<span class="badge live">LIVE · {a["days_running"]}d</span>' if a.get("live") is True
            else f'<span class="badge dead">killed {a["died_between"][0][5:].replace("-","/")}–{a["died_between"][1][5:].replace("-","/")} · at {a["days_at_death_min"]}d</span>' if a.get("died_between")
            else '<span class="badge dead">stopped</span>')
    media = (f'<img loading="lazy" src="{img}" alt="">' if img
             else '<div class="noimg">no thumbnail</div>')
    tx = (a.get("full_transcription") or "")
    return f"""<figure class="card">
  <a href="{esc(a.get('video') or a.get('foreplay_url') or '#')}" target="_blank" rel="noopener">{media}</a>
  <figcaption>
    {days if show_days else ''}
    <b>{esc(a['vertical'])}</b>
    <span class="hook">{esc(a['hook'])}</span>
    <p class="op">{esc(tx[:130])}{'…' if len(tx)>130 else ''}</p>
    <p class="lnk"><a href="{esc(a.get('video') or '#')}" target="_blank" rel="noopener">video</a> ·
       <a href="{esc(a.get('foreplay_url') or '#')}" target="_blank" rel="noopener">foreplay</a></p>
  </figcaption>
</figure>"""

# ---- data blocks -------------------------------------------------------
niche = [a for a in ads if a["funnel"] in ("med","law","pros")]
w1 = [a for a in niche if a["started_date"] < "2026-08-01"]
vert = collections.defaultdict(list)
for a in w1:
    if a["vertical"] != "General / no vertical": vert[a["vertical"]].append(a)
vrows = sorted(((k, len(v), sum(1 for x in v if x.get("live") is True), sum(1 for x in v if x.get("died_between")))
                for k,v in vert.items()), key=lambda r: -(r[2]/r[1]))

top = sorted(live, key=lambda a: -a["days_running"])[:12]
niche_live = sorted([a for a in niche if a.get("live") is True],
                    key=lambda a: (a["funnel"], -a["days_running"]))
niche_dead = sorted([a for a in niche if a.get("live") is not True and a.get("full_transcription")],
                    key=lambda a: (not a.get("died_between"), (a.get("died_between") or ["0"])[0] != SNAP, -a.get("days_at_death_min", 0)))

hook_niche = collections.defaultdict(list)
for a in niche:
    if a["hook"] != "Unclassified": hook_niche[a["hook"]].append(a)
hrows = sorted(((k, len(v), sum(1 for x in v if x.get("live") is True))
                for k,v in hook_niche.items()), key=lambda r: -(r[2]/r[1]))

# transcripts shown in-page: every live ad + every niche ad that died
tx_ads = [a for a in ads if a.get("full_transcription") and
          (a.get("live") is True or a["funnel"] in ("med","law","pros"))]
tx_ads.sort(key=lambda a: (a.get("live") is not True, -a["days_running"]))

def bar(pct, cls):
    return f'<div class="bar"><i class="{cls}" style="width:{pct}%"></i><span>{pct}%</span></div>'

vert_rows = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{n}</td><td class="n">{l}</td>'
    f'<td>{bar(round(100*l/n), "good" if l/n>=.5 else "mid" if l/n>=.3 else "bad")}</td>'
    f'<td class="n" style="color:var(--dead)">{"−"+str(dd) if dd else ""}</td></tr>'
    for k,n,l,dd in vrows)

hook_rows = "".join(
    f'<tr><td>{esc(k)}</td><td class="n">{n}</td><td class="n">{l}</td>'
    f'<td>{bar(round(100*l/n), "good" if l/n>=.45 else "mid" if l/n>=.3 else "bad")}</td></tr>'
    for k,n,l in hrows)

top_rows = "".join(
    f'<tr><td class="n big">{a["days_running"]}</td><td><code>{esc(a["funnel"])}</code></td>'
    f'<td>{esc(a.get("headline") or "—")}</td>'
    f'<td><a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a></td></tr>'
    for a in top)

tx_blocks = "".join(
    f'<article class="tx" data-v="{esc(a["vertical"])}" data-f="{esc(a["funnel"])}" '
    f'data-s="{"live" if a.get("live") is True else "dead"}">'
    f'<header><span class="badge {"live" if a.get("live") is True else "dead"}">'
    f'{"LIVE · %dd" % a["days_running"] if a.get("live") is True else "stopped"}</span>'
    f'<b>{esc(a["vertical"])}</b><span class="hook">{esc(a["hook"])}</span>'
    f'<code>{esc(a["funnel"])}</code>'
    f'<a href="{esc(a.get("video") or "#")}" target="_blank" rel="noopener">video</a></header>'
    f'<p>{esc(a["full_transcription"])}</p></article>'
    for a in tx_ads)

died_all = [a for a in ads if a.get("died_between")]
died = [a for a in died_all if a["died_between"] == [SNAP, NOW]]
new  = [a for a in ads if a.get("new_since")]
ntx  = sum(1 for a in ads if a.get("full_transcription"))

def cnt(rows): return len(rows), sum(1 for x in rows if x.get("live") is True)
def pct(n,l): return round(100*l/n) if n else 0
def cls(p, hi=45, lo=30): return "good" if p>=hi else "mid" if p>=lo else "bad"

# funnel cards, generated
FUN = [("cpy","Main funnel","viralcoach.com/cpy"),("med","Medical","med.viralcoach.com"),
       ("law","Legal","law.viralcoach.com"),("pros","Trades","pros.viralcoach.com")]
funnel_cards = ""
for key,label,url in FUN:
    rows=[a for a in ads if a["funnel"]==key]; n,l=cnt(rows); dd=sum(1 for a in rows if a.get("died_between"))
    c = "hi" if pct(n,l)>=25 else "zero" if pct(n,l)<10 else ""
    funnel_cards += (f'<div class="wave"><h4>{label}</h4><code>{url}</code>'
        f'<div class="row"><span>Ads</span><b>{n:,}</b></div>'
        f'<div class="row"><span>Still live</span><b class="{c}">{l}</b></div>'
        f'<div class="row"><span>Survival</span><b class="{c}">{pct(n,l)}%</b></div>'
        f'<div class="row"><span>Killed this week</span><b>{"−"+str(dd) if dd else "0"}</b></div></div>')

# wave table, generated: niche funnels × launch wave
def wave_of(a):
    s=a.get("started_date") or ""
    return "w1" if s<"2026-08-01" else "w2" if s<"2026-08-25" else "w3"
wave_rows=""
for key,label,_ in FUN[1:]:
    rows=[a for a in ads if a["funnel"]==key]
    w1=[a for a in rows if wave_of(a)=="w1"]; w2=[a for a in rows if wave_of(a)=="w2"]; w3=[a for a in rows if wave_of(a)=="w3"]
    n1,l1=cnt(w1); n2,l2=cnt(w2); p1=pct(n1,l1)
    wave_rows += (f'<tr><td><b>{label}</b></td><td class="n">{n1} ads</td>'
        f'<td><div class="bar"><i class="{cls(p1)}" style="width:{p1}%"></i><span>{p1}%</span></div></td>'
        f'<td class="n">{n2} ads → <b style="color:var(--{"live" if l2 else "dead"})">{l2} live</b></td>'
        f'<td class="n"><b style="color:var(--{"live" if len(w3) else "dead"})">{len(w3)} new</b></td></tr>')
w3_all=[a for a in new if (a.get("started_date") or "")>="2026-08-31"]
w3_cpy=sum(1 for a in w3_all if a["funnel"]=="cpy")

# deaths this week: by funnel and by real tenure-at-death
death_funnel = ", ".join(f"{v} {k}" for k,v in sorted(collections.Counter(a["funnel"] for a in died).items(), key=lambda kv:-kv[1]))
def _lbl(rows):
    fun = collections.Counter(a["funnel"] for a in rows).most_common(1)[0][0]
    day = collections.Counter(a.get("started_date") for a in rows).most_common(1)[0][0]
    what = {"med":"medical","law":"legal","pros":"trades","cpy":"main-funnel"}.get(fun, fun)
    wave = ("wave-1 niche" if fun in ("med","law","pros") and (day or "")<"2026-08-01" else
            "wave-2 niche" if fun in ("med","law","pros") else what)
    return f"{wave} ads launched {day[5:] if day else '?'}"
ten = collections.defaultdict(list)
for a in died: ten[a["days_at_death_min"]].append(a)
death_rows = "".join(f'<tr><td class="n big">{d}d</td><td class="n">{len(r)}</td><td>{esc(_lbl(r))}</td></tr>'
    for d,r in sorted(ten.items()))
# active-count sparkline from analytics.csv
import csv
rows=sorted(csv.DictReader(open("analytics.csv")), key=lambda r:r["date"])
ys=[int(r["active"]) for r in rows]; W,H=1080,120; PAD=14; mx=max(ys); mn=min(ys)
pts=[(PAD+i*(W-2*PAD)/(len(ys)-1), H-22-(y-mn)/(mx-mn)*(H-48)) for i,y in enumerate(ys)]
path="M"+" L".join(f"{x:.1f},{y:.1f}" for x,y in pts)
area=path+f" L{pts[-1][0]:.1f},{H-20} L{PAD},{H-20} Z"
lx,ly=pts[-1]; px,py=max(pts,key=lambda p:-p[1])
spark=(f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block;height:auto" role="img" '
  f'aria-label="Active ad count by day, {rows[0]["date"]} to {rows[-1]["date"]}">'
  f'<line x1="{PAD}" y1="{H-20}" x2="{W-PAD}" y2="{H-20}" stroke="var(--rule)" stroke-width="1"/>'
  f'<path d="{area}" fill="var(--dead-bg)" opacity=".6"/><path d="{path}" fill="none" stroke="var(--dead)" stroke-width="2.2" stroke-linejoin="round"/>'
  f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="var(--ink-3)"/>'
  f'<text x="{px:.0f}" y="{py-9:.0f}" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="12" fill="var(--ink-2)">{mx}</text>'
  f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="var(--dead)"/>'
  f'<text x="{lx-9:.0f}" y="{ly+4:.0f}" text-anchor="end" font-family="IBM Plex Mono,monospace" font-size="13" font-weight="500" fill="var(--ink)">{ys[-1]}</text>'
  f'<text x="{PAD}" y="{H-5}" font-family="IBM Plex Mono,monospace" font-size="11" fill="var(--ink-3)">{rows[0]["date"]}</text>'
  f'<text x="{W-PAD}" y="{H-5}" text-anchor="end" font-family="IBM Plex Mono,monospace" font-size="11" fill="var(--ink-3)">{rows[-1]["date"]}</text></svg>')
peak=max(rows,key=lambda r:int(r["active"]))

med_n,med_l=cnt([a for a in ads if a["funnel"]=="med"]); law_n,law_l=cnt([a for a in ads if a["funnel"]=="law"]); pro_n,pro_l=cnt([a for a in ads if a["funnel"]=="pros"])
n_w2,l_w2=cnt([a for a in niche if wave_of(a)=="w2"])
CSS = open("report.css").read()
JS  = open("report.js").read()
BODY = open("report_body.html").read()

out = (f"<title>Viral Coach Teardown</title>\n<style>{CSS}</style>\n"
       + BODY
         .replace("{{VERT_ROWS}}", vert_rows)
         .replace("{{HOOK_ROWS}}", hook_rows)
         .replace("{{TOP_ROWS}}", top_rows)
         .replace("{{TX_BLOCKS}}", tx_blocks)
         .replace("{{TX_COUNT}}", str(len(tx_ads)))
         .replace("{{FUNNEL_CARDS}}", funnel_cards).replace("{{WAVE_ROWS}}", wave_rows)
         .replace("{{DEATH_ROWS}}", death_rows).replace("{{DEATH_FUNNEL}}", death_funnel)
         .replace("{{SPARK}}", spark).replace("{{N_ADS}}", f"{len(ads):,}").replace("{{N_LIVE}}", str(len(live)))
         .replace("{{N_TX}}", f"{ntx:,}").replace("{{N_DIED}}", str(len(died))).replace("{{N_DIED_ALL}}", str(len(died_all))).replace("{{N_NEW}}", str(len(new)))
         .replace("{{W3_N}}", str(len(w3_all))).replace("{{W3_CPY}}", str(w3_cpy))
         .replace("{{MED_P}}", str(pct(med_n,med_l))).replace("{{LAW_P}}", str(pct(law_n,law_l))).replace("{{PRO_P}}", str(pct(pro_n,pro_l)))
         .replace("{{MED_L}}", str(med_l)).replace("{{LAW_L}}", str(law_l)).replace("{{PRO_L}}", str(pro_l))
         .replace("{{W2_N}}", str(n_w2)).replace("{{W2_L}}", str(l_w2))
         .replace("{{N_NEW_ALL}}", str(sum(1 for a in ads if a.get("new_since")))).replace("{{PEAK}}", peak["active"]).replace("{{PEAK_D}}", peak["date"][5:]).replace("{{NOW_ACT}}", rows[-1]["active"])
         .replace("{{WINNERS}}", "".join(card(a) for a in top))
         .replace("{{NICHE_LIVE}}", "".join(card(a) for a in niche_live))
         .replace("{{NICHE_DEAD}}", "".join(card(a) for a in niche_dead[:60]))
       + f"\n<script>{JS}</script>")
open("report.html","w").write(out)
print(f"report.html  {os.path.getsize('report.html')/1e6:.2f} MB · {len(tx_ads)} transcripts inline")
