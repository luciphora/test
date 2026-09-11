# Ads targeting service-based businesses — market scan

Foreplay discovery + per-brand pulls · **10 Sep 2026** · **409 live ads, 9 advertisers, 194 transcripts**
Every advertiser here *sells to* service businesses (agencies, automation, marketing-for-practices).

---

## What this is, and what it isn't

**One snapshot.** For the Iles teardown I had four, so I could report what he killed and when. Here I
have today only — so this ranks by **how long an ad has already been running**, which is real, and
says nothing about kill rates, which I can't see.

I pulled **live ads only**. Any "survival %" you compute off this file will read 100% and mean nothing.
Tenure is the metric.

---

## The ten advertisers

| Advertiser | Live ads | Longest | Median | Sells |
|---|--:|--:|--:|---|
| *(fb.me, golf)* | 32 | **516d** | 13d | Golf-coaching client acquisition |
| foreverbooked.com | 25 | 348d | 23d | Med spa marketing, in-house model |
| nonstopautomation.com | 127 | 343d | 21d | AI/automation for home services |
| growwithclover.com | 21 | 317d | 8d | Home-service business coaching |
| authenticadvisorysystems.com | 5 | 307d | **300d** | Financial advisors *(Malay-language)* |
| homeserviceaccelerator.com | 97 | 287d | 2d | Contractor/roofing marketing |
| patientengine.co | 35 | 146d | 7d | Aesthetics patient acquisition |
| mrmedspa.com | 67 | 121d | 45d | Med spa patient acquisition |

**Two shapes of advertiser.** Nonstop Automation and Home Service Accelerator run enormous books
(127 and 97 live) with 2–21 day medians — high-volume testers, like Iles. Authentic Advisory and
Mr Med Spa run small books with high medians (300d and 45d) — they found something and left it on.
Copy the second group's *ads*; copy the first group's *process*.

---

## Hook families, ranked by median tenure

Derived from these 194 transcripts, not imported.

| Hook family | Ads | Median | Max |
|---|--:|--:|--:|
| **Not-what-you-think reframe** | 3 | **146d** | 147d |
| **Two-types-of-owner split** | 2 | 111d | 121d |
| **Anti-discount** | 4 | 80d | 121d |
| **Slow-month diagnostic** | 10 | 72d | 121d |
| Platform-change news | 6 | 50d | 121d |
| Recorded call | 7 | 34d | 91d |
| Named-client case study | 8 | 31d | 161d |
| Mechanism walkthrough | 21 | 30d | 151d |
| **Guarantee** | 3 | **7d** | 65d |
| AI / automation demo | 14 | 6d | 151d |

Small n on the top rows — three ads is a hint, not a law. But the bottom row isn't:
**the guarantee hook has the lowest median in this cohort**, exactly as it did in Iles's library,
where it went to zero of 26 inside the medical niche. Two independent corpora, same result.

---

## The four openers worth stealing

**1. "Your lead problem isn't what you think it is."** *(147d — the longest-running English opener with
a transcript)*
> "Sacramento Home Service Business Owners, your lead problem isn't what you think it is. You don't
> need more leads…"

Geo-named, then a denial of the thing they came for. It refuses the obvious sale before making one.

**2. The two-types split.** *(121d)*
> "There are two types of med spa owners. The ones who get new patients predictably and on-demand,
> and those at the mercy of…"

Forces self-identification in one sentence. The listener sorts themselves before any claim is made.

**3. Anti-discount.** *(121d)*
> "Med Spas, you don't have to run discount promos or limited-time specials to get new patients."

Attacks the prospect's current tactic rather than their competence — the same move that carried Iles's
best med spa ads. Cross-target confirmation.

**4. Slow-month diagnostic.** *(72d median, 10 ads — the most-used of the durable families)*
> "If you're having a slower month, the first thing to check is…"

Conditional entry. Only speaks to people already in pain, which is why it survives.

---

## Where this cohort differs from Iles

- **He sells a guarantee; they sell a mechanism.** 35 of 194 transcripts classify as automation or
  walkthrough demos. Iles's library leads with "1M views or you don't pay" — a promise. Only one ad
  in this entire cohort uses "or we work for free," and it's at 55 days.
- **They demo the product on camera.** Screen-recorded funnel walkthroughs, AI voice agents answering
  a call, Angi/Yelp integrations. Nothing in Iles's 2,116 ads does this.
- **Nobody here has an evergreen backbone the way he did.** His top ad ran 408 days before he killed it
  last week; the best here is 516 days and still up, but it's a single outlier with no transcript.

---

## Limits — read before quoting

- **No spend or conversion data exists.** Tenure says "not killed," never "profitable."
- **One snapshot.** No kill rates, no died-between windows, no trend. Re-pull in two weeks and the
  deltas become real.
- **Discovery search can't be ranked.** Foreplay's `/discovery` index returns `running_duration` as
  null or as a flat constant echoing the filter floor. Every number above comes from per-brand pulls,
  where tenure is genuine. Anything you see ranked straight out of discovery is not measuring what it
  claims to.
- **Coverage is not the whole market.** Nine advertisers found by four text queries. There is no niche
  filter that works — Foreplay's "service business" tag returns zero brands.
- **194 of 409 ads have transcripts**; 80 of those classified into 11 families. The rest are one-offs.
- **Four ads are in Malay** (Authentic Advisory Systems, Malaysian market). Their 300-day median is
  real but the market isn't yours.
- ASR is rough: "vet spa" is med spa, "MedSpar" is med spa.

---

## What to do

1. **Drop the guarantee from the opener.** Lowest median here, zero survivors in Iles's niche cohort.
   Two corpora agree. Keep it as a closing line if you want it at all.
2. **Open by denying the obvious.** "Your lead problem isn't what you think" — 147 days. "You don't
   have to run discounts" — 121 days. Both refuse the expected pitch first.
3. **Demo something.** This whole cohort shows the product working on screen. Iles never does, and
   his ads still needed a guarantee to carry belief. A demo buys belief cheaper.
4. **Watch mrmedspa.com and authenticadvisorysystems.com.** Small books, high medians — they're the
   two that look like they found a winner and stopped testing. Those are the ads to study.
