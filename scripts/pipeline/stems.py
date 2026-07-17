"""Stage 4 — stems: isochronic tone (synthesized) + whisper stem (sliced & placed).

Isochronic: signal(t) = sin(2π·carrier·t) · e(t),
            e(t) = (1−d) + d·(0.5 − 0.5·cos(2π·pulse·t)).
Whisper stem: selected W-block takes sliced into single statements, placed on
a seeded timeline (loops of all statements, shuffled per loop, random gaps,
no overlaps). Placement JSON is validated programmatically before rendering.
"""

from __future__ import annotations

import json
import random

import numpy as np

from . import dsp, manifest, qa
from .config import Project
from .util import StageError, fmt_time, parse_time, say

TOTAL_S = 30 * 60  # night program length


# -- isochronic ----------------------------------------------------------------

def build_isochronic(project: Project) -> dict:
    cfg = project.settings["isochronic"]
    sr = project.sample_rate
    carrier = float(cfg["carrier_hz"])
    pulse = float(cfg["pulse_hz"])
    depth = float(cfg["depth"])
    fade_in = float(cfg["fade_in_s"])
    fade_out_start = parse_time(cfg["fade_out_start"])
    silent_by = parse_time(cfg["silent_by"])

    t = np.arange(int(TOTAL_S * sr)) / sr
    envelope = (1 - depth) + depth * (0.5 - 0.5 * np.cos(2 * np.pi * pulse * t))
    x = np.sin(2 * np.pi * carrier * t) * envelope

    gain = np.ones_like(x)
    n_in = int(fade_in * sr)
    gain[:n_in] = dsp.raised_cosine_fade(n_in, "in")
    i0, i1 = int(fade_out_start * sr), int(silent_by * sr)
    gain[i0:i1] = dsp.raised_cosine_fade(i1 - i0, "out")
    gain[i1:] = 0.0
    x *= gain
    x *= 0.5  # headroom; final level set at assembly

    stereo = dsp.to_stereo(x)  # identical L/R (dual mono)
    path = project.stems_dir / "isochronic.wav"
    dsp.write_wav(path, stereo, sr, project.bit_depth)

    # -- Done-when verification, all programmatic ---------------------------
    steady = x[int(120 * sr): int(600 * sr)]
    peak_hz = dsp.fft_peak_hz(steady, sr)
    env_hz = dsp.envelope_rate_hz(steady, sr)
    lr_null = float(np.max(np.abs(stereo[:, 0] - stereo[:, 1])))
    fade_checks = {
        "pre_fade_in_quiet": dsp.rms_dbfs(x[: int(1 * sr)]) < -20,
        "full_level_after_fade_in": dsp.rms_dbfs(
            x[int(fade_in * sr): int((fade_in + 10) * sr)]) > -20,
        "declining_after_fade_out_start": dsp.rms_dbfs(
            x[int((silent_by - 30) * sr): int(silent_by * sr)]) < dsp.rms_dbfs(
            x[i0: i0 + int(30 * sr)]),
        "silent_by": bool(np.all(x[i1:] == 0.0)),
    }
    verification = {
        "lr_null_max_abs": lr_null,
        "fft_peak_hz": round(peak_hz, 2),
        "envelope_rate_hz": round(env_hz, 3),
        "fades": fade_checks,
        "duration_s": len(x) / sr,
    }
    failures = []
    if lr_null != 0.0:
        failures.append(f"L−R null is not silent (max {lr_null})")
    if abs(peak_hz - carrier) > 1.0:
        failures.append(f"FFT peak at {peak_hz} Hz, expected {carrier}")
    if abs(env_hz - pulse) > 0.02:
        failures.append(f"envelope rate {env_hz} Hz, expected {pulse:.2f}")
    if not all(fade_checks.values()):
        failures.append(f"fade checks failed: {fade_checks}")
    if failures:
        raise StageError("isochronic verification failed:\n  " + "\n  ".join(failures))
    say(f"  isochronic.wav verified: peak {peak_hz:.1f} Hz, "
        f"envelope {env_hz:.2f} Hz, fades OK, L−R null silent.")
    return verification


# -- whisper stem -----------------------------------------------------------------

def _statement_count(text: str) -> int:
    """Expected statements in a W-block: non-empty lines, else sentences."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) > 1:
        return len(lines)
    import re
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    return max(1, len(sentences))


def _collect_statements(project: Project, selections: dict[str, str]) -> dict[str, list[np.ndarray]]:
    """block_id -> ordered statement audio, sliced from the selected takes."""
    mani = manifest.load(project.manifest_path)
    chunks = mani.get("chunks", {})
    sr = project.sample_rate
    out: dict[str, list[np.ndarray]] = {}
    for chunk_id, entry in sorted(chunks.items()):
        if entry["track"] != "whisper_stem":
            continue
        take = selections[chunk_id]
        path = project.takes_dir / "whisper_stem" / chunk_id / f"{take}.wav"
        audio, file_sr = dsp.read_wav(path)
        audio = dsp.resample(dsp.mono(audio), file_sr, sr)
        expected = _statement_count((project.root / entry["path"]).read_text())
        pieces = dsp.slice_on_silences(audio, sr, threshold_db=-45.0, min_silence_s=0.4)
        if len(pieces) != expected:
            raise StageError(
                f"whisper stem block {chunk_id}: slicing found {len(pieces)} statements, "
                f"expected {expected}. Fall back: regenerate this block one statement "
                "per request (delete its takes, split the chunk text, re-run takes), "
                "then re-run stems."
            )
        out[chunk_id] = pieces
    if not out:
        raise StageError("no whisper_stem blocks found")
    return out


def _place_statements(project: Project, statements: dict[str, list[np.ndarray]]) -> dict:
    cfg = project.settings["whisper_stem_layer"]
    sr = project.sample_rate
    start = parse_time(cfg["start"])
    end = parse_time(cfg["end"])
    gap_lo, gap_hi = (float(g) for g in cfg["gap_s"])
    loops = int(cfg["loop_orders"])
    rng = random.Random(int(cfg["seed"]))

    keys = [(block, i) for block in sorted(statements) for i in range(len(statements[block]))]
    durations = {k: len(statements[k[0]][k[1]]) / sr for k in keys}

    for attempt in range(500):
        events = []
        t = start
        ok = True
        orders = []
        for _ in range(loops):
            order = keys[:]
            rng.shuffle(order)
            orders.append(order)
        for loop_idx, order in enumerate(orders):
            for key in order:
                dur = durations[key]
                if t + dur > end:
                    ok = False
                    break
                events.append({"block": key[0], "statement": key[1], "loop": loop_idx,
                               "start_s": round(t, 3), "end_s": round(t + dur, 3)})
                t = t + dur + rng.uniform(gap_lo, gap_hi)
            if not ok:
                break
        if ok:
            placement = {
                "seed": cfg["seed"], "attempt": attempt, "window": [start, end],
                "gap_s": [gap_lo, gap_hi], "loop_orders": loops, "events": events,
            }
            _validate_placement(placement, keys)
            return placement
    raise StageError(
        f"could not fit {loops} loops of {len(keys)} statements into "
        f"{fmt_time(start)}–{fmt_time(end)} with gaps {gap_lo}–{gap_hi}s — "
        "statements are too long; widen the window or shrink gaps in config"
    )


def _validate_placement(placement: dict, keys: list) -> None:
    """The four constraints, checked programmatically. Every statement exactly
    once per loop also guarantees the key revenue statement appears exactly
    once per loop."""
    events = placement["events"]
    start, end = placement["window"]
    problems = []
    for loop_idx in range(placement["loop_orders"]):
        loop_keys = [(e["block"], e["statement"]) for e in events if e["loop"] == loop_idx]
        if sorted(loop_keys) != sorted(keys):
            problems.append(f"loop {loop_idx} is not exactly one of each statement")
    ordered = sorted(events, key=lambda e: e["start_s"])
    for a, b in zip(ordered[:-1], ordered[1:]):
        if b["start_s"] < a["end_s"]:
            problems.append(f"overlap: {a['block']}#{a['statement']} / {b['block']}#{b['statement']}")
        gap = b["start_s"] - a["end_s"]
        lo, hi = placement["gap_s"]
        if not (lo - 0.01 <= gap <= hi + 0.01):
            problems.append(f"gap {gap:.2f}s outside [{lo}, {hi}] before "
                            f"{b['block']}#{b['statement']}")
    if ordered and (ordered[0]["start_s"] < start - 0.01 or ordered[-1]["end_s"] > end + 0.01):
        problems.append("events outside the configured window")
    if problems:
        raise StageError("placement constraint failures:\n  " + "\n  ".join(problems))


def build_whisper_stem(project: Project, selections: dict[str, str]) -> dict:
    sr = project.sample_rate
    statements = _collect_statements(project, selections)
    placement = _place_statements(project, statements)

    path_json = project.stems_dir / "whisper_stem_placement.json"
    path_json.write_text(json.dumps(placement, indent=2) + "\n")

    buf = np.zeros(int(TOTAL_S * sr))
    for e in placement["events"]:
        seg = statements[e["block"]][e["statement"]]
        i0 = int(e["start_s"] * sr)
        buf[i0: i0 + len(seg)] += seg

    # render check: stem audio exists exactly where placement says
    for e in placement["events"]:
        i0, i1 = int(e["start_s"] * sr), int(e["end_s"] * sr)
        if dsp.rms_dbfs(buf[i0:i1]) <= -60:
            raise StageError(f"rendered stem is silent at placed event {e}")

    dsp.write_wav(project.stems_dir / "whisper_stem.wav", dsp.to_stereo(buf),
                  sr, project.bit_depth)
    say(f"  whisper_stem.wav rendered: {len(placement['events'])} placements, "
        "all four constraints verified.")
    return {"placement_events": len(placement["events"]),
            "placement_json": str(path_json.relative_to(project.root))}


def run(project: Project) -> None:
    project.ensure_dirs()
    selections = qa.load_confirmed_selections(project)  # hard stop unless Gate 2 passed
    mani = manifest.load(project.manifest_path)
    stems_info = mani.setdefault("stems", {})
    say("Synthesizing isochronic tone...")
    stems_info["isochronic"] = build_isochronic(project)
    say("Building whisper stem...")
    stems_info["whisper_stem"] = build_whisper_stem(project, selections)
    if project.settings.get("ambience", {}).get("enabled"):
        raise StageError("ambience.enabled is true but no ambience source is configured")
    manifest.save(project.manifest_path, mani)
    say("Stage 4 done.")


def is_done(project: Project) -> bool:
    mani = manifest.load(project.manifest_path)
    stems = mani.get("stems", {})
    return ((project.stems_dir / "isochronic.wav").is_file()
            and (project.stems_dir / "whisper_stem.wav").is_file()
            and "isochronic" in stems and "whisper_stem" in stems)
