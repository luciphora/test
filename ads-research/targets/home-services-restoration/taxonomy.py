"""Taxonomy derived from this corpus only (2026-09-16 pull, 1,149 ads).

Contract used by analyze_survival.py: VERTICALS and HOOKS are (label, regex)
pairs tested against the first 200 chars of the transcript, first match wins;
funnel() takes a link_url string; FEATURED_FUNNELS names the ones worth
featuring. Nothing is imported from another target — every family below recurs
verbatim in at least two ads, and what did not is left unclassified.

Three populations that must never be pooled:

  duct_carpet   a shop selling a scheduled, discountable clean. Coupon-led,
                books an appointment, competes on price.
  restoration   a firm selling emergency mitigation. Sells trust and response
                time, never a price. Often sells to referral partners instead.
  product       a DTC brand renting home-anxiety to sell a bottle or a gadget
                (BugMD, Clarifion). Not a competitor for the job — but it is
                what the audience is shown about mold and indoor air, so it
                sets the price anchor. Pulled live-only, as contrast.

Certified Safe straddles the first two, which is the point of the report.
"""

# (display name, segment, region) — region flags the one non-US advertiser so
# it never lands in a US price or funnel comparison.
BRANDS = {
    "NooxnLTVd1xiG1dwmWHg": ("Stanley Steemer",              "duct_carpet", "US"),
    "LncBStMoRtrI7ut5hj1N": ("Zerorez",                      "duct_carpet", "US"),
    "cIxHQeizC6s4e3ubXs8Z": ("Xtreme Carpet Cleaning",       "duct_carpet", "US"),
    "sYjSaG508Vs9ec9YVm1D": ("Universe Duct Cleaning",       "duct_carpet", "US"),
    "OJVGq5sWychB8HsZzMFt": ("MDF Air Duct Cleaning",        "duct_carpet", "US"),
    "xF2ioIhAqa7Oduzdidj1": ("Dr Air Duct",                  "duct_carpet", "US"),
    "ydV9d51mPyv3pHWrUXBk": ("Fresh Air Ducts Cleaning",     "duct_carpet", "US"),
    "IqdZmcEGsscaG0R0zR3v": ("Eco Air Duct Cleaning",        "duct_carpet", "US"),
    "vWZoaoC8As6MEHfGa4Bh": ("Cardinal Carpet & Air Duct",   "duct_carpet", "US"),
    "viKnFHIodcat0nPTWXYf": ("McCall Carpet and Air Duct",   "duct_carpet", "US"),
    "woxo68JBs5h7gWJqRK1i": ("Premier Carpet Cleaning",      "duct_carpet", "US"),
    "jXO6zO4GJMoMjBwHneIx": ("Renew Carpet Cleaning",        "duct_carpet", "IE"),

    "yzsD0nZWYMmVsXk37qBH": ("SERVPRO",                      "restoration", "US"),
    "thVVXjU3bb5mCuG4ZZgl": ("SERVPRO Metro Pittsburgh East","restoration", "US"),
    "kNeHHmsG14RpZCM7BwaQ": ("Ram Restoration",              "restoration", "US"),
    "bT9QDLsayKmVJzgmEkpx": ("1-800 WATER DAMAGE",           "restoration", "US"),
    "YtKpCkkv3KHNzkWFHiNo": ("1-800 Water Damage Harrisburg","restoration", "US"),
    "s5xzXVlXsmjL0GEdKVN5": ("All Dry Water Damage Experts", "restoration", "US"),
    "Leu3fH2ZrqFgnGnR8arm": ("Instacure Mold Remediation",   "restoration", "US"),

    "R0BPPOpBQ1hSHjWwATSt": ("BugMD",                        "product",     "US"),
    "IuFIW4O7ePnBVuFm2pKT": ("Clarifion",                    "product",     "US"),
}

def brand(ad):   return BRANDS.get(ad.get("brand_id"), ("Unknown", "unclassified", "?"))[0]
def segment(ad): return BRANDS.get(ad.get("brand_id"), ("Unknown", "unclassified", "?"))[1]
def region(ad):  return BRANDS.get(ad.get("brand_id"), ("Unknown", "unclassified", "?"))[2]

# --- Verticals ---------------------------------------------------------------
# Which of Certified Safe's services the ad is actually selling. Order matters:
# an ad naming both ducts and a dryer vent is filed under the dryer vent, the
# narrower job.

VERTICALS = [
    ("Dryer vent",     r"(dryer vent|clothes taking forever to dry|lint)"),
    ("Air duct",       r"(air ?duct|ductwork|vents?\b|hvac|the air you breathe|indoor air)"),
    ("Water damage",   r"(water damage|burst pipe|flood|sewage|storm|water intrusion|mitigation)"),
    ("Mold",           r"(\bmold\b|mould|mildew|remediation)"),
    ("Chimney",        r"(chimney|fireplace|creosote)"),
    ("Upholstery / tile", r"(upholstery|sofa|couch|tile (and|&) grout|area rugs?)"),
    ("Carpet",         r"(carpet|rug\b|stain|pet (odor|odour|stains))"),
]

# --- Hooks -------------------------------------------------------------------
# `junk` first: ~40 clips transcribe to "you", "🎵", "thanks for watching" or an
# emoji — ASR output for a clip with no speech. Not a family; must not dilute one.

HOOKS = [
    ("junk",              r"^\s*(you\.?|uh\.?|🎵|🙏🏼|outro|thanks for watching!?|thank you for watching\.?)\s*$"),
    ("Brand jingle",      r"(stanley stea?mer gets your home cleaner|gets your home cleaner)"),
    ("Social proof at scale", r"(with over [\d,]+ reviews|190,?000|average rating of|has always been wonderful|there'?s a reason people keep calling)"),
    ("Symptom list",      r"(dust everywhere|allergies,? bad odors|are you experiencing allergies|clothes taking forever to dry|stuffy nose)"),
    ("Hidden cause",      r"(could your air ducts be the reason|your home might be the culprit|may be the problem|the real culprit|what you can'?t see)"),
    ("Last-time question", r"(when was the last time|when'?s the last time|how long has it been since)"),
    ("Dirt reveal",       r"(all the dirt and grime|tada|ta-?dah|not a bit of marker|check this out the client|thought they had tan carpet)"),
    ("Coupon pitch",      r"(we'?re offering premium|for just \$\d|get air ?duct cleaning for|\$\d+ only|2 rooms? (special|of)|every third vent)"),
    ("Health risk",       r"(pose health risks|kill (viruses?|virus) and bacteria|allergens? (and|&) (irritants|contaminants)|bacteria buildup)"),
    ("Empathy / disaster", r"(no such thing as a small disaster|if you'?re calling us,? we'?re sorry|when things couldn'?t be worse|disasters don'?t happen on a schedule)"),
    ("Authority intro",   r"(i'?m test director|hi,? i'?m \w+ (at|with)|kevin here with|my name is \w+ and)"),
    ("Confession open",   r"(okay,? i'?ve been trying to tell you|i was honestly shocked|let me tell you about)"),
    ("Curiosity / oddity", r"(why are landlords using|this strange liquid|one bug you see means|when you close your eyes at night)"),
    ("Pet owner",         r"(every dog owner|pet stains? (and|&) odors?|muddy paws|pet dander)"),
]

# --- Themes (body copy, not speech) -------------------------------------------
# Four message themes recur in `description` but almost never in the voiceover,
# so they cannot be hook families: classification runs on the transcript only.
# build_report.py scores these over description + headline instead.

THEMES = [
    ("Seasonal",          r"(as the weather cools|winter (is )?approach|chimney sweep season|holiday|back to school|heating season|spring clean)"),
    ("Cost reframe",      r"(costing you money|higher energy bill|reduce energy bill|pays for itself|lower bills|energy savings|save \$\d)"),
    ("Referral partner",  r"(property manager|plumbers|insurance adjuster|partner with us|realtor)"),
    ("Replace vs restore", r"(before you replace|replacing (them|it) costs|rip up your carpet|instead of replacing)"),
    ("Guarantee",         r"(or it'?s free|money[- ]back guarantee|100% satisfaction|guaranteed results|satisfaction guarantee)"),
    ("First-time gate",   r"(first[- ]time customers? only|new customers? only|introductory rate)"),
]

def theme(ad):
    import re
    blob = ((ad.get("description") or "") + " " + (ad.get("headline") or "")).lower()
    return [n for n, p in THEMES if re.search(p, blob)]

# --- Funnels -----------------------------------------------------------------
# In this corpus the important split is not on-platform vs site — it is whether
# the click lands somewhere that can take a booking.

ON_PLATFORM  = ("fb.me", "fb.com", "facebook.com", "instagram.com", "youtube.com", "")
MESSAGING    = ("api.whatsapp.com", "m.me")
# A path or host built to quote/book rather than to brand.
BOOKING_HINT = ("cleaning-quote-pricing", "schedule-service-online", "book", "quote", "offer", "promo", "estimate")

def funnel(link_url):
    u = (link_url or "").strip().lower()
    host = u.replace("https://", "").replace("http://", "").split("/")[0]
    host = host[4:] if host.startswith("www.") else host
    if host in MESSAGING:                      return "messaging"
    if host in ON_PLATFORM:                    return "on_platform"
    if any(h in u for h in BOOKING_HINT):      return "booking_page"
    return "brand_site" if host else "unclassified"

# What a Boston home-services advertiser could actually copy.
FEATURED_FUNNELS = ("booking_page", "on_platform", "messaging")
