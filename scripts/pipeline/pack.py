"""Parser for the pack format contract.

Contract (see CLAUDE.md "Later" section):
- H1 sections delimit tracks.
- Chunk headings shaped `## <ID> — <Name> | m:ss–m:ss` (the time span may be
  absent on non-gridded blocks, e.g. a single anchor block).
- Fenced ```text blocks are the ONLY spoken content; wording is verbatim,
  inline audio tags preserved, everything outside the fences excluded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .util import StageError, parse_time

# em dash, en dash, or hyphen both as ID/name separator and time-span separator
_CHUNK_HEADING = re.compile(
    r"^##\s+(?P<id>[A-Za-z][A-Za-z0-9_]*)\s*[—–-]\s*(?P<name>[^|]+?)"
    r"(?:\s*\|\s*(?P<t0>\d+:\d{2})\s*[—–-]\s*(?P<t1>\d+:\d{2})\s*)?$"
)
_H1 = re.compile(r"^#\s+(?P<title>.+?)\s*$")
_H2 = re.compile(r"^##\s+")
_FENCE_OPEN = re.compile(r"^```(?P<lang>\w*)\s*$")
_FENCE_CLOSE = re.compile(r"^```\s*$")


@dataclass
class Chunk:
    id: str
    name: str
    section: str            # owning H1 title
    text: str               # verbatim fenced ```text content
    start_s: float | None = None
    end_s: float | None = None


@dataclass
class Pack:
    chunks: list[Chunk] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)  # H1 title -> raw body

    def section_matching(self, pattern: str) -> tuple[str, str] | None:
        rx = re.compile(pattern)
        for title, body in self.sections.items():
            if rx.search(title):
                return title, body
        return None


def _fenced_text_blocks(lines: list[str]) -> list[str]:
    """All fenced blocks tagged `text` (or untagged) in a run of lines."""
    blocks, buf, lang = [], None, None
    for line in lines:
        if buf is None:
            m = _FENCE_OPEN.match(line)
            if m:
                lang = m.group("lang") or "text"
                buf = []
        elif _FENCE_CLOSE.match(line):
            if lang == "text":
                blocks.append("\n".join(buf).strip("\n"))
            buf, lang = None, None
        else:
            buf.append(line)
    return blocks


def parse_pack(path: Path) -> Pack:
    if not path.is_file():
        raise StageError(f"pack file not found: {path}")
    lines = path.read_text().splitlines()

    pack = Pack()
    section_title = ""
    section_lines: list[str] = []
    # (heading match, lines under it) for the chunk currently being collected
    open_chunk: tuple[re.Match, list[str]] | None = None
    in_fence = False

    def close_chunk() -> None:
        nonlocal open_chunk
        if open_chunk is None:
            return
        m, body = open_chunk
        blocks = _fenced_text_blocks(body)
        if blocks:
            pack.chunks.append(Chunk(
                id=m.group("id"),
                name=m.group("name").strip(),
                section=section_title,
                text="\n\n".join(blocks),
                start_s=parse_time(m.group("t0")) if m.group("t0") else None,
                end_s=parse_time(m.group("t1")) if m.group("t1") else None,
            ))
        open_chunk = None

    def close_section() -> None:
        nonlocal section_lines
        if section_title:
            pack.sections[section_title] = "\n".join(section_lines)
        section_lines = []

    for line in lines:
        if _FENCE_OPEN.match(line) and not in_fence:
            in_fence = True
        elif _FENCE_CLOSE.match(line) and in_fence:
            in_fence = False
        elif not in_fence:
            h1 = _H1.match(line)
            if h1:
                close_chunk()
                close_section()
                section_title = h1.group("title")
                continue
            if _H2.match(line):
                close_chunk()
                ch = _CHUNK_HEADING.match(line.rstrip())
                if ch:
                    open_chunk = (ch, [])
                section_lines.append(line)
                continue
        if open_chunk is not None:
            open_chunk[1].append(line)
        section_lines.append(line)

    close_chunk()
    close_section()

    if not pack.chunks:
        raise StageError(
            f"{path.name}: no chunks found — expected `## <ID> — <Name> | m:ss–m:ss` "
            "headings with fenced ```text blocks"
        )
    return pack


def track_for_chunk(chunk: Chunk, tracks_cfg: dict) -> str | None:
    """Map a chunk to its track: by ID prefix first, then by H1 section regex."""
    prefixes = tracks_cfg.get("id_prefixes", {})
    for prefix, track in sorted(prefixes.items(), key=lambda kv: -len(kv[0])):
        if chunk.id.upper().startswith(prefix.upper()):
            return track
    for pattern, track in tracks_cfg.get("section_map", {}).items():
        if re.search(pattern, chunk.section):
            return track
    return None
