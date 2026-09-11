"""Rank collected Ad Library records and write an analysis report.

    python analyze_ads.py targets/audreyyadamsfit

The Ad Library publishes no spend or performance data, so "winning" is inferred
from the two signals it does expose:

  longevity   an ad still running after 60+ days is one the advertiser keeps
              paying for, which is the closest public proxy for profitable.
  duplication the same creative running as many near-identical cards means
              budget is being split across it deliberately.

Both are heuristics. Treat the output as a shortlist to watch, not a verdict.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

# Hook families worth counting separately in this niche.
HOOK_PATTERNS = {
    "identity / 'woman who has tried it all'": r"tried (it all|everything)|you'?re not broken|woman who",
    "metabolism damage": r"metabol(ism|ic)|slow metabolism|metabolic damage",
    "hormones / perimenopause": r"hormon|perimenopause|menopause|cortisol|thyroid",
    "eat more not less": r"eat more|under[- ]?eat|not eating enough|reverse diet",
    "anti quick-fix / anti-diet": r"quick fix|fad diet|crash diet|restrictive|yo-?yo",
    "age gated (30s/40s/50s)": r"\b(over|after|in your)\s*(30|35|40|45|50)s?\b",
    "strength / recomp": r"recomp|lift|strength train|build muscle|toned",
    "GLP-1 / medication": r"ozempic|glp-?1|semaglutide|mounjaro|weight loss shot",
    "proof / numbers": r"\b\d{2,3}\s?(lbs|pounds)\b|\b\d{3,}\+? women\b",
    "free lead magnet": r"free (guide|training|masterclass|webinar|quiz|challenge)",
    "application / call": r"apply|book a call|schedule a call|qualify",
}

LONG_RUNNER_DAYS = 60


def load(target: Path) -> list[dict]:
    data = json.loads((target / "ads.json").read_text())
    if not data:
        raise SystemExit(f"{target}/ads.json is empty — run collect_meta_ads.py first.")
    return data


def classify(text: str) -> list[str]:
    low = text.lower()
    return [name for name, pat in HOOK_PATTERNS.items() if re.search(pat, low)]


def dedupe_key(ad: dict) -> str:
    """Collapse whitespace and IDs so near-identical creatives group together."""
    body = re.sub(r"Library ID:\s*\d+", "", ad.get("body", ""))
    return re.sub(r"\s+", " ", body).strip().lower()[:180]


def report(ads: list[dict], target: Path) -> str:
    dated = [a for a in ads if a.get("days_running") is not None]
    dated.sort(key=lambda a: a["days_running"], reverse=True)

    variants = Counter(dedupe_key(a) for a in ads)
    hooks = Counter()
    for ad in ads:
        for h in classify(ad.get("body", "")):
            hooks[h] += 1

    long_runners = [a for a in dated if a["days_running"] >= LONG_RUNNER_DAYS]

    out = [
        f"# Ad teardown — {target.name}",
        "",
        f"- Ads captured: **{len(ads)}**",
        f"- With a start date: **{len(dated)}**",
        f"- Running {LONG_RUNNER_DAYS}+ days: **{len(long_runners)}**",
        f"- Distinct creatives: **{len(variants)}** "
        f"(most-duplicated runs as {variants.most_common(1)[0][1]} cards)",
        "",
        "## Long-runners — the shortlist",
        "",
        "| Days | Started | Library ID | Hooks | Opening line |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for ad in long_runners[:25]:
        first = next((ln for ln in ad.get("body", "").split("\n") if len(ln) > 25), "")
        first = first.replace("|", "\\|")[:110]
        tags = ", ".join(classify(ad.get("body", ""))) or "—"
        out.append(
            f"| {ad['days_running']} | {ad['started_on']} | `{ad['library_id']}` | {tags} | {first} |"
        )
    if not long_runners:
        out.append("| — | — | — | — | nothing has been running long enough yet |")

    out += ["", "## Hook families across every captured ad", ""]
    for name, n in hooks.most_common():
        share = 100 * n / len(ads)
        plural = "ad" if n == 1 else "ads"
        out.append(f"- **{name}** — {n} {plural} ({share:.0f}%)")
    if not hooks:
        out.append("- no hook patterns matched; widen HOOK_PATTERNS for this niche")

    out += ["", "## Most-duplicated creatives", ""]
    for key, n in variants.most_common(10):
        if n < 2:
            break
        out.append(f"- **{n}×** — {key[:140]}")

    out += [
        "",
        "## How to read this",
        "",
        "Meta publishes no spend or performance figures. Longevity and duplication are"
        " inference, not measurement — a long-running ad may simply be one nobody turned"
        " off. Confirm a shortlist by watching it across two captures a few weeks apart:"
        " the creatives that survive both are the ones worth modelling.",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path, help="directory holding ads.json")
    args = ap.parse_args()

    ads = load(args.target)
    text = report(ads, args.target)
    (args.target / "analysis.md").write_text(text + "\n")
    print(text)
    print(f"\nWrote {args.target}/analysis.md")


if __name__ == "__main__":
    main()
