#!/usr/bin/env python3
"""Write per-ad transcript files plus a combined, longest-running-first index.

One file per ad so a reader can be sent a single transcript without the other
1,500; the combined markdown is for skimming. Live ads come first and are
ordered by tenure, because tenure is the only survival signal the Ad Library
gives us.
"""
import json, os, sys, csv, re

def slug(s, n=40):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "untitled"

def main(target):
    ads = json.load(open(os.path.join(target, "ads.json")))
    tdir = os.path.join(target, "transcripts")
    os.makedirs(tdir, exist_ok=True)
    # Filenames encode status and tenure, so a re-run after a refresh must drop
    # last week's files or an ad that died shows up twice.
    for old in os.listdir(tdir):
        if old.endswith(".txt"): os.remove(os.path.join(tdir, old))
    have = [a for a in ads if a.get("full_transcription")]
    have.sort(key=lambda a: (a.get("live") is not True, -a["days_running"]))

    rows, combined = [], []
    for a in have:
        status = "LIVE" if a.get("live") is True else "stopped"
        days = f"{a['days_running']}d" if a.get("live") is True else "n/a"
        name = f"{'live' if a.get('live') is True else 'dead'}-{a['days_running']:04d}d-{a['id']}.txt"
        header = (f"Ad {a['id']}  ({a['ad_id']})\n"
                  f"Status      : {status}\n"
                  f"Running     : {days}   started {a['started_date']}\n"
                  f"Funnel      : {a['funnel']}   ({a.get('link_url') or '-'})\n"
                  f"Vertical    : {a['vertical']}\n"
                  f"Hook family : {a['hook']}\n"
                  f"Headline    : {a.get('headline') or '-'}\n"
                  f"Video       : {a.get('video') or '-'}\n"
                  f"Foreplay    : {a.get('foreplay_url') or '-'}\n"
                  + "-" * 72 + "\n")
        open(os.path.join(tdir, name), "w").write(header + a["full_transcription"] + "\n")
        rows.append({"file": name, "id": a["id"], "status": status,
                     "days_running_live_only": a["days_running"] if a.get("live") is True else "",
                     "started": a["started_date"], "funnel": a["funnel"],
                     "vertical": a["vertical"], "hook": a["hook"],
                     "headline": a.get("headline") or "", "video": a.get("video") or "",
                     "foreplay_url": a.get("foreplay_url") or ""})
        combined.append(f"### {status} · {days} · {a['vertical']} · {a['hook']}\n\n"
                        f"`{a['id']}` · started {a['started_date']} · {a['funnel']} funnel  \n"
                        f"[Video]({a.get('video') or '#'}) · [Foreplay]({a.get('foreplay_url') or '#'})\n\n"
                        f"> {a['full_transcription']}\n")

    with open(os.path.join(target, "transcripts_index.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    live_n = sum(1 for a in have if a.get("live") is True)
    open(os.path.join(target, "all_transcripts.md"), "w").write(
        "# Viral Coach — every transcript\n\n"
        f"{len(have)} ads with usable audio, of {len(ads)} scraped. "
        f"Live ads first ({live_n}), longest-running at the top; stopped ads after.\n\n"
        "Day counts are shown for live ads only — Foreplay does not record a real "
        "stop date for inactive ads, so their tenure is unknown.\n\n" + "\n".join(combined))
    print(f"{len(have)} transcripts -> {tdir}/  ({live_n} live)")
    print(f"index -> {target}/transcripts_index.csv")
    print(f"combined -> {target}/all_transcripts.md")

if __name__ == "__main__":
    main(sys.argv[1])
