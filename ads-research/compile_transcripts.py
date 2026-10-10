"""Compile per-ad transcripts into one browsable document plus an index.

    python compile_transcripts.py targets/audreyyadamsfit

The individual .txt files in creatives/transcripts/ are named by library ID,
which means nothing to a human without cross-referencing ads.json. This reads
both and writes:

    creatives/transcripts_index.csv   one row per video, sortable in a
                                       spreadsheet: days running, duration,
                                       CTA, media file, opening line
    creatives/all_transcripts.md      every transcript in one document,
                                       longest-running first, each preceded
                                       by its ad metadata — scan or Ctrl-F
                                       instead of opening 98 files
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    args = ap.parse_args()

    root = args.target / "creatives"
    ads = {a["library_id"]: a for a in json.loads((args.target / "ads.json").read_text())}
    transcripts = json.loads((root / "transcripts.json").read_text())

    # Every video creative, whether or not it has speech — a silent clip is
    # still an ad worth listing, just with an empty transcript.
    video_libs = sorted(
        {p.stem for p in (root / "video").glob("*.mp4")},
        key=lambda lib: (ads.get(lib, {}).get("days_running") or -1),
        reverse=True,
    )

    # --- index.csv ---
    with (root / "transcripts_index.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["library_id", "days_running", "started_on", "duration_s",
                    "words", "cta", "landing_domain", "video_file",
                    "transcript_file", "hook"])
        for lib in video_libs:
            ad = ads.get(lib, {})
            tx = transcripts.get(lib, {})
            w.writerow([
                lib, ad.get("days_running"), ad.get("started_on"),
                tx.get("duration_s"), tx.get("words", 0), ad.get("cta"),
                ad.get("landing_domain"), f"video/{lib}.mp4",
                f"transcripts/{lib}.txt", tx.get("hook", ""),
            ])

    # --- all_transcripts.md ---
    lines = [
        "# All video transcripts — audreyyadamsfit",
        "",
        f"{len(video_libs)} videos, sorted by days running (longest-proven first). "
        "Transcribed with faster-whisper; treat wording as close, not verbatim — "
        "check the source clip in `video/<library_id>.mp4` before quoting externally.",
        "",
        "## Contents", "",
    ]
    for lib in video_libs:
        ad = ads.get(lib, {})
        days = ad.get("days_running")
        lines.append(f"- [{days if days is not None else '?'}d — `{lib}`](#{lib})")

    lines += ["", "---", ""]
    for lib in video_libs:
        ad = ads.get(lib, {})
        tx = transcripts.get(lib, {})
        lines += [
            f'<a id="{lib}"></a>',
            f"## `{lib}` — {ad.get('days_running', '?')} days running",
            "",
            f"- **Started** {ad.get('started_on', 'unknown')}",
            f"- **Duration** {tx.get('duration_s', '?')}s"
            f" &nbsp;&nbsp; **Words** {tx.get('words', 0)}"
            f" &nbsp;&nbsp; **CTA** {ad.get('cta') or '—'}",
            f"- **Landing** {ad.get('landing_domain') or '—'}",
            f"- **Video file** `video/{lib}.mp4`",
            "",
        ]
        text = tx.get("text", "")
        if text:
            lines += ["> " + text.replace("\n", "\n> "), ""]
        else:
            lines += ["*No speech detected — message is carried by on-screen text "
                      "or music. Watch the clip directly.*", ""]
        lines += ["[↑ back to contents](#contents)", "", "---", ""]

    (root / "all_transcripts.md").write_text("\n".join(lines))
    print(f"Wrote {root/'transcripts_index.csv'} ({len(video_libs)} rows)")
    print(f"Wrote {root/'all_transcripts.md'} ({len(video_libs)} transcripts)")


if __name__ == "__main__":
    main()
