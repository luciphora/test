# identity-audio

Pipeline that turns `BYMOE_250K_Identity_Installation_Production_Pack.md` into
four finished audio deliverables. **CLAUDE.md is the single source of truth for
process; the pack file is the single source of truth for script text and
creative intent.**

## Quickstart

```bash
pip install -e .            # or: pip install -r requirements.txt
export ELEVENLABS_API_KEY=...
# place the pack file at the repo root (filename in config/settings.json)

python -m pipeline status   # per-stage done/pending + next open gate
python -m pipeline run      # runs stages in order, halts at the next gate
```

Without `pip install -e .`, prefix commands with `PYTHONPATH=scripts`.

## Stages & gates

| stage | command | gate |
|---|---|---|
| 0 chunk | `python -m pipeline chunk` | |
| 1 voice | `python -m pipeline voice` | ⛔ GATE 1 — pick voice_id |
| 2 takes | `python -m pipeline takes` | |
| 3 qa | `python -m pipeline qa` | ⛔ GATE 2 — confirm selections.yaml |
| 4 stems | `python -m pipeline stems` | |
| 5 assemble | `python -m pipeline assemble` | |
| 6 master | `python -m pipeline master` | ⛔ GATE 3 — Speaker QA by ear |

Gates are hard stops for human input; the pipeline never auto-advances
through them. After Gate 1, either write a known `voice_id` into
`config/settings.json` or promote a preview:
`python -m pipeline voice --adopt <generated_voice_id> <voice name>`.

## Tests

```bash
pip install pytest
pytest
```

Tests cover the pack chunker (against a generic fixture pack), the DSP core
(BS.1770 loudness, filters), isochronic synthesis verification, and the
whisper-stem placement constraints. Nothing in `tests/` or `scripts/` is
project-specific — everything BYMOE lives in the pack file and `config/`.
