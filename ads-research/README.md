# ads-research

Pull a competitor's ads out of the Meta Ad Library, rank them by the signals the
library actually exposes, and keep the teardown next to the raw capture.

```bash
pip install playwright && playwright install chromium

python collect_meta_ads.py --query "Metabolic Makeover Academy" --out targets/audreyyadamsfit
python analyze_ads.py targets/audreyyadamsfit
```

`collect_meta_ads.py` writes `ads.json`, `ads.csv` and a screenshot per card into the
target directory. `analyze_ads.py` reads `ads.json` and writes `analysis.md` beside it.

## Run it locally, not in CI

Meta serves `403` to datacenter IPs and `facebook.com/robots.txt` is `Disallow: /`.
The collector runs headed by default because a visible window is far less likely to be
blocked; `--headless` exists but expect it to fail more often. If a run comes back
empty, open the library URL by hand first and confirm the page renders for you.

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
