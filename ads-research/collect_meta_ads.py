"""Collect ads for one advertiser from the Meta Ad Library.

Runs a real browser against https://www.facebook.com/ads/library/. Meta blocks
datacenter IPs, so this is meant to run on your own machine, not in CI.

    pip install playwright && playwright install chromium
    python collect_meta_ads.py --query "Metabolic Makeover Academy" --out targets/audreyyadamsfit

Writes:
    <out>/ads.json          one record per ad card
    <out>/ads.csv           flat table for sorting in a spreadsheet
    <out>/shots/ad-NNN.png  screenshot of each card
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

LIBRARY_URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status={active_status}&ad_type=all&country={country}"
    "&q={query}&search_type=keyword_unordered&media_type=all"
)

# "Library ID: 1234567890" / "Started running on Jan 5, 2026"
RE_LIBRARY_ID = re.compile(r"Library ID:\s*(\d+)")
RE_STARTED = re.compile(r"Started running on ([A-Z][a-z]{2} \d{1,2}, \d{4})")
RE_TOTAL = re.compile(r"~?([\d,]+)\s+results")


@dataclass
class Ad:
    library_id: str
    started_on: str | None
    days_running: int | None
    status: str | None
    platforms: list[str] = field(default_factory=list)
    body: str = ""
    cta: str | None = None
    landing_domain: str | None = None
    media: str | None = None
    screenshot: str | None = None
    raw_text: str = ""


def _parse_card(text: str) -> dict:
    library_id = RE_LIBRARY_ID.search(text)
    started = RE_STARTED.search(text)
    started_on = None
    days = None
    if started:
        started_on = datetime.strptime(started.group(1), "%b %d, %Y").date()
        days = (date.today() - started_on).days
        started_on = started_on.isoformat()
    return {
        "library_id": library_id.group(1) if library_id else "",
        "started_on": started_on,
        "days_running": days,
        "status": "Active" if "Active" in text.split("\n")[0:3] else None,
    }


def collect(query: str, out: Path, country: str, active_status: str,
            max_scrolls: int, headless: bool) -> list[Ad]:
    shots = out / "shots"
    shots.mkdir(parents=True, exist_ok=True)

    url = LIBRARY_URL.format(
        active_status=active_status, country=country, query=query.replace(" ", "%20")
    )

    ads: list[Ad] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_context(viewport={"width": 1440, "height": 1200}).new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(6_000)

        body = page.inner_text("body")
        total = RE_TOTAL.search(body)
        print(f"Ad Library reports: {total.group(0) if total else 'result count not found'}")

        # The result grid is virtualised; scroll until it stops growing.
        seen = 0
        for i in range(max_scrolls):
            page.mouse.wheel(0, 4_000)
            page.wait_for_timeout(2_500)
            count = page.locator("text=Library ID:").count()
            if count == seen:
                break
            seen = count
            print(f"  scroll {i + 1}: {count} cards loaded")

        cards = page.locator("div:has(> div > div:text-matches('Library ID:'))")
        n = cards.count()
        print(f"Capturing {n} cards...")
        for i in range(n):
            card = cards.nth(i)
            try:
                text = card.inner_text(timeout=5_000)
            except Exception:
                continue
            if "Library ID:" not in text:
                continue
            parsed = _parse_card(text)
            if not parsed["library_id"]:
                continue
            shot = shots / f"ad-{i:03d}-{parsed['library_id']}.png"
            try:
                card.screenshot(path=str(shot))
            except Exception:
                shot = None
            ads.append(
                Ad(
                    **parsed,
                    body=text,
                    screenshot=str(shot.relative_to(out)) if shot else None,
                    raw_text=text,
                )
            )
        browser.close()

    # De-duplicate on library id, keeping the first capture.
    unique: dict[str, Ad] = {}
    for ad in ads:
        unique.setdefault(ad.library_id, ad)
    return list(unique.values())


def write(ads: list[Ad], out: Path) -> None:
    (out / "ads.json").write_text(json.dumps([asdict(a) for a in ads], indent=2))
    with (out / "ads.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["library_id", "started_on", "days_running", "status", "screenshot", "first_line"])
        for a in sorted(ads, key=lambda x: x.days_running or 0, reverse=True):
            first = next((ln for ln in a.body.split("\n") if len(ln) > 25), "")
            w.writerow([a.library_id, a.started_on, a.days_running, a.status, a.screenshot, first])
    print(f"Wrote {len(ads)} ads to {out}/ads.json and {out}/ads.csv")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True, help="advertiser name or keyword")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--country", default="US")
    ap.add_argument("--active-status", default="active", choices=["active", "inactive", "all"])
    ap.add_argument("--max-scrolls", type=int, default=40)
    ap.add_argument("--headless", action="store_true",
                    help="off by default: a visible window is far less likely to be blocked")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    ads = collect(args.query, args.out, args.country, args.active_status,
                  args.max_scrolls, args.headless)
    write(ads, args.out)


if __name__ == "__main__":
    main()
