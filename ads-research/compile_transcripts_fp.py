#!/usr/bin/env python3
"""Write per-ad transcript files plus a combined, longest-running-first index.

One file per ad so a reader can be sent a single transcript without the other
1,500; the combined markdown is for skimming. Live ads come first and are
ordered by tenure, because tenure is the only survival signal the Ad Library
gives us — and only for ads the live query returns. An ad missing from that query
is unconfirmed, not dead: the live pull comes back partial on some days.
"""
# Records can arrive from two places: a full page dump (every field) or a live-set pull
# (only the fields that pull asked for). Read defensively so the second kind does not
# crash the compiler halfway through writing the transcripts directory.
import json, os, sys, csv, re

def slug(s, n=40):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "untitled"

def main(target):
    ads = json.load(open(os.path.join(target, "ads.json")))
    tdir = os.path.join(target, "transcripts")
    os.makedirs(tdir, exist_ok=True)
    for stale in os.listdir(tdir):  # an ad that died since last run would otherwise exist twice
        os.remove(os.path.join(tdir, stale))
    have = [a for a in ads if a.get("full_transcription")]
    have.sort(key=lambda a: (a.get("live") is not True, -(a.get("days_running") or 0)))

    rows, combined = [], []
    for a in have:
        status = "LIVE" if a.get("live") is True else "NOT LIVE"
        days = f"{a.get('days_running') or 0}d" if a.get("live") is True else "n/a"
        name = f"{'live' if a.get('live') is True else 'notlive'}-{a.get('days_running') or 0:04d}d-{a['id']}.txt"
        header = (f"Ad {a['id']}  ({a.get('ad_id') or '-'})\n"
                  f"Status      : {status}\n"
                  f"Running     : {days}   started {a.get('started_date') or '?'}\n"
                  f"Funnel      : {a.get('funnel') or '?'}   ({a.get('link_url') or '-'})\n"
                  f"Vertical    : {a.get('vertical') or '?'}\n"
                  f"Hook family : {a.get('hook') or '?'}\n"
                  f"Headline    : {a.get('headline') or '-'}\n"
                  f"Video       : {a.get('video') or '-'}\n"
                  f"Foreplay    : {a.get('foreplay_url') or '-'}\n"
                  + "-" * 72 + "\n")
        open(os.path.join(tdir, name), "w").write(header + a["full_transcription"] + "\n")
        rows.append({"file": name, "id": a["id"], "status": status,
                     "days_running_live_only": (a.get("days_running") or 0) if a.get("live") is True else "",
                     "started": a.get("started_date") or "", "funnel": a.get("funnel") or "",
                     "vertical": a.get("vertical") or "", "hook": a.get("hook") or "",
                     "headline": a.get("headline") or "", "video": a.get("video") or "",
                     "foreplay_url": a.get("foreplay_url") or ""})
        combined.append(f"### {status} · {days} · {a.get('vertical') or '?'} · {a.get('hook') or '?'}\n\n"
                        f"`{a['id']}` · started {a.get('started_date') or '?'} · {a.get('funnel') or '?'} funnel  \n"
                        f"[Video]({a.get('video') or '#'}) · [Foreplay]({a.get('foreplay_url') or '#'})\n\n"
                        f"> {a['full_transcription']}\n")

    with open(os.path.join(target, "transcripts_index.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    live_n = sum(1 for a in have if a.get("live") is True)
    open(os.path.join(target, "all_transcripts.md"), "w").write(
        f"# {os.path.basename(os.path.normpath(target))} — every transcript\n\n"
        f"{len(have)} ads with usable audio, of {len(ads)} scraped. "
        f"Live ads first ({live_n}), longest-running at the top; the rest after.\n\n"
        "Day counts are shown for live ads only — Foreplay does not record a real "
        "stop date for inactive ads, so their tenure is unknown.\n\n"
        "**LIVE means some live-set pull returned this ad — reliable as of that pull's date, "
        "which is not necessarily the latest one. NOT LIVE means no pull returned it, which "
        "is weaker: a live pull comes back partial, so absence is not proof the ad stopped. "
        "For the current live set, take the union of the most recent pulls rather than this "
        "flag.**\n\n" + "\n".join(combined))
    print(f"{len(have)} transcripts -> {tdir}/  ({live_n} live)")
    print(f"index -> {target}/transcripts_index.csv")
    print(f"combined -> {target}/all_transcripts.md")

if __name__ == "__main__":
    main(sys.argv[1])
