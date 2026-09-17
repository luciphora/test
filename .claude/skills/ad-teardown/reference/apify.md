# Apify fallback — when Foreplay hasn't indexed the page

Meta serves 403 to datacenter IPs and `robots.txt` is a blanket disallow, so nothing here can hit the Ad Library directly. Apify supplies the browsers and residential IPs.

**Collector.** `ads-research/collect_apify.py --url "<ad-library-url>" --out targets/<slug> --limit N --active-status ""`. Actor `apify/facebook-ads-scraper` (`JJghSZmShuco4j9gJ`). Needs `APIFY_TOKEN` in the environment — never written to disk, never committed. If Moe pastes a token into chat, use it once and tell him to rotate it.

**Scope with `view_all_page_id=<page_id>` in the URL, never with a search term.** A keyword search for the advertiser's name returned 196 of 200 ads from an agency that name-dropped her. The collector warns when more than one `page_name` comes back; treat that warning as a failed pull.

**Fields nest under `snapshot`.** `ctaText`, `linkUrl`, `body`, `videos`, `images` are inside `item["snapshot"]`; the collector's `_first()` probes both levels. If CTA/domain coverage comes back near zero, that nesting has moved again.

**Then the stages Foreplay would have skipped.**
- `download_creatives.py targets/<slug>` — signed CDN URLs in `raw.json` expire in hours; download the same session as the pull.
- `transcribe_creatives.py targets/<slug>` — faster-whisper `small`, int8, VAD on; ~1 clip/min on 4 CPU cores; resumable; longest-running clips first so an interrupted run still has the winners.
- Frame extraction is PyAV + Pillow. The Playwright-bundled ffmpeg is a stripped build with no H.264 decoder.

**Delivery caps.** Chat upload is 30 MB per file; a folder of mp4s will not fit and zipping doesn't help. Send the longest-running clips renamed `<days>d-<id>.mp4` and say plainly which ones couldn't be sent.
