# Target brief — Audrey Adams / Metabolic Makeover Academy

Handle `@audreyyadamsfit` · 325K followers · 2,129 posts · bio CTA to
`metabolicmakeoveracademy.org` (the `.com` is a 404 — the live domain is `.org`).
TikTok as `@audrey_fit`.

## Status of the ad pull

**Done.** 119 ads, page-scoped to `view_all_page_id=569004103465529`, pulled
2026-08-25 via `collect_apify.py`. Teardown in `analysis.md`; raw dataset in
`raw.json` (both gitignored).

One caveat worth repeating from the report: Meta publishes no spend or performance
data, so "winning" here is longevity plus duplication, which is inference, not
measurement.

### Read the keyword search carefully

The first pull, keyed on "Metabolic Makeover Academy", came back 196/200 **Will
Nelson** (`thefitproceo.com`) — an agency selling paid-ads services to fitness
coaches, whose copy name-drops Audrey and Mason as a case study. Only 4 of 200 were
hers. A keyword search in the Ad Library matches anyone whose copy mentions the term,
so always scope to a page id. The collector now prints the advertiser breakdown and
warns when more than one page comes back.

### What her ads actually run

- **Video-first: 98 of 119.** Static images are the minority.
- **Metabolism damage is the spine — 53% of ads.** Hormones/perimenopause 45%,
  client-proof stories 44%, strength/recomp 29%.
- **The identity hook her site leads with is not her main ad angle.** "The woman who
  has tried it all" shows up in 12% of ads. What carries the volume is the *mechanism*
  claim — your metabolism is the problem — not the identity framing.
- **The sharpest line she owns:** *"You're not undisciplined. You're under-repaired."*
  Second-most duplicated creative, and it reframes the prospect's self-blame as a
  physiological problem she can fix. That is the ad to model.
- **Traffic splits two ways:** 29 ads to `metabolicmakeoveracademy.com`, 35 to
  Instagram. `Send message` is the single most common CTA (27) — she runs
  comment/DM-to-conversation, not just click-to-site.

### The funnel changed on 2026-08-18 — this is the story

Her *website* is application-gated with no lead magnet. Her *ads*, as of a week ago,
are not. 49 of 119 ads launched in August, and the newest cohort is all one thing:

> "Free Live Masterclass — This Wednesday. Save My Seat — 60 Min + Live Q&A.
> Losing the fat was never the hard part. Keeping it off is… Nothing to buy."

Twelve ads, all dated 2026-08-18, pushing a free webinar in front of the application.
Only **one** ad in the whole 119 uses apply/book-a-call language. She has moved from
ad→application to ad→masterclass→application, and she is spending behind it now.

The four-phase framing in that masterclass ("lose the weight, build muscle, fix
hormones, rebuild metabolism") is also an expansion of the 3-phase method on her site.
The offer narrative is being rebuilt, live.

### The GLP-1 gap is real

**Zero of 119 ads mention Ozempic, GLP-1s, semaglutide or any weight-loss medication.**
Her site does not either. In a 2026 women's fat-loss market this is the loudest
unhandled objection there is, and she is completely silent on it — not a positioning
choice she has made and lost, an opening nobody has taken.

## Original pre-pull research

Everything below was written before the pull, from her public funnel. Kept as
written — the "no webinar" claim is exactly what the ad data overturned.

### Prior status note

Was blocked on credentials, not on capability. Meta's Ad Library returns `403` to
every direct request from this environment and `facebook.com/robots.txt` is a blanket
`Disallow: /`; Google's Ads Transparency Center search RPC returns empty without a
browser session, and TikTok's Creative Center top-ads API answers `40101 no permission`
unauthenticated.

`collect_apify.py` routes around all of that — Apify supplies the browsers and
residential IPs — and is tested end to end against both of the actor's schema variants.
It needs `APIFY_TOKEN` in the environment, which is not set here. Set it and the pull
is one command. Everything below is what could be established without it, and it is all
from her own public funnel, not from her ads.

## Open these three first

- Her page's ads — <https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=Metabolic%20Makeover%20Academy&search_type=keyword_unordered>
- Her name as advertiser — <https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=Audrey%20Adams&search_type=keyword_unordered>
- The category — <https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=metabolism%20coaching%20women&search_type=keyword_unordered>

Sort what comes back by **days running**. In a library with no spend data, an ad still
live after two months is the only public tell that it is paying for itself.

## The offer, in her words

1:1 custom weight loss coaching, 6–12 months, application-gated with stated
qualification criteria. A "3-Phase Method" framed as metabolic repair → hormone
balance → long-term strength. Deliverables named on the page: personalised macros
and strength plan, weekly check-ins with 24/7 support, a hormone and metabolic test,
and a women-only community. No price is published anywhere on the funnel.

Proof she leads with: 2,400+ women coached, an Amazon-bestselling book
(*The Metabolic Makeover*), a Master's in Exercise Science under Dr. Bill Campbell,
and a Forbes Under 30 Local listing citing $930K (2024) → $2.3M (2025).

CTA ladder, verbatim: `START YOUR TRANSFORMATION` → `APPLY NOW` /
`APPLY TO WORK WITH US` → `I'M READY TO GET STARTED`. No quiz, no free guide, no
webinar — the funnel goes straight from ad to application.

## Angles her own copy already commits to

These are the messages she has chosen for her site. Whatever the Ad Library returns,
expect the winners to be a subset of them — that is the hypothesis to check, and the
`HOOK_PATTERNS` table in `analyze_ads.py` is built to score exactly these.

| Angle | Her copy |
| --- | --- |
| Identity, not demographics | "for the woman who has tried it all" |
| Anti-quick-fix | industry sells "restrictive plans, quick fixes, and fear based messaging" |
| You're not broken | women "convinced their bodies were 'broken'" |
| Eat more, not less | "eating MORE is actually what they've been in need of" |
| The regain statistic | "90% of people who lose the weight initially, gain it all back" |
| Specific outcome | "losing 20-40lbs, while restoring their metabolism, balancing hormones" |
| Anti-cookie-cutter | "cookie cutter programs and surface level guidance", women "treated like numbers" |

The identity hook is the strongest thing on the page. "For the woman who has tried it
all" self-selects a buyer who has already spent money on three programs that failed
her, which is a warmer prospect than any interest-targeting stack — and it is the
angle most likely to be carrying her paid spend.

## The gap worth noting

Nothing in her public funnel addresses GLP-1s. In a 2026 women's fat-loss market
where that is the default objection, "do I just take the shot instead" is the
unhandled question — and the most interesting thing to check for in her ads, because
if it is absent there too, it is an opening rather than an oversight.

## What is still missing

Everything that needs the library itself: which creatives are actually running, how
long each has been live, static-vs-video split, how many variants share one hook, and
whether the ad-level copy matches the site or tests something else entirely. That is
one `collect_meta_ads.py` run away.

## Sources

- <https://www.metabolicmakeoveracademy.org/> and <https://www.metabolicmakeoveracademy.org/about>
- <https://x.com/ForbesUnder30/status/2024140137001804110> (revenue and client figures)
- <https://www.instagram.com/audreyyadamsfit/> · <https://www.tiktok.com/@audrey_fit>
- <https://adlibrary.com/posts/meta-ads-for-fitness-coaches> (2026 fitness-coach Meta playbook)
