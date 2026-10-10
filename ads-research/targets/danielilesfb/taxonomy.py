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
    ("Status-quo callout",   r"only way (you'?re getting|you get)|word of mouth (and|or) referral|every (single )?marketing strategy you'?re using"),
    ("Channel callout",      r"relying on (google )?seo|missing (out on )?the biggest|static image ads"),
    ("Failed-attempt callout", r"tried social media and (felt|it didn'?t)|posts (that you made )?(just )?(don'?t|never)|haven'?t logged in"
                             r"|if you'?ve (tried|ever hired|been burned)|you'?ve tried social media,? but|posting on social media is easy"),
    ("Risk reversal / free trial", r"try my (social media )?team for seven days|seven days and if|test social media .{0,30}without|guaranteed you (a |1 )?million views"
                             r"|try (my|our) (whole )?team.{0,30}seven days"),
    ("Free-month offer",       r"best deal any social media agency|entire month of service completely for free|sign with us this week"),
    ("Ad-spend threshold",   r"spend over \$?[\d,]+ (a|per) month on ads|running ads for your business and you have fewer|expert team to run your ad"),
    ("Proof number cold open", r"^\s*[\d.]+ (million|point)[^.]{0,45}(that'?s|that is) how|^\s*15\.?5 million|what would [\d.]+ million views do"),
    ("Guarantee (views or free)", r"we'?ll get you (a |1 )?million views|or you don'?t pay|views.{0,12}it'?s free|or you didn'?t pay"
                             r"|(craziest|best) offer|i'?ll guarantee almost anyone|agencies that guarantees? a million"),
    ("Hypothetical scale",   r"let me ask you a (really )?crazy question|crazy thought|what if 15 million|^what if|^imagine if|if you just spent 2 hours"),
    ("Case study",           r"^(we got|we had|this is|here'?s (what|how) we helped|here'?s what \d|our client|this got (him|her))"
                             r"|before coming to us|here'?s what happened to (a few )?(of )?(our )?clients|^we turned a|here'?s how we (took|helped)|^this dentist has"),
    ("Authority / #1 way",   r"number one way to grow|only three ways|best ways to grow your business right now isn'?t"),
    # Main /cpy families
    ("Stat / proof-point",   r"^(social media generates|15\.?5 million views|we'?ve built social media|organic social media generates)"),
    ("Contrarian authority", r"most successful entrepreneurs|grant cardone|competition isn'?t smarter|most surprising thing about successful"
                             r"|business owners making the most money|most successful law firms"),
    ("Paid-ads switch",      r"run(ning)? paid ads|giving up equity|getting customers from ads|cost per result|price shoppers|low quality leads"
                             r"|ads don'?t fail because|conversion rates on social media a(d)?s|facebook doesn'?t allow targeting|spending \$[\d,]+ a month on ads"),
    ("Agency / employee cost callout", r"paying an employee to do|marketing agency is charging|your agency is charging more|hiring a professional team|social media managers? (that|who) don'?t"),
    ("Channel claim",        r"social media does something no other|social media isn'?t an experiment"),
    ("Buyer-is-scrolling",   r"someone who needs exactly what you offer|scrolling"),
    ("Founder voice",        r"^(three and a half years ago|i was (a )?social media influencer)|we shot an entire month|you'?ve probably seen my content"
                             r"|most annoying ad|last month i spent over a million|i work from the moment"),
    ("Confession / insider", r"most marketing companies would never|hire us to fire us|only marketing company"),
    ("Volume proof",         r"^after generating [\d.]+ billion|4 billion views"),
    ("Competitor threat",    r"seeing this video, so is your competitor|reason why some businesses seem to print money|every day you don'?t start posting"),
    ("Objection handler",    r"how do i know this will work for my niche|how quickly will i see results"),
    ("Prestige qualifier",   r"if you make at least a million"),
    ("Polish callout",       r"social media looks like (a |it )?cut ?(out|off) from (a )?magazine"),
]

def funnel(url):
    u = url or ""
    m = re.search(r"//(?:www\.)?([a-z0-9-]+)\.viralcoach\.com", u)
    if m and m.group(1) not in ("www",):
        return m.group(1)
    m = re.search(r"viralcoach\.com/([a-z0-9-]+)", u)
    return m.group(1) if m else "(none)"


FEATURED_FUNNELS = ("med", "law", "pros")
