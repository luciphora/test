"""Stage 2 — takes. TTS every chunk x takes_per_chunk, PCM path only.

Idempotency (hash rule): unchanged chunk sha256 + takes on disk -> skip.
Changed -> regenerate that chunk only and invalidate its selection in
selections.yaml. A confirmed take is never silently regenerated.
"""

from __future__ import annotations

import soundfile as sf

from . import dsp, eleven, manifest
from .config import Project
from .util import StageError, say

try:
    import yaml
except ImportError:  # surfaced properly when selections handling is needed
    yaml = None


def _load_selections(project: Project) -> dict:
    if yaml is None or not project.selections_path.is_file():
        return {}
    return yaml.safe_load(project.selections_path.read_text()) or {}


def _save_selections(project: Project, sel: dict) -> None:
    if yaml is None:
        raise StageError("pyyaml is required to update selections.yaml")
    project.selections_path.write_text(
        yaml.safe_dump(sel, sort_keys=True, allow_unicode=True))


def _invalidate_selection(project: Project, chunk_id: str) -> None:
    sel = _load_selections(project)
    entry = sel.get("selections", {}).get(chunk_id)
    if entry:
        if entry.get("confirmed"):
            say(f"NOTE: {chunk_id} changed — its previously CONFIRMED selection "
                "was invalidated and must be re-reviewed at Gate 2.")
        entry["confirmed"] = False
        entry["take"] = None
        entry["invalidated_reason"] = "chunk text changed"
        _save_selections(project, sel)


def _takes_on_disk(project: Project, track: str, chunk_id: str, n: int) -> bool:
    d = project.takes_dir / track / chunk_id
    return all((d / f"take{i}.wav").is_file() for i in range(1, n + 1))


def run(project: Project) -> None:
    voice_id = project.settings.get("voice_id")
    if not voice_id:
        raise StageError("voice_id is null — Gate 1 has not been passed")
    eleven.require_api_key()

    mani = manifest.load(project.manifest_path)
    chunks = mani.get("chunks", {})
    if not chunks:
        raise StageError("no chunks in manifest — run `python -m pipeline chunk` first")

    n_takes = int(project.settings["tts"]["takes_per_chunk"])
    model_id = project.settings["tts"]["model"]
    respell = project.respellings()
    take_entries = mani.setdefault("takes", {})
    sr_out, bits = project.sample_rate, project.bit_depth
    generated = skipped = 0

    for chunk_id, entry in sorted(chunks.items()):
        track = entry["track"]
        text = (project.root / entry["path"]).read_text().strip()
        current_sha = entry["sha256"]
        prior = take_entries.get(chunk_id, {})

        if (prior.get("chunk_sha256") == current_sha
                and _takes_on_disk(project, track, chunk_id, n_takes)):
            skipped += 1
            continue
        if prior and prior.get("chunk_sha256") != current_sha:
            _invalidate_selection(project, chunk_id)

        profile = project.tts_profile(track)
        request_text = text
        for word, spelled in respell.items():
            if spelled != word:
                request_text = request_text.replace(word, spelled)
        prefix = profile.get("prefix_tag")
        if prefix:  # prepended to the request only, never written to the chunk file
            request_text = f"{prefix} {request_text}"
        settings = eleven.voice_settings_from_profile(profile)

        take_dir = project.takes_dir / track / chunk_id
        take_dir.mkdir(parents=True, exist_ok=True)
        takes_meta = {}
        for i in range(1, n_takes + 1):
            say(f"  {chunk_id} take{i}/{n_takes} ...")
            raw, info = eleven.tts_pcm(voice_id, request_text, model_id, settings)
            audio = dsp.pcm16le_to_float(raw)
            audio = dsp.resample(audio, info["sample_rate"], sr_out)
            path = take_dir / f"take{i}.wav"
            dsp.write_wav(path, audio, sr_out, bits)
            info["duration_s"] = round(len(audio) / sr_out, 3)
            info["resampled_to"] = {"sample_rate": sr_out, "bit_depth": bits}
            takes_meta[f"take{i}"] = info
        take_entries[chunk_id] = {"chunk_sha256": current_sha, "takes": takes_meta}
        manifest.save(project.manifest_path, mani)  # resume-safe: save per chunk
        generated += 1

    say(f"Stage 2 done: {generated} chunks generated, {skipped} skipped (unchanged).")


def is_done(project: Project) -> bool:
    mani = manifest.load(project.manifest_path)
    chunks = mani.get("chunks", {})
    takes = mani.get("takes", {})
    if not chunks:
        return False
    n = int(project.settings["tts"]["takes_per_chunk"])
    for chunk_id, entry in chunks.items():
        t = takes.get(chunk_id)
        if not t or t.get("chunk_sha256") != entry["sha256"]:
            return False
        if not _takes_on_disk(project, entry["track"], chunk_id, n):
            return False
    return True
