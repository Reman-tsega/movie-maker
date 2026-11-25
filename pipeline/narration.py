"""Stage: narration. One Gemini TTS call per shot -> outputs/narration/<shot>_<hash>.wav.

Cache key = (model, voice, style instruction, narration text). Changing one line
regenerates only that shot.
"""
from __future__ import annotations

import base64
import os
import sys
import time
import wave

import requests

from common import (OUT, Retryable, check_http, input_hash, load_env, load_storyboard,
                    log_call, media_duration, with_retries, write_manifest)

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
SAMPLE_RATE = 24000  # Gemini TTS returns 24 kHz, 16-bit, mono PCM


def tts(model: str, voice: str, style: str, text: str) -> bytes:
    body = {
        "contents": [{"parts": [{"text": f"{style}:\n{text}"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }

    def call():
        try:
            r = requests.post(API.format(model=model), json=body, timeout=120,
                              headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")})
        except requests.RequestException as e:
            raise Retryable(str(e))
        check_http(r)
        part = r.json()["candidates"][0]["content"]["parts"][0]
        return base64.b64decode(part["inlineData"]["data"])

    return with_retries(call, what=f"TTS {model}")


def main() -> int:
    load_env()
    sb = load_storyboard()
    model, voice, style = sb["models"]["tts"], sb["voice"]["name"], sb["voice"]["style_instruction"]
    out_dir = OUT / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for shot in sb["shots"]:
        h = input_hash(model, voice, style, shot["narration"])
        path = out_dir / f"{shot['id']}_{h}.wav"
        if path.exists():
            log_call("narration", model, shot=shot["id"], cache_hit=True, output=str(path.relative_to(OUT.parent)))
            print(f"  {shot['id']}: cached")
        else:
            t0 = time.time()
            try:
                pcm = tts(model, voice, style, shot["narration"])
            except Exception as e:  # noqa: BLE001
                log_call("narration", model, shot=shot["id"], latency_s=time.time() - t0,
                         status="error", error=str(e)[:300], params={"voice": voice})
                print(f"  {shot['id']}: FAILED {e}")
                return 1
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(pcm)
            log_call("narration", model, shot=shot["id"], latency_s=time.time() - t0,
                     params={"voice": voice, "chars": len(shot["narration"])},
                     output=str(path.relative_to(OUT.parent)))
            print(f"  {shot['id']}: generated in {time.time() - t0:.1f}s")
        manifest[shot["id"]] = {"file": str(path.relative_to(OUT.parent)), "duration_s": round(media_duration(path), 3)}
    write_manifest("narration", manifest)
    total = sum(v["duration_s"] for v in manifest.values())
    print(f"narration: {len(manifest)} lines, {total:.1f}s of speech")
    return 0


if __name__ == "__main__":
    sys.exit(main())
