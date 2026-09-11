"""Taxonomy for agencies selling TO service businesses.

Derived from this cohort's own 194 transcripts, not imported from another target.
VERTICALS here are the *buyer* the ad names (its audience), since these advertisers
sell to service businesses rather than being one.
"""
import re

VERTICALS = [
    ("Med spa / aesthetics", r"med ?spa|medspa|vet spa|aesthetic|botox|body scul"),
    ("Roofing / storm",      r"\broof|storm restoration|storm alert"),
    ("Home services",        r"home service|residential home|contractor|hvac|plumb"),
    ("Financial advisor",    r"financial advisor|advisor kewangan|mdrt"),
    ("Golf",                 r"\bgolf"),
    ("Dental / medical",     r"\bdentist|dental|chiroprac"),
]

HOOKS = [
    ("Mechanism walkthrough",  r"this is called the|the way that .{0,15} works|this is how we connect|going to be a (very )?brief demo|speed run"),
    ("AI / automation demo",   r"\bai agent|voice ?ai|automation|\bbots?\b|webhook"),
    ("Recorded call",          r"^hi,? (this is|my name)|^hi [A-Z][a-z]+, this is"),
    ("Named-client case study", r"here'?s how we helped|our client |case stud|i started it, two days"),
    ("Two-types split",        r"two types of"),
    ("Not-what-you-think reframe", r"isn'?t what you think|not what you think|the better question"),
    ("Anti-discount",          r"discount promo|limited time special|don'?t have to run discount"),
    ("Predictability promise", r"predictabl|on.demand|consistent \$"),
    ("Guarantee",              r"\bguarantee|or (you )?don'?t pay|or we work for free"),
    ("Slow-month / diagnostic", r"having a slower month|if you'?re not adding"),
    ("Platform-change news",   r"after facebook changed|death of ads|changed their advertising polic"),
]

def funnel(url):
    u = url or ""
    m = re.sub(r"https?://", "", u).split("/")[0]
    return (m or "fb.me").replace("www.", "")

FEATURED_FUNNELS = ()   # discovery target: every advertiser is featured
