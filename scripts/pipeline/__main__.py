"""CLI: python -m pipeline chunk|voice|takes|qa|stems|assemble|master|run|status.

Each stage is independently runnable and resume-safe. `run` executes stages
in order and halts at the next unmet gate with the waiting-on message.
"""

from __future__ import annotations

import sys

from . import assemble, chunk, master, qa, stems, takes, voice
from .config import Project
from .util import GateOpen, StageError, say

STAGES = [
    ("chunk", chunk),
    ("voice", voice),      # ⛔ GATE 1
    ("takes", takes),
    ("qa", qa),            # ⛔ GATE 2
    ("stems", stems),
    ("assemble", assemble),
    ("master", master),    # ⛔ GATE 3
]
GATES = {"voice": "GATE 1", "qa": "GATE 2", "master": "GATE 3"}


def _project() -> Project:
    return Project()


def cmd_status() -> int:
    project = _project()
    open_gate = None
    for name, mod in STAGES:
        done = False
        try:
            done = mod.is_done(project)
        except Exception:
            done = False
        marker = "done   " if done else "pending"
        gate = f"  ({GATES[name]})" if name in GATES else ""
        say(f"  {name:<9} {marker}{gate}")
        if not done and open_gate is None and name in GATES:
            open_gate = GATES[name]
    if open_gate:
        say(f"\nNext gate: {open_gate}")
    return 0


def cmd_run() -> int:
    project = _project()
    for name, mod in STAGES:
        if mod.is_done(project):
            say(f"[{name}] already done — skipping")
            continue
        say(f"[{name}] running...")
        try:
            mod.run(project)
        except GateOpen as g:
            say(f"\n⛔ {g.gate} — pipeline halted, waiting on you:")
            say(f"   {g.message}")
            return 2
        project = _project()  # re-read settings a stage may have updated
    say("All stages done.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        say("usage: python -m pipeline "
            "chunk|voice|takes|qa|stems|assemble|master|run|status")
        return 64
    cmd, *rest = argv
    try:
        if cmd == "status":
            return cmd_status()
        if cmd == "run":
            return cmd_run()
        if cmd == "voice" and rest[:1] == ["--adopt"]:
            if len(rest) != 3:
                say("usage: python -m pipeline voice --adopt <generated_voice_id> <name>")
                return 64
            voice.adopt(_project(), rest[1], rest[2])
            return 0
        for name, mod in STAGES:
            if cmd == name:
                mod.run(_project())
                return 0
        say(f"unknown stage: {cmd}")
        return 64
    except GateOpen as g:
        say(f"\n⛔ {g.gate} — pipeline halted, waiting on you:")
        say(f"   {g.message}")
        return 2
    except StageError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
