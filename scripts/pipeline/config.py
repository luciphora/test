"""Project root discovery, settings access, and canonical paths."""

from __future__ import annotations

import json
from pathlib import Path

from .util import StageError

SETTINGS_REL = Path("config") / "settings.json"


def find_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) to the directory holding config/settings.json."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / SETTINGS_REL).is_file():
            return candidate
    raise StageError(
        f"could not find {SETTINGS_REL} above {cur} — run from inside the project"
    )


class Project:
    def __init__(self, root: Path | None = None):
        self.root = find_root(root)
        self.settings_path = self.root / SETTINGS_REL
        self.settings = json.loads(self.settings_path.read_text())

        self.chunks_dir = self.root / "chunks"
        self.takes_dir = self.root / "takes"
        self.stems_dir = self.root / "stems"
        self.premaster_dir = self.root / "premaster"
        self.masters_dir = self.root / "masters"
        self.reports_dir = self.root / "reports"
        self.selections_path = self.root / "config" / "selections.yaml"
        self.manifest_path = self.reports_dir / "manifest.json"
        self.grid_path = self.reports_dir / "grid.json"

    # -- settings access ----------------------------------------------------

    def save_settings(self) -> None:
        self.settings_path.write_text(json.dumps(self.settings, indent=2) + "\n")

    @property
    def pack_path(self) -> Path:
        return self.root / self.settings["pack_file"]

    @property
    def sample_rate(self) -> int:
        return int(self.settings["session"]["sample_rate"])

    @property
    def bit_depth(self) -> int:
        return int(self.settings["session"]["bit_depth"])

    @property
    def tracks(self) -> list[str]:
        counts = self.settings["tracks"]["expected_counts"]
        return list(counts.keys())

    def expected_count(self, track: str) -> int:
        return int(self.settings["tracks"]["expected_counts"][track])

    def tts_profile(self, track: str) -> dict:
        """Resolve a track's TTS profile, following `profile` inheritance."""
        tts = self.settings["tts"]
        prof = dict(tts[track])
        base_name = prof.pop("profile", None)
        if base_name:
            base = dict(tts[base_name])
            base.pop("profile", None)
            base.update(prof)
            prof = base
        return prof

    def respellings(self) -> dict[str, str]:
        """Convention: any settings key `<word>_spelling` respells WORD in TTS
        request text only (never in chunk files)."""
        out = {}
        for key, val in self.settings.items():
            if key.endswith("_spelling") and isinstance(val, str):
                out[key[: -len("_spelling")].upper()] = val
        return out

    def ensure_dirs(self) -> None:
        for d in (self.chunks_dir, self.takes_dir, self.stems_dir,
                  self.premaster_dir, self.masters_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)
        for track in self.tracks:
            (self.chunks_dir / track).mkdir(parents=True, exist_ok=True)
