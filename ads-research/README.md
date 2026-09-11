# ads-research

Pull a competitor's ads out of the Meta Ad Library, rank them by the signals the
library actually exposes, and keep the teardown next to the raw capture.

Two collectors write the same `ads.json`, so either can feed the analysis.

**Apify (default — runs anywhere).** Apify supplies the browsers and residential IPs,
so Meta's datacenter block does not apply and this works from CI or a cloud session.

```bash
export APIFY_TOKEN=...   # console.apify.com/settings/integrations

python collect_apify.py --query "Metabolic Makeover Academy" --out targets/audreyyadamsfit
python analyze_ads.py targets/audreyyadamsfit
```

It drives `apify/facebook-ads-scraper`. Pass `--url` instead of `--query` to use a
`view_all_page_id` link, which is exact where a keyword search is fuzzy. The actor's
field names have drifted across builds, so the normalizer probes the known spellings
(`FIELD_ALIASES` at the top of the file) and warns on rows it cannot map.

**Playwright (fallback — your own machine only).** No Apify account needed, and it
captures a screenshot per card, which the Apify path does not.

```bash
pip install playwright && playwright install chromium
python collect_meta_ads.py --query "Metabolic Makeover Academy" --out targets/audreyyadamsfit
```

Meta serves `403` to datacenter IPs and `facebook.com/robots.txt` is `Disallow: /`, so
this one only works from a residential connection. It runs headed by default because a
visible window is far less likely to be blocked; `--headless` exists but expect it to
fail more often. If a run comes back empty, open the library URL by hand first and
confirm the page renders for you.

## Creatives and transcripts

The three steps above give you copy and metadata. These give you the assets and
what is actually said out loud in them.

```bash
python download_creatives.py targets/audreyyadamsfit
python transcribe_creatives.py targets/audreyyadamsfit --model small --workers 4
python analyze_creatives.py targets/audreyyadamsfit
python compile_transcripts.py targets/audreyyadamsfit
```

The first three give you assets and an aggregate report. `compile_transcripts.py`
gives you the raw, per-ad transcripts in a form a human can actually use — the
`.txt` files in `transcripts/` are named by Ad Library ID and mean nothing on
their own. It cross-references `ads.json` and writes:

- `transcripts_index.csv` — one row per video: days running, duration, CTA,
  landing domain, opening line, and which files it maps to. Sort it in a
  spreadsheet.
- `all_transcripts.md` — every transcript in one document, longest-running
  first, each preceded by its metadata. Scan or Ctrl-F instead of opening 98
  files one at a time.

Everything lands in `targets/<name>/creatives/`:

```
video/<library_id>.mp4        one per video ad
image/<library_id>.jpg        one per static ad
transcripts/<library_id>.txt  plain text, one per video
transcripts.json              text + hook + duration + wpm per clip
index.csv                     what was downloaded, and how big
creative_analysis.md          the report
```

Meta's CDN URLs are signed and expire within days, so download against a fresh
`raw.json` — a 403 here means the pull is stale, not that the script is broken.
Transcription is CPU-only faster-whisper; `small` is the sweet spot for
ad-length clips at roughly a clip a minute on four cores. It is resumable:
already-transcribed clips are skipped, so a killed run costs nothing.

`analyze_creatives.py` reuses the same `HOOK_PATTERNS` taxonomy as
`analyze_ads.py`, so spoken hooks and written hooks are scored alike and can be
compared directly. Its most useful output is the claims table: a theme that
appears in the audio but never in the ad text is one a copy-only teardown
misses entirely.

Creatives are gitignored — they are third-party assets and run to gigabytes.

## What "winning" means here

The Ad Library publishes no spend, impressions or conversions. Two things it does
expose stand in:

- **Longevity.** Advertisers switch off ads that lose money. Something still running
  after 60+ days is being paid for on purpose. `analyze_ads.py` shortlists on this.
- **Duplication.** The same creative appearing as many near-identical cards means
  budget is deliberately split across it.

Neither is a measurement, and a long-running ad can equally be one nobody bothered to
turn off. The way to firm it up is two captures a few weeks apart — run the collector
again into the same target and keep both `ads.json` files. What survives both is the
shortlist worth modelling.

## Adding a target

One directory per advertiser under `targets/`, with a `brief.md` covering the offer,
funnel and angles their own public copy commits to. Written before the pull, it gives
the ad data something to confirm or contradict; see
`targets/audreyyadamsfit/brief.md`.

The niche hook taxonomy lives in `HOOK_PATTERNS` at the top of `analyze_ads.py` and is
currently tuned for women's fat-loss and metabolism coaching. Edit it for other
verticals — the analysis is only as good as that table.

## Use

Research and inspiration. Model structure, angle and offer mechanics; do not lift copy
or creative.

## Running a teardown

The procedure lives in the project skill at `.claude/skills/ad-teardown/` — ask for a
competitor's winning ads, or to refresh an existing target, and it fires. The post-pull
half is one command:

    python run_after_pull.py targets/<slug> --pages targets/<slug>/pages_<date> [--snap <prev> --now <today>]

Each target keeps its own `taxonomy.py` (derived from that advertiser's ads, never copied),
`build_report.py` + `report_body.html` (its prose), and `snapshots.json` (the dates it has
been pulled). Raw pulls, media and transcripts are gitignored.
