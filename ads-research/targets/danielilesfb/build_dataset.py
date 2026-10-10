#!/usr/bin/env python3
"""Rebuild ads.json for the 10 Oct refresh from three snapshots that disagree on IDs.

Why this exists instead of refresh_foreplay.py: the live pulls are partial, so
"absent now" is not "dead", and Foreplay re-keys its own ids between pulls (the
412-day guarantee ad was YDlyqR8b... on 17 Sep and is zebUc... on 10 Oct; the old
id no longer resolves). So an ad is matched across snapshots by id first, then by
content: same start date (+/-1 day), headline, funnel and opening words.

Inputs
  snapshots/report_2026-09-17.html   the published 17 Sep artifact (its 266 ad ids,
                                     tenure, headline and transcript are recoverable)
  pages_2026-09-29/live_*.json       five live-set pulls
  pages_2026-10-10/live_*.json       four live-set pulls
  pages_2026-10-10/history_*.json    every ad started since 17 Sep, live or not
  pages_2026-10-10/probe_*.json      targeted pulls for the 17 Sep proven set
Output
  ads.json, one row per ad, with seen_live (dates a live pull returned it), live
  (returned live on 10 Oct), status_1010 and, for 17 Sep ads, fate.
"""
import json, glob, os, re, html, datetime, collections

S17, S29, S10 = "2026-09-17", "2026-09-29", "2026-10-10"


def day(ts):
    return datetime.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else None


def shift(d, n):
    return (datetime.date.fromisoformat(d) + datetime.timedelta(days=n)).isoformat()


def funnel(url):
    u = url or ""
    m = re.search(r"//(?:www\.)?([a-z0-9-]+)\.viralcoach\.com", u)
    if m and m.group(1) != "www":
        return m.group(1)
    m = re.search(r"viralcoach\.com/([a-z0-9-]+)", u)
    return m.group(1) if m else "(none)"


def norm(s, n=90):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()[:n]


def head(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def rows(path):
    return json.load(open(path)).get("data") or []


def baseline_0917():
    """The 266 ads the published 17 Sep page carries, with tenure as of that day."""
    h = open("snapshots/report_2026-09-17.html", encoding="utf-8").read()
    h = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "", h)
    base = {}
    for m in re.finditer(r'<article class="tx" data-band="\d+" data-d="(\d+)">\s*<header>(.*?)</header>\s*<p>(.*?)</p>', h, re.S):
        fid = re.search(r"ad=([A-Za-z0-9]+)", m.group(2)).group(1)
        code = re.search(r"<code>(.*?)</code>", m.group(2))
        fmt = re.search(r'badge gap">(.*?)<', m.group(2))
        base[fid] = {"days": int(m.group(1)), "headline": html.unescape(code.group(1)) if code else "",
                     "fmt": (fmt.group(1) if fmt else "").upper(), "tx": html.unescape(m.group(3))}
    for m in re.finditer(r'<figure class="card">(.*?)</figure>', h, re.S):
        c = m.group(1)
        fid = re.search(r"ad=([A-Za-z0-9]+)", c).group(1)
        d = re.search(r"running (\d+) days", c)
        b = base.setdefault(fid, {"tx": "", "headline": "", "fmt": ""})
        if d:
            b["days"] = int(d.group(1))
        hb = re.search(r"<b>(.*?)</b>", c)
        if hb and not b.get("headline"):
            b["headline"] = html.unescape(hb.group(1))
        vk = re.search(r"r2\.foreplay\.co/(\d+)/", c)
        if vk:
            b["vid_key"] = vk.group(1)  # the Meta ad id, as a string: survives Foreplay re-keying
        fm = re.search(r"badge live\">\d+d · (\w+)", c)
        if fm and not b.get("fmt"):
            b["fmt"] = fm.group(1).upper()
    for b in base.values():
        b["started_date"] = shift(S17, -b.get("days", 0))
    return base


def main():
    recs = {}          # foreplay id -> merged record
    seen = collections.defaultdict(set)
    flagged_inactive = set()

    def take(a, date, live_pull):
        r = recs.get(a["id"])
        if r is None or (a.get("live") and not r.get("_live_row")) or date > r.get("_date", ""):
            keep = {k: v for k, v in (r or {}).items()}
            keep.update({k: v for k, v in a.items() if v not in (None, "", [], {})})
            keep["_date"] = max(date, (r or {}).get("_date", ""))
            keep["_live_row"] = bool(a.get("live")) or (r or {}).get("_live_row", False)
            recs[a["id"]] = keep
        if a.get("live") is True:
            seen[a["id"]].add(date)
        elif date == S10:
            flagged_inactive.add(a["id"])

    for p in sorted(glob.glob(f"pages_{S29}/live_*.json")):
        for a in rows(p):
            take(a, S29, True)
    for p in sorted(glob.glob(f"pages_{S10}/*.json")):
        for a in rows(p):
            take(a, S10, "live_" in p)

    base = baseline_0917()
    # Same-id matches first.
    for fid in base:
        if fid in recs:
            seen[fid].add(S17)

    # Content matches for 17 Sep ids Foreplay has since re-keyed.
    def sig(started, hl, tx):
        return (started, head(hl), norm(tx, 60))
    index = collections.defaultdict(list)
    for fid, r in recs.items():
        sd = day(r.get("started_running"))
        for off in (-1, 0, 1):
            index[sig(shift(sd, off), r.get("headline"), r.get("full_transcription"))].append(fid)
    rekeyed = {}
    by_meta = {str(r.get("ad_id")): fid for fid, r in recs.items() if r.get("ad_id")}
    for fid, b in base.items():
        if fid in recs:
            continue
        if b.get("vid_key") in by_meta:
            rekeyed[fid] = by_meta[b["vid_key"]]
            seen[rekeyed[fid]].add(S17)
            continue
        cands = [c for c in index.get(sig(b["started_date"], b["headline"], b["tx"]), []) if c not in base]
        # A content match is only accepted when it is unique and has a transcript or a
        # distinctive headline; the 15.5m posters share both and cannot be told apart.
        if len(set(cands)) == 1 and (b["tx"] or b["headline"] not in ("", "Our avg clients get 15.5m views")):
            rekeyed[fid] = cands[0]
            seen[cands[0]].add(S17)

    ads = []
    for fid, r in recs.items():
        r = {k: v for k, v in r.items() if not k.startswith("_")}
        s = sorted(seen.get(fid, ()))
        live = S10 in s
        rd = (r.get("running_duration") or {}).get("days")
        r.update({
            "started_date": day(r.get("started_running")),
            "funnel": funnel(r.get("link_url")),
            "seen_live": s,
            "live": live,
            "status_1010": "live" if live else ("flagged_inactive" if fid in flagged_inactive else "not_returned"),
            # running_duration is only real for a live row; for anything else Foreplay
            # reports a censored figure (usually 1-2 days), so it is dropped.
            "days_running": rd if live else None,
            "in_0917": S17 in s,
            "was_id_0917": next((k for k, v in rekeyed.items() if v == fid), None),
        })
        ads.append(r)

    # 17 Sep ads with no record since: keep them as baseline rows so their fate is countable.
    matched = set(recs) | set(rekeyed)
    for fid, b in base.items():
        if fid in matched:
            continue
        ads.append({"id": fid, "foreplay_url": f"https://app.foreplay.co/discovery?ad={fid}",
                    "headline": b["headline"], "display_format": b["fmt"], "full_transcription": b["tx"],
                    "started_date": b["started_date"], "funnel": None, "seen_live": [S17], "live": False,
                    "status_1010": "not_returned", "days_running": None, "in_0917": True,
                    "days_0917": b.get("days"), "baseline_only": True})
    for a in ads:
        fid = a.get("was_id_0917") or a["id"]
        if fid in base:
            a["days_0917"] = base[fid].get("days")

    for a in ads:
        if (a.get("started_date") or "") > S17:
            a["new_since"] = S17
        # Cards in the report: everything that was in the 17 Sep set, so its fate can be shown.
        a["feature"] = bool(a.get("in_0917"))
    ads.sort(key=lambda a: (not a["live"], -(a.get("days_running") or 0), a.get("started_date") or ""))
    json.dump(ads, open("ads.json", "w"), indent=1)

    live = [a for a in ads if a["live"]]
    print(f"ads.json: {len(ads)} rows · live on {S10}: {len(live)} · flagged inactive: "
          f"{sum(a['status_1010']=='flagged_inactive' for a in ads)} · 17 Sep baseline: {len(base)} "
          f"(same id {sum(1 for f in base if f in recs)}, re-keyed {len(rekeyed)}, no record {len(base)-len(matched & set(base))-len(rekeyed)})")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
