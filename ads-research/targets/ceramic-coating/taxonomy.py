"""Taxonomy derived from this corpus only (2026-09-11 pull, 1,421 ads).

Contract used by analyze_survival.py: VERTICALS and HOOKS are (label, regex)
pairs tested against the first 200 chars of the transcript, first match wins;
funnel() takes a link_url string; FEATURED_FUNNELS names the ones worth
featuring. Nothing here is imported from another target — every family below
recurs verbatim in at least two ads, and anything that did not is left
unclassified rather than forced into a bucket.

The corpus holds three businesses that must never be pooled:

  service   a local shop selling the *application* of a coating. Sells an
            appointment, in a radius, at a ticket price.
  product   a DTC brand selling a *bottle*. Sells a cart.
  franchise a brand selling the *business*. Sells a territory. (Detailing
            Devils, Rs 15-20 lakh, b2b, mostly Hindi.)

Segment is a property of the advertiser, not of the ad text, so it comes from
BRANDS below rather than from a regex. Survival is only ever compared inside a
segment.
"""

BRANDS = {
    "4HA7vPgmUz3UtHseCyPQ": ("Huracan Nero Luxury Auto Spa",    "service"),
    "J2n25Ac4juAtNDu6BDaO": ("Adam's Polishes",                 "product"),
    "r3ocRLOZkeTpvbK7IhIK": ("Bob Moses Ceramic Coating",       "service"),
    "MoMS1nFV3RCP04vLw8zb": ("Detailing Devils",                "franchise"),
    "k8t4CdjAAPQlrCK1glAv": ("Tint World",                      "service"),
    "dcGNmnODVYzWigghhNVO": ("ElitePro Detailing",              "service"),
    "pX0nVeELKzNOoqIMrI16": ("Torque Detail",                   "product"),
    "mdlCqu4XDjpuiWWMbUah": ("Greenville Detailing",            "service"),
    "MlK2m1ASQLN3cbghSxql": ("Shine Armor",                     "product"),
    "IOMQVUHnmWdvA2KHevkp": ("Nexgen",                          "product"),
    "T179L0oJeK0FeTl0MtgV": ("Lambency Detailing",              "service"),
    "DTKX2umG3cZGBGpmryWB": ("Cerakote Ceramic Coatings",       "product"),
    "fRW9qg0NHdsHu76cqhrL": ("Super Ceramic Coating",           "product"),
    "0QlSy9YHLOla349oK7Q1": ("Naples Ceramic Coatings",         "service"),
    "6NlNM3al2kEz6sdpLQp2": ("Grit Detailing",                  "service"),
    "CgK7UmdtdAbhKk67SEGx": ("Elite Auto Spa",                  "service"),
    "HHPzyREaYavQ2v1fuv32": ("Clearvu Ceramic Coating",         "service"),
    "p3kwXAQvMVtjGhLchgfA": ("Harker Heights Ceramic Coatings", "service"),
    "SbghA3mjTFodWBKRojer": ("Ceramic Pro Daytona",             "service"),
    "B025kBfEgBD0tNsEoGcy": ("Bob Moses Ceramic Coating Dallas","service"),
}

def brand(ad):    return BRANDS.get(ad.get("brand_id"), ("Unknown", "unclassified"))[0]
def segment(ad):  return BRANDS.get(ad.get("brand_id"), ("Unknown", "unclassified"))[1]

# --- Verticals ---------------------------------------------------------------
# The thing the ad says it is protecting. Thin but real: most ads name no
# vehicle at all, and saying so is more useful than inventing a split.

VERTICALS = [
    ("RV / camper",      r"\b(rv|rvs|motorhome|camper|travel trailer)\b"),
    ("Exotic / luxury",  r"\b(lamborghini|porsche|ferrari|mclaren|corvette|exotic|supercar)\b"),
    ("Truck",            r"\b(truck|trucks|f-?250|f-?150|raptor|tacoma|silverado|ram \d|pickup)\b"),
    ("Fleet / commercial", r"\b(fleet|fleets|work van|box truck|commercial vehicle)\b"),
    ("Motorcycle",       r"\b(motorcycle|motorcycles|bike\b.{0,12}paint)\b"),
    ("New vehicle",      r"(brand new (car|truck|vehicle)|just bought a new|straight from the dealership|20(2[0-9]|3[0-9]) or newer)"),
]

# --- Hooks -------------------------------------------------------------------
# First match wins, so the order is the claim: a geo call-out that also names a
# deal is filed under geo_callout, because the city is what the viewer hears in
# the first second.
#
# `junk` runs first. Roughly 60 clips transcribe to "you", "uh.", "thanks for
# watching!" or an outro-music marker -- ASR output for a clip with no speech.
# Those are not a hook family and must not dilute one.

HOOKS = [
    ("junk",                r"^\s*(you\.?|uh\.?|so\.?|bye\.?|thanks for watching!?|.{0,3}outro music.{0,3})\s*$"),
    ("Hiring",              r"(experienced window tint installer|we'?re hiring|now hiring|join our team)"),
    ("Franchise pitch",     r"(franchise opportunity|start your business|i am owner of detailing devils|my car fleet is one of|profitable business with a trusted brand)"),
    ("Intent match",        r"(if you'?re looking for a ceramic coating|if you'?ve been thinking about|look no further|if you'?re in \w+ and you'?ve been looking)"),
    ("Geo call-out",        r"(car owners|surrounding cities|residents!|if you live in|attention \w+ drivers|^\s*(austin|frisco|charlotte|charleston|dallas|houston|phoenix)[,!])"),
    ("Seasonal",            r"(summer is destroying|i love summer here|winter is coming|road salt|pollen season)"),
    ("Stop doing X",        r"(stop running your car|still waxing|stop paying for car washes|tired of wasting hours|stop washing|never wax|waxes they are|can waxes fill|why scrub away|automatic car wash)"),
    ("Objection pre-empt",  r"(do not buy|before you skip this video|i gotta be honest|i'?m going to get right to the point)"),
    ("Myth correction",     r"(most people,? (think|just like our client)|the biggest mistake|it usually isn'?t|what most people don'?t know|here'?s what nobody tells you)"),
    ("Damage warning",      r"(isn'?t protected right now|taking damage|looks absolutely terrible|the sunlight exposes|every scratch,? swirl|see those swirl marks|paint is covered in scratches|ruining your paint|destroying your paint|real-world damage|rocks,? keys|looks like absolute|scratches,? water spots)"),
    ("New-vehicle trigger", r"(just bought a new car|20\d\d or newer|brand new truck|straight from the dealership|maybe you'?re about to|new truck owners)"),
    ("Secret tease",        r"(game-?changing secret|want to hear a|here'?s the trick|nobody talks about)"),
    ("Demo proof",          r"(watch what happens when i pour|water and soap sliding off|watch what \d+ hours of work|look at this|pour water on a ceramic|washing a ceramic coated car|let'?s see if this next ?gen actually|this is how i keep my car)"),
    ("Reaction reveal",     r"(so here it is|this is a different car|look at the difference)"),
    ("Job showcase",        r"(received our full|just came into our shop|take a minute and feature|this lamborghini|turned out|came in looking|paint correction and show-?em ready)"),
    ("Owner intro",         r"(what is up,? (you guys|it'?s)|my name is|i am owner of|owner at|hey my name is|i'?m the owner|i'?m ray)"),
    ("Interior comfort",    r"(feel comfortable right away|should feel better the moment|heats up way faster|look at your car from the outside)"),
    ("Scarcity offer",      r"(ceramic coating special|sold out|limited slots|spots left|before this offer expires|we ran a deal)"),
    ("Question open",       r"(quick question|are you tired of|have you been looking for|what if i told you|when'?s the last time)"),
    ("Product claim",       r"(our coating offers|unbeatable protection|only one way to correct|keep your car looking)"),
]

# --- Funnels -----------------------------------------------------------------
# 800 of 1,421 ads carry link_url "fb.me" or empty: the ad never leaves Meta.
# That is the single largest funnel in the category, not a missing value.

ON_PLATFORM    = ("fb.me", "fb.com", "facebook.com", "instagram.com", "api.whatsapp.com", "")
MARKETPLACE    = ("walmart.com", "amazon.com", "homedepot.com")
BOOKING_TOOL   = ("app.tintwiz.com",)
# A host built for one offer rather than for the brand.
CAPTURE_PREFIX = ("promo.", "quote.", "offer.", "cf.", "hhcc.", "review.")

def funnel(link_url):
    host = (link_url or "").strip()
    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    host = host[4:] if host.startswith("www.") else host
    if host in ON_PLATFORM:  return "on_platform"
    if host in BOOKING_TOOL: return "booking_tool"
    if host in MARKETPLACE:  return "marketplace"
    if any(host.startswith(p) for p in CAPTURE_PREFIX): return "capture_page"
    return "brand_site" if host else "unclassified"

# The funnels a ceramic-coating service business could actually copy.
FEATURED_FUNNELS = ("capture_page", "on_platform")
