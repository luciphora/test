"""reports/manifest.json — the pipeline's durable memory.

Layout:
{
  "chunks":   { "<ID>": {"track", "sha256", "path"} },
  "takes":    { "<ID>": {"chunk_sha256", "takes": {"take1": {...params...}}} },
  "voice":    { "design_request": {...}, "previews": [...] },
  "stems":    { "isochronic": {...verification...}, "whisper_stem": {...} },
  "assemble": { "night": {...}, "morning": {...}, "anchor": {...} },
  "master":   { "<name>": {...measurements...} }
}
"""

from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text())
    return {}


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
