#!/usr/bin/env python3
"""Pull one advertiser's Meta ads from the Foreplay public API into pages_<date>/.

    export FOREPLAY_API_KEY=...          # app.foreplay.co/api-overview
    python collect_foreplay.py 265406025348448 targets/danielilesfb            # first pull
    python collect_foreplay.py 265406025348448 targets/danielilesfb --since 2026-09-01   # refresh

Writes the same {metadata, data} page files the MCP tool spills, so
run_after_pull.py consumes them unchanged. Three passes, same as the skill:
newest-first history (cursor-paginated), the complete live set, and the
trailing 30 days of daily active counts. Foreplay bills 1 credit per ad returned,
so the projected spend is printed and confirmed before the first paid call.
"""
import argparse, json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error

BASE = "https://public.api.foreplay.co"

def get(path, key, **params):
    q = {k: v for k, v in params.items() if v not in (None, "", [])}
    req = urllib.request.Request(f"{BASE}{path}?{urllib.parse.urlencode(q, doseq=True)}",
                                 headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt); continue
            sys.exit(f"HTTP {e.code} on {path}: {body}")
        except urllib.error.URLError as e:
            if attempt < 3: time.sleep(2 ** attempt); continue
            sys.exit(f"network error on {path}: {e}")

def paginate(key, out_dir, stem, **params):
    """Follow the cursor until it is null; verify no id repeats across pages."""
    seen, page, cursor, total = set(), 1, None, 0
    while True:
        doc = get("/api/brand/getAdsByPageId", key, limit=250, cursor=cursor, **params)
        data = doc.get("data") or []
        dup = [a["id"] for a in data if a["id"] in seen]
        if dup:
            sys.exit(f"{stem}: {len(dup)} ids repeated on page {page} — cursor is not advancing "
                     f"(this happens under order=longest_running; use a date order)")
        seen.update(a["id"] for a in data); total += len(data)
        json.dump(doc, open(os.path.join(out_dir, f"{stem}_p{page}.json"), "w"))
        cursor = (doc.get("metadata") or {}).get("cursor")
        print(f"  {stem} p{page}: {len(data)} ads  (cumulative {total})", flush=True)
        if not cursor or not data: return total
        page += 1

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page_id"); ap.add_argument("target")
    ap.add_argument("--since", help="only history started on/after this date (refresh); omit for the full library")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="snapshot date for the pages_ dir")
    ap.add_argument("--yes", action="store_true", help="skip the credit confirmation")
    ap.add_argument("--no-analytics", action="store_true")
    a = ap.parse_args()
    key = os.environ.get("FOREPLAY_API_KEY")
    if not key: sys.exit("FOREPLAY_API_KEY is not set — copy it from https://app.foreplay.co/api-overview")

    usage = (get("/api/usage", key).get("data") or {})
    remaining, total = usage.get("remaining_credits"), usage.get("total_credits")
    print(f"credits: {remaining} of {total} remaining (window ends {str(usage.get('end_date',''))[:10]})")

    # Size the job with one free-ish probe: analytics tells us the live count; history is unknown until paged.
    est_live = None
    if not a.no_analytics:
        end = a.date; start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=29)).isoformat()
        an = get("/api/brand/analytics", key, id=a.page_id, start_date=start, end_date=end)
        rows = an.get("data") or []
        if rows:
            est_live = rows[0].get("active_count"); est_total = rows[0].get("active_count", 0) + rows[0].get("inactive_count", 0)
            print(f"analytics: {len(rows)} days · ~{est_live} active / ~{est_total} indexed on {rows[0].get('date')}")
        out_dir = os.path.join(a.target, f"pages_{a.date.replace('-', '')[4:]}"); os.makedirs(out_dir, exist_ok=True)
        json.dump(an, open(os.path.join(out_dir, "analytics.json"), "w"))
    else:
        out_dir = os.path.join(a.target, f"pages_{a.date.replace('-', '')[4:]}"); os.makedirs(out_dir, exist_ok=True)

    est = (est_live or 250) + (0 if a.since else (est_total if est_live is not None else 2000))
    print(f"projected spend: roughly {est:,} credits ({'live set + history since ' + a.since if a.since else 'live set + full history'})")
    if not a.yes:
        if not sys.stdin.isatty(): sys.exit("non-interactive: re-run with --yes to spend the credits")
        if input("continue? [y/N] ").strip().lower() != "y": sys.exit("aborted, nothing spent")

    print("pulling live set…"); n_live = paginate(key, out_dir, "live", page_id=a.page_id, order="newest", live="true")
    print("pulling history…");  n_hist = paginate(key, out_dir, "new", page_id=a.page_id, order="newest", start_date=a.since)
    print(f"\ndone → {out_dir}/  live={n_live} history={n_hist}")
    print(f"next: python run_after_pull.py {a.target} --pages {out_dir}"
          + (f" --snap <previous-date> --now {a.date}" if a.since else ""))

if __name__ == "__main__":
    main()
