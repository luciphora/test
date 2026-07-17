"""Shared helpers: time parsing, hashing, gate signalling."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


class GateOpen(Exception):
    """Raised when a stage reaches a gate: a hard stop for human input.

    The message is the exact waiting-on text to show the operator.
    """

    def __init__(self, gate: str, message: str):
        self.gate = gate
        self.message = message
        super().__init__(f"{gate}: {message}")


class StageError(Exception):
    """A stage failed its own assertions. Fail loudly, never continue."""


def parse_time(value: str | int | float) -> float:
    """Parse 'm:ss' / 'mm:ss' / 'h:mm:ss' (or a bare number) into seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"unparseable time: {value!r}")
    secs = 0.0
    for part in parts:
        secs = secs * 60 + float(part)
    return secs


def fmt_time(seconds: float) -> str:
    m, s = divmod(round(seconds), 60)
    return f"{m}:{s:02d}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def say(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    raise StageError(msg)


_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def normalize_words(text: str) -> list[str]:
    """Lowercased word tokens, punctuation and inline [audio tags] stripped."""
    text = re.sub(r"\[[^\]]*\]", " ", text)  # inline audio tags are not spoken
    return [w.lower() for w in _WORD_RE.findall(text)]
