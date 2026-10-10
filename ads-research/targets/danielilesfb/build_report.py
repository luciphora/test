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


def is_guar(h):
    return "don't pay" in h.lower() or "don’t pay" in h.lower()


def pct(n, d):
    return round(100 * n / d) if d else 0


def bar(n, d, cls=""):
    w = min(100, 100 * n / d) if d else 0
    return (f'<div class="barrow"><div class="track"><i class="{cls}" style="width:{w:.1f}%"></i></div>'
            f'<var>{n}</var></div>')


def day_of(a):
    return datetime.datetime.utcfromtimestamp(a["started_running"] / 1000).strftime("%Y-%m-%d")


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
    """One row per pull file; a file whose id list is identical to an earlier one is a repeat, not a new pull."""
    seen, rows, lists = set(), [], {}
    for p in sorted(glob.glob(f"pages_{date}/live_*.json"), key=lambda p: (["longest", "newest", "oldest", "relevant"].index(re.sub(r"\d", "", os.path.basename(p)[5:-5])), p)):
        order = re.sub(r"\d", "", os.path.basename(p)[5:-5])
        idl = [a["id"] for a in load(p) if a.get("live")]
        same = next((k for k, v in lists.items() if v == idl), None)
        lists[os.path.basename(p)] = idl
        new = len(set(idl) - seen); seen |= set(idl)
        rows.append((order + (f" (identical to {re.sub(r'live_|.json', '', same)})" if same else ""), len(idl), new, not same))
    return rows, seen


pulls29, u29 = pull_table(S29)
pulls10, u10 = pull_table(S10)
V["N_LIVE_29"], V["PULLS_29"] = len(u29), sum(r[3] for r in pulls29)
V["N_LIVE"], V["PULLS_10"] = len(u10), sum(r[3] for r in pulls10)
V["FILES_29"], V["FILES_10"] = len(pulls29), len(pulls10)
assert V["N_LIVE"] == len(live), (V["N_LIVE"], len(live))
V["N_ROWS"] = len(ads)
V["N_TX"] = sum(1 for a in ads if a.get("full_transcription"))
hist = load(glob.glob(f"pages_{S10}/history_*.json")[0])
V["HIST_N"] = len(hist)
V["PROBE_N"] = len(glob.glob(f"pages_{S10}/probe_*.json"))
V["PROBE_ADS"] = sum(len(load(p)) for p in glob.glob(f"pages_{S10}/probe_*.json"))

pull_rows = ""
for date, rows, uni in ((S17, [(r[1], int(r[2]), int(r[4].lstrip("+") or 0), True) for r in pulls17 if r[0] != "∪"], union17),
                        (S29, pulls29, len(u29)), (S10, pulls10, len(u10))):
    for i, (order, n, new, _) in enumerate(rows):
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
sd29 = [day_of(a) for a in live29.values()]
sd10 = [a["started_date"] or "" for a in live]
mrows = ""
for m in months:
    if m == "2026-09":   # the 17 Sep flood and the 29-30 Sep relaunch share a month; keep them apart
        for lab, lo, hi, c17 in (("2026-09 (1–17)", "2026-09-01", S17, m17(m)), ("2026-09 (18–30)", "2026-09-18", "2026-09-30", 0)):
            mrows += (f'<tr><td class="big">{lab}</td><td class="n">{c17}</td><td class="n">{sum(lo <= d <= hi for d in sd29)}</td>'
                      f'<td class="n"><b>{sum(lo <= d <= hi for d in sd10)}</b></td></tr>')
            V["SEP1_10" if lo == "2026-09-01" else "SEP2_10"] = sum(lo <= d <= hi for d in sd10)
        continue
    mrows += (f'<tr><td class="big">{m}</td><td class="n">{m17(m)}</td><td class="n">{m29.get(m, 0)}</td>'
              f'<td class="n"><b>{m10.get(m, 0)}</b></td></tr>')
B["MONTH_ROWS"] = mrows
V["SEP_17"], V["SEP_10"] = m17("2026-09"), m10.get("2026-09", 0)
V["OCT_10"] = m10.get("2026-10", 0)
V["JUN_17"], V["JUN_29"], V["JUN_10"] = m17("2026-06"), m29.get("2026-06", 0), m10.get("2026-06", 0)

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
        how = ("17 Sep id only; no record under any id in any later pull or probe" if a.get("baseline_only") else
               "same Foreplay id" if a.get("in_0917") and not a.get("was_id_0917") else
               f're-keyed from <code>{a["was_id_0917"][:8]}…</code>, matched on {a["rekey_match"]}' if a.get("was_id_0917") else
               "start date, format and funnel only (no id on the 17 Sep page)")
        if st in ("grey", "dead"):
            how += "; not in the age-sorted head"
        if st == "dead" and a.get("was_id_0917"):
            how += "; its surviving record says inactive but looks stale"
        elif st == "dead":
            how += "; probe returns it inactive"
        proven.append((r, a, st, say, how))
    else:
        dups = [a for a in ads if (a.get("display_format") or "").upper() == fmt and (a.get("started_date") or "") == start and dup_of_live(a)]
        how = (f"{len(c)} inactive records share its start date; "
               + (f"one (<code>{dups[0]['id'][:8]}…</code>) is a stale twin of the live DCO above, so 17 Sep may have counted one ad twice"
                  if dups else "none can be singled out"))
        proven.append((r, None, "grey", "unresolved", how))

B["PROVEN_ROWS"] = "".join(
    f'<tr><td class="big">{r[0]}</td><td><span class="st {st}">{say}</span></td><td class="hl">{esc(r[2])}</td>'
    f'<td>{esc(r[1])}</td><td><code>{esc(r[3])}</code></td><td class="ev">{how}</td></tr>' for r, a, st, say, how in proven)
V["PROVEN_LIVE"] = sum(st == "live" for _, _, st, _, _ in proven)
V["PROVEN_OFF"] = sum(st in ("dead",) or (st == "grey" and say == "not returned") for _, _, st, say, _ in proven)
V["PROVEN_FLAGGED"] = sum(st == "dead" and not a.get("was_id_0917") for _, a, st, _, _ in proven)   # own-id flags only
V["PROVEN_UNRES"] = sum(say == "unresolved" for _, _, _, say, _ in proven)
V["PROVEN_MISSING"] = len(proven) - sum(st == "live" for _, _, st, _, _ in proven)
V["REKEYED_N"] = sum(1 for a in ads if a.get("was_id_0917"))
posters = [(r, a, st) for r, a, st, _, _ in proven if r[1].lower() == "image"]
V["POSTERS_N"] = len(posters)
V["POSTERS_OFF"] = sum(st != "live" for _, _, st in posters)
V["POSTERS_FLAGGED"] = sum(st == "dead" for _, _, st in posters)
V["POSTER_MIN"] = min(int(r[0]) for r, _, _ in posters)
V["POSTER_MAX"] = max(int(r[0]) for r, _, _ in posters)
yp29 = [a for a in live29.values() if (a.get("display_format") or "").upper() == "IMAGE"]
V["YOUNG_POSTERS_29"] = len(yp29)
V["YOUNG_POSTERS_10"] = sum(by_id.get(a["id"], {}).get("live", False) for a in yp29)
guar = [(r, a, st) for r, a, st, _, _ in proven if r[1].lower() in ("video", "dco")]
V["GUAR_PROVEN_N"] = len(guar)
V["GUAR_PROVEN_LIVE"] = sum(st == "live" for _, _, st in guar)
proven_ads = [a for _, a, _, _, _ in proven if a]

# ---------------------------------------------------------------- the 17 Sep set, by tenure then
for r, a, *_ in proven:
    if a and not a.get("in_0917"):
        a["_days17"] = int(r[0])      # a proven DCO: the 17 Sep page gave its tenure but no id
in17 = [a for a in ads if a.get("in_0917") or a.get("_days17")]
V["BASE_N"] = len(in17)
V["BASE_IDS"] = sum(1 for a in ads if a.get("in_0917"))
V["BASE_NOID"] = union17 - V["BASE_IDS"]


def b17(a):
    return band(a.get("days_0917") or a.get("_days17") or 0)


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
V["MID_MISSED_29"] = sum(a["live"] and S29 not in a["seen_live"] for a in mid)
V["YOUNG_GONE"] = V["YOUNG_N"] - V["YOUNG_10"]


# How far did the September cohort fall? The 10 Oct newest-first pull stops at 29 Sep launches, so the
# September cohort is seen only through the two age-sorted pulls, which see old ads in
# full and newer ones in part. Compare like with like inside those pulls, then give the
# equal-catch scenario as a range rather than pretending 17 is a count.
def asc_union(date):
    out = {}
    for p in glob.glob(f"pages_{date}/live_longest*.json") + glob.glob(f"pages_{date}/live_oldest*.json"):
        for a in load(p):
            if a.get("live"):
                out[a["id"]] = day_of(a)
    return out


YW = ("2026-08-19", S17)        # the 17 Sep under-30-day window
for date, tag in ((S29, "29"), (S10, "10")):
    au = asc_union(date)
    V[f"ASC_YOUNG_{tag}"] = sum(YW[0] <= d <= YW[1] for d in au.values())
    V[f"ASC_EST_{tag}"] = sum(d < YW[0] for d in au.values())
    V[f"ASC_RATIO_{tag}"] = f'{V[f"ASC_YOUNG_{tag}"] / V[f"ASC_EST_{tag}"]:.2f}'
au10 = asc_union(S10)
oct_live = [a for a in live if (a.get("started_date") or "") >= "2026-10-01"]
catch = sum(a["id"] in au10 for a in oct_live) / len(oct_live)
V["CATCH_IN"], V["CATCH_OF"] = sum(a["id"] in au10 for a in oct_live), len(oct_live)
late_sep = [a for a in live if "2026-09-29" <= (a.get("started_date") or "") <= "2026-09-30"]
V["LATESEP_IN"], V["LATESEP_OF"] = sum(a["id"] in au10 for a in late_sep), len(late_sep)
V["CATCH_PCT"] = round(100 * catch)
V["YOUNG_EST"] = round(V["YOUNG_10"] / catch)
V["YOUNG_EST_PCT"] = pct(V["YOUNG_EST"], V["YOUNG_N"])
for date, tag in ((S29, "29"), (S10, "10")):
    au = asc_union(date)
    V[f"ASC_SEPR_{tag}"] = f'{sum("2026-09-01" <= d <= S17 for d in au.values()) / sum(d < YW[0] for d in au.values()):.2f}'
V["YOUNG_AUG"] = sum(a["started_date"] < "2026-09-01" for a in young)
V["YOUNG_SEP"] = V["YOUNG_N"] - V["YOUNG_AUG"]
V["YOUNG_10_AUG"] = sum(a["live"] and a["started_date"] < "2026-09-01" for a in young)
V["YOUNG_10_SEP"] = V["YOUNG_10"] - V["YOUNG_10_AUG"]

# ---------------------------------------------------------------- old ads the 17 Sep pulls never returned
proven_ids = {a["id"] for a in proven_ads}
returners = sorted([a for a in live if (a.get("started_date") or "9") < "2026-06-01" and not a.get("in_0917") and a["id"] not in proven_ids],
                   key=lambda a: a["started_date"])
V["RETURN_N"] = len(returners)
V["RET155_N"] = sum("15.5m" in (a.get("headline") or "") for a in returners)
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
    out, lists = [], []
    for p in sorted(glob.glob(f"pages_{date}/live_longest*.json") + glob.glob(f"pages_{date}/live_oldest*.json")):
        idl = [a["id"] for a in load(p)]
        if idl in lists:
            continue                      # an identical repeat of a pull already counted
        lists.append(idl)
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
V["NEW_29"] = sum(a["started_date"] >= "2026-09-29" for a in new)
_d = lambda x, y: (datetime.date.fromisoformat(y) - datetime.date.fromisoformat(x)).days
V["GAP_DAYS"] = _d(S17, "2026-09-29")
V["BATCH_DAYS"] = _d("2026-09-29", max(a["started_date"] for a in new)) + 1
V["NEW_29_LIVE"] = sum(a["live"] for a in new if a["started_date"] >= "2026-09-29")
by_day = collections.defaultdict(list)
for a in new:
    by_day[a["started_date"]].append(a)
peak_day = max(by_day, key=lambda d: len(by_day[d]))
V["PEAK_DAY"], V["PEAK_DAY_N"] = fmt_date(peak_day), len(by_day[peak_day])
V["PEAK_DAY_LIVE"] = sum(a["live"] for a in by_day[peak_day])
newest10 = {a["id"] for a in load(f"pages_{S10}/live_newest.json")}
top2 = sorted({a["started_date"] for a in live})[-2:]
V["HEAD_N"] = sum(1 for a in live if a["started_date"] in top2)
V["HEAD_IN"] = sum(1 for a in live if a["started_date"] in top2 and a["id"] in newest10)
first29 = day_of(load(f"pages_{S29}/live_newest.json")[0])
V["HEAD29_FIRST"] = fmt_date(first29)
gap_days = [d for d in by_day if S17 < d < "2026-09-29"]
V["GAP_LAUNCHES"] = sum(len(by_day[d]) for d in gap_days)
mx = max(len(v) for v in by_day.values())
B["CAL_ROWS"] = "".join(
    f'<tr><td class="big">{fmt_date(d)}</td><td class="n">{len(g)}</td><td class="n"><b class="is">{sum(a["live"] for a in g)}</b></td>'
    f'<td class="n" style="color:var(--dead)">{sum(a["status_1010"]=="flagged_inactive" for a in g) or ""}</td>'
    f'<td>{bar(len(g), mx, "good")}</td></tr>' for d, g in sorted(by_day.items()))
early = [a for d, g in by_day.items() if "2026-09-29" <= d <= "2026-09-30" for a in g]
V["EARLY_N"], V["EARLY_FLAG"] = len(early), sum(a["status_1010"] == "flagged_inactive" for a in early)
hist_ids = {a["id"] for a in hist}
for tag, lo, hi in (("EARLYH", "2026-09-29", "2026-09-30"), ("PEAKH", peak_day, peak_day)):
    lv = [a for a in live if lo <= (a.get("started_date") or "") <= hi]
    V[f"{tag}_IN"], V[f"{tag}_OF"] = sum(a["id"] in hist_ids for a in lv), len(lv)
pk = by_day[peak_day]
V["PEAK_FLAG"] = sum(a["status_1010"] == "flagged_inactive" for a in pk)
V["PEAK_AGE"] = _d(peak_day, S10)

# ---------------------------------------------------------------- script reuse
# Three tests, because a re-upload, a re-shoot and a niche swap differ: same opening
# (first 80 normalised characters), same words (token-set Jaccard on the whole script),
# and same recording (half or more of the new ad's word 5-grams found in one old ad).
def words(t):
    return norm(t, 10 ** 6).split()


def jac(x, y):
    return len(x & y) / len(x | y) if x | y else 0


def grams(w, n=5):
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


OLD = {}
for a in ads:
    if (a.get("started_date") or "9") <= S17 and len(words(a.get("full_transcription"))) >= 20:
        OLD.setdefault(norm(a["full_transcription"], 10 ** 6), a)
old_txt = [(norm(t), set(words(t)), grams(words(t)), a) for t, a in OLD.items()]
V["OLD_DISTINCT"] = len(old_txt)
# calibration: how much do unrelated old scripts overlap? (sets the re-use thresholds' context)
_pairs = sorted(jac(old_txt[i][1], old_txt[j][1]) for i in range(len(old_txt)) for j in range(i + 1, len(old_txt)))
V["JAC_MED"], V["JAC_P99"] = f"{_pairs[len(_pairs) // 2]:.1f}", f"{_pairs[int(len(_pairs) * .99)]:.1f}"
young_ids = {a["id"] for a in young}
NEW = [a for a in new if len(words(a.get("full_transcription"))) >= 20]
for a in NEW:
    w = words(a["full_transcription"]); ws, g = set(w), grams(w)
    a["_m1"] = any(norm(a["full_transcription"]) == o[0] for o in old_txt)
    best = max(old_txt, key=lambda o: jac(ws, o[1]))
    a["_jac"] = jac(ws, best[1])
    src = max(old_txt, key=lambda o: (len(g & o[2]) / len(g)) if g else 0)
    a["_cont"] = (len(g & src[2]) / len(g)) if g else 0
    a["_src"] = src[3]
    a["_tier"] = ("A" if a["_cont"] >= .5 else "B" if a["_m1"] or a["_jac"] >= .6 else "C" if a["_jac"] >= .45 else "D")
    a["_src_young"] = best[3]["id"] in young_ids
V["NEW_TX"] = len(NEW)
reused = [a for a in NEW if a["_m1"] or a["_jac"] >= .8]
V["REUSE_N"], V["REUSE_PCT"] = len(reused), pct(len(reused), len(NEW))
V["SAME_REC"] = sum(a["_tier"] == "A" for a in NEW)
V["REUSE_YOUNG"] = sum(a["_src_young"] for a in NEW if a["_tier"] in "AB")
V["REUSE_AB"] = sum(a["_tier"] in "AB" for a in NEW)
# cluster the new scripts among themselves, then label each cluster by its most-reused member
parent = list(range(len(NEW)))


def root(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i


nw = [set(words(a["full_transcription"])) for a in NEW]
for i in range(len(NEW)):
    for j in range(i + 1, len(NEW)):
        if norm(NEW[i]["full_transcription"]) == norm(NEW[j]["full_transcription"]) or jac(nw[i], nw[j]) >= .8:
            parent[root(i)] = root(j)
clusters = collections.defaultdict(list)
for i, a in enumerate(NEW):
    clusters[root(i)].append(a)
ctier = collections.Counter(min(x["_tier"] for x in g) for g in clusters.values())
V["NEW_SCRIPTS"] = len(clusters)
V["SCRIPTS_REUSED"] = ctier["A"] + ctier["B"]
V["SCRIPTS_REWRITE"] = ctier["C"]
V["SCRIPTS_FRESH"] = ctier["D"]
fresh_ads = [a for a in NEW if a["_tier"] in "CD"]
V["FRESH_ADS"] = len(fresh_ads)
V["FRESH_D_ADS"] = sum(a["_tier"] == "D" for a in NEW)

V["REUSE_AB_PCT"] = pct(V["REUSE_AB"], len(NEW))
V["REWRITE_ADS"] = sum(a["_tier"] == "C" for a in NEW)
A_ads = [a for a in NEW if a["_tier"] == "A"]
V["SAME_REC_SRC"] = len({norm(a["_src"]["full_transcription"], 10 ** 6) for a in A_ads})
V["SAME_REC_FLAG"] = sum(a["status_1010"] == "flagged_inactive" for a in A_ads)
pp = [a for a in A_ads if a.get("publisher_platform") and a["_src"].get("publisher_platform")]
V["A_PP_N"] = len(pp)
V["A_PP_SAME"] = sum(set(a["publisher_platform"]) == set(a["_src"]["publisher_platform"]) for a in pp)
V["FRESH_CLUSTERS"] = V["SCRIPTS_REWRITE"] + V["SCRIPTS_FRESH"]

# the September ads that dropped out: did their scripts come back?
new_txt = [(norm(a["full_transcription"]), set(words(a["full_transcription"]))) for a in NEW]
gone = [a for a in young if not a["live"] and len(words(a.get("full_transcription"))) >= 20]
back = [a for a in gone if any(norm(a["full_transcription"]) == t or jac(set(words(a["full_transcription"])), w) >= .8 for t, w in new_txt)]
V["YOUNG_GONE_TX"], V["YOUNG_GONE_BACK"] = len(gone), len(back)
V["YOUNG_GONE_BACK_PCT"] = pct(len(back), len(gone))

# what the fresh scripts say that the old ones did not
PHR = {
    "CLOSE_REVIEWS": r"(1\s?000|thousa?e?nd)\s*(plus)?\s*(5|five)\s?star",   # norm() turns "1,000" into "1 000"
    "CLOSE_PG": r"performance guarantee",
    "CLOSE_NOINC": r"no (incentive|reason) (to|so) sell",
    "TRIAL": r"(seven|7)[ -]days?(?! a week)",
}
old_texts = [t for t in OLD]
fresh_texts = [norm(a["full_transcription"], 10 ** 6) for a in fresh_ads]
fresh_cl = [g for g in clusters.values() if min(x["_tier"] for x in g) in "CD"]
for k, rx in PHR.items():
    V[f"{k}_OLD"] = pct(sum(bool(re.search(rx, t)) for t in old_texts), len(old_texts))
    V[f"{k}_FRESH"] = pct(sum(any(re.search(rx, norm(x["full_transcription"], 10 ** 6)) for x in g) for g in fresh_cl), len(fresh_cl))
V["CLOSE_ALL3"] = sum(all(any(re.search(PHR[k], norm(x["full_transcription"], 10 ** 6)) for x in g)
                          for k in ("CLOSE_REVIEWS", "CLOSE_PG", "CLOSE_NOINC")) for g in fresh_cl)
fresh_age = [a["days_running"] for g in fresh_cl for a in g if a["live"]]
V["FRESH_AGE_MIN"], V["FRESH_AGE_MAX"] = min(fresh_age), max(fresh_age)
V["TRIAL_FRESH_N"] = sum(bool(re.search(PHR["TRIAL"], t)) for t in fresh_texts)

# placements and length
WIDE = {"audience_network", "whatsapp", "threads"}
base_pp = [a for a in in17 if a.get("publisher_platform")]
V["WIDE_NEW"] = sum(bool(WIDE & set(a.get("publisher_platform") or [])) for a in new)
V["WIDE_NEW_PCT"] = pct(V["WIDE_NEW"], len(new))
V["WIDE_17_PCT"] = pct(sum(bool(WIDE & set(a.get("publisher_platform") or [])) for a in base_pp), len(base_pp))
V["WIDE_FRESH"] = sum(bool(WIDE & set(a.get("publisher_platform") or [])) for a in fresh_ads)
V["WIDE_REUP"] = sum(bool(WIDE & set(a.get("publisher_platform") or [])) for a in NEW if a["_tier"] == "A")
# wide placements went with new recordings, not with a batch: compare same-day re-uploads
wide = lambda a: bool(WIDE & set(a.get("publisher_platform") or []))
newrec = [a for a in NEW if a["_tier"] in "BCD" and "2026-09-30" <= a["started_date"] <= "2026-10-07"]
reup_same = [a for a in NEW if a["_tier"] == "A" and "2026-09-30" <= a["started_date"] <= "2026-10-07"]
niche8 = [a for a in NEW if a["_tier"] in "BCD" and a["started_date"] == "2026-10-08"]
V["WIDE_NEWREC"], V["NEWREC_N"] = sum(map(wide, newrec)), len(newrec)
V["WIDE_REUP_SAME"], V["REUP_SAME_N"] = sum(map(wide, reup_same)), len(reup_same)
V["WIDE_OCT8"], V["OCT8_N"] = sum(map(wide, niche8)), len(niche8)
dn = sorted(a["video_duration"] for a in new if a.get("video_duration"))
d17 = sorted(a["video_duration"] for a in in17 if a.get("video_duration"))
V["VDUR_NEW"], V["VDUR_17"] = round(dn[len(dn) // 2]), round(d17[len(d17) // 2])

# ---------------------------------------------------------------- headlines and funnels
H155 = "Our avg clients get 15.5m views"
heads10 = collections.Counter((a.get("headline") or "").strip() for a in live)
V["H155_LIVE"], V["H155_PCT"] = heads10[H155], pct(heads10[H155], len(live))
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
V["MED_NEW_ALL"] = sum(1 for a in new if a["funnel"] == "med")
top5 = sorted(live, key=lambda a: -(a["days_running"] or 0))[:5]
V["GUAR_TOP5"] = sum(is_guar(a.get("headline") or "") for a in top5)
V["H155_TOP12"] = sum("15.5m" in (a.get("headline") or "") for a in sorted(live, key=lambda a: -(a["days_running"] or 0))[:12])
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

# ---------------------------------------------------------------- guarantee vs proof-number survival
def fam(a):
    h = (a.get("headline") or "")
    return "guar" if is_guar(h) else "155" if "15.5m" in h else "other"


aged = [a for a in in17 if (a.get("days_0917") or a.get("_days17") or 0) >= 30]
for f in ("guar", "155"):
    g = [a for a in aged if fam(a) == f]
    V[f"AGED_{f.upper()}_N"], V[f"AGED_{f.upper()}_LIVE"] = len(g), sum(a["live"] for a in g)
V["AGED_155_PCT"] = pct(V["AGED_155_LIVE"], V["AGED_155_N"])
mid_aged = [a for a in aged if (a.get("days_0917") or a.get("_days17") or 0) < 180]
for f in ("guar", "155"):
    g = [a for a in mid_aged if fam(a) == f]
    V[f"MIDAGE_{f.upper()}_N"], V[f"MIDAGE_{f.upper()}_LIVE"] = len(g), sum(a["live"] for a in g)
from math import comb


def fisher(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]]."""
    n1, n2, k = a + b, c + d, a + c
    pk = lambda x: comb(n1, x) * comb(n2, k - x) / comb(n1 + n2, k)
    p0 = pk(a)
    return sum(pk(x) for x in range(max(0, k - n2), min(k, n1) + 1) if pk(x) <= p0 + 1e-12)


V["GUAR_P"] = f'{fisher(V["AGED_GUAR_LIVE"], V["AGED_GUAR_N"] - V["AGED_GUAR_LIVE"], V["AGED_155_LIVE"], V["AGED_155_N"] - V["AGED_155_LIVE"]):.1f}'
pg = [(r, a, st) for r, a, st, _, _ in proven if fam({"headline": r[2]}) == "guar"]
p155 = [(r, a, st) for r, a, st, _, _ in proven if "15.5m" in r[2]]
V["PROVEN_GUAR_N"], V["PROVEN_GUAR_LIVE"] = len(pg), sum(st == "live" for *_, st in pg)
V["PROVEN_155_N"], V["PROVEN_155_LIVE"] = len(p155), sum(st == "live" for *_, st in p155)
V["PROVEN_DCO_LIVE"] = sum(st == "live" for r, a, st, _, _ in proven if r[1].upper() == "DCO")
dco_heads = []
for r, a, st, _, _ in proven:
    if a and st == "live" and r[1].upper() == "DCO":
        for c in a.get("cards") or []:
            h = (c.get("headline") or c.get("title") or "").strip() if isinstance(c, dict) else ""
            if h and h not in dco_heads:
                dco_heads.append(h)
V["DCO_HEADS"] = " and ".join(f'"{esc(h)}"' for h in dco_heads)
yg = [a for a in young if fam(a) == "guar"]; y155 = [a for a in young if fam(a) == "155"]
V["YG_N"], V["YG_SEEN"] = len(yg), sum(len(a["seen_live"]) > 1 for a in yg)
V["Y155_N"], V["Y155_SEEN"] = len(y155), sum(len(a["seen_live"]) > 1 for a in y155)
V["YG_PCT"], V["Y155_PCT"] = pct(V["YG_SEEN"], V["YG_N"]), pct(V["Y155_SEEN"], V["Y155_N"])

# niche template ads the 17 Sep page said were holding at 71-73 days
niche73 = [a for a in in17 if 71 <= (a.get("days_0917") or 0) <= 73 and a.get("vertical") not in (None, "General / no vertical")]
V["NICHE73_N"], V["NICHE73_LIVE"] = len(niche73), sum(a["live"] for a in niche73)
V["NICHE73_29"] = sum(S29 in a["seen_live"] for a in niche73)
V["NICHE73_NOW_MIN"] = min((a["days_running"] for a in niche73 if a["live"]), default=0)
V["NICHE73_NOW_MAX"] = max((a["days_running"] for a in niche73 if a["live"]), default=0)

# launch volume the 17 Sep month table hid: the probes of the proven posters' launch days
probe_155, probe_files = collections.Counter(), set()
for pth in glob.glob(f"pages_{S10}/probe_*.json"):
    for a in load(pth):
        d = day_of(a)
        if "15.5m" in (a.get("headline") or "") and d < "2026-03-01":
            probe_155[a["id"]] = d
            probe_files.add(pth)
V["PROBE_155_N"] = len(probe_155)
V["PROBE_155_DAYS"] = len(set(probe_155.values()))
V["PROBE_155_FILES"] = len(probe_files)
V["PROBE_155_CAPPED"] = sum(bool(json.load(open(p))["metadata"].get("cursor")) for p in probe_files)
V["SEP_LIVE_17"] = m17("2026-09"); V["AUG_LIVE_17"] = m17("2026-08")
V["JANFEB_LIVE_17"] = m17("2026-01") + m17("2026-02")
V["ACT_0909"] = act.get("2026-09-09")

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
    hl = a.get("headline") or next((c.get("headline") for c in a.get("cards") or [] if isinstance(c, dict) and c.get("headline")), "") or "no fixed headline"
    fun = "" if a.get("funnel") in (None, "(none)") else f' · {esc(a["funnel"])}'
    return (f'<figure class="card{"" if a["live"] else " off"}"><a href="{esc(link)}" target="_blank" rel="noopener">{media}</a>'
            f'<figcaption>{status_badge(a)}<b>{esc(hl)}</b>'
            f'<span class="meta">{esc((a.get("display_format") or "").lower())}{fun} · started {fmt_date(a["started_date"]) if a.get("started_date") else "?"}{then}</span>'
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
fresh_cards, seen_cl = [], set()
for k, g in sorted(clusters.items(), key=lambda kv: min(x["started_date"] for x in kv[1])):
    if min(x["_tier"] for x in g) in "CD":
        pick = sorted(g, key=lambda x: (not x["live"], x["started_date"]))[0]
        fresh_cards.append(pick)
B["FRESH_CARDS"] = "".join(card(a) for a in fresh_cards[:24])
V["FRESH_SHOWN"] = min(24, len(fresh_cards))
V["FRESH_CARDS_N"] = len(fresh_cards)

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

# ---------------------------------------------------------------- fresh-script openers
def opener(a, n=230):
    t = re.sub(r"\s+", " ", a.get("full_transcription") or "").strip()
    cut = t[:n]
    return cut[:cut.rfind(" ")] + "…" if len(t) > n else t


fresh_live = [a for a in fresh_cards if a["live"]]
QUOTE_IDS = ["LhtFrPatLN1DNatNpbrT", "0I3aLGXNt2a5vbRDDL7c", "oRBA7xzVhrpa7PDa3hxF", "Ri1nMldbk5RsyJqWi5G3",
             "a1AhVo4EWdw2SOmjPy9r", "183oF3zdOudpl7WCcDPb"]
qs = [by_id[i] for i in QUOTE_IDS if i in by_id and by_id[i].get("_tier") in ("C", "D")]
B["FRESH_QUOTES"] = '<div class="cols2">' + "".join(
    f'<div class="quote new"><p>"{esc(opener(a))}"</p><p class="out">{status_badge(a)} started {fmt_date(a["started_date"])} · '
    f'{"new script" if a["_tier"] == "D" else "rewrite"} · <a href="{esc(a.get("foreplay_url") or "#")}" target="_blank" rel="noopener">foreplay</a></p></div>'
    for a in qs) + "</div>"
V["QUOTES_N"] = len(qs)
def caps(a):   # ASR sometimes title-cases every word; quote the cleanest transcript
    w = re.findall(r"[A-Za-z]+", a["full_transcription"])
    return sum(x[0].isupper() for x in w) / max(1, len(w))


close_ex = min((a for a in fresh_ads if re.search(PHR["CLOSE_PG"], norm(a["full_transcription"], 10 ** 6))
                and re.search(PHR["CLOSE_REVIEWS"], norm(a["full_transcription"], 10 ** 6))), key=caps, default=None)
if close_ex:
    t = re.sub(r"\s+", " ", close_ex["full_transcription"])
    i = max(0, t.lower().find("star review") - 120)
    B["CLOSE_QUOTE"] = (f'<div class="quote"><p>"…{esc(t[i:i + 300].strip())}…"</p><p class="out">the close, as one fresh script says it · '
                        f'<a href="{esc(close_ex.get("foreplay_url") or "#")}" target="_blank" rel="noopener">foreplay</a></p></div>')
else:
    B["CLOSE_QUOTE"] = ""

# ---------------------------------------------------------------- what 17 Sep got wrong
tag = lambda t: f'<span class="verdict-tag {t.lower()}">{t}</span>'
olix = by_id.get("olixEmcDbZ5hTpuKeECD")
AUDIT = [
    ('"The fourth pull added a single new ad, so the union has effectively converged" at ' + str(union17) + ".",
     "Unsupported",
     f'The fourth pull (oldest-first) largely repeated the first (longest-running), so it could not show convergence. '
     f' {V["RETURN_N"]} ads started before June, none in the {union17}, have led every '
     f'age-sorted pull since. They were probably paused or not yet flagged live on 17 Sep; which, the data cannot say.'),
    (f'"{V["MAX_17"]} days, the longest-running ad in the account."',
     "Overtaken",
     f'An ad started {V["MAX_LIVE_START"]} is live at {V["MAX_LIVE"]} days and heads every age-sorted pull on 29 Sep and '
     f'10 Oct. It was in no 17 Sep pull; it was most likely switched back on or newly indexed.'),
    ('"Not one ad launched in March, April or May 2026 is still running… whatever ran that spring is gone."',
     "Overtaken",
     f'No spring ad was in the 17 Sep data, but {V["RETURN_APR"]} April ads have led every age-sorted pull since 29 Sep, '
     f'most likely switched back on. The count may have been right on the day; reading absence as "gone" was not.'),
    (f'"Six of the fifteen proven ads are static images… Anyone concluding \'only video lasts\' has not counted it."',
     "Overtaken",
     f'All {V["POSTERS_N"]} posters are absent from the head of every age-sorted pull since; {V["POSTERS_FLAGGED"]} carry '
     f'an inactive flag under their own 17 Sep ids. They went with the 15.5m video from the same Jan–Feb launches, and '
     f'{V["YOUNG_POSTERS_10"]} of the {V["YOUNG_POSTERS_29"]} younger posters live on 29 Sep are still live, so this was '
     f'a cohort, not a format.'),
    ('"The guarantee is what endures: the three oldest ads, 423, 412 and 405 days."',
     "Refuted",
     'The 405-day ad, "Effortless Social Media Success", is a client case study with no guarantee in it. The pattern '
     f'still fits: {V["PROVEN_GUAR_LIVE"]} of {V["PROVEN_GUAR_N"]} proven guarantee videos are live, and '
     f'{V["AGED_GUAR_LIVE"]} of {V["AGED_GUAR_N"]} guarantee ads past 30 days, against {V["AGED_155_LIVE"]} of '
     f'{V["AGED_155_N"]} on the 15.5m headline. Too few ads to call it a rule (p≈{V["GUAR_P"]}).'),
    (f'"{V["SEP_LIVE_17"]} launches in the first seventeen days of September alone, against {V["AUG_LIVE_17"]} in all of August."',
     "Refuted",
     f'Those were ads still live by start month, which shrinks older months by construction. {V["PROBE_155_FILES"]} small '
     f'probes of January and February return at least {V["PROBE_155_N"]} ads on the 15.5m headline ({V["PROBE_155_CAPPED"]} '
     f'stopped at a page limit), where that page\'s month table showed {V["JANFEB_LIVE_17"]} for the two months.'),
    ('"The September flood proves nothing yet."',
     "Holds",
     f'It was not left running long enough to be judged. {V["YOUNG_29"]} of the {V["YOUNG_N"]} under-30-day ads that can '
     f'be followed were live on 29 Sep; on 10 Oct at least {V["YOUNG_10"]} are, and the pulls cannot see the cohort well '
     f'enough to say more. Most of its scripts are back in new ads.'),
    ('"The 9 September pull returned zero ads; brand analytics read 0 that day."',
     "Refuted",
     f'Refuted for the pull: the 9 Sep brief was built on live ads from it, so it was partial, not empty. The analytics '
     f'figure was right when quoted; Foreplay has since revised 9 Sep to {V["ACT_0909"]}. The rule drawn from it (live is '
     f'trustworthy, absence is not) holds.'),
    ('"Niche template ads cluster at 71–73 days and are still running."',
     "Holds",
     f'All {V["NICHE73_N"]} are live at {V["NICHE73_NOW_MIN"]}–{V["NICHE73_NOW_MAX"]} days, though only {V["NICHE73_29"]} '
     f'showed up on 29 Sep: a clean case of absence not meaning death.'),
    (f'"One headline on {V["H155_17_PCT"]}% of the live set."',
     "Holds",
     f'{V["H155_PCT"]}% of the 10 Oct set ({V["H155_LIVE"]} of {V["N_LIVE"]}) and {V["H155_NEW_PCT"]}% of the live ads '
     f'launched since. Single pulls on one day differ by more than the snapshots do, so this is not a measured rise.'),
    ('"Has been paid for every day for nearly eleven months"; the guarantee ads "convert coldest traffic".',
     "Unsupported",
     'The Ad Library shows no spend, delivery or conversions, and a live ad\'s tenure is just today minus its start date. '
     'Ads with old start dates have dropped out and come back. "Not killed" is all longevity says.'),
]
B["AUDIT_ROWS"] = "".join(f'<tr><td>{esc(c)}</td><td>{tag(t)}</td><td class="ev">{e}</td></tr>' for c, t, e in AUDIT)
V["AUDIT_REFUTED"] = sum(t == "Refuted" for _, t, _ in AUDIT)
V["AUDIT_OVERTAKEN"] = sum(t == "Overtaken" for _, t, _ in AUDIT)
V["AUDIT_HOLDS"] = sum(t == "Holds" for _, t, _ in AUDIT)
V["AUDIT_UNSUP"] = sum(t == "Unsupported" for _, t, _ in AUDIT)

# ---------------------------------------------------------------- assemble
assert all("hook" in a for a in ads), "run analyze_survival.py on ads.json after build_dataset.py"
CSS, JS, BODY = open("report.css").read(), open("report.js").read(), open("report_body.html").read()


def fill(text):
    for k, v in B.items():
        text = text.replace("{{" + k + "}}", v)
    for k, v in V.items():
        text = text.replace("{{" + k + "}}", f"{v:,}" if isinstance(v, int) and not k.startswith("MAX") and v >= 10000 else str(v))
    left = sorted(set(re.findall(r"\{\{[A-Z_0-9]+\}\}", text)))
    if left:
        raise SystemExit(f"unfilled placeholders: {left}")
    return text


out = f"<title>Viral Coach Teardown</title>\n<style>{CSS}</style>\n" + fill(BODY) + f"\n<script>{JS}</script>"
open("report.html", "w").write(out)
open("brief.md", "w").write(fill(open("brief_template.md").read()))
json.dump(V, open("figures.json", "w"), indent=1, sort_keys=True)
print(f"report.html {os.path.getsize('report.html') / 1e6:.2f} MB · {V['TX_INLINE']} transcripts inline · brief.md · figures.json")
