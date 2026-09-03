# Foreplay MCP — what the tool descriptions don't tell you

**Cost.** 1 credit per ad returned, every call, including re-pulls of ads you already have. Empty responses are free. `get_user_usage` is free — call it first and quote the projected spend to Moe before a pull over ~500 credits. A ~2,000-ad library costs ~2,900 for the first pull and ~500 per refresh.

**Pagination only works under a date order.** The cursor is a base64 `{ts, id}` pair. `order=newest` or `oldest` paginate cleanly (verified: zero overlap across 8 pages). `order=longest_running` returned 145 duplicate ids in 249 between consecutive pages. Compute longevity yourself from `running_duration.days`.

**Three pulls per snapshot.**
1. `order=newest, limit=250`, follow `cursor` until null — the full library back to your chosen horizon (all history for a first pull; `start_date=<last snapshot>` for a refresh).
2. `live=true, order=newest, limit=250` — the complete live set regardless of age. This is what makes "still running" answerable.
3. `get_brands_analytics(id, start_date, end_date)` — max 30-day window (406 otherwise), 1 credit per row. Daily `active_count` for the trend chart.

**Fields to request** (`fields=[…]`): `id ad_id live started_running running_duration display_format headline description link_url cta_type video thumbnail image cards video_duration full_transcription niches market_target publisher_platform foreplay_url`. Skip `timestamped_transcription` and `last_checked` (always null). `transcriptionStatus` is never returned even when transcripts exist.

**Large results spill to disk.** Over the token cap, the tool writes the JSON to `…/tool-results/mcp-Foreplay-…txt` and returns the path. `cp` it into the target's `pages_<date>/` and work with `jq`; never Read it. A 250-ad page with transcripts is ~700 KB — it will always spill, which is what you want.

**Stills live in different fields.** Video → `thumbnail`. Image ad → `image`. Carousel/DCO → inside `cards[]`. Some videos have no still at all — `fetch_stills.py` frame-grabs those with PyAV. `r2.foreplay.co` is fetchable from the container.

**`get_ad_by_id` returns `data: null`** for ids that `get_brands_ads_by_page_id` just returned. Don't rely on it; re-query the page with a filter.

**`running_duration` is only real for live ads.** 98% of inactive ads report exactly 1 day. That is a data artifact, not a stop date. The overlay in `refresh_foreplay.py` is the only source of real dead-ad tenure.

**Transcripts contain U+FFFD** where a byte was lost — always an apostrophe (`don�t`). `refresh_foreplay.py`/`consolidate_foreplay.py` should repair it; `validate_report.py` refuses to ship if any remain, and the Artifact host rejects the file outright.

**The `description` field is near-identical across hundreds of ads** (one long body copy reused). It's fine to pull but useless to classify on; classify on `full_transcription` openers and `link_url`.
