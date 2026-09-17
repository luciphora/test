#!/usr/bin/env python3
"""Derive a hook x vertical taxonomy from an advertiser's own corpus.

Nothing here is pre-written: the tables live in <target>/taxonomy.py and are
derived per advertiser — the vertical from the noun the ad names in its own
opening line, the hook family from the phrasing template that recurs across
those verticals. Ads that match neither are reported as unclassified rather
than forced into a bucket. A target with no taxonomy.py gets funnel-level
survival only, which is the honest floor.
"""
import json, re, sys, os, collections, statistics, importlib.util

# Verticals: the trade the ad names in its opener. Order matters - the more
# specific label wins (personal injury attorney before attorney).

def load_taxonomy(target):
    p = os.path.join(target, "taxonomy.py")
    if not os.path.exists(p):
        return [], [], lambda u: (re.search(r"//([a-z0-9.-]+)/?([a-z0-9-]*)", u or "") or [None, "(none)", ""])[1], ()
    spec = importlib.util.spec_from_file_location("taxonomy", p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.VERTICALS, m.HOOKS, m.funnel, getattr(m, "FEATURED_FUNNELS", ())

def classify(text, table):
    low = (text or "").lower()
    for label, pat in table:
        if re.search(pat, low):
            return label
    return None

def main(path):
    target = os.path.dirname(os.path.abspath(path))
    VERTICALS, HOOKS, funnel, FEATURED = load_taxonomy(target)
    ads = json.load(open(path))
    for a in ads:
        head = (a.get("full_transcription") or "")[:200]
        a["vertical"] = classify(head, VERTICALS) or "General / no vertical"
        a["hook"] = classify(head, HOOKS) or "Unclassified"
        a["funnel"] = funnel(a.get("link_url"))

    def block(title, rows, keyfn):
        """Survival table.

        running_duration is only trustworthy for LIVE ads: 98.4% of inactive ads
        in this corpus report exactly 1 day, which is a Foreplay artifact rather
        than a real stop date. So every day-figure below is computed from live
        ads only, and dead ads contribute to counts alone.
        """
        print(f"\n## {title}\n")
        groups = collections.defaultdict(list)
        for a in rows:
            groups[keyfn(a)].append(a)
        print(f"| {title} | Ads | Live | Killed | Survival | Median days (live) | Max days (live) |")
        print("|---|--:|--:|--:|--:|--:|--:|")
        for k, g in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            live = [x for x in g if x.get("live") is True]
            med = int(statistics.median([x["days_running"] for x in live])) if live else 0
            mx = max((x["days_running"] for x in live), default=0)
            print(f"| {k} | {len(g)} | {len(live)} | {len(g)-len(live)} | "
                  f"{100*len(live)//len(g)}% | {med or '-'} | {mx or '-'} |")

    print(f"# {os.path.basename(target)} — {len(ads)} unique ads")
    live = [a for a in ads if a.get("live") is True]
    print(f"\nLive: {len(live)} · Inactive: {len(ads)-len(live)} · "
          f"With transcript: {sum(1 for a in ads if a.get('full_transcription'))}")

    block("Funnel", ads, lambda a: a["funnel"])
    niche = [a for a in ads if a["funnel"] in FEATURED]
    if FEATURED:
        block("Vertical (featured funnels)", niche, lambda a: a["vertical"])
        block("Hook family (featured funnels)", niche, lambda a: a["hook"])
    block("Hook family (all)", ads, lambda a: a["hook"])

    json.dump(ads, open(path, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
