"""QA for narration: transcribe every line with a Gemini text model and flag non-Amharic speech
or wrong length. Added after FAILURES F4, where the TTS read the English style instruction aloud
for 11 s and nobody could tell from the file alone."""
import base64
import json
import os
import sys
import time

import requests

from common import OUT, PRICE_GEMINI3_FLASH_AUDIO_IN, load_env, load_storyboard, log_call, read_manifest

MODEL = "gemini-3-flash-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def main() -> int:
    load_env()
    sb = load_storyboard()
    narr = read_manifest("narration")
    parts = []
    for s in sb["shots"]:
        parts += [{"text": f"Audio {s['id']}:"},
                  {"inline_data": {"mime_type": "audio/wav",
                                   "data": base64.b64encode((OUT.parent / narr[s["id"]]["file"]).read_bytes()).decode()}}]
    parts.append({"text": "For each audio return JSON lines only: "
                          '{"id": ..., "languages": [...], "transcript": ...}'})
    t0 = time.time()
    r = requests.post(URL, headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")},
                      json={"contents": [{"parts": parts}]}, timeout=300)
    ok = r.ok
    usage = r.json().get("usageMetadata", {}) if ok else {}
    log_call("narration_check", MODEL, latency_s=time.time() - t0, status="ok" if ok else "error",
             params={"input_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount")},
             cost_usd=round((usage.get("promptTokenCount") or 0) * PRICE_GEMINI3_FLASH_AUDIO_IN, 6),
             error=None if ok else r.text[:300])
    if not ok:
        print(f"check failed: HTTP {r.status_code}")
        return 1
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    report, bad = [], 0
    for line in text.splitlines():
        line = line.strip().strip(",")
        if not line.startswith("{"):
            continue
        row = json.loads(line)
        sid = row["id"].replace("Audio", "").strip()
        dur = narr.get(sid, {}).get("duration_s", 0)
        words = len(next(s["narration"] for s in sb["shots"] if s["id"] == sid).split())
        flags = []
        # the model labels the language inconsistently between runs: "Amharic", "am", "amh" (ISO 639-3)
        if any(l.lower().split()[0].strip("()") not in ("amharic", "am", "amh") for l in row["languages"]):
            flags.append("non-Amharic speech")
        if words and dur / words > 1.2:
            flags.append(f"slow: {dur / words:.1f} s/word")
        bad += bool(flags)
        report.append({"id": sid, "duration_s": dur, "languages": row["languages"],
                       "transcript": row["transcript"], "flags": flags})
        print(f"  {sid}: {'OK' if not flags else 'CHECK ' + ', '.join(flags)} | {row['transcript']}")
    (OUT / "narration" / "check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"narration check: {len(report) - bad}/{len(report)} lines OK")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
