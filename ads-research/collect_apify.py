"""Collect ads for one advertiser via the Apify Facebook Ads Library scraper.

Runs `apify/facebook-ads-scraper` (actor JJghSZmShuco4j9gJ) and normalizes its
dataset into the same `ads.json` shape `analyze_ads.py` consumes, so either
collector can feed the analysis.

    export APIFY_TOKEN=...
    python collect_apify.py --query "Metabolic Makeover Academy" --out targets/audreyyadamsfit
    python analyze_ads.py targets/audreyyadamsfit

Unlike `collect_meta_ads.py`, this runs anywhere: Apify supplies the browsers
and residential IPs, so Meta's datacenter block does not apply.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ACTOR = "apify~facebook-ads-scraper"
API = "https://api.apify.com/v2"

LIBRARY_URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status={active_status}&ad_type=all&country={country}"
    "&q={query}&search_type=keyword_unordered&media_type=all"
)

# The actor's field names have drifted across builds, so read each value by
# probing the spellings seen in the wild rather than pinning one.
FIELD_ALIASES = {
    "library_id": ("adArchiveID", "ad_archive_id", "adArchiveId", "adId", "id"),
    "start": ("startDate", "start_date", "startDateFormatted"),
    "end": ("endDate", "end_date"),
    "active": ("isActive", "is_active", "activeStatus"),
    "page": ("pageName", "page_name", "pageID", "page_id"),
    "platforms": ("publisherPlatform", "publisher_platform", "publisherPlatforms"),
    "cta": ("ctaText", "cta_text", "ctaType", "cta_type"),
    "link": ("linkUrl", "link_url", "link"),
}
# The live actor nests cta/link inside `snapshot`; older builds put them at the
# top level. Probe both rather than picking one.
NESTED = ("snapshot",)
BODY_PATHS = (
    ("snapshot", "body", "text"),
    ("snapshot", "body"),
    ("adText",),
    ("text",),
)
TITLE_PATHS = (("snapshot", "title"), ("title",))


def _first(d: dict, keys: tuple[str, ...]):
    scopes = [d] + [d[n] for n in NESTED if isinstance(d.get(n), dict)]
    for scope in scopes:
        for k in keys:
            if scope.get(k) not in (None, ""):
                return scope[k]
    return None


def _dig(d, path: tuple[str, ...]):
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur if cur not in (None, "") else None


def _as_date(value) -> str | None:
    """Actor emits epoch seconds on some builds, ISO strings on others."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    text = str(value)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%b %d, %Y"):
        try:
            return datetime.strptime(text[: len(fmt) + 6], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _api(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    url = f"{API}/{path}{'&' if '?' in path else '?'}token={urllib.parse.quote(token)}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read() or b"{}")


def run_actor(token: str, url: str, limit: int, active_status: str,
              newer_than: str | None, wait_s: int) -> list[dict]:
    payload = {
        "startUrls": [{"url": url}],
        "resultsLimit": limit,
        "isDetailsPerAd": True,
        "activeStatus": active_status,
    }
    if newer_than:
        payload["onlyAdsNewerThan"] = newer_than

    run = _api("POST", f"acts/{ACTOR}/runs", token, payload)["data"]
    run_id, dataset_id = run["id"], run["defaultDatasetId"]
    print(f"Apify run {run_id} started; polling (timeout {wait_s}s)...")

    deadline = time.monotonic() + wait_s
    status = run["status"]
    while status in ("READY", "RUNNING") and time.monotonic() < deadline:
        time.sleep(10)
        status = _api("GET", f"actor-runs/{run_id}", token)["data"]["status"]
        print(f"  status: {status}")

    if status != "SUCCEEDED":
        print(f"Run ended as {status}; collecting whatever the dataset holds.",
              file=sys.stderr)

    items_url = f"{API}/datasets/{dataset_id}/items?clean=true&format=json&token={urllib.parse.quote(token)}"
    with urllib.request.urlopen(items_url, timeout=120) as resp:
        return json.loads(resp.read() or b"[]")


def normalize(items: list[dict]) -> list[dict]:
    ads, unmapped = [], 0
    for item in items:
        library_id = _first(item, FIELD_ALIASES["library_id"])
        if not library_id:
            unmapped += 1
            continue
        started = _as_date(_first(item, FIELD_ALIASES["start"]))
        days = (date.today() - date.fromisoformat(started)).days if started else None

        body = next((v for p in BODY_PATHS if (v := _dig(item, p))), "") or ""
        title = next((v for p in TITLE_PATHS if (v := _dig(item, p))), "") or ""
        platforms = _first(item, FIELD_ALIASES["platforms"]) or []
        if isinstance(platforms, str):
            platforms = [platforms]

        active = _first(item, FIELD_ALIASES["active"])
        link = _first(item, FIELD_ALIASES["link"])
        # analyze_ads.py reads `body` for hooks, so keep title and text together.
        combined = "\n".join(part for part in (title, body) if part)

        ads.append({
            "library_id": str(library_id),
            "page_name": _first(item, FIELD_ALIASES["page"]),
            "page_id": item.get("pageID") or item.get("pageId"),
            "started_on": started,
            "days_running": days,
            "status": "Active" if active in (True, "active") else "Inactive",
            "platforms": list(platforms),
            "body": combined,
            "cta": _first(item, FIELD_ALIASES["cta"]),
            "landing_domain": urllib.parse.urlparse(link).netloc if link else None,
            "media": "video" if _dig(item, ("snapshot", "videos")) else "image",
            "screenshot": None,
            "raw_text": combined,
        })

    if unmapped:
        print(f"Skipped {unmapped} dataset rows with no recognizable ad id — "
              "the actor's schema may have changed; check FIELD_ALIASES.",
              file=sys.stderr)

    unique: dict[str, dict] = {}
    for ad in ads:
        unique.setdefault(ad["library_id"], ad)
    return list(unique.values())


def write(ads: list[dict], out: Path) -> None:
    (out / "ads.json").write_text(json.dumps(ads, indent=2))
    with (out / "ads.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["library_id", "page_name", "started_on", "days_running", "status",
                    "media", "cta", "landing_domain", "first_line"])
        for a in sorted(ads, key=lambda x: x["days_running"] or 0, reverse=True):
            first = next((ln for ln in a["body"].split("\n") if len(ln) > 25), "")
            w.writerow([a["library_id"], a["page_name"], a["started_on"],
                        a["days_running"], a["status"], a["media"], a["cta"],
                        a["landing_domain"], first])
    print(f"Wrote {len(ads)} ads to {out}/ads.json and {out}/ads.csv")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--query", help="keyword searched in the Ad Library")
    src.add_argument("--url", help="a full Ad Library URL, e.g. a view_all_page_id link")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--country", default="US")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--active-status", default="active", choices=["", "active", "inactive"])
    ap.add_argument("--newer-than", help="ISO date; skip ads that started before it")
    ap.add_argument("--wait", type=int, default=900, help="seconds to wait for the run")
    args = ap.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN is not set. Create a token at "
                 "https://console.apify.com/settings/integrations and export it.")

    url = args.url or LIBRARY_URL.format(
        active_status=args.active_status or "all",
        country=args.country,
        query=urllib.parse.quote(args.query),
    )
    args.out.mkdir(parents=True, exist_ok=True)
    items = run_actor(token, url, args.limit, args.active_status,
                      args.newer_than, args.wait)
    print(f"Dataset returned {len(items)} rows.")
    (args.out / "raw.json").write_text(json.dumps(items, indent=2))

    ads = normalize(items)
    pages = Counter(a["page_name"] for a in ads)
    print("Advertisers in this pull:")
    for name, n in pages.most_common(10):
        print(f"  {n:>4}  {name}")
    if len(pages) > 1:
        print("More than one advertiser came back — a keyword search matches anyone "
              "whose copy mentions the term. Re-run with --url and a "
              "view_all_page_id link to scope it to one page.", file=sys.stderr)
    write(ads, args.out)


if __name__ == "__main__":
    main()
