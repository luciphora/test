"""Stage 3 — qa.  GATE 2.

Whisper (ASR) transcription of every take; duration / effective-wpm /
word-diff / watchlist metrics; advisory ranking; take_report.md and a
prefilled selections.yaml (confirmed: false). Tone is the operator's call —
ASR can flag drift on watchlist terms; it cannot approve them.
"""

from __future__ import annotations

import difflib
import json
import statistics

from . import dsp, manifest
from .config import Project
from .util import GateOpen, StageError, normalize_words, say

GATE_MESSAGE = ("Review take_report.md, audition flagged takes, "
                "edit selections.yaml, set confirmed: true.")

_ASR_MODEL = "medium"  # multilingual medium, per spec


def _transcribe_all(project: Project, take_paths: dict[str, dict[str, object]]) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise StageError("faster-whisper is not installed (pip install faster-whisper)") from e
    say(f"Loading Whisper (ASR) model '{_ASR_MODEL}' (multilingual)...")
    model = WhisperModel(_ASR_MODEL, compute_type="auto")
    out = {}
    for key, path in take_paths.items():
        segments, _info = model.transcribe(str(path), beam_size=5)
        out[key] = " ".join(s.text for s in segments).strip()
    return out


def _diff_metrics(ref_words: list[str], hyp_words: list[str],
                  watchlist: list[str], whitelisted: set[str]) -> dict:
    sm = difflib.SequenceMatcher(a=ref_words, b=hyp_words, autojunk=False)
    subs, flags, whitelisted_hits = [], [], 0
    watch = {w.lower() for word in watchlist for w in normalize_words(word)}
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            continue
        ref_side = ref_words[a0:a1]
        hyp_side = hyp_words[b0:b1]
        for w in ref_side:
            if w in watch:
                flags.append({"word": w, "heard": " ".join(hyp_side) or "(omitted)"})
        plain = [w for w in ref_side if w not in watch]
        wl = [w for w in plain if w in whitelisted]
        whitelisted_hits += len(wl)
        remaining = [w for w in plain if w not in whitelisted]
        if remaining or (op != "replace" and hyp_side and not ref_side):
            subs.append({"op": op, "ref": " ".join(ref_side), "hyp": " ".join(hyp_side)})
    return {"substitutions": subs, "watchlist_flags": flags,
            "whitelisted_spelling_hits": whitelisted_hits}


def run(project: Project) -> None:
    try:
        import yaml
    except ImportError as e:
        raise StageError("pyyaml is not installed") from e

    mani = manifest.load(project.manifest_path)
    chunks = mani.get("chunks", {})
    takes = mani.get("takes", {})
    if not takes:
        raise StageError("no takes in manifest — run `python -m pipeline takes` first")

    grid = {g["id"]: g for g in json.loads(project.grid_path.read_text())} \
        if project.grid_path.is_file() else {}
    watchlist = project.settings.get("pronunciation_watchlist", [])
    whitelisted = {w.lower()
                   for word in project.respellings()
                   for w in normalize_words(word)}

    take_paths: dict[str, object] = {}
    for chunk_id, t in takes.items():
        track = chunks[chunk_id]["track"]
        for take_name in t["takes"]:
            take_paths[f"{chunk_id}/{take_name}"] = (
                project.takes_dir / track / chunk_id / f"{take_name}.wav")
    transcripts = _transcribe_all(project, take_paths)

    results: dict[str, list[dict]] = {}
    for chunk_id, t in sorted(takes.items()):
        track = chunks[chunk_id]["track"]
        ref_text = (project.root / chunks[chunk_id]["path"]).read_text()
        ref_words = normalize_words(ref_text)
        rows = []
        for take_name, meta in sorted(t["takes"].items()):
            path = project.takes_dir / track / chunk_id / f"{take_name}.wav"
            audio, sr = dsp.read_wav(path)
            duration = len(audio) / sr
            hyp = transcripts[f"{chunk_id}/{take_name}"]
            m = _diff_metrics(ref_words, normalize_words(hyp), watchlist, whitelisted)
            slot = grid.get(chunk_id)
            slot_len = (slot["end_s"] - slot["start_s"]) if slot and slot.get("end_s") else None
            rows.append({
                "take": take_name,
                "duration_s": round(duration, 2),
                "wpm": round(len(ref_words) / duration * 60, 1) if duration else 0,
                "fits_slot": (duration <= slot_len) if slot_len else None,
                "transcript": hyp,
                **m,
            })
        results[chunk_id] = rows

    # wpm intent: all takes on a track share the profile speed, so the track
    # median is the empirical realization of that intent.
    track_wpms: dict[str, list[float]] = {}
    for chunk_id, rows in results.items():
        track_wpms.setdefault(chunks[chunk_id]["track"], []).extend(r["wpm"] for r in rows)
    track_median = {tr: statistics.median(v) for tr, v in track_wpms.items()}

    def rank_key(chunk_id: str, row: dict):
        med = track_median[chunks[chunk_id]["track"]]
        return (len(row["watchlist_flags"]),
                len(row["substitutions"]),
                0 if row["fits_slot"] in (True, None) else 1,
                abs(row["wpm"] - med))

    report = ["# Take report", "",
              f"ASR: faster-whisper `{_ASR_MODEL}` (multilingual). "
              "Ranking is advisory only — tone is the operator's call.", ""]
    selections = {}
    flagged_chunks = []
    for chunk_id, rows in sorted(results.items()):
        rows.sort(key=lambda r: rank_key(chunk_id, r))
        best = rows[0]
        any_flags = any(r["watchlist_flags"] for r in rows)
        if any_flags:
            flagged_chunks.append(chunk_id)
        report.append(f"## {chunk_id} ({chunks[chunk_id]['track']})"
                      + ("  ⚠ WATCHLIST FLAGS — audition by ear" if any_flags else ""))
        report.append("")
        report.append("| rank | take | dur (s) | wpm | fits slot | watchlist flags | word subs | flagged words |")
        report.append("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(rows, 1):
            flags = "; ".join(f"{f['word']}→{f['heard']}" for f in r["watchlist_flags"]) or "—"
            fits = {True: "yes", False: "NO", None: "n/a"}[r["fits_slot"]]
            report.append(f"| {i} | {r['take']} | {r['duration_s']} | {r['wpm']} "
                          f"| {fits} | {len(r['watchlist_flags'])} "
                          f"| {len(r['substitutions'])} | {flags} |")
        report.append("")
        selections[chunk_id] = {"take": best["take"], "confirmed": False}

    if flagged_chunks:
        report.insert(3, "**Flags first — audition these by ear:** "
                      + ", ".join(flagged_chunks) + "\n")

    (project.reports_dir / "take_report.md").write_text("\n".join(report) + "\n")
    mani["qa"] = {"results": results, "track_median_wpm": track_median}
    manifest.save(project.manifest_path, mani)

    existing = {}
    if project.selections_path.is_file():
        existing = (yaml.safe_load(project.selections_path.read_text()) or {}).get("selections", {})
    for chunk_id, sel in selections.items():
        prior = existing.get(chunk_id)
        if prior and prior.get("confirmed"):
            selections[chunk_id] = prior  # never overwrite a confirmed selection
    project.selections_path.write_text(yaml.safe_dump(
        {"selections": selections}, sort_keys=True, allow_unicode=True))

    say(f"Wrote reports/take_report.md and prefilled config/selections.yaml "
        f"({len(selections)} chunks, all confirmed: false).")
    raise GateOpen("GATE 2", GATE_MESSAGE)


def load_confirmed_selections(project: Project) -> dict[str, str]:
    """chunk_id -> take name; raises unless Gate 2 is fully passed."""
    try:
        import yaml
    except ImportError as e:
        raise StageError("pyyaml is not installed") from e
    if not project.selections_path.is_file():
        raise StageError("config/selections.yaml does not exist — run qa first")
    sel = (yaml.safe_load(project.selections_path.read_text()) or {}).get("selections", {})
    mani = manifest.load(project.manifest_path)
    chunks = mani.get("chunks", {})
    problems = []
    out = {}
    for chunk_id in chunks:
        entry = sel.get(chunk_id)
        if not entry or not entry.get("take"):
            problems.append(f"{chunk_id}: no take selected")
        elif not entry.get("confirmed"):
            problems.append(f"{chunk_id}: not confirmed")
        else:
            out[chunk_id] = entry["take"]
    if problems:
        raise StageError("Gate 2 not passed:\n  " + "\n  ".join(problems))
    return out


def is_done(project: Project) -> bool:
    try:
        load_confirmed_selections(project)
        return True
    except StageError:
        return False
