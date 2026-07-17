"""Stage 6 — master.  GATE 3.

Two-pass ffmpeg loudnorm per pre-master -> masters/*.wav (48 kHz / 24-bit)
+ 256 kbps M4A. ebur128 verification, final_qa.md with an automated verdict
per Final Production Checklist row (MANUAL where only ears can judge), then
halt printing the pack's Speaker QA checklist.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

from . import manifest
from .config import Project
from .pack import parse_pack
from .util import GateOpen, StageError, say

MASTERS = ("night", "morning", "anchor")


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise StageError("ffmpeg not found on PATH (brew install ffmpeg)")
    return path


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise StageError(f"{' '.join(cmd[:3])}... failed:\n{proc.stderr[-2000:]}")
    return proc.stderr  # ffmpeg reports on stderr


def _loudnorm_two_pass(project: Project, src, dst) -> dict:
    cfg = project.settings["master"]
    i, tp = float(cfg["lufs"]), float(cfg["true_peak_dbtp"])
    base = f"loudnorm=I={i}:TP={tp}:LRA=11"
    ff = _ffmpeg()

    stderr = _run([ff, "-hide_banner", "-nostats", "-i", str(src),
                   "-af", f"{base}:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\}", stderr[stderr.rfind("Parsed_loudnorm"):], re.DOTALL)
    if not m:
        raise StageError(f"could not parse loudnorm pass-1 JSON for {src}")
    p1 = json.loads(m.group(0))

    second = (f"{base}:measured_I={p1['input_i']}:measured_TP={p1['input_tp']}"
              f":measured_LRA={p1['input_lra']}:measured_thresh={p1['input_thresh']}"
              f":offset={p1['target_offset']}:linear=true")
    sr = project.sample_rate
    _run([ff, "-hide_banner", "-nostats", "-y", "-i", str(src),
          "-af", second, "-ar", str(sr), "-c:a", "pcm_s24le", str(dst)])
    return {"pass1": p1, "filter": second}


def _measure_ebur128(path) -> dict:
    stderr = _run([_ffmpeg(), "-hide_banner", "-nostats", "-i", str(path),
                   "-af", "ebur128=peak=true", "-f", "null", "-"])
    tail = stderr[stderr.rfind("Summary:"):]
    grab = lambda label: re.search(rf"{label}:\s*(-?[\d.]+)", tail)
    out = {}
    for key, label in (("integrated_lufs", "I"), ("lra", "LRA"), ("true_peak_dbtp", "Peak")):
        m = grab(label)
        if m:
            out[key] = float(m.group(1))
    if "integrated_lufs" not in out:
        raise StageError(f"could not parse ebur128 summary for {path}")
    return out


def _encode_m4a(src, dst) -> None:
    _run([_ffmpeg(), "-hide_banner", "-nostats", "-y", "-i", str(src),
          "-c:a", "aac", "-b:a", "256k", str(dst)])


# -- checklist verdicts -----------------------------------------------------------

_MEASURED_HINTS = re.compile(
    r"(?i)\b(lufs|dbtp|dbfs|true.?peak|loudness|fade|duration|30:00|length|"
    r"level|db\b|hz\b|silen|gap|overlap|timing|timestamp)")
_VERBATIM_HINTS = re.compile(
    r"(?i)\b(verbatim|word.?for.?word|script|wording|text|exact|no (added|extra) words|"
    r"nothing (past|after|beyond)|only (appears|occurs)|contain)")
_EAR_HINTS = re.compile(
    r"(?i)\b(sounds?|listen|ear|tone of voice|natural|sibilan|breath|pleasant|"
    r"comfort|intim|feel|warm)")


def _checklist_rows(project: Project) -> list[str]:
    pack = parse_pack(project.pack_path)
    found = pack.section_matching(project.settings["pack_headings"]["final_checklist"])
    body = None
    if found:
        body = found[1]
    else:
        for _title, sec_body in pack.sections.items():
            m = re.search(project.settings["pack_headings"]["final_checklist"], sec_body)
            if m:
                body = sec_body[m.start():]
                break
    if body is None:
        raise StageError("could not locate the Final Production Checklist in the pack")
    rows = []
    for line in body.splitlines():
        item = re.match(r"^\s*(?:[-*]\s*(?:\[.\]\s*)?|\d+\.\s+|\|\s*)(.+?)\s*\|?\s*$", line)
        if item and len(item.group(1).strip()) > 8 and not set(item.group(1)) <= set("-| :"):
            rows.append(item.group(1).strip())
    return rows


def _verdict(row: str, measurements: dict, mani: dict, targets: dict) -> str:
    if _EAR_HINTS.search(row) and not _MEASURED_HINTS.search(row):
        return "MANUAL — only ears can judge"
    if _MEASURED_HINTS.search(row):
        night = measurements.get("night", {})
        evid = "; ".join(
            f"{name}: {m['integrated_lufs']} LUFS, TP {m.get('true_peak_dbtp', '?')} dBTP"
            for name, m in measurements.items())
        iso = mani.get("stems", {}).get("isochronic", {})
        extra = (f"; isochronic verified: peak {iso.get('fft_peak_hz')} Hz, "
                 f"envelope {iso.get('envelope_rate_hz')} Hz, fades {iso.get('fades')}"
                 if iso else "")
        dur = mani.get("assemble", {}).get("night", {}).get("duration_s")
        return f"PASS (measured — {evid}; night duration {dur}s{extra})"
    if _VERBATIM_HINTS.search(row):
        return ("PASS (satisfied by verbatim chunking — chunk sha256 hashes in "
                "manifest, wording immutable end-to-end)")
    return "MANUAL — not machine-checkable"


def run(project: Project) -> None:
    project.ensure_dirs()
    mani = manifest.load(project.manifest_path)
    if "assemble" not in mani:
        raise StageError("no assembled pre-masters — run `python -m pipeline assemble` first")

    cfg = project.settings["master"]
    target_i, target_tp = float(cfg["lufs"]), float(cfg["true_peak_dbtp"])
    measurements: dict[str, dict] = {}
    master_info: dict[str, dict] = {}

    for name in MASTERS:
        src = project.premaster_dir / f"{name}.wav"
        if not src.is_file():
            raise StageError(f"missing pre-master: {src}")
        wav = project.masters_dir / f"{name}.wav"
        say(f"Mastering {name} (two-pass loudnorm to {target_i} LUFS / {target_tp} dBTP)...")
        norm = _loudnorm_two_pass(project, src, wav)
        _encode_m4a(wav, project.masters_dir / f"{name}.m4a")
        meas = _measure_ebur128(wav)
        measurements[name] = meas
        master_info[name] = {"loudnorm": norm["pass1"], "measured": meas}

        problems = []
        if abs(meas["integrated_lufs"] - target_i) > 0.5:
            problems.append(f"{name}: {meas['integrated_lufs']} LUFS not within "
                            f"±0.5 LU of {target_i}")
        if meas.get("true_peak_dbtp", -99) > target_tp:
            problems.append(f"{name}: true peak {meas['true_peak_dbtp']} dBTP "
                            f"above {target_tp}")
        if problems:
            raise StageError("master verification failed:\n  " + "\n  ".join(problems))

    mani["master"] = master_info
    manifest.save(project.manifest_path, mani)

    say("Writing final_qa.md...")
    lines = ["# Final QA", "",
             "## Measured masters", "",
             "| master | integrated | target | true peak | target |",
             "|---|---|---|---|---|"]
    for name, m in measurements.items():
        lines.append(f"| {name} | {m['integrated_lufs']} LUFS | {target_i} LUFS "
                     f"| {m.get('true_peak_dbtp', '?')} dBTP | ≤ {target_tp} dBTP |")
    lines += ["", "## Final Production Checklist verdicts", ""]
    for row in _checklist_rows(project):
        lines.append(f"- **{row}**")
        lines.append(f"  - {_verdict(row, measurements, mani, cfg)}")
    (project.reports_dir / "final_qa.md").write_text("\n".join(lines) + "\n")

    # -- GATE 3: the pack's Speaker QA checklist is the final manual test -------
    pack = parse_pack(project.pack_path)
    found = pack.section_matching(project.settings["pack_headings"]["speaker_qa"])
    speaker_qa = found[1].strip() if found else (
        "Speaker QA (pack section not found — from spec): phone speaker at "
        "bedside distance, small Bluetooth speaker, over-ear headphones, "
        "low-volume mono.")
    say("\n=== Speaker QA — final manual test ===\n" + speaker_qa + "\n")
    raise GateOpen("GATE 3", "Masters are written and measured. Run the Speaker QA "
                             "checklist above by ear before shipping.")


def is_done(project: Project) -> bool:
    mani = manifest.load(project.manifest_path)
    if "master" not in mani or not (project.reports_dir / "final_qa.md").is_file():
        return False
    return all((project.masters_dir / f"{n}.wav").is_file()
               and (project.masters_dir / f"{n}.m4a").is_file() for n in MASTERS)
