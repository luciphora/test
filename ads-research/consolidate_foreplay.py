#!/usr/bin/env python3
"""Merge Foreplay page dumps into one deduplicated ads.json.

Foreplay's cursor is a {ts, id} pair, so it only paginates correctly under a
date ordering. Pages pulled under `longest_running` overlap heavily and are
ignored here; longevity is recomputed from running_duration instead.
"""
import json, sys, glob, os, re, datetime

def _repair(s):
    """Foreplay transcripts lose the odd byte, always an apostrophe ("don\ufffdt")."""
    if not isinstance(s, str) or "\ufffd" not in s: return s
    return re.sub(r"(?<=[A-Za-z])\ufffd(?=[A-Za-z])", "'", s).replace("\ufffd", "")

def _repair_ad(a):
    for k in ("full_transcription", "description", "headline"):
        if k in a: a[k] = _repair(a[k])
    return a

def load(target: str, pages: str) -> list[dict]:
    by_id: dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(pages, "*.json"))):
        if "census" in os.path.basename(path):
            continue  # longest_running pages: unreliable cursor, superseded
        doc = json.load(open(path))
        for ad in doc.get("data") or []:
            prev = by_id.get(ad["id"])
            # A later page can carry a fresher live flag; prefer the richer row.
            if prev is None or _score(ad) > _score(prev):
                by_id[ad["id"]] = _repair_ad(ad)
    return list(by_id.values())

def _score(ad: dict) -> int:
    return sum(1 for v in ad.values() if v not in (None, "", [], {}))

def days(ad: dict) -> int:
    rd = ad.get("running_duration") or {}
    return rd.get("days") or 0

def main(target: str, pages: str, date: str) -> None:
    ads = load(target, pages)
    for ad in ads:
        ad["days_running"] = days(ad)
        ts = ad.get("started_running")
        ad["started_date"] = (
            datetime.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            if ts else None
        )
    ads.sort(key=lambda a: (-a["days_running"], a.get("started_date") or ""))
    out = os.path.join(target, "ads.json")
    json.dump(ads, open(out, "w"), indent=1)
    json.dump([date], open(os.path.join(target, "snapshots.json"), "w"))
    live = sum(1 for a in ads if a.get("live") is True)
    tx = sum(1 for a in ads if a.get("full_transcription"))
    print(f"{len(ads)} unique ads -> {out}")
    print(f"  live={live}  dead={len(ads)-live}  with_transcript={tx}")
    print(f"  date span: {min(a['started_date'] for a in ads if a['started_date'])}"
          f" .. {max(a['started_date'] for a in ads if a['started_date'])}")

if __name__ == "__main__":
    t = sys.argv[1]
    pages = sys.argv[2] if len(sys.argv) > 2 else os.path.join(t, "pages")
    date = sys.argv[3] if len(sys.argv) > 3 else datetime.date.today().isoformat()
    main(t, pages, date)
