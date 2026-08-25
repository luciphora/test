# Target brief — Audrey Adams / Metabolic Makeover Academy

Handle `@audreyyadamsfit` · 325K followers · 2,129 posts · bio CTA to
`metabolicmakeoveracademy.org` (the `.com` is a 404 — the live domain is `.org`).
TikTok as `@audrey_fit`.

## Status of the ad pull

Not done. Meta's Ad Library returns `403` to every request from this environment and
`facebook.com/robots.txt` is a blanket `Disallow: /`, so there is no compliant path to
her live ads from a datacenter IP. Google's Ads Transparency Center is reachable but
its search RPC returns empty without a browser session, and TikTok's Creative Center
top-ads API answers `40101 no permission` unauthenticated.

Run `collect_meta_ads.py` from your Mac — the Ad Library loads normally from a
residential IP in a logged-in browser. Everything below is what could be established
without it, and it is all from her own public funnel, not from her ads.

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
