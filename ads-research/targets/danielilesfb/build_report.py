#!/usr/bin/env python3
"""Render the Viral Coach teardown as one self-contained HTML page."""
import json, base64, os, html, collections, statistics

ads = json.load(open("ads.json"))
live = [a for a in ads if a.get("live") is True]

def b64(aid):
    p = f"thumbs_small/{aid}.jpg"
    if not os.path.exists(p): return None
    return "data:image/jpeg;base64," + base64.b64encode(open(p,"rb").read()).decode()

def esc(s): return html.escape(s or "")

def card(a, show_days=True):
    img = b64(a["id"])
    days = (f'<span class="badge live">LIVE · {a["days_running"]}d</span>'
            if a.get("live") is True else '<span class="badge dead">stopped</span>')
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
vrows = sorted(((k, len(v), sum(1 for x in v if x.get("live") is True))
                for k,v in vert.items()), key=lambda r: -(r[2]/r[1]))

top = sorted(live, key=lambda a: -a["days_running"])[:12]
niche_live = sorted([a for a in niche if a.get("live") is True],
                    key=lambda a: (a["funnel"], -a["days_running"]))
niche_dead = [a for a in niche if a.get("live") is not True and a.get("full_transcription")]

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
    f'<td>{bar(round(100*l/n), "good" if l/n>=.5 else "bad")}</td></tr>'
    for k,n,l in vrows)

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

med_live = sum(1 for a in niche if a["funnel"]=="med" and a.get("live") is True)
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
         .replace("{{WINNERS}}", "".join(card(a) for a in top))
         .replace("{{NICHE_LIVE}}", "".join(card(a) for a in niche_live))
         .replace("{{NICHE_DEAD}}", "".join(card(a) for a in niche_dead[:60]))
       + f"\n<script>{JS}</script>")
open("report.html","w").write(out)
print(f"report.html  {os.path.getsize('report.html')/1e6:.2f} MB · {len(tx_ads)} transcripts inline")
