# home-services-restoration — competitor scan for Certified Safe

Not a single-page teardown. A **category scan** for Certified Safe LLC
(certifiedsafe.co, Greater Boston), who sell air duct cleaning, mold
remediation, water-damage mitigation, carpet cleaning, chimney sweep and
dryer-vent cleaning.

Certified Safe's own ads are **not** in this corpus — they are not indexed by
Foreplay (domain and name lookups both returned zero) and no Ad Library link or
Apify token was supplied. A second pass with either would make the comparison
direct.

Three populations, never pooled (`taxonomy.py` keys `BRANDS` on this):

- **duct_carpet** — a scheduled, discountable clean. Coupon-led, books an
  appointment, competes on price. 746 ads, 31% still live.
- **restoration** — emergency mitigation. Sells trust and response time, often
  to referral partners rather than homeowners. 315 ads, 3% still live.
- **product** — DTC brands renting home-anxiety to sell a bottle (BugMD,
  Clarifion). Not a competitor for the job, but it is what the audience is shown
  about mold, so it sets the price anchor. Pulled **live-only** as a contrast
  set, which is why it has no comparable live rate.

`BRANDS` also carries a region flag: Renew Carpet Cleaning is Irish and must not
be read as a US price comparison.

Spoken **hooks** and written **themes** are classified separately —
`analyze_survival.py` only sees `full_transcription[:200]`, and four real message
families (seasonal, cost reframe, referral partner, replace-vs-restore) live in
body copy, not the voiceover. `taxonomy.theme()` handles those.

One snapshot (2026-09-16). A state, not a trend.
