#!/usr/bin/env python3
"""Overlay a fresh Foreplay pull onto an earlier ads.json snapshot.

The earlier snapshot is the only place a real stop date can come from: Foreplay
does not record when an inactive ad stopped, but an ad that was live in the
snapshot and is absent from today's live set died in between. That window is
recorded on the ad as `died_between`, and live-ad tenure is refreshed from the
new pull. New ads are appended.
"""
import json, sys, glob, os, datetime

import re
def scrub(s):
    """Foreplay transcripts occasionally carry U+FFFD where an apostrophe was lost
    ("don<?>t pay"). Restore it between letters, drop it elsewhere; the artifact
    host rejects the raw character."""
    if not isinstance(s, str) or "\ufffd" not in s: return s
    return re.sub(r"(?<=[A-Za-z])\ufffd(?=[A-Za-z])", "'", s).replace("\ufffd", "")

def d(ms): return datetime.datetime.utcfromtimestamp(ms/1000).strftime("%Y-%m-%d") if ms else None

def main(target, pages_dir, snap_date, now_date):
    base = {a["id"]: a for a in json.load(open(os.path.join(target, "ads.json")))}
    fresh = {}
    for p in sorted(glob.glob(os.path.join(pages_dir, "*.json"))):
        for a in json.load(open(p)).get("data") or []:
            if a["id"] not in fresh or a.get("live") is True:
                fresh[a["id"]] = a
    live_now = {i for i, a in fresh.items() if a.get("live") is True}

    died = added = refreshed = 0
    for i, a in base.items():
        was_live = a.get("live") is True
        if i in fresh:
            f = fresh[i]
            for k, v in f.items():
                if v not in (None, "", [], {}): a[k] = v
            a["live"] = f.get("live") is True
            a["days_running"] = (a.get("running_duration") or {}).get("days") or 0
            refreshed += 1
        elif was_live:
            # Live a week ago, not in today's live set: it stopped in the window.
            a["live"] = False
            a["died_between"] = [snap_date, now_date]
            a["days_at_death_min"] = a["days_running"]  # tenure at last sighting
            died += 1
        a.setdefault("seen_live", [])
        if was_live and snap_date not in a["seen_live"]: a["seen_live"].append(snap_date)
        if a.get("live") is True and now_date not in a["seen_live"]: a["seen_live"].append(now_date)
    for i, f in fresh.items():
        if i in base: continue
        f["days_running"] = (f.get("running_duration") or {}).get("days") or 0
        f["started_date"] = d(f.get("started_running"))
        f["seen_live"] = [now_date] if f.get("live") is True else []
        f["new_since"] = snap_date
        base[i] = f; added += 1

    for a in base.values():
        for k in ("full_transcription", "description", "headline"):
            a[k] = scrub(a.get(k))
    ads = sorted(base.values(), key=lambda a: (-a["days_running"], a.get("started_date") or ""))
    json.dump(ads, open(os.path.join(target, "ads.json"), "w"), indent=1)
    live = sum(1 for a in ads if a.get("live") is True)
    print(f"{len(ads)} ads · live={live} · refreshed={refreshed} · died in window={died} · new={added}")

if __name__ == "__main__":
    main(*sys.argv[1:5])
