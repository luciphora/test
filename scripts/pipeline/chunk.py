"""Stage 0 — chunk. Pack -> chunks/{track}/{ID}.txt + grid.json + manifest hashes."""

from __future__ import annotations

import json

from . import manifest
from .config import Project
from .pack import parse_pack, track_for_chunk
from .util import StageError, say, sha256_text


def run(project: Project) -> None:
    project.ensure_dirs()
    pack = parse_pack(project.pack_path)
    tracks_cfg = project.settings["tracks"]

    mani = manifest.load(project.manifest_path)
    chunk_entries = mani.setdefault("chunks", {})
    grid = []
    counts = {t: 0 for t in project.tracks}

    for chunk in pack.chunks:
        track = track_for_chunk(chunk, tracks_cfg)
        if track is None:
            raise StageError(
                f"chunk {chunk.id} (section {chunk.section!r}) maps to no track — "
                "extend tracks.id_prefixes or tracks.section_map in config"
            )
        counts[track] += 1
        path = project.chunks_dir / track / f"{chunk.id}.txt"
        text = chunk.text + "\n"
        path.write_text(text)
        chunk_entries[chunk.id] = {
            "track": track,
            "sha256": sha256_text(text),
            "path": str(path.relative_to(project.root)),
        }
        if chunk.start_s is not None:
            grid.append({
                "id": chunk.id, "track": track,
                "start_s": chunk.start_s, "end_s": chunk.end_s,
            })

    # -- Done-when assertions: fail loudly on mismatch -----------------------
    problems = []
    for track in project.tracks:
        want = project.expected_count(track)
        if counts[track] != want:
            problems.append(f"track {track}: expected {want} chunks, found {counts[track]}")
    expected_total = sum(project.expected_count(t) for t in project.tracks)
    total = sum(counts.values())
    if total != expected_total:
        problems.append(f"expected {expected_total} chunk files total, found {total}")

    gridded_ids = {g["id"] for g in grid}
    for track in tracks_cfg.get("grid_required", []):
        for cid, entry in chunk_entries.items():
            if entry["track"] == track and cid not in gridded_ids:
                problems.append(f"{track} chunk {cid} has no grid entry (missing time span)")

    if problems:
        raise StageError("Stage 0 count assertions failed:\n  " + "\n  ".join(problems))

    grid.sort(key=lambda g: (g["track"], g["start_s"]))
    project.grid_path.write_text(json.dumps(grid, indent=2) + "\n")
    manifest.save(project.manifest_path, mani)

    say(f"Stage 0 done: {total} chunk files "
        f"({', '.join(f'{counts[t]} {t}' for t in project.tracks)}), "
        f"{len(grid)} grid entries, {len(chunk_entries)} hashes in manifest.")


def is_done(project: Project) -> bool:
    mani = manifest.load(project.manifest_path)
    chunks = mani.get("chunks", {})
    if not chunks or not project.grid_path.is_file():
        return False
    expected_total = sum(project.expected_count(t) for t in project.tracks)
    if len(chunks) != expected_total:
        return False
    return all((project.root / e["path"]).is_file() for e in chunks.values())
