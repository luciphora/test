"""Thin ElevenLabs REST client (stdlib only, so the surface is explicit).

Verified against live docs 2026-07:
- POST /v1/text-to-voice/design            (model eleven_ttv_v3) -> previews
- POST /v1/text-to-voice                   create voice from generated_voice_id
- POST /v1/text-to-speech/{voice_id}?output_format=pcm_48000

Config expresses stability/similarity/style as 0-100 intent; the live API
takes 0.0-1.0, so values > 1 are divided by 100. PCM output is 16-bit mono
at the requested rate; PCM >= 44.1 kHz is plan-gated, so we negotiate down
the format ladder on rejection and record what was actually used.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .util import StageError

API_BASE = "https://api.elevenlabs.io"
PCM_LADDER = ["pcm_48000", "pcm_44100", "pcm_32000", "pcm_24000", "pcm_22050", "pcm_16000"]


def require_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise StageError(
            "ELEVENLABS_API_KEY is not set. Export it and re-run: "
            "export ELEVENLABS_API_KEY=..."
        )
    return key


def _request(method: str, path: str, body: dict | None = None,
             query: str = "") -> tuple[bytes, dict]:
    url = f"{API_BASE}{path}{('?' + query) if query else ''}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "xi-api-key": require_api_key(),
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:2000]
        raise StageError(f"ElevenLabs {method} {path} -> HTTP {e.code}: {detail}") from e


def normalize_setting(value: float) -> float:
    return value / 100.0 if value > 1 else float(value)


def voice_settings_from_profile(profile: dict) -> dict:
    return {
        "stability": normalize_setting(profile["stability"]),
        "similarity_boost": normalize_setting(profile["similarity"]),
        "style": normalize_setting(profile.get("style", 0)),
        "speed": float(profile["speed"]),
    }


def design_previews(voice_description: str, sample_text: str | None = None,
                    model_id: str = "eleven_ttv_v3") -> dict:
    body: dict = {"voice_description": voice_description, "model_id": model_id}
    if sample_text and 100 <= len(sample_text) <= 1000:
        body["text"] = sample_text
    else:
        body["auto_generate_text"] = True
    raw, _ = _request("POST", "/v1/text-to-voice/design", body)
    return json.loads(raw)


def create_voice_from_preview(generated_voice_id: str, voice_name: str,
                              voice_description: str) -> dict:
    raw, _ = _request("POST", "/v1/text-to-voice", {
        "generated_voice_id": generated_voice_id,
        "voice_name": voice_name,
        "voice_description": voice_description,
    })
    return json.loads(raw)


def tts_pcm(voice_id: str, text: str, model_id: str, voice_settings: dict,
            preferred_formats: list[str] | None = None) -> tuple[bytes, dict]:
    """Generate speech, negotiating the highest PCM format the plan allows.

    Returns (pcm16le_bytes, info) where info records the format and request id
    actually used — the manifest stores info, not the config intent.
    """
    ladder = preferred_formats or PCM_LADDER
    last_err: StageError | None = None
    for fmt in ladder:
        try:
            raw, headers = _request(
                "POST", f"/v1/text-to-speech/{voice_id}",
                {"text": text, "model_id": model_id, "voice_settings": voice_settings},
                query=f"output_format={fmt}",
            )
            info = {
                "output_format": fmt,
                "sample_rate": int(fmt.split("_")[1]),
                "model_id": model_id,
                "voice_settings": voice_settings,
                "request_id": headers.get("request-id") or headers.get("Request-Id"),
                "char_count": len(text),
            }
            return raw, info
        except StageError as e:
            msg = str(e)
            # Plan-gated format: step down the ladder. Anything else is fatal.
            if "HTTP 4" in msg and ("format" in msg.lower() or "tier" in msg.lower()
                                    or "subscription" in msg.lower()):
                last_err = e
                continue
            raise
    raise StageError(f"no PCM output format accepted; last error: {last_err}")
