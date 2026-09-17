"""Download every creative referenced by a target's raw Apify dataset.

    python download_creatives.py targets/audreyyadamsfit

Writes creatives/video/<library_id>.mp4, creatives/image/<library_id>.jpg and
creatives/index.csv. Meta's CDN URLs are signed and expire within days, so run
this against a fresh raw.json — a 403 here means the pull is stale, not broken.
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def pick_media(item: dict, prefer_hd: bool) -> tuple[str, str] | tuple[None, None]:
    """Return (kind, url) for the ad's single creative, or (None, None)."""
    snap = item.get("snapshot") or {}
    videos = snap.get("videos") or []
    if videos:
        v = videos[0]
        order = ("videoHdUrl", "videoSdUrl") if prefer_hd else ("videoSdUrl", "videoHdUrl")
        for key in order:
            if v.get(key):
                return "video", v[key]
    images = snap.get("images") or []
    if images:
        i = images[0]
        for key in ("originalImageUrl", "resizedImageUrl", "watermarkedResizedImageUrl"):
            if i.get(key):
                return "image", i[key]
    return None, None


def fetch(url: str, dest: Path) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return True, "cached"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as resp:
            dest.write_bytes(resp.read())
        return True, f"{dest.stat().st_size // 1024} KB"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - report whatever the network did
        return False, type(e).__name__


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    ap.add_argument("--sd", action="store_true", help="prefer SD video (smaller, faster)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    items = json.loads((args.target / "raw.json").read_text())
    root = args.target / "creatives"
    (root / "video").mkdir(parents=True, exist_ok=True)
    (root / "image").mkdir(parents=True, exist_ok=True)

    jobs, skipped = [], 0
    for item in items:
        lib = item.get("adArchiveID") or item.get("ad_archive_id")
        kind, url = pick_media(item, prefer_hd=not args.sd)
        if not lib or not url:
            skipped += 1
            continue
        ext = "mp4" if kind == "video" else "jpg"
        jobs.append((str(lib), kind, url, root / kind / f"{lib}.{ext}"))

    print(f"{len(jobs)} creatives to fetch ({skipped} ads had no media URL)")

    rows, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(lambda j: fetch(j[2], j[3]), jobs)
        for (lib, kind, url, dest), (ok, note) in zip(jobs, results):
            if ok:
                rows.append({"library_id": lib, "kind": kind,
                             "file": str(dest.relative_to(root)),
                             "bytes": dest.stat().st_size})
            else:
                failures.append((lib, note))

    with (root / "index.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["library_id", "kind", "file", "bytes"])
        w.writeheader()
        w.writerows(rows)

    total_mb = sum(r["bytes"] for r in rows) / 1e6
    print(f"Downloaded {len(rows)} files ({total_mb:.0f} MB) -> {root}")
    if failures:
        print(f"{len(failures)} failed:")
        for lib, note in failures[:10]:
            print(f"  {lib}: {note}")


if __name__ == "__main__":
    main()
