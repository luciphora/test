---
name: ad-teardown
description: Survival teardown of a competitor's Meta ad library — which ads have run longest, which were killed, where new money went. Use when Moe asks for a competitor's winning ads, what's working for someone, whether a campaign is still running, or to run or refresh a teardown again.
---

# Ad teardown

Meta publishes no spend or results for commercial ads. The only signals are **survival** — an ad still live has outlived its owner's own culling — and **where new money goes**. Everything here ranks on those two. Scripts live in `ads-research/`; each target in `ads-research/targets/<slug>/`.

## Steps

1. **Scope to one page.** Resolve the target to a numeric Meta `page_id` (Ad Library → "About the advertiser", or the screenshot Moe sends). Never keyword-search — it matches anyone whose copy mentions the name. *Done when* one page_id and the advertiser's name are confirmed.

2. **Check the source and the budget.** Foreplay bills 1 credit per ad returned against a 10,000/month pool shared with the MCP connector. With `FOREPLAY_API_KEY` set (Moe copies it from app.foreplay.co/api-overview), `collect_foreplay.py` checks usage and prints the projected spend before the first paid call. Without a key, probe via the MCP tool `get_user_usage` then `get_brands_ads_by_page_id` with `limit=5`. Not indexed at all → [reference/apify.md](reference/apify.md). *Done when* the right advertiser comes back and Moe has heard the cost of the full pull.

3. **Snapshot before every pull.** If `<target>/ads.json` exists, copy it to `snapshots/ads_<YYYY-MM-DD>.json`. This is the only way a dead ad ever gets a real stop date. *Done when* the copy exists.

4. **Pull and process — one command with a key.** `python run_after_pull.py targets/<slug> --page-id <id>`, adding `--snap <prev-date>` on a refresh. It collects (live set, history, 30-day analytics), then consolidates or overlays, classifies, fetches stills, compiles transcripts, builds and validates the report, stopping at the first failure. Without a key, make the three MCP pulls by hand per [reference/foreplay.md](reference/foreplay.md), `cp` the spilled files into `<target>/pages_<date>/`, and run the same command with `--pages` instead of `--page-id`. *Done when* validation passes: zero unfilled placeholders, zero U+FFFD, zero cards without a still.

5. **Derive the taxonomy — once per target, never imported.** Survey `link_url` for funnels and the first 100 chars of each transcript for openers (`jq … | sort | uniq -c | sort -rn`). Write only what recurs verbatim into `<target>/taxonomy.py` — `VERTICALS`, `HOOKS`, `funnel()`, `FEATURED_FUNNELS` — and re-run step 4. Unclassified stays unclassified. *Done when* the classified share is stated and no hook family exists that isn't in at least two ads.

6. **Write the verdict.** `brief.md` and `report_body.html` are prose; every figure is a `{{PLACEHOLDER}}` that `build_report.py` fills. Never type a number by hand. Open with what changed since the last snapshot, then with what the previous verdict got wrong. *Done when* every figure in the brief also appears in the built report.

7. **Ship.** Publish `report.html` as an Artifact — same file path keeps the URL on refresh; `label` the version. **Share it before anyone else gets the link** — artifacts are private by default; if sharing needs Moe's click, the message says so. Zip `transcripts/ all_transcripts.md transcripts_index.csv brief.md analytics.csv` and send it. Commit code, brief and taxonomy; data, media, transcripts and `report.html` stay gitignored. Delivery routes per destination in [reference/delivery.md](reference/delivery.md). *Done when* the destination has been **read back** — the message, file or page seen where it landed, not a tool's `ok: true` — and `git status` is clean.

## Reading survival

- **Live tenure is sound; dead tenure is censored.** Inactive ads report about one day whatever the truth. Never say how long a dead ad ran unless it died between two snapshots (`died_between` set, `days_at_death_min` real).
- **Longevity says "not killed", not "profitable".** Every report says so.
- **A cluster of deaths at one tenure is a scheduled review**, not attrition. Read it as a decision.
- **New money is the verdict.** A segment given a fresh wave earned another look; a segment skipped in a new wave is one the advertiser stopped believing in. Weigh this above survival percentages.
- **Same script, swapped noun.** When an advertiser templates one hook across verticals, survival differences are about the audience, not the copy. Hunt for this — it is the most transferable thing a library can show.
- **Foreplay's daily active count and its per-ad live flag disagree.** Chart the count for shape; tables use only the flag.
- **One snapshot is a state, two is a delta, three is a trend.** Say which you have.

Report structure, design tokens and the mistakes to check for: [reference/report.md](reference/report.md). Where things go and how to confirm they arrived: [reference/delivery.md](reference/delivery.md).
