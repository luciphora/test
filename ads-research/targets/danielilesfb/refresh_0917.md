# Viral Coach (Daniel Iles) — live-set refresh, 17 Sep 2026

> **Superseded by a second pass the same day.** This page was written from ONE live pull
> returning 225 ads. Three further pulls that day returned 159, 134 and 225 — a different
> partial subset each time. The union is **286**, and pull four added only one ad, so it has
> converged. Every figure below that cites 225 is a single-pull reading; the corrected
> numbers are in the artifact and in `ads.json`, which now holds the union plus 250
> transcripts (was 96). The finding this page establishes — that absence from a pull is not
> evidence of death — is unchanged, and is what the second pass confirms.

Page `265406025348448`. Previous snapshot: 9 Sep 2026. This pass pulled the live set
only (225 ads, 1 credit each) — not the full history — because the question was which
ads are still running.

## Headline finding: the offer moved from a guarantee to a proof number

| Offer family | Live ads | Oldest | Newest |
|---|---:|---:|---:|
| "Our avg clients get 15.5m views" | **197** | 249d | 5d |
| "1M / 10M views… or you don't pay" | 19 | 422d | 1d |
| "We fund your first campaign" | 3 | 100d | 98d |
| no headline | 5 | 309d | — |
| "Effortless Social Media Success" | 1 | 404d | — |

**197 of 225 live ads — 88% — carry one headline.** The guarantee that the business was
built on is not dead: he launched a new one yesterday. It is simply outweighed, running
at roughly a tenth of the proof-number's volume.

The proof-number launches cluster hard and recently:

```
2026-01    5
2026-02    2
2026-06   41
2026-07   17
2026-08   23
2026-09  109     <- 17 days
```

109 launches this month against 23 in all of August. Whatever he is doing, he committed
to it in the last two weeks.

The four oldest ads in the account are all guarantee ads — 422d, 411d, 356d, 321d — and
all four are still live. So the guarantee is what *endures*; the proof number is what he
is *spending on*. Those are two different signals and worth not collapsing.

## What is still running from our 9 Sep snapshot

| | count |
|---|---:|
| live in the 9 Sep snapshot | 79 |
| of those, in today's live set | **25** |
| of those, absent from today's live set | 54 |
| live today, present in ads.json but flagged dead | 100 |
| live today, absent from ads.json entirely | 100 |
| **live today, total** | **225** |

## The 9 Sep snapshot's death data was wrong, and here is the proof

`refresh_foreplay.py` infers a stop date this way: an ad that was live in the previous
snapshot and is absent from today's live set died in between, recorded as `died_between`.
That inference assumes the live-set pull is complete.

It is not. **100 of the 266 ads carrying a `died_between` window are running right now.**

The brand analytics for the last eight days show why:

```
2026-09-09      0 active      <- the day we took the snapshot
2026-09-10    160
2026-09-11     44
2026-09-12    168
2026-09-13    168
2026-09-14    169
2026-09-15    150
2026-09-16    180
```

An advertiser does not go 0 → 160 → 44 → 168. That is collection coverage varying by day,
and 9 Sep — our snapshot date — reads zero. The pull we built the survival analysis on
was taken on the worst day in the window.

**The rule this establishes:** `live: true` is trustworthy — an ad returned by the live
query is running. `live: false` is not: it conflates "stopped" with "not returned by that
day's pull." Absence is not evidence of death.

This also narrows what I told you earlier today about the home-services transcripts. The
LIVE/stopped split there does come from the live-set query rather than the null
`is_active` field, which is what I said — but I presented it as sound in both directions.
It is sound in one. The 112 marked live there are live; the 218 marked stopped are
"not returned that day," which is a weaker claim than the file's wording implies.

## What was changed in the data

- `ads.json` — cleared the 100 `died_between` windows refuted by today's live set, marked
  those records `refuted_death_0917`, and refreshed `live` / `days_running` on the 125 ads
  we already held that are live today. 166 `died_between` windows remain, and by the rule
  above they are suspect by the same mechanism — they have simply not been refuted yet.
- `pages_0917/live_raw.json` — the raw pull, 225 records.
- Nothing was demoted to dead. 54 previously-live ads are absent from today's set and
  stay flagged live, because absence proves nothing.

## What this refresh does not cover

- **100 live ads are absent from our dataset** and have no transcript. Pulling them with
  transcription costs ~1 credit each.
- **129 of the 225 live ads have no transcript** in our set at all.
- The history was not re-pulled, so `2,116 ads scraped` is still the 9 Sep figure and is
  certainly low.
- Credits: 2,781 of 10,000 remaining, window ends 25 Sep. This pass cost ~233.
