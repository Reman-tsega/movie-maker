"""Smoke test: call each hosted provider once, log latency to runs.jsonl, report what works.

1. Gemini: list models (finds the exact TTS / text model names available to this key)
2. Gemini TTS: speak one short Amharic sentence
3. Cloudflare Workers AI: one 4-step FLUX image
"""
from __future__ import annotations

import base64
import os
import sys
import time

import requests

from common import OUT, load_env, load_storyboard, log_call

G = "https://generativelanguage.googleapis.com/v1beta"


def main() -> int:
    load_env()
    sb = load_storyboard()
    hdr = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}
    ok = True
    out = OUT / "smoke"
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    try:
        r = requests.get(f"{G}/models?pageSize=200", headers=hdr, timeout=60)
        r.raise_for_status()
        names = [m["name"].split("/")[-1] for m in r.json().get("models", [])]
        tts = [n for n in names if "tts" in n]
        flash = [n for n in names if "flash" in n and "tts" not in n][:8]
        log_call("smoke", "gemini:list-models", latency_s=time.time() - t0, params={"n": len(names)})
        print(f"gemini models OK ({len(names)}). TTS models: {tts}\n  flash text models: {flash}")
        if sb["models"]["tts"] not in names:
            print(f"  ! storyboard models.tts = {sb['models']['tts']} is NOT in this list: update it")
    except Exception as e:  # noqa: BLE001
        ok = False
        log_call("smoke", "gemini:list-models", latency_s=time.time() - t0, status="error", error=str(e)[:300])
        print(f"gemini list FAILED: {e}")

    from narration import tts as speak
    t0 = time.time()
    try:
        pcm = speak(sb["models"]["tts"], sb["voice"]["name"], sb["voice"]["style_instruction"],
                    "ሰላም፤ ይህ የሙከራ ድምፅ ነው።")
        import wave
        with wave.open(str(out / "tts_test.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
        log_call("smoke", sb["models"]["tts"], latency_s=time.time() - t0, params={"voice": sb["voice"]["name"]},
                 output="outputs/smoke/tts_test.wav")
        print(f"gemini TTS OK in {time.time() - t0:.1f}s -> outputs/smoke/tts_test.wav")
    except Exception as e:  # noqa: BLE001
        ok = False
        log_call("smoke", sb["models"]["tts"], latency_s=time.time() - t0, status="error", error=str(e)[:300])
        print(f"gemini TTS FAILED: {e}")

    from keyframes import generate
    t0 = time.time()
    try:
        img = generate(sb["models"]["image"], "a small grey-brown rabbit on a green hill, picture-book style", 7)  # noqa
        (out / "image_test.jpg").write_bytes(img)
        log_call("smoke", sb["models"]["image"], seed=7, latency_s=time.time() - t0, output="outputs/smoke/image_test.jpg")
        print(f"cloudflare image OK in {time.time() - t0:.1f}s -> outputs/smoke/image_test.jpg")
    except Exception as e:  # noqa: BLE001
        ok = False
        log_call("smoke", sb["models"]["image"], latency_s=time.time() - t0, status="error", error=str(e)[:300])
        print(f"cloudflare image FAILED: {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
