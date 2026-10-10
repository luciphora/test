"""Merge transcripts with ad metadata into a creative-level report.

    python analyze_creatives.py targets/audreyyadamsfit

Writes creatives/creative_analysis.md. The point of this pass is what the
copy-only teardown cannot see: what she actually says out loud, whether the
spoken hook matches the written one, and whether any claim shows up in audio
that never appears in the ad text.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_hook_patterns() -> dict[str, str]:
    """Reuse the taxonomy from analyze_ads.py so both passes score alike."""
    spec = importlib.util.spec_from_file_location("aa", HERE / "analyze_ads.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.HOOK_PATTERNS


def classify(text: str, patterns: dict[str, str]) -> list[str]:
    low = text.lower()
    return [name for name, pat in patterns.items() if re.search(pat, low)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    args = ap.parse_args()

    root = args.target / "creatives"
    transcripts = json.loads((root / "transcripts.json").read_text())
    ads = {a["library_id"]: a for a in json.loads((args.target / "ads.json").read_text())}
    patterns = load_hook_patterns()

    spoken = {k: v for k, v in transcripts.items() if v.get("words")}
    silent = {k: v for k, v in transcripts.items() if not v.get("words")}
    durations = [v["duration_s"] for v in transcripts.values() if v.get("duration_s")]
    wpm = [v["words"] / (v["duration_s"] / 60)
           for v in spoken.values() if v.get("duration_s")]

    out = [
        f"# Creative teardown — {args.target.name}",
        "",
        "Audio transcribed with faster-whisper (`small`, int8, VAD-filtered). "
        "ASR is imperfect on brand terms and crosstalk; treat wording as close, "
        "not exact, and check the clip before quoting a line externally.",
        "",
        "## Coverage",
        "",
        f"- Video creatives transcribed: **{len(transcripts)}**",
        f"- Containing speech: **{len(spoken)}**",
        f"- Silent (message carried by on-screen text or music): **{len(silent)}**",
    ]
    if durations:
        out += [
            f"- Runtime: median **{statistics.median(durations):.0f}s**, "
            f"range {min(durations):.0f}–{max(durations):.0f}s, "
            f"total {sum(durations)/60:.0f} min",
        ]
    if wpm:
        out += [f"- Delivery pace: median **{statistics.median(wpm):.0f} wpm**"]

    # --- the claim check: audio-only claims the written copy never makes ---
    probes = {
        "GLP-1 / medication": r"ozempic|glp-?1|semaglutide|mounjaro|tirzepatide|"
                              r"weight loss (shot|drug|med)|the shot\b",
        "Menopause / perimenopause": r"perimenopaus|menopaus",
        "Price / cost": r"\$\d|\bprice\b|\binvestment\b|\bcost\b|\bafford",
        "Guarantee": r"guarantee|money back|refund",
    }
    out += ["", "## Claims in audio vs. written copy", "",
            "Whether each theme appears in the spoken track, the ad text, or both. "
            "A theme she says but never writes is one the copy-only pass would miss.",
            "",
            "| Theme | In audio | In ad text |", "| --- | ---: | ---: |"]
    for label, pat in probes.items():
        rx = re.compile(pat, re.I)
        in_audio = sum(1 for v in spoken.values() if rx.search(v["text"]))
        in_text = sum(1 for a in ads.values() if rx.search(a["body"]))
        out.append(f"| {label} | {in_audio} | {in_text} |")

    # --- hook families, scored on speech rather than copy ---
    audio_hooks = Counter()
    for lib, v in spoken.items():
        for h in classify(v["text"], patterns):
            audio_hooks[h] += 1
    out += ["", "## Hook families in the spoken track", ""]
    for name, n in audio_hooks.most_common():
        out.append(f"- **{name}** — {n} of {len(spoken)} ({100*n/len(spoken):.0f}%)")

    # --- the openers, ranked by how long the ad has run ---
    ranked = sorted(
        ((lib, v, ads.get(lib)) for lib, v in spoken.items() if lib in ads),
        key=lambda t: t[2].get("days_running") or 0, reverse=True,
    )
    out += ["", "## Spoken openers, longest-running first", "",
            "The first line out of her mouth is the scroll-stopper. These are the "
            "ones attached to ads that have survived longest.", "",
            "| Days | Library ID | Secs | Opening line |", "| ---: | --- | ---: | --- |"]
    for lib, v, ad in ranked[:30]:
        hook = v["hook"].replace("|", "\\|")[:120]
        out.append(f"| {ad.get('days_running')} | `{lib}` | {v.get('duration_s')} | {hook} |")

    # --- repeated openers = a hook she is deliberately re-cutting ---
    norm = Counter(re.sub(r"[^a-z ]", "", v["hook"].lower()).strip()[:60]
                   for v in spoken.values() if v.get("hook"))
    repeats = [(h, n) for h, n in norm.most_common(12) if n > 1 and h]
    if repeats:
        out += ["", "## Openers reused across clips", "",
                "Same spoken opening, multiple videos — a hook she keeps re-cutting.", ""]
        for hook, n in repeats:
            out.append(f"- **{n}×** — {hook}…")

    if silent:
        out += ["", "## Silent creatives", "",
                "No detectable speech. These carry the message in on-screen text or "
                "music, so read the file rather than the transcript.", ""]
        for lib in list(silent)[:20]:
            days = (ads.get(lib) or {}).get("days_running")
            out.append(f"- `{lib}` — video/{lib}.mp4" + (f" ({days} days running)" if days else ""))

    (root / "creative_analysis.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[:40]))
    print(f"\nWrote {root/'creative_analysis.md'}")


if __name__ == "__main__":
    main()
