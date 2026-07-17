import json
import shutil
from pathlib import Path

import pytest

from pipeline import chunk
from pipeline.config import Project
from pipeline.pack import parse_pack, track_for_chunk
from pipeline.util import StageError, parse_time

FIXTURE = Path(__file__).parent / "fixture_pack.md"

TRACKS_CFG = {
    "id_prefixes": {"N": "night", "W": "whisper_stem", "M": "morning"},
    "section_map": {"(?i)track\\s*4": "anchor"},
    "expected_counts": {"night": 2, "whisper_stem": 2, "morning": 1, "anchor": 1},
    "grid_required": ["night", "morning"],
}


def test_parse_time():
    assert parse_time("0:45") == 45
    assert parse_time("24:00") == 1440
    assert parse_time("27:30") == 1650


def test_chunks_verbatim_and_gridded():
    pack = parse_pack(FIXTURE)
    by_id = {c.id: c for c in pack.chunks}
    assert set(by_id) == {"N01", "N02", "W01", "W02", "M01", "A01"}
    # verbatim: inline tags preserved, prose outside fences excluded
    assert by_id["N01"].text == "Settle in. [soft breath] Let the day loosen its grip."
    assert "excluded" not in by_id["N01"].text
    assert by_id["N02"].start_s == 60 and by_id["N02"].end_s == 150
    # multi-line statement blocks survive intact
    assert by_id["W01"].text.count("\n") == 1


def test_track_mapping_prefix_and_section():
    pack = parse_pack(FIXTURE)
    got = {c.id: track_for_chunk(c, TRACKS_CFG) for c in pack.chunks}
    assert got == {"N01": "night", "N02": "night", "W01": "whisper_stem",
                   "W02": "whisper_stem", "M01": "morning", "A01": "anchor"}


def test_named_sections_found():
    pack = parse_pack(FIXTURE)
    assert pack.section_matching(r"(?i)voice\s+design")
    assert pack.section_matching(r"(?i)final\s+production\s+checklist")
    assert pack.section_matching(r"(?i)speaker\s+qa")


@pytest.fixture
def project(tmp_path):
    (tmp_path / "config").mkdir()
    settings = json.loads((Path(__file__).parents[1] / "config" / "settings.json").read_text())
    settings["pack_file"] = "pack.md"
    settings["tracks"] = TRACKS_CFG
    (tmp_path / "config" / "settings.json").write_text(json.dumps(settings))
    shutil.copy(FIXTURE, tmp_path / "pack.md")
    return Project(tmp_path)


def test_stage0_end_to_end(project):
    chunk.run(project)
    assert chunk.is_done(project)
    files = sorted(p.name for p in project.chunks_dir.rglob("*.txt"))
    assert files == ["A01.txt", "M01.txt", "N01.txt", "N02.txt", "W01.txt", "W02.txt"]
    grid = json.loads(project.grid_path.read_text())
    assert {g["id"] for g in grid} >= {"N01", "N02", "M01"}
    mani = json.loads(project.manifest_path.read_text())
    assert len(mani["chunks"]) == 6
    assert all(len(e["sha256"]) == 64 for e in mani["chunks"].values())


def test_stage0_fails_loudly_on_count_mismatch(project):
    project.settings["tracks"]["expected_counts"]["night"] = 25
    with pytest.raises(StageError, match="expected 25"):
        chunk.run(project)
