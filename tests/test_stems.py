import json
import math
from pathlib import Path

import numpy as np
import pytest

from pipeline import dsp, stems
from pipeline.config import Project
from pipeline.util import StageError

SR = 48000


@pytest.fixture
def project(tmp_path):
    (tmp_path / "config").mkdir()
    settings = (Path(__file__).parents[1] / "config" / "settings.json").read_text()
    (tmp_path / "config" / "settings.json").write_text(settings)
    return Project(tmp_path)


def test_isochronic_synthesis_and_verification(project):
    project.ensure_dirs()
    verification = stems.build_isochronic(project)
    assert verification["lr_null_max_abs"] == 0.0
    assert verification["fft_peak_hz"] == pytest.approx(240.0, abs=1.0)
    assert verification["envelope_rate_hz"] == pytest.approx(4.0, abs=0.02)
    assert all(verification["fades"].values())
    audio, sr = dsp.read_wav(project.stems_dir / "isochronic.wav")
    assert len(audio) / sr == pytest.approx(1800.0, abs=0.01)
    # digital silence from silent_by to the end
    assert np.all(audio[int(1650.5 * sr):] == 0.0)


def _fake_statements(durs_by_block):
    out = {}
    for block, durs in durs_by_block.items():
        out[block] = [dsp.fade_edges(
            0.2 * np.sin(2 * math.pi * 300 * np.arange(int(d * SR)) / SR), SR, 0.01)
            for d in durs]
    return out


def test_placement_constraints_hold(project):
    statements = _fake_statements({
        "W01": [3.0, 2.5], "W02": [2.0], "W03": [4.0], "W04": [2.2, 3.1]})
    placement = stems._place_statements(project, statements)
    events = placement["events"]
    keys = [(b, i) for b in sorted(statements) for i in range(len(statements[b]))]
    assert len(events) == 3 * len(keys)
    stems._validate_placement(placement, keys)  # must not raise
    # deterministic under the configured seed
    again = stems._place_statements(project, statements)
    assert again["events"] == events


def test_placement_rejects_impossible_window(project):
    project.settings["whisper_stem_layer"]["end"] = "6:30"  # 30 s window
    statements = _fake_statements({"W01": [10.0, 10.0], "W02": [10.0]})
    with pytest.raises(StageError, match="could not fit"):
        stems._place_statements(project, statements)


def test_statement_count():
    assert stems._statement_count("One line.\nTwo lines.\n") == 2
    assert stems._statement_count("One sentence. Another one. A third!") == 3
