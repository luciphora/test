#!/usr/bin/env python3
"""Derive a hook x vertical taxonomy from an advertiser's own corpus.

Nothing here is pre-written: the vertical comes from the noun the ad names in
its own opening line, and the hook family comes from the phrasing template that
recurs across those verticals. Ads that match neither are reported as
unclassified rather than forced into a bucket.
"""
import json, re, sys, collections, statistics

# Verticals: the trade the ad names in its opener. Order matters - the more
# specific label wins (personal injury attorney before attorney).
VERTICALS = [
    ("Personal injury attorney", r"personal injury attorney"),
    ("Criminal defense attorney", r"criminal defense attorney"),
    ("Attorney",            r"\battorneys?\b|\blaw firm\b"),
    ("Med spa",             r"med ?spa|medspot|med spot"),
    ("Dentist",             r"\bdentists?\b|dental practice"),
    ("Chiropractor",        r"chiropract"),
    ("Plastic surgeon",     r"plastic surgeon"),
    ("Medical (general)",   r"medical (health )?professional|\bclinic\b"),
    ("Roofer",              r"\broofers?\b|roofing"),
    ("Plumber",             r"\bplumbers?\b|plumbing"),
    ("Contractor",          r"\bcontractors?\b|\bconcrete\b"),
    ("Home services",       r"home service"),
]

# Hook families: the opening move, keyed on the template that repeats verbatim
# across verticals. These were read off the corpus, not brought to it.
HOOKS = [
    # Niche-funnel families (read off med./law./pros. openers)
    ("Status-quo callout",   r"only way (you'?re getting|you get)|word of mouth (and|or) referral"),
    ("Channel callout",      r"relying on (google )?seo|missing (out on )?the biggest|static image ads"),
    ("Failed-attempt callout", r"tried social media and (felt|it didn'?t)|posts (that you made )?(just )?(don'?t|never)|haven'?t logged in"),
    ("Risk reversal / free trial", r"try my (social media )?team for seven days|seven days and if|test social media .{0,30}without|guaranteed you (a |1 )?million views"),
    ("Guarantee (views or free)", r"we'?ll get you (a |1 )?million views|or you don'?t pay|views.{0,12}it'?s free|or you didn'?t pay"),
    ("Hypothetical scale",   r"let me ask you a (really )?crazy question|crazy thought|what if 15 million"),
    ("Case study",           r"^(we got|we had|this is|here'?s (what|how) we helped|here'?s what \d|our client|this got (him|her))"),
    ("Authority / #1 way",   r"number one way to grow"),
    # Main /cpy families
    ("Stat / proof-point",   r"^(social media generates|15\.?5 million views|we'?ve built social media)"),
    ("Contrarian authority", r"most successful entrepreneurs|grant cardone|competition isn'?t smarter"),
    ("Paid-ads switch",      r"run(ning)? paid ads|giving up equity|getting customers from ads|cost per result|price shoppers|low quality leads"),
    ("Buyer-is-scrolling",   r"someone who needs exactly what you offer|scrolling"),
    ("Founder story",        r"^(three and a half years ago|i was (a )?social media influencer)"),
    ("Confession / insider", r"most marketing companies would never|hire us to fire us|only marketing company"),
    ("Simplify / delegate",  r"simplify your entire market|hiring a professional team|delegate"),
    ("Man-on-the-street",    r"sorry to bother you|interview random people|take some calls from the request line"),
    ("In-house cost callout", r"paying an employee to do all of your content|hiring a professional team"),
    ("Ad-spend threshold",   r"spend over \$[\d,]+ a month on ads|running ads for your business and you have fewer|expert team to run your ads"),
    ("Volume proof",         r"^after generating [\d.]+ billion|4 billion views"),
    ("Competitor threat",    r"seeing this video, so is your competitor|reason why some businesses seem to print money"),
    ("Never-post-again",     r"never had to post on|years worth of content in four"),
]

def classify(text, table):
    low = (text or "").lower()
    for label, pat in table:
        if re.search(pat, low):
            return label
    return None

def funnel(url):
    u = url or ""
    m = re.search(r"//(?:www\.)?([a-z0-9-]+)\.viralcoach\.com", u)
    if m and m.group(1) not in ("www",):
        return m.group(1)
    m = re.search(r"viralcoach\.com/([a-z0-9-]+)", u)
    return m.group(1) if m else "(none)"

def main(path):
    ads = json.load(open(path))
    for a in ads:
        head = (a.get("full_transcription") or "")[:200]
        a["vertical"] = classify(head, VERTICALS) or "General / no vertical"
        a["hook"] = classify(head, HOOKS) or "Unclassified"
        a["funnel"] = funnel(a.get("link_url"))

    def block(title, rows, keyfn):
        """Survival table.

        running_duration is only trustworthy for LIVE ads: 98.4% of inactive ads
        in this corpus report exactly 1 day, which is a Foreplay artifact rather
        than a real stop date. So every day-figure below is computed from live
        ads only, and dead ads contribute to counts alone.
        """
        print(f"\n## {title}\n")
        groups = collections.defaultdict(list)
        for a in rows:
            groups[keyfn(a)].append(a)
        print(f"| {title} | Ads | Live | Killed | Survival | Median days (live) | Max days (live) |")
        print("|---|--:|--:|--:|--:|--:|--:|")
        for k, g in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            live = [x for x in g if x.get("live") is True]
            med = int(statistics.median([x["days_running"] for x in live])) if live else 0
            mx = max((x["days_running"] for x in live), default=0)
            print(f"| {k} | {len(g)} | {len(live)} | {len(g)-len(live)} | "
                  f"{100*len(live)//len(g)}% | {med or '-'} | {mx or '-'} |")

    print(f"# Viral Coach ad corpus — {len(ads)} unique ads")
    live = [a for a in ads if a.get("live") is True]
    print(f"\nLive: {len(live)} · Inactive: {len(ads)-len(live)} · "
          f"With transcript: {sum(1 for a in ads if a.get('full_transcription'))}")

    block("Funnel", ads, lambda a: a["funnel"])
    niche = [a for a in ads if a["funnel"] in ("med", "law", "pros")]
    block("Vertical (niche funnels only)", niche, lambda a: a["vertical"])
    block("Hook family (niche funnels only)", niche, lambda a: a["hook"])
    block("Hook family (main /cpy funnel)", [a for a in ads if a["funnel"] == "cpy"],
          lambda a: a["hook"])

    json.dump(ads, open(path, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
