"""Stage 5 — assemble: night / morning / anchor pre-masters.

Night: selected takes at grid start_s, tail-padded to the next grid start;
overruns borrow from the following gap (logged, never stretched or cut);
25 ms equal-power edge fades over a glue bed; narration bus chain; stems
layered at configured offsets below narration LUFS; isochronic ducked under
active narration (GR capped at 2 dB).
"""

from __future__ import annotations

import json

import numpy as np

from . import dsp, manifest, qa
from .config import Project
from .util import StageError, fmt_time, say

TOTAL_S = 30 * 60
JOIN_FADE_S = 0.025
GLUE_FLOOR_GATE_DB = -80.0
GLUE_SYNTH_DB = -68.0


def _narration_chain(project: Project, x: np.ndarray, sr: int) -> tuple[np.ndarray, dict]:
    cfg = project.settings["narration_chain"]
    info: dict = {}
    b, a = dsp.biquad_highpass(float(cfg["hpf_hz"]), sr)
    x = dsp.apply_biquad(x, b, a)
    mud = cfg["mud_cut"]
    b, a = dsp.biquad_peaking(float(mud["hz"]), sr, float(mud["db"]), float(mud["q"]))
    x = dsp.apply_biquad(x, b, a)
    x = dsp.deess(x, sr)
    x, comp_info = dsp.compress(x, sr, float(cfg["comp_ratio"]), float(cfg["comp_gr_db"]))
    info["compressor"] = comp_info

    target_lufs = float(cfg["premaster_lufs"])
    peak_ceiling = float(cfg["premaster_peak_dbfs"])
    measured = dsp.integrated_lufs(x, sr)
    gain_db = target_lufs - measured
    x = x * dsp.db_to_lin(gain_db)
    peak = dsp.peak_dbfs(x)
    if peak > peak_ceiling:
        trim = peak_ceiling - peak
        x = x * dsp.db_to_lin(trim)
        gain_db += trim
        info["peak_limited"] = f"trimmed {abs(trim):.2f} dB to honor {peak_ceiling} dBFS peak"
    info["lufs"] = round(dsp.integrated_lufs(x, sr), 2)
    info["peak_dbfs"] = round(dsp.peak_dbfs(x), 2)
    return x, info


def _glue_bed(project: Project, takes: list[np.ndarray], sr: int,
              n_total: int) -> tuple[np.ndarray, str]:
    """Inter-phrase noise floor tiled full-length, or synthesized brown noise."""
    best: np.ndarray | None = None
    best_db = -np.inf
    win = int(0.3 * sr)
    for audio in takes:
        m = dsp.mono(audio)
        for sil0, sil1 in dsp.find_silences(m, sr, threshold_db=-40.0, min_len_s=0.3):
            seg = m[sil0:sil1][:win]
            level = dsp.rms_dbfs(seg)
            if np.isfinite(level) and level > best_db:
                best, best_db = seg, level
    if best is not None and best_db > GLUE_FLOOR_GATE_DB:
        reps = n_total // len(best) + 2
        tiled = np.tile(best, reps)[:n_total]
        return tiled, f"noise floor extracted from takes ({best_db:.1f} dBFS)"
    bed = dsp.brown_noise(n_total, GLUE_SYNTH_DB, seed=1)
    return bed, f"floor below {GLUE_FLOOR_GATE_DB:.0f} dBFS (digital black) — synthesized brown noise at {GLUE_SYNTH_DB} dBFS"


def _assemble_gridded(project: Project, track: str, selections: dict[str, str],
                      total_s: float | None, log: list[str]) -> np.ndarray:
    """Place selected takes at grid starts; pad tails; log borrowed overruns."""
    sr = project.sample_rate
    mani = manifest.load(project.manifest_path)
    chunks = mani["chunks"]
    grid = [g for g in json.loads(project.grid_path.read_text()) if g["track"] == track]
    grid.sort(key=lambda g: g["start_s"])
    if not grid:
        raise StageError(f"no grid entries for track {track}")

    takes_audio = []
    for g in grid:
        path = project.takes_dir / track / g["id"] / f"{selections[g['id']]}.wav"
        audio, file_sr = dsp.read_wav(path)
        takes_audio.append(dsp.resample(dsp.mono(audio), file_sr, sr))

    end_estimate = total_s or (grid[-1]["end_s"] or grid[-1]["start_s"] + 60)
    n_total = int(end_estimate * sr)
    buf = np.zeros(n_total)

    prev_end = 0.0
    for g, audio in zip(grid, takes_audio):
        start = g["start_s"]
        if start < prev_end:
            borrowed = prev_end - start
            start = prev_end
            log.append(f"OVERRUN: {g['id']} start pushed {borrowed:.2f}s late "
                       f"(previous take borrowed from the following gap) — "
                       f"grid {fmt_time(g['start_s'])}, actual {fmt_time(start)}")
        dur = len(audio) / sr
        slot_len = (g["end_s"] - g["start_s"]) if g.get("end_s") else None
        if slot_len and dur > slot_len:
            log.append(f"NOTE: {g['id']} take runs {dur:.2f}s in a {slot_len:.0f}s slot — "
                       f"borrowing {dur - slot_len:.2f}s from the following gap")
        i0 = int(start * sr)
        seg = dsp.fade_edges(audio, sr, JOIN_FADE_S)
        end_i = min(i0 + len(seg), n_total)
        if i0 + len(seg) > n_total:
            raise StageError(f"{g['id']} overruns the program end ({fmt_time(start + dur)}) — "
                             "select a shorter take; never cut words")
        buf[i0:end_i] += seg[: end_i - i0]
        prev_end = start + dur

    bed, bed_method = _glue_bed(project, takes_audio, sr, n_total)
    span0 = int(grid[0]["start_s"] * sr)
    span1 = int(prev_end * sr)
    bed_track = np.zeros(n_total)
    bed_track[span0:span1] = dsp.fade_edges(bed[span0:span1], sr, 0.5)
    log.append(f"glue bed: {bed_method}; joins get {JOIN_FADE_S * 1000:.0f} ms "
               "equal-power edge fades over the bed")
    return buf + bed_track


def _layer_table(project: Project, narration_lufs: float, layers: dict[str, float]) -> list[str]:
    cfg = project.settings["levels_db_below_narration"]
    rows = ["| stem | configured offset | measured offset | within ±1 dB |",
            "|---|---|---|---|"]
    failures = []
    for name, lufs in layers.items():
        want = float(cfg[name])
        got = narration_lufs - lufs
        ok = abs(got - want) <= 1.0
        rows.append(f"| {name} | −{want:.1f} dB | −{got:.1f} dB | {'yes' if ok else 'NO'} |")
        if not ok:
            failures.append(f"{name} offset {got:.2f} dB vs configured {want} dB")
    if failures:
        raise StageError("layer levels out of tolerance:\n  " + "\n  ".join(failures))
    return rows


def run(project: Project) -> None:
    project.ensure_dirs()
    selections = qa.load_confirmed_selections(project)
    sr = project.sample_rate
    bits = project.bit_depth
    mani = manifest.load(project.manifest_path)
    report: list[str] = ["# Assembly report", ""]
    info: dict = {}

    # -- night ----------------------------------------------------------------
    say("Assembling night narration...")
    log: list[str] = []
    narration = _assemble_gridded(project, "night", selections, TOTAL_S, log)
    narration, chain_info = _narration_chain(project, narration, sr)
    narr_lufs = chain_info["lufs"]

    say("Layering stems...")
    iso, iso_sr = dsp.read_wav(project.stems_dir / "isochronic.wav")
    stem_w, w_sr = dsp.read_wav(project.stems_dir / "whisper_stem.wav")
    iso = dsp.mono(dsp.resample(iso, iso_sr, sr))[: len(narration)]
    stem_w = dsp.mono(dsp.resample(stem_w, w_sr, sr))[: len(narration)]

    layers: dict[str, np.ndarray] = {}
    measured: dict[str, float] = {}
    for name, audio in (("isochronic", iso), ("whisper_stem", stem_w)):
        target = narr_lufs - float(project.settings["levels_db_below_narration"][name])
        cur = dsp.integrated_lufs(audio, sr)
        gained = audio * dsp.db_to_lin(target - cur)
        layers[name] = gained
        measured[name] = dsp.integrated_lufs(gained, sr)

    duck_cfg = project.settings["duck"]
    layers["isochronic"], duck_info = dsp.duck(
        layers["isochronic"], narration, sr,
        gr_db=float(duck_cfg["gr_db"]), attack_ms=float(duck_cfg["attack_ms"]),
        release_ms=float(duck_cfg["release_ms"]), max_gr_db=2.0)

    night = narration + layers["isochronic"] + layers["whisper_stem"]
    night_dur = len(night) / sr
    if abs(night_dur - TOTAL_S) > 2.0:
        raise StageError(f"night duration {fmt_time(night_dur)} outside 30:00 ± 2 s")
    dsp.write_wav(project.premaster_dir / "night.wav", dsp.to_stereo(night), sr, bits)

    report += [f"## Night ({fmt_time(night_dur)})", "",
               f"Narration chain: {chain_info}", "",
               f"Ducking (isochronic): {duck_info} (cap 2 dB)", ""]
    report += _layer_table(project, narr_lufs, measured)
    report += ["", "### Assembly log", *[f"- {line}" for line in log], ""]
    info["night"] = {"duration_s": night_dur, "chain": chain_info,
                     "duck": duck_info, "layer_lufs": measured}

    # -- morning ---------------------------------------------------------------
    say("Assembling morning...")
    log = []
    grid = json.loads(project.grid_path.read_text())
    m_grid = [g for g in grid if g["track"] == "morning"]
    m_total = max(g["end_s"] or g["start_s"] + 60 for g in m_grid)
    morning = _assemble_gridded(project, "morning", selections, m_total, log)
    morning, m_info = _narration_chain(project, morning, sr)
    dsp.write_wav(project.premaster_dir / "morning.wav", dsp.to_stereo(morning), sr, bits)
    report += [f"## Morning ({fmt_time(len(morning) / sr)})", "",
               f"Narration chain: {m_info} (no stem layers)", "",
               *[f"- {line}" for line in log], ""]
    info["morning"] = {"duration_s": len(morning) / sr, "chain": m_info}

    # -- anchor ------------------------------------------------------------------
    say("Assembling anchor...")
    chunks = mani["chunks"]
    anchor_ids = [cid for cid, e in chunks.items() if e["track"] == "anchor"]
    if len(anchor_ids) != 1:
        raise StageError(f"expected exactly one anchor chunk, found {anchor_ids}")
    cid = anchor_ids[0]
    audio, a_sr = dsp.read_wav(project.takes_dir / "anchor" / cid / f"{selections[cid]}.wav")
    audio = dsp.resample(dsp.mono(audio), a_sr, sr)
    audio, a_info = _narration_chain(project, audio, sr)
    anchor = np.concatenate([np.zeros(int(0.5 * sr)), audio, np.zeros(int(1.0 * sr))])
    dsp.write_wav(project.premaster_dir / "anchor.wav", dsp.to_stereo(anchor), sr, bits)
    report += [f"## Anchor ({fmt_time(len(anchor) / sr)})", "",
               f"Narration chain: {a_info}; 0.5 s head / 1.0 s tail silence", ""]
    info["anchor"] = {"duration_s": len(anchor) / sr, "chain": a_info}

    (project.reports_dir / "assemble_report.md").write_text("\n".join(report) + "\n")
    mani["assemble"] = info
    manifest.save(project.manifest_path, mani)
    say("Stage 5 done: premaster/night.wav, morning.wav, anchor.wav "
        "(layer offsets verified within ±1 dB).")


def is_done(project: Project) -> bool:
    mani = manifest.load(project.manifest_path)
    return ("assemble" in mani and all(
        (project.premaster_dir / f"{n}.wav").is_file()
        for n in ("night", "morning", "anchor")))
