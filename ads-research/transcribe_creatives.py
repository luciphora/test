"""Transcribe downloaded video creatives with faster-whisper.

    python transcribe_creatives.py targets/audreyyadamsfit

Writes creatives/transcripts/<library_id>.txt and creatives/transcripts.json,
the latter carrying duration, detected language and the spoken hook (the first
sentence) alongside the full text.

CPU-only by default. `small` is the sweet spot for ad-length clips; pass
--model medium if a pass comes back noticeably garbled on the Arabic or
clinical terms.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def hook_of(text: str, max_chars: int = 180) -> str:
    """First sentence — for a video ad this is the scroll-stopper."""
    text = text.strip()
    if not text:
        return ""
    first = SENTENCE_END.split(text, maxsplit=1)[0].strip()
    return first if len(first) <= max_chars else first[:max_chars].rsplit(" ", 1)[0] + "…"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    ap.add_argument("--model", default="small",
                    help="faster-whisper size: tiny/base/small/medium/large-v3")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--workers", type=int, default=2,
                    help="CTranslate2 intra-op threads per transcription")
    ap.add_argument("--limit", type=int, help="stop after N clips (for a trial run)")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    root = args.target / "creatives"
    videos = sorted((root / "video").glob("*.mp4"))
    if args.limit:
        videos = videos[: args.limit]
    if not videos:
        sys.exit(f"No videos in {root/'video'} — run download_creatives.py first.")

    out_dir = root / "transcripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    store_path = root / "transcripts.json"
    store = json.loads(store_path.read_text()) if store_path.exists() else {}

    print(f"Loading faster-whisper '{args.model}' ({args.compute_type})...")
    model = WhisperModel(args.model, device="cpu", compute_type=args.compute_type,
                         cpu_threads=args.workers)

    todo = [v for v in videos if v.stem not in store]
    print(f"{len(videos)} clips, {len(videos) - len(todo)} already done, {len(todo)} to go")

    for n, path in enumerate(todo, 1):
        lib = path.stem
        try:
            segments, info = model.transcribe(str(path), beam_size=1,
                                              vad_filter=True, language="en")
            text = " ".join(s.text.strip() for s in segments).strip()
        except Exception as e:  # noqa: BLE001 - one bad file must not kill the batch
            print(f"  [{n}/{len(todo)}] {lib}: FAILED ({type(e).__name__})")
            store[lib] = {"error": type(e).__name__, "text": "", "hook": "",
                          "duration_s": None, "words": 0}
            continue

        (out_dir / f"{lib}.txt").write_text(text + "\n")
        store[lib] = {
            "text": text,
            "hook": hook_of(text),
            "duration_s": round(info.duration, 1),
            "language": info.language,
            "words": len(text.split()),
            # No speech at all is a real finding, not a failure: it means the ad
            # carries its message in on-screen text or music.
            "silent": not text,
        }
        store_path.write_text(json.dumps(store, indent=2))
        print(f"  [{n}/{len(todo)}] {lib}  {store[lib]['duration_s']}s  "
              f"{store[lib]['words']}w  {store[lib]['hook'][:70]}")

    store_path.write_text(json.dumps(store, indent=2))
    spoken = [v for v in store.values() if v.get("words")]
    print(f"\nTranscribed {len(store)} clips; {len(spoken)} contain speech.")
    print(f"Wrote {out_dir} and {store_path}")


if __name__ == "__main__":
    main()
