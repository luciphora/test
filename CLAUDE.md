# CLAUDE.md — Identity Audio Production Pipeline

Build and run a local pipeline that turns `BYMOE_250K_Identity_Installation_Production_Pack.md` into four finished audio deliverables: the 30-minute night master (narration + whisper stem + isochronic tone), the morning incantation, the pre-call anchor, and a QA report. The pack file is the **single source of truth** for all script text and creative intent. This file is the single source of truth for process.

**Terminology guard:** "Whisper (ASR)" always means speech-to-text transcription (faster-whisper). "Whisper stem" always means Track 2 of the pack. Never use the bare word "whisper" in code, filenames, or reports.

The pipeline has 7 stages and 3 **gates**. A gate is a hard stop for human input — the pipeline must halt and tell Moe exactly what it's waiting for. Never auto-advance through a gate.

---

## Environment

- macOS on Apple Silicon (M4 Max). Python 3.11+, `ffmpeg` via Homebrew.
- Python deps: `elevenlabs`, `numpy`, `soundfile`, `soxr`, `faster-whisper`, `pyyaml`.
- `ELEVENLABS_API_KEY` must be set in env. If missing, stop at Stage 1 with a clear message.
- Verify the current ElevenLabs API surface (model IDs, v3 parameter names, max PCM output format on this account's plan) against live docs before writing Stage 1–2 code. The pack's numeric settings express intent; record the actual parameters used in the manifest.

## Repo layout (target)

```
identity-audio/
├── CLAUDE.md
├── BYMOE_250K_Identity_Installation_Production_Pack.md
├── config/
│   ├── settings.json          # all tunable parameters (below)
│   └── selections.yaml        # Gate 2 output: chunk → chosen take
├── chunks/{night,whisper_stem,morning,anchor}/   # Stage 0 output
├── takes/                     # Stage 2 output: {track}/{chunk_id}/take{1..3}.wav
├── stems/                     # Stage 4 output: isochronic.wav, whisper_stem.wav
├── premaster/                 # Stage 5 output
├── masters/                   # Stage 6 output: WAV + M4A
├── reports/                   # take_report.md, final_qa.md, manifest.json
└── scripts/                   # pipeline code, runnable as python -m pipeline <stage>
```

## config/settings.json (initial values — transcribed from the pack)

```json
{
  "voice_id": null,
  "bymoe_spelling": "BYMOE",
  "session": { "sample_rate": 48000, "bit_depth": 24 },
  "tts": {
    "model": "eleven_v3",
    "night":        { "stability": 60, "similarity": 75, "style": 0, "speed": 0.88 },
    "whisper_stem": { "stability": 65, "similarity": 75, "style": 0, "speed": 0.90,
                      "prefix_tag": "[whispering, calm and intimate]" },
    "morning":      { "stability": 50, "similarity": 75, "style": 0, "speed": 0.97 },
    "anchor":       { "profile": "morning", "speed": 0.95 },
    "takes_per_chunk": 3
  },
  "isochronic": { "carrier_hz": 240, "pulse_hz": 4.0, "depth": 0.90,
                  "fade_in_s": 45, "fade_out_start": "24:00", "silent_by": "27:30" },
  "whisper_stem_layer": { "start": "6:00", "end": "24:00",
                          "gap_s": [5, 12], "loop_orders": 3, "seed": 250 },
  "levels_db_below_narration": { "whisper_stem": 27, "isochronic": 29, "ambience": 25 },
  "ambience": { "enabled": false },
  "narration_chain": { "hpf_hz": 75, "mud_cut": { "hz": 250, "db": -1.5, "q": 1.2 },
                       "comp_ratio": 2.0, "comp_gr_db": 3,
                       "premaster_lufs": -20, "premaster_peak_dbfs": -6 },
  "duck": { "gr_db": 1.5, "attack_ms": 50, "release_ms": 800 },
  "master": { "lufs": -19, "true_peak_dbtp": -1.0 },
  "pronunciation_watchlist": ["BYMOE", "Alhamdulillah", "Tawakkul", "Sabr",
                               "Salah", "Amanah", "Rhode Island", "New England"]
}
```

---

## Stage 0 — chunk

Parse the pack. Every fenced ```text block under a chunk heading (`## N01 — Arrival | 0:00–1:00`) becomes `chunks/{track}/{ID}.txt`, wording verbatim, inline audio tags preserved, everything outside the fences excluded. Build `reports/grid.json` from the chunk headings: `{id, track, start_s, end_s}`. Compute sha256 per chunk file; store in `reports/manifest.json`.

Track mapping: N01–N25 → night, W01–W04 → whisper_stem, M01–M06 → morning, the Track 4 block → anchor.

**Done when:** 36 chunk files exist (25 + 4 + 6 + 1), every night/morning chunk has a grid entry, manifest has 36 hashes. Assert these counts; fail loudly on mismatch.

## Stage 1 — voice  ⛔ GATE 1

Call the ElevenLabs voice design endpoint with the pack's Voice Design prompt verbatim. Save the returned previews to `takes/voice_previews/` with a short listening note per preview (what differs).

**Stop.** Print: "Listen to the previews. Write the chosen voice_id into config/settings.json." Do not proceed until `voice_id` is non-null.

## Stage 2 — takes

For every chunk, generate `takes_per_chunk` takes with the track's TTS profile. Whisper_stem chunks get `prefix_tag` prepended to the request text (not written into the chunk file). Request the highest PCM output format the plan allows; resample to 48 kHz / 24-bit with soxr; never transcode from MP3. Write per-take metadata (params actually sent, request ID, char count) to the manifest.

**Idempotency (hash rule):** before generating, compare the chunk's current sha256 to the manifest. Unchanged + takes on disk → skip. Changed → regenerate that chunk only and invalidate its selection in `selections.yaml`. Never silently regenerate a confirmed take.

**Done when:** every chunk has all takes on disk at 48 kHz / 24-bit and a manifest entry.

## Stage 3 — qa  ⛔ GATE 2

Transcribe every take with faster-whisper (multilingual `medium`). Per take, compute: duration, effective wpm, normalized word-diff vs the chunk text, and watchlist flags — any watchlist word whose transcript token differs gets flagged for human ear (ASR can flag drift on the Arabic terms; it cannot approve them). `bymoe_spelling` deviations are whitelisted in the diff.

Rank takes per chunk: clean watchlist > zero unflagged word substitutions > duration fits grid slot > wpm closest to profile speed intent. Emit `reports/take_report.md` (table per chunk, flags first) and prefill `config/selections.yaml` with top-ranked takes marked `confirmed: false`.

**Stop.** Print: "Review take_report.md, audition flagged takes, edit selections.yaml, set confirmed: true." Tone is Moe's call — ranking is advisory only.

**Done when:** `selections.yaml` has `confirmed: true` and exactly one take per chunk.

## Stage 4 — stems

**Isochronic tone** — synthesize with numpy, don't source samples. `signal(t) = sin(2π·240·t) · e(t)` where `e(t) = (1−d) + d·(0.5 − 0.5·cos(2π·4·t))`, d = depth. 30:00 long, 45 s fade-in from 0:00, fade-out begins 24:00, digital silence by 27:30. Render identical L/R (dual mono).
*Done when:* L−R null test is silent, FFT peak sits at 240 Hz, measured envelope rate = 4.00 Hz, fades land on the configured timestamps.

**Whisper stem** — slice the selected W-block takes into single statements on silences ≥ 400 ms below −45 dBFS; if slicing yields the wrong statement count for any block, fall back to regenerating that block one statement per request. Build a seeded placement timeline from 6:00 to 24:00: a loop = every statement from W01–W04 exactly once; three shuffled loop orders; gaps uniform-random in `gap_s`; the exact revenue statement appears exactly once per loop; statements never overlap. Save the placement JSON, then render the stem.
*Done when:* placement JSON passes all four constraints programmatically and the rendered stem matches it.

**Ambience** — only if `ambience.enabled`. Default stays off.

## Stage 5 — assemble

**Night pre-master:** place each selected take at its grid `start_s`; pad tail silence to the next grid start. If a take overruns its slot, borrow from the following gap and log it in the report — never time-stretch, never cut words. Joins get 25 ms equal-power crossfades over a glue bed: try extracting inter-phrase noise floor from the selected takes; if the floor is below −80 dBFS (digital black), synthesize a −68 dBFS brown-noise glue bed instead.

Narration bus chain, in order: HPF 75 Hz → mud cut per config → light de-ess → 2:1 compression (≈3 dB GR) → gain to −20 LUFS integrated / −6 dBFS peaks.

Layer at offsets from the narration's measured integrated LUFS per `levels_db_below_narration`. Duck isochronic (+ ambience if on) under active narration by `duck.gr_db` using an envelope follower with the configured attack/release — GR must never exceed 2 dB.

**Morning pre-master:** M01–M06 on their grid, narration chain only — no stem layers.
**Anchor pre-master:** single chunk, narration chain, 0.5 s head / 1.0 s tail silence.

**Done when:** three pre-master WAVs exist; night duration is 30:00 ± 2 s; a layer-level table in the report confirms each stem's offset is within its configured value ± 1 dB.

## Stage 6 — master  ⛔ GATE 3

Two-pass ffmpeg loudnorm to `master.lufs` / `master.true_peak_dbtp` on each pre-master → `masters/*.wav` (48 kHz / 24-bit) plus 256 kbps M4A copies. Measure the results with ebur128 and write `reports/final_qa.md`: for every row of the pack's **Final Production Checklist**, an automated verdict where machine-checkable (positive-wording rows are satisfied by verbatim chunking; timing, fade, level, and constraint rows are measured) and an explicit `MANUAL` marker where only ears can judge.

**Stop.** Print the pack's Speaker QA checklist (phone speaker at bedside distance, small Bluetooth speaker, over-ear headphones, low-volume mono) as the final manual test.

**Done when:** every master measures within ±0.5 LU of target with true peak ≤ −1.0 dBTP, and `final_qa.md` is written.

---

## Decisions already made — do not re-litigate

1. **The grid wins.** Chunk-heading timestamps are the timing truth; the pack's wpm ranges (76–82 vs 72–78) are generation guidance only, and the conflict between them is void — timing is met by adjusting silence between complete thoughts, exactly as the pack's Track 1 header instructs.
2. **Script text is immutable.** Fix problems by regenerating takes, never by rewording chunks. Sole exception: `bymoe_spelling` may respell BYMOE in the TTS request text if the default gets mangled.
3. **Take speeds** are fixed at the midpoints in config, not ranges.
4. **Anchor** uses the morning TTS profile at 0.95.
5. **PCM path only** — highest plan format, soxr to 48 kHz.
6. Business-imagery containment (nothing past N23's start) is enforced by the grid + verbatim chunking; no additional content filter is needed or permitted.

## Do not

- Advance through a gate, auto-confirm selections, or regenerate a confirmed take.
- Overlap or stack whisper-stem statements.
- Time-stretch narration or master hotter than −18 LUFS.
- Add, remove, or paraphrase any spoken words.

## CLI surface

`python -m pipeline chunk | voice | takes | qa | stems | assemble | master` — each stage is independently runnable and resume-safe. `python -m pipeline run` executes stages in order and halts at the next unmet gate with the waiting-on message. `python -m pipeline status` prints per-stage done/pending and any open gate.

## Later: lifting this into the `audio-production-pack` skill

Keep the pipeline code pack-agnostic from the start: no BYMOE strings in `scripts/` — everything project-specific lives in the pack file and `config/`. The **pack format contract** the chunker depends on: H1 track sections, chunk headings shaped `## <ID> — <Name> | m:ss–m:ss`, fenced ```text blocks as the only spoken content, and per-track settings sections. When this project ships and holds up, the skill is: `scripts/` + the Pipeline and Decisions sections of this file as SKILL.md steps (each stage's *Done when* is already the completion criterion), with the BYMOE pack as the worked example. Model-invoked, description keyed on: turning a scripted audio production pack (hypnosis, meditation, incantation, narration) into finished masters via ElevenLabs.
