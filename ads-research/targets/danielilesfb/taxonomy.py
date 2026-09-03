"""Viral Coach taxonomy — derived from this advertiser's own openers and URLs, not imported.

VERTICALS: the trade the ad names in its first 200 chars (specific before general).
HOOKS: phrasing templates that recur verbatim across verticals.
FEATURED_FUNNELS: funnels whose every ad gets a card and transcript in the report.
"""
import re

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

def funnel(url):
    u = url or ""
    m = re.search(r"//(?:www\.)?([a-z0-9-]+)\.viralcoach\.com", u)
    if m and m.group(1) not in ("www",):
        return m.group(1)
    m = re.search(r"viralcoach\.com/([a-z0-9-]+)", u)
    return m.group(1) if m else "(none)"


FEATURED_FUNNELS = ("med", "law", "pros")
