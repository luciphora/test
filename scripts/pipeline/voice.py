"""Stage 1 — voice.  GATE 1.

Voice design previews from the pack's Voice Design prompt, verbatim.
Halts until config voice_id is non-null.
"""

from __future__ import annotations

import base64
import re

from . import eleven, manifest
from .config import Project
from .pack import parse_pack
from .util import GateOpen, StageError, say

GATE_MESSAGE = ("Listen to the previews. "
                "Write the chosen voice_id into config/settings.json.")


def _voice_design_prompt(project: Project) -> str:
    pack = parse_pack(project.pack_path)
    pattern = project.settings["pack_headings"]["voice_design"]
    found = pack.section_matching(pattern)
    if found is None:
        # the prompt may live under an H2 inside a track section
        for title, body in pack.sections.items():
            if re.search(pattern, body):
                found = (title, body)
                break
    if found is None:
        raise StageError(
            "could not locate the Voice Design section in the pack "
            f"(heading pattern: {pattern})"
        )
    _, body = found
    # Prefer a fenced block (any language) as the verbatim prompt; otherwise
    # the section's prose.
    fence = re.search(r"```\w*\n(.*?)```", body, re.DOTALL)
    prompt = (fence.group(1) if fence else body).strip()
    if not prompt:
        raise StageError("Voice Design section is empty")
    return prompt


def _sample_text(project: Project) -> str | None:
    """Longest chunk text, trimmed to the API's 100-1000 char preview window."""
    mani = manifest.load(project.manifest_path)
    best = ""
    for entry in mani.get("chunks", {}).values():
        text = (project.root / entry["path"]).read_text().strip()
        if len(text) > len(best):
            best = text
    if len(best) < 100:
        return None
    return best[:1000]


def run(project: Project) -> None:
    if project.settings.get("voice_id"):
        say(f"Stage 1 done: voice_id already set ({project.settings['voice_id']}).")
        return

    eleven.require_api_key()
    prompt = _voice_design_prompt(project)
    previews_dir = project.takes_dir / "voice_previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    say("Requesting voice design previews (prompt taken verbatim from the pack)...")
    result = eleven.design_previews(prompt, _sample_text(project))
    previews = result.get("previews", [])
    if not previews:
        raise StageError("voice design returned no previews")

    notes = ["# Voice previews — listening notes", "",
             "Prompt used (verbatim from pack):", "", "> " + prompt.replace("\n", "\n> "),
             ""]
    mani = manifest.load(project.manifest_path)
    saved = []
    for i, p in enumerate(previews, 1):
        ext = "mp3" if "mp3" in (p.get("media_type") or "mp3") else "bin"
        path = previews_dir / f"preview{i}.{ext}"
        path.write_bytes(base64.b64decode(p["audio_base_64"]))
        meta = {k: p.get(k) for k in ("generated_voice_id", "media_type",
                                      "duration_secs", "language")}
        saved.append(meta)
        notes.append(
            f"- **preview{i}.{ext}** — generated_voice_id `{meta['generated_voice_id']}`, "
            f"{meta.get('duration_secs', '?')}s. "
            "Listen for: overall timbre, pacing at rest, warmth vs. clarity — "
            "note here what differs from the other previews:"
        )
        notes.append(f"  - [ ] note for preview{i}: ")
    (previews_dir / "notes.md").write_text("\n".join(notes) + "\n")

    mani["voice"] = {"design_prompt_chars": len(prompt), "previews": saved}
    manifest.save(project.manifest_path, mani)

    say(f"Saved {len(previews)} previews to {previews_dir.relative_to(project.root)}/ "
        "with notes.md.")
    say("To adopt a preview as a saved voice, its generated_voice_id must be "
        "promoted via the create-voice endpoint (python -m pipeline voice --adopt "
        "<generated_voice_id> <name>), or pick an existing voice_id.")
    raise GateOpen("GATE 1", GATE_MESSAGE)


def adopt(project: Project, generated_voice_id: str, name: str) -> None:
    """Promote a chosen preview to a saved voice and write voice_id to config."""
    prompt = _voice_design_prompt(project)
    result = eleven.create_voice_from_preview(generated_voice_id, name, prompt)
    voice_id = result.get("voice_id")
    if not voice_id:
        raise StageError(f"create-voice returned no voice_id: {result}")
    project.settings["voice_id"] = voice_id
    project.save_settings()
    say(f"voice_id {voice_id} written to config/settings.json.")


def is_done(project: Project) -> bool:
    return bool(project.settings.get("voice_id"))
