#!/usr/bin/env python3
"""Render the 10 Oct Viral Coach refresh as one self-contained HTML page, and the brief.

Every figure on the page and in brief.md is computed here, from ads.json, the raw
pull pages, analytics.csv and the published 17 Sep page (snapshots/report_2026-09-17.html,
parsed for its own tables). report_body.html and brief_template.md hold prose with
{{PLACEHOLDERS}}; nothing numeric is typed into either.
"""
import json, os, re, html, glob, csv, base64, collections, datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
S17, S29, S10 = "2026-09-17", "2026-09-29", "2026-10-10"
ads = json.load(open("ads.json"))
by_id = {a["id"]: a for a in ads}
live = [a for a in ads if a["live"]]
esc = lambda s: html.escape(s or "")
V, B = {}, {}


def norm(s, n=80):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()[:n]


def pct(n, d):
    return round(100 * n / d) if d else 0


def bar(n, d, cls=""):
    w = min(100, 100 * n / d) if d else 0
    return (f'<div class="barrow"><div class="track"><i class="{cls}" style="width:{w:.1f}%"></i></div>'
            f'<var>{n}</var></div>')


def fmt_date(d):
    return datetime.date.fromisoformat(d).strftime("%-d %b")


# ---------------------------------------------------------------- 17 Sep page
P17 = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "", open("snapshots/report_2026-09-17.html", encoding="utf-8").read())


def table_after(header_cell):
    """Rows (lists of cell text) of the first table whose header contains header_cell."""
    for t in re.findall(r"<table>(.*?)</table>", P17, re.S):
        if header_cell in t:
            rows = []
            for tr in re.findall(r"<tr>(.*?)</tr>", t.split("</thead>")[-1], re.S):
                rows.append([html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)])
            return rows
    raise SystemExit(f"17 Sep table with '{header_cell}' not found")


pulls17 = table_after("Order requested")
union17 = int(next(r for r in pulls17 if r[0] == "∪")[2])
bands17 = {r[0]: int(r[1]) for r in table_after("What this band is")}
months17 = {r[0]: int(r[1]) for r in table_after("Month")}
proven17 = table_after("In pulls")
heads17 = {r[0]: int(r[1]) for r in table_after("Newest")}
V["N_LIVE_17"], V["PULLS_17"] = union17, sum(1 for r in pulls17 if r[0] != "∪")
V["PROVEN_N"] = len(proven17)
V["H155_17"] = heads17.get("Our avg clients get 15.5m views", 0)
V["H155_17_PCT"] = pct(V["H155_17"], union17)
V["BAND_365_17"] = bands17.get("365d+", 0)


# ---------------------------------------------------------------- pulls
def load(p):
    return json.load(open(p)).get("data") or []


def pull_table(date):
    seen, rows = set(), []
    order = {"longest": "longest_running", "newest": "newest", "oldest": "oldest", "relevant": "most_relevant"}
    for p in sorted(glob.glob(f"pages_{date}/live_*.json"), key=lambda p: ["longest", "newest", "oldest", "relevant"].index(re.sub(r"\d", "", os.path.basename(p)[5:-5]))):
        ids = {a["id"] for a in load(p) if a.get("live")}
        new = len(ids - seen); seen |= ids
        rows.append((re.sub(r"\d", "", os.path.basename(p)[5:-5]), len(ids), new))
    return rows, seen


pulls29, u29 = pull_table(S29)
pulls10, u10 = pull_table(S10)
V["N_LIVE_29"], V["PULLS_29"] = len(u29), len(pulls29)
V["N_LIVE"], V["PULLS_10"] = len(u10), len(pulls10)
assert V["N_LIVE"] == len(live), (V["N_LIVE"], len(live))
V["N_ROWS"] = len(ads)
V["N_TX"] = sum(1 for a in ads if a.get("full_transcription"))
hist = load(glob.glob(f"pages_{S10}/history_*.json")[0])
V["HIST_N"] = len(hist)
V["PROBE_N"] = len(glob.glob(f"pages_{S10}/probe_*.json"))
V["PROBE_ADS"] = sum(len(load(p)) for p in glob.glob(f"pages_{S10}/probe_*.json"))

pull_rows = ""
for date, rows, uni in ((S17, [(r[1], int(r[2]), int(r[4].lstrip("+") or 0)) for r in pulls17 if r[0] != "∪"], union17),
                        (S29, pulls29, len(u29)), (S10, pulls10, len(u10))):
    for i, (order, n, new) in enumerate(rows):
        pull_rows += (f'<tr><td class="big">{fmt_date(date) if i == 0 else ""}</td><td><code>{esc(order)}</code></td>'
                      f'<td class="n">{n}</td><td class="n">+{new}</td><td class="n">{"<b class=is>%d</b>" % uni if i == len(rows) - 1 else ""}</td></tr>')
B["PULL_ROWS"] = pull_rows

# ---------------------------------------------------------------- tenure and month
def band(d):
    return "365d+" if d >= 365 else "180–364d" if d >= 180 else "90–179d" if d >= 90 else "30–89d" if d >= 30 else "under 30d"


bands10 = collections.Counter(band(a["days_running"] or 0) for a in live)
B["BAND_ROWS"] = "".join(
    f'<tr><td class="big">{k}</td><td class="n"><span class="was">{bands17.get(k, 0)}</span></td>'
    f'<td class="n"><b class="is">{bands10.get(k, 0)}</b></td><td>{bar(bands10.get(k, 0), V["N_LIVE"], "good" if k != "under 30d" else "warn")}</td></tr>'
    for k in ("365d+", "180–364d", "90–179d", "30–89d", "under 30d"))
V["U30_10"], V["U30_17"] = bands10["under 30d"], bands17.get("under 30d", 0)
V["P180_10"] = bands10["365d+"] + bands10["180–364d"]
V["P180_17"] = bands17.get("365d+", 0) + bands17.get("180–364d", 0)

live29 = {}
for p in glob.glob(f"pages_{S29}/live_*.json"):
    for a in load(p):
        live29[a["id"]] = a
m29 = collections.Counter(datetime.datetime.utcfromtimestamp(a["started_running"] / 1000).strftime("%Y-%m") for a in live29.values())
m10 = collections.Counter((a["started_date"] or "")[:7] for a in live)


def m17(m):
    if m in months17:
        return months17[m]
    for k, v in months17.items():          # the 17 Sep page folds empty months into a range row
        if "–" in k and k[:4] == m[:4] and k[5:7] <= m[5:7] <= k.split("–")[1].strip():
            return v
    return 0


months = sorted(set(m29) | set(m10) | {k for k in months17 if "–" not in k})
B["MONTH_ROWS"] = "".join(
    f'<tr><td class="big">{m}</td><td class="n">{m17(m)}</td><td class="n">{m29.get(m, 0)}</td>'
    f'<td class="n"><b>{m10.get(m, 0)}</b></td></tr>' for m in months)
V["SEP_17"], V["SEP_10"] = m17("2026-09"), m10.get("2026-09", 0)
V["OCT_10"] = m10.get("2026-10", 0)
V["JUN_17"], V["JUN_29"], V["JUN_10"] = m17("2026-06"), m29.get("2026-06", 0), m10.get("2026-06", 0)

# ---------------------------------------------------------------- the 17 Sep set, by tenure then
in17 = [a for a in ads if a.get("in_0917")]
V["BASE_N"] = len(in17)


def b17(a):
    return band(a.get("days_0917") or 0)


fate_rows = ""
FATE = {}
for k in ("365d+", "180–364d", "90–179d", "30–89d", "under 30d"):
    g = [a for a in in17 if b17(a) == k]
    s29 = sum(S29 in a["seen_live"] for a in g); l10 = sum(a["live"] for a in g)
    fl = sum(a["status_1010"] == "flagged_inactive" for a in g)
    FATE[k] = (len(g), s29, l10, fl)
    fate_rows += (f'<tr><td class="big">{k}</td><td class="n">{len(g)}</td><td class="n">{s29}</td>'
                  f'<td class="n"><b>{l10}</b></td><td>{bar(l10, len(g), "good" if pct(l10, len(g)) >= 50 else "warn")}</td>'
                  f'<td class="n">{pct(l10, len(g))}%</td></tr>')
B["FATE_ROWS"] = fate_rows
young = [a for a in in17 if b17(a) == "under 30d"]
mid = [a for a in in17 if b17(a) in ("30–89d", "90–179d")]
V["YOUNG_N"], V["YOUNG_29"], V["YOUNG_10"] = FATE["under 30d"][0], FATE["under 30d"][1], FATE["under 30d"][2]
V["YOUNG_PCT_29"], V["YOUNG_PCT_10"] = pct(V["YOUNG_29"], V["YOUNG_N"]), pct(V["YOUNG_10"], V["YOUNG_N"])
V["MID_N"] = len(mid); V["MID_10"] = sum(a["live"] for a in mid); V["MID_PCT"] = pct(V["MID_10"], V["MID_N"])
V["MID_29"] = sum(S29 in a["seen_live"] for a in mid)
V["YOUNG_GONE"] = V["YOUNG_N"] - V["YOUNG_10"]

# ---------------------------------------------------------------- the proven fifteen
FMT = {"video": "VIDEO", "dco": "DCO", "image": "IMAGE", "carousel": "CAROUSEL"}
live_meta = [int(a["ad_id"]) for a in live if str(a.get("ad_id") or "").isdigit()]


def dup_of_live(a):
    m = str(a.get("ad_id") or "")
    return m.isdigit() and any(abs(int(m) - x) <= 8 for x in live_meta) and not a["live"]


used, proven = set(), []
for r in proven17:
    days, fmt, hl, fun = int(r[0]), FMT.get(r[1].lower(), r[1].upper()), r[2], r[3]
    start = (datetime.date.fromisoformat(S17) - datetime.timedelta(days=days)).isoformat()
    hl0 = "" if "no fixed headline" in hl else hl

    def ok(a):
        if a["id"] in used or (a.get("display_format") or "").upper() != fmt:
            return False
        sd = a.get("started_date") or ""
        if not sd or abs((datetime.date.fromisoformat(sd) - datetime.date.fromisoformat(start)).days) > 1:
            return False
        if norm(a.get("headline")) != norm(hl0):
            return False
        return a.get("funnel") in (None, "(none)", fun)
    c = [a for a in ads if ok(a)]
    pick = ([a for a in c if a.get("in_0917") and (a.get("days_0917") or 0) == days] or [a for a in c if a.get("in_0917")]
            or [a for a in c if a["live"]] or (c if len(c) == 1 else []))
    if pick:
        a = pick[0]; used.add(a["id"])
        st = ("live" if a["live"] else "dead" if a["status_1010"] == "flagged_inactive" else "grey")
        say = (f'live · {a["days_running"]}d' if a["live"] else "flagged inactive" if st == "dead" else "not returned")
        how = ("same Foreplay id" if a.get("in_0917") and not a.get("was_id_0917") else
               f'Foreplay re-keyed it from <code>{a["was_id_0917"][:8]}…</code>; matched on Meta id or start date + headline + script' if a.get("was_id_0917") else
               "start date, format and funnel match; the 17 Sep page carried no id for DCO ads")
        if st == "grey":
            how += f"; absent from all {V['PULLS_29'] + V['PULLS_10']} live pulls on {fmt_date(S29)} and {fmt_date(S10)}, including every longest-running pull"
        if st == "dead":
            how += "; a probe of its launch window returns it with live=false, and no live pull since 17 Sep has returned it"
        proven.append((r, a, st, say, how))
    else:
        dups = [a for a in ads if (a.get("display_format") or "").upper() == fmt and (a.get("started_date") or "") == start and dup_of_live(a)]
        how = (f"{len(c)} candidate records share its start date and format, all flagged inactive; "
               + (f"one (<code>{dups[0]['id'][:8]}…</code>) is a duplicate Foreplay record of the live DCO above (Meta id within ±8), "
                  "so the 17 Sep union most likely counted that one ad twice" if dups else "none can be singled out"))
        proven.append((r, None, "grey", "unresolved", how))

B["PROVEN_ROWS"] = "".join(
    f'<tr><td class="big">{r[0]}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td><td><code>{esc(r[3])}</code></td>'
    f'<td><span class="st {st}">{say}</span></td><td class="ev">{how}</td></tr>' for r, a, st, say, how in proven)
V["PROVEN_LIVE"] = sum(st == "live" for _, _, st, _, _ in proven)
V["PROVEN_OFF"] = sum(st in ("dead",) or (st == "grey" and say == "not returned") for _, _, st, say, _ in proven)
V["PROVEN_FLAGGED"] = sum(st == "dead" for _, _, st, _, _ in proven)
V["PROVEN_UNRES"] = sum(say == "unresolved" for _, _, _, say, _ in proven)
posters = [(r, a, st) for r, a, st, _, _ in proven if r[1].lower() == "image"]
V["POSTERS_N"] = len(posters)
V["POSTERS_OFF"] = sum(st != "live" for _, _, st in posters)
V["POSTERS_FLAGGED"] = sum(st == "dead" for _, _, st in posters)
V["POSTER_MIN"] = min(int(r[0]) for r, _, _ in posters)
V["POSTER_MAX"] = max(int(r[0]) for r, _, _ in posters)
guar = [(r, a, st) for r, a, st, _, _ in proven if r[1].lower() in ("video", "dco")]
V["GUAR_PROVEN_N"] = len(guar)
V["GUAR_PROVEN_LIVE"] = sum(st == "live" for _, _, st in guar)
proven_ads = [a for _, a, _, _, _ in proven if a]

# ---------------------------------------------------------------- old ads the 17 Sep pulls never returned
proven_ids = {a["id"] for a in proven_ads}
returners = sorted([a for a in live if (a.get("started_date") or "9") < "2026-06-01" and not a.get("in_0917") and a["id"] not in proven_ids],
                   key=lambda a: a["started_date"])
V["RETURN_N"] = len(returners)
V["RETURN_APR"] = sum((a["started_date"] or "").startswith("2026-04") for a in returners)
V["RETURN_29_ALL"] = sum(S29 in a["seen_live"] for a in returners)
oldest = max(live, key=lambda a: a["days_running"] or 0)
V["MAX_LIVE"], V["MAX_LIVE_START"] = oldest["days_running"], fmt_date(oldest["started_date"]) + " " + oldest["started_date"][:4]
V["MAX_LIVE_17"] = V["MAX_LIVE"] - (datetime.date.fromisoformat(S10) - datetime.date.fromisoformat(S17)).days
V["MAX_17"] = max(int(r[0]) for r in proven17)
B["RETURN_ROWS"] = "".join(
    f'<tr><td class="big">{a["days_running"]}</td><td>{fmt_date(a["started_date"])} {a["started_date"][:4]}</td>'
    f'<td>{esc(a.get("display_format","").lower())}</td><td>{esc(a.get("headline") or "no fixed headline")}</td>'
    f'<td><code>{esc(a["funnel"])}</code></td><td class="n">{len(a["seen_live"])}</td></tr>' for a in returners)
pre_june_10 = [a for a in live if (a.get("started_date") or "9") < "2026-06-01"]
pre_june_29 = [a for a in live29.values() if datetime.datetime.utcfromtimestamp(a["started_running"] / 1000).strftime("%Y-%m-%d") < "2026-06-01"]
V["PREJUNE_10"], V["PREJUNE_29"] = len(pre_june_10), len(pre_june_29)


def per_pull_prejune(date):
    out = []
    for p in sorted(glob.glob(f"pages_{date}/live_longest*.json") + glob.glob(f"pages_{date}/live_oldest*.json")):
        out.append(sum(1 for a in load(p) if a.get("live") and datetime.datetime.utcfromtimestamp(a["started_running"] / 1000).strftime("%Y-%m-%d") < "2026-06-01"))
    return out


pj = per_pull_prejune(S29) + per_pull_prejune(S10)
V["PREJUNE_PULLS_SAME"] = sum(x == pj[0] for x in pj)
V["PREJUNE_PULLS_N"] = len(pj)

# ---------------------------------------------------------------- launches since 17 Sep
new = [a for a in ads if a.get("new_since")]
V["NEW_N"] = len(new)
V["NEW_LIVE"] = sum(a["live"] for a in new)
V["NEW_FLAG"] = sum(a["status_1010"] == "flagged_inactive" for a in new)
V["NEW_FIRST"] = fmt_date(min(a["started_date"] for a in new))
by_day = collections.defaultdict(list)
for a in new:
    by_day[a["started_date"]].append(a)
peak_day = max(by_day, key=lambda d: len(by_day[d]))
V["PEAK_DAY"], V["PEAK_DAY_N"] = fmt_date(peak_day), len(by_day[peak_day])
V["PEAK_DAY_LIVE"] = sum(a["live"] for a in by_day[peak_day])
gap_days = [d for d in by_day if S17 < d < "2026-09-29"]
V["GAP_LAUNCHES"] = sum(len(by_day[d]) for d in gap_days)
mx = max(len(v) for v in by_day.values())
B["CAL_ROWS"] = "".join(
    f'<tr><td class="big">{fmt_date(d)}</td><td class="n">{len(g)}</td><td class="n"><b class="is">{sum(a["live"] for a in g)}</b></td>'
    f'<td class="n" style="color:var(--dead)">{sum(a["status_1010"]=="flagged_inactive" for a in g) or ""}</td>'
    f'<td>{bar(len(g), mx, "good")}</td></tr>' for d, g in sorted(by_day.items()))
early = [a for d, g in by_day.items() if "2026-09-29" <= d <= "2026-09-30" for a in g]
V["EARLY_N"], V["EARLY_FLAG"] = len(early), sum(a["status_1010"] == "flagged_inactive" for a in early)
pk = by_day[peak_day]
V["PEAK_FLAG"] = sum(a["status_1010"] == "flagged_inactive" for a in pk)

# ---------------------------------------------------------------- script reuse
old_scripts = {}
for a in ads:
    if (a.get("started_date") or "9") <= S17 and a.get("full_transcription"):
        old_scripts.setdefault(norm(a["full_transcription"]), []).append(a)
young_scripts = {norm(a["full_transcription"]) for a in young if a.get("full_transcription")}
ntx = [a for a in new if a.get("full_transcription")]
V["NEW_TX"] = len(ntx)
V["NEW_TX_DISTINCT"] = len({norm(a["full_transcription"]) for a in ntx})
reused = [a for a in ntx if norm(a["full_transcription"]) in old_scripts]
V["REUSE_N"], V["REUSE_PCT"] = len(reused), pct(len(reused), len(ntx))
V["REUSE_YOUNG"] = sum(norm(a["full_transcription"]) in young_scripts for a in reused)
V["REUSE_DISTINCT"] = len({norm(a["full_transcription"]) for a in reused})
V["FRESH_DISTINCT"] = V["NEW_TX_DISTINCT"] - V["REUSE_DISTINCT"]
young_tx = [a for a in young if a.get("full_transcription")]
new_scripts = {norm(a["full_transcription"]) for a in ntx}
young_gone_tx = [a for a in young_tx if not a["live"]]
V["YOUNG_GONE_TX"] = len(young_gone_tx)
V["YOUNG_GONE_BACK"] = sum(norm(a["full_transcription"]) in new_scripts for a in young_gone_tx)
V["YOUNG_GONE_BACK_PCT"] = pct(V["YOUNG_GONE_BACK"], V["YOUNG_GONE_TX"])

# ---------------------------------------------------------------- headlines and funnels
H155 = "Our avg clients get 15.5m views"
heads10 = collections.Counter((a.get("headline") or "").strip() for a in live)
V["H155_LIVE"], V["H155_PCT"] = heads10[H155], pct(heads10[H155], len(live))
is_guar = lambda h: "don't pay" in h.lower() or "don’t pay" in h.lower()
V["GUAR_LIVE"] = sum(v for k, v in heads10.items() if is_guar(k))
V["GUAR_17"] = sum(v for k, v in heads17.items() if is_guar(k))
V["H155_NEW"] = sum(1 for a in new if a["live"] and (a.get("headline") or "") == H155)
V["H155_NEW_PCT"] = pct(V["H155_NEW"], V["NEW_LIVE"])
hl_rows = ""
for k, v in heads10.most_common():
    oldest_d = max((a["days_running"] or 0) for a in live if (a.get("headline") or "").strip() == k)
    cell = esc(k) or '<span class="badge gap">no fixed headline</span>'
    hl_rows += (f'<tr><td>{cell}</td><td class="n"><b>{v}</b></td>'
                f'<td class="n">{pct(v, len(live))}%</td><td class="n">{oldest_d}d</td></tr>')
B["HEAD_ROWS"] = hl_rows
funs10 = collections.Counter(a["funnel"] for a in live)
V["CPY_LIVE"], V["CPY_PCT"] = funs10["cpy"], pct(funs10["cpy"], len(live))
V["MED_LIVE"], V["LAW_LIVE"], V["PROS_LIVE"] = funs10["med"], funs10["law"], funs10["pros"]
V["MED_NEW"] = sum(1 for a in new if a["live"] and a["funnel"] == "med")
V["LAW_NEW"] = sum(1 for a in new if a["live"] and a["funnel"] == "law")
V["PROS_NEW"] = sum(1 for a in new if a["live"] and a["funnel"] == "pros")
fmt10 = collections.Counter((a.get("display_format") or "").upper() for a in live)
V["VIDEO_PCT"] = pct(fmt10["VIDEO"], len(live)); V["IMAGE_LIVE"] = fmt10["IMAGE"]
durs = sorted(a["video_duration"] for a in live if a.get("video_duration"))
V["VDUR_MED"] = round(durs[len(durs) // 2])
fun_rows = ""
for k, v in funs10.most_common():
    nn = sum(1 for a in new if a["live"] and a["funnel"] == k)
    fun_rows += (f'<tr><td><code>{esc(k)}</code></td><td class="n"><b>{v}</b></td><td class="n">{nn or ""}</td>'
                 f'<td class="n">{max((a["days_running"] or 0) for a in live if a["funnel"] == k)}d</td></tr>')
B["FUNNEL_ROWS"] = fun_rows

# ---------------------------------------------------------------- analytics sparkline
rows = sorted(csv.DictReader(open("analytics.csv")), key=lambda r: r["date"])
rows = [r for r in rows if int(r["active"]) > 0]
ys = [int(r["active"]) for r in rows]
W, H, PAD = 1080, 130, 16
lo_y, hi_y = 0, max(ys)
xs = [PAD + i * (W - 2 * PAD) / (len(ys) - 1) for i in range(len(ys))]
yy = [H - 24 - (y - lo_y) / (hi_y - lo_y) * (H - 52) for y in ys]
path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, yy))
area = path + f" L{xs[-1]:.1f},{H-24} L{xs[0]:.1f},{H-24} Z"
marks = ""
for d in (S17, S29, S10):
    if d in [r["date"] for r in rows]:
        i = [r["date"] for r in rows].index(d)
        marks += (f'<line x1="{xs[i]:.1f}" y1="12" x2="{xs[i]:.1f}" y2="{H-24}" stroke="var(--brass)" stroke-dasharray="3 3" stroke-width="1"/>'
                  f'<text x="{xs[i]-5:.1f}" y="22" text-anchor="end" font-size="11" fill="var(--brass)">{fmt_date(d)} · {ys[i]}</text>')
B["SPARK"] = (f'<div class="spark"><svg viewBox="0 0 {W} {H}" width="100%" style="display:block;height:auto" role="img" '
              f'aria-label="Foreplay daily active-ad count, {rows[0]["date"]} to {rows[-1]["date"]}">'
              f'<line x1="{PAD}" y1="{H-24}" x2="{W-PAD}" y2="{H-24}" stroke="var(--rule)"/>'
              f'<path d="{area}" fill="var(--track)" opacity=".7"/><path d="{path}" fill="none" stroke="var(--ink-2)" stroke-width="2" stroke-linejoin="round"/>'
              f'{marks}<text x="{PAD}" y="{H-6}" font-size="11" fill="var(--ink-3)">{rows[0]["date"]}</text>'
              f'<text x="{W-PAD}" y="{H-6}" text-anchor="end" font-size="11" fill="var(--ink-3)">{rows[-1]["date"]}</text></svg></div>')
act = {r["date"]: int(r["active"]) for r in rows}
V["ACT_17"], V["ACT_29"], V["ACT_10"] = act.get(S17), act.get(S29), act.get(S10)
win = {d: v for d, v in act.items() if S17 <= d <= S10}
V["ACT_MIN"] = min(win.values()); V["ACT_MIN_D"] = fmt_date(min(win, key=win.get))
V["ACT_MAX_W"] = max(win.values())
V["ANALYTICS_FIRST"] = fmt_date(rows[0]["date"])

# ---------------------------------------------------------------- cards
def b64(aid):
    p = f"thumbs_small/{aid}.jpg"
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else None


def still_id(a):
    """Re-keyed ads carry their still under either id."""
    for i in (a["id"], a.get("was_id_0917")):
        if i and os.path.exists(f"thumbs_small/{i}.jpg"):
            return i
    return a["id"]


def status_badge(a):
    if a["live"]:
        return f'<span class="badge live">live · {a["days_running"]}d</span>'
    if a["status_1010"] == "flagged_inactive":
        return '<span class="badge dead">flagged inactive</span>'
    return '<span class="badge grey">not returned since ' + (fmt_date(max(a["seen_live"])) if a["seen_live"] else "?") + "</span>"


def card(a, note=""):
    img = b64(still_id(a))
    link = a.get("foreplay_url") or f"https://app.foreplay.co/discovery?ad={a['id']}"
    tx = a.get("full_transcription") or ""
    then = f' · was {a["days_0917"]}d on 17 Sep' if a.get("days_0917") else ""
    media = f'<img loading="lazy" src="{img}" alt="Still from the ad">' if img else '<div class="noimg">no still</div>'
    return (f'<figure class="card{"" if a["live"] else " off"}"><a href="{esc(link)}" target="_blank" rel="noopener">{media}</a>'
            f'<figcaption>{status_badge(a)}<b>{esc(a.get("headline") or "no fixed headline")}</b>'
            f'<span class="meta">{esc((a.get("display_format") or "").lower())} · {esc(a.get("funnel") or "?")} · started {fmt_date(a["started_date"]) if a.get("started_date") else "?"}{then}</span>'
            + (f'<p class="op">{esc(note)}</p>' if note else (f'<p class="op">{esc(tx[:120])}{"…" if len(tx) > 120 else ""}</p>' if tx else ""))
            + f'<p class="lnk"><a href="{esc(link)}" target="_blank" rel="noopener">foreplay</a>'
            + (f' · <a href="{esc(a["video"])}" target="_blank" rel="noopener">video</a>' if a.get("video") else "")
            + "</p></figcaption></figure>")


B["PROVEN_CARDS"] = "".join(card(a) for a in proven_ads)
control = sorted(live, key=lambda a: -(a["days_running"] or 0))[:12]
B["CONTROL_ROWS"] = "".join(
    f'<tr><td class="big">{a["days_running"]}</td><td>{fmt_date(a["started_date"])} {a["started_date"][:4]}</td>'
    f'<td>{esc((a.get("display_format") or "").lower())}</td><td>{esc(a.get("headline") or "no fixed headline")}</td>'
    f'<td><code>{esc(a["funnel"])}</code></td></tr>' for a in control)
V["CONTROL_MIN"] = control[-1]["days_running"]
young_live = sorted([a for a in young if a["live"]], key=lambda a: a["started_date"])
B["YOUNG_LIVE_CARDS"] = "".join(card(a) for a in young_live)
young_gone = sorted([a for a in young if not a["live"] and S29 in a["seen_live"]], key=lambda a: a["started_date"])
B["YOUNG_GONE_CARDS"] = "".join(card(a) for a in young_gone[:24])
V["YOUNG_GONE_SHOWN"] = min(24, len(young_gone))
V["YOUNG_GONE_29"] = len(young_gone)
fresh = [a for a in ntx if a["live"] and norm(a["full_transcription"]) not in old_scripts]
seen_fresh, fresh_cards = set(), []
for a in sorted(fresh, key=lambda a: a["started_date"]):
    k = norm(a["full_transcription"])
    if k not in seen_fresh:
        seen_fresh.add(k); fresh_cards.append(a)
B["FRESH_CARDS"] = "".join(card(a) for a in fresh_cards[:24])
V["FRESH_SHOWN"] = min(24, len(fresh_cards))
V["FRESH_LIVE_DISTINCT"] = len(fresh_cards)

# ---------------------------------------------------------------- transcripts
def cohort(a):
    if a.get("new_since"):
        return "launched since 17 Sep"
    if a.get("in_0917"):
        return "17 Sep · " + b17(a)
    return "older, first seen after 17 Sep"


def sval(a):
    return "live" if a["live"] else "flagged" if a["status_1010"] == "flagged_inactive" else "gone"


tx_ads = [a for a in ads if a.get("full_transcription") and (a["live"] or a.get("in_0917") or a.get("new_since"))]
tx_ads.sort(key=lambda a: (not a["live"], -(a["days_running"] or 0), a.get("started_date") or ""))
B["TX_BLOCKS"] = "".join(
    f'<article class="tx" data-s="{sval(a)}" data-c="{esc(cohort(a))}"><header>{status_badge(a)}'
    f'<b>{esc(a.get("headline") or "no fixed headline")}</b><code>{esc(a.get("funnel") or "?")}</code>'
    f'<span class="meta">started {a["started_date"] or "?"}</span>'
    f'<a href="{esc(a.get("foreplay_url") or "#")}" target="_blank" rel="noopener">foreplay</a></header>'
    f'<p>{esc(a["full_transcription"])}</p></article>' for a in tx_ads)
V["TX_INLINE"] = len(tx_ads)
V["TX_LIVE"] = sum(a["live"] for a in tx_ads)
