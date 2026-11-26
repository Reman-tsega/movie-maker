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


def tts(model: str, voice: str, style: str, text: str, key: str | None = None) -> bytes:
    body = {
        "contents": [{"parts": [{"text": f"{style}:\n{text}" if style else text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }

    def call():
        try:
            r = requests.post(API.format(model=model), json=body, timeout=120,
                              headers={"x-goog-api-key": key or os.environ.get("GEMINI_API_KEY", "")})
        except requests.RequestException as e:
            raise Retryable(str(e))
        if r.status_code == 429 and "PerDay" in r.text:
            raise RuntimeError(f"HTTP 429 per day quota: {r.text[:200]}")
        check_http(r)
        part = r.json()["candidates"][0]["content"]["parts"][0]
        return base64.b64decode(part["inlineData"]["data"])

    return with_retries(call, what=f"TTS {model}")


def spoken(shot: dict) -> str:
    """Exactly what is sent to the TTS: bracketed delivery tags (not spoken, E14) + the line."""
    return f"{shot['delivery']} {shot['narration']}" if shot.get("delivery") else shot["narration"]


class DailyQuota(Exception):
    pass


def tts_any(models: list[str], voice: str, style: str, text: str):
    """Try each TTS model in order; a model whose free daily quota is spent is skipped (each
    Gemini model has its own quota, found in FAILURES F3)."""
    errors = []
    keys = [k for k in (os.environ.get("GEMINI_API_KEY"), os.environ.get("GEMINI_API_KEY_2")) if k]
    # each (key's project, model) pair has its own daily quota: same model on the next key first,
    # so the voice stays the same; a different model only when every key is spent
    for m, (ki, key) in ((m, k) for m in models for k in enumerate(keys)):
        try:
            return m, tts(m, voice, style, text, key=key)
        except RuntimeError as e:
            msg = str(e)
            if "429" in msg and "per day" in msg.lower() or "PerDay" in msg:
                errors.append(f"{m} (key {ki + 1}): daily quota spent")
                continue
            raise
    raise DailyQuota("; ".join(errors))


def split_batch(pcm: bytes, n: int, expected_chars: list[int]) -> list[bytes] | None:
    """Cut one long narration into n lines at the n-1 longest pauses. Returns None if the cut
    does not match the text (a segment's length is far from its share of the characters)."""
    import array
    s = array.array("h"); s.frombytes(pcm)
    win = SAMPLE_RATE // 50                      # 20 ms windows
    quiet = [max(abs(x) for x in s[i:i + win]) < 600 for i in range(0, len(s) - win, win)]
    gaps, start = [], None
    for i, q in enumerate(quiet + [False]):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if start > 0 and i < len(quiet):     # ignore leading / trailing silence
                gaps.append((i - start, start, i))
            start = None
    if len(gaps) < n - 1:
        return None
    cuts = sorted(((a + b) // 2) * win for _, a, b in sorted(gaps, reverse=True)[:n - 1])
    bounds = [0] + cuts + [len(s)]
    segs = [s[bounds[k]:bounds[k + 1]].tobytes() for k in range(n)]
    total_c, total_t = sum(expected_chars), len(s)
    for seg, c in zip(segs, expected_chars):
        share = (len(seg) / 2) / total_t / (c / total_c)
        if not 0.4 < share < 2.5:
            return None
    return segs


def batch_generate(models, voice, style, shots, out_dir):
    """One call for all missing lines (saves daily quota: 1 request instead of len(shots))."""
    text = "\n\n".join(spoken(s) for s in shots)
    t0 = time.time()
    used, pcm = tts_any(models, voice, style, text)
    segs = split_batch(pcm, len(shots), [len(s["narration"]) for s in shots])
    log_call("narration", used, shot="batch:" + ",".join(s["id"] for s in shots),
             latency_s=time.time() - t0, status="ok" if segs else "error",
             params={"voice": voice, "lines": len(shots), "mode": "batch"},
             error=None if segs else "could not split batch at pauses")
    if not segs:
        return None
    paths = {}
    for s, seg in zip(shots, segs):
        p = out_dir / f"{s['id']}_{input_hash(used, voice, style, spoken(s))}.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(seg)
        paths[s["id"]] = (p, used)
    print(f"  batch: {len(shots)} lines in one call with {used} ({time.time() - t0:.1f}s)")
    return paths


def main() -> int:
    load_env()
    sb = load_storyboard()
    models = [sb["models"]["tts"]] + sb["models"].get("tts_fallbacks", [])
    voice, style = sb["voice"]["name"], sb["voice"]["style_instruction"]
    out_dir = OUT / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}

    redo = set()
    if "--redo" in sys.argv:                      # e.g. --redo s07: re-record a line made by a fallback
        redo = set(sys.argv[sys.argv.index("--redo") + 1].split(","))

    def cached_file(shot):
        for m in (models[:1] if shot["id"] in redo else models):
            p = out_dir / f"{shot['id']}_{input_hash(m, voice, style, spoken(shot))}.wav"
            if p.exists():
                return p, m
        return None

    missing = [s for s in sb["shots"] if not cached_file(s)]
    if len(missing) > 1 and "--per-line" not in sys.argv:
        batch_generate(models, voice, style, missing, out_dir)   # falls back to per-line below
    for shot in sb["shots"]:
        # cache: prefer a file made by the primary model, else accept one made by a fallback
        hit = cached_file(shot)
        if hit:
            path, used = hit
            log_call("narration", used, shot=shot["id"], cache_hit=True, output=str(path.relative_to(OUT.parent)))
            print(f"  {shot['id']}: cached ({used})")
        else:
            t0 = time.time()
            try:
                used, pcm = tts_any(models, voice, style, spoken(shot))
            except Exception as e:  # noqa: BLE001
                log_call("narration", models[0], shot=shot["id"], latency_s=time.time() - t0,
                         status="error", error=str(e)[:300], params={"voice": voice})
                print(f"  {shot['id']}: FAILED {e}")
                return 1
            path = out_dir / f"{shot['id']}_{input_hash(used, voice, style, spoken(shot))}.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(pcm)
            log_call("narration", used, shot=shot["id"], latency_s=time.time() - t0,
                     status="ok" if used == models[0] else "fallback",
                     params={"voice": voice, "chars": len(shot["narration"])},
                     output=str(path.relative_to(OUT.parent)))
            print(f"  {shot['id']}: generated with {used} in {time.time() - t0:.1f}s")
        manifest[shot["id"]] = {"file": str(path.relative_to(OUT.parent)), "model": used,
                                "duration_s": round(media_duration(path), 3)}
    write_manifest("narration", manifest)
    total = sum(v["duration_s"] for v in manifest.values())
    print(f"narration: {len(manifest)} lines, {total:.1f}s of speech")
    return 0


if __name__ == "__main__":
    sys.exit(main())
