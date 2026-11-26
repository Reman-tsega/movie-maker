"""Stage 1: script. Turns storyboard.json into a readable screenplay and checks the subtitles.

  python pipeline/script.py  ->  outputs/script/script_<hash>.md (+ manifest.json)

- The screenplay lists every shot: beat, reason, shot size, minimum length, delivery tags, the
  Amharic narration and the English subtitle. It is the document a person reviews before any
  voice or image is spent.
- One Gemini text call back-translates all Amharic lines into English, placed next to each
  subtitle, so a reviewer who doesn't read Amharic can check that the subtitle says the same thing.
  If that call fails (no key, quota), the screenplay is still written and the failure is logged:
  this stage never blocks the film.
Cache key: (model, every narration line, every subtitle, this script's source).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import requests

from common import (OUT, PRICE_GEMINI3_FLASH_AUDIO_IN, code_version, input_hash, load_env,
                    load_storyboard, log_call, write_manifest)

MODEL = "gemini-3-flash-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def back_translate(lines: dict[str, str]) -> tuple[dict[str, str], dict]:
    prompt = ("Translate each Amharic line into plain English, literally, one line per id. "
              "Return JSON only: {\"s01\": \"...\", ...}\n" +
              "\n".join(f"{k}: {v}" for k, v in lines.items()))
    r = requests.post(URL, headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}, timeout=120,
                      json={"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"responseMimeType": "application/json"}})
    r.raise_for_status()
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(re.sub(r"^```(json)?|```$", "", text.strip())), data.get("usageMetadata", {})


def main() -> int:
    load_env()
    sb = load_storyboard()
    lines = {s["id"]: re.sub(r"\[[^\]]*\]\s*", "", s["narration"]) for s in sb["shots"]}
    h = input_hash(MODEL, lines, {s["id"]: s["subtitle_en"] for s in sb["shots"]},
                   [(s["id"], s["reason"], s.get("delivery")) for s in sb["shots"]], code_version(__file__))
    out_dir = OUT / "script"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"script_{h}.md"
    rel = str(path.relative_to(OUT.parent))
    if path.exists():
        log_call("script", MODEL, cache_hit=True, output=rel)
        print(f"script: cached ({rel})")
        write_manifest("script", {"file": rel})
        return 0

    t0 = time.time()
    back, usage, err = {}, {}, None
    try:
        back, usage = back_translate(lines)
    except Exception as e:  # noqa: BLE001  (the screenplay is still useful without it)
        err = str(e)[:300]
    log_call("script", MODEL, latency_s=time.time() - t0, status="ok" if back else "error", error=err,
             params={"task": "back-translate narration", "lines": len(lines),
                     "input_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount")},
             cost_usd=round((usage.get("promptTokenCount") or 0) * PRICE_GEMINI3_FLASH_AUDIO_IN, 6),
             output=rel)

    md = [f"# {sb['title']}: screenplay", "", f"*{sb.get('logline', '')}*", "",
          f"**Audience:** {sb['audience']}", "", f"**Intent:** {sb['intent']}", "",
          f"**Voice:** {sb['models']['tts']} · {sb['voice']['name']} · language {sb['language']}", ""]
    for s in sb["shots"]:
        md += [f"## {s['id']}: {s['beat']} ({s['shot_size']}, ≥ {s['duration_s']} s)",
               f"- **Why this shot:** {s['reason']}",
               f"- **Characters:** {', '.join(s['characters']) or 'none'} · **Motion:** {s['motion']['mode']}",
               f"- **Delivery:** {s.get('delivery', '(none)')}",
               f"- **Narration (am):** {s['narration']}",
               f"- **Subtitle (en):** {s['subtitle_en']}",
               f"- **Back-translation (check):** {back.get(s['id'], '(not available: ' + (err or 'no result') + ')')}", ""]
    path.write_text("\n".join(md), encoding="utf-8")
    write_manifest("script", {"file": rel, "back_translated": bool(back)})
    print(f"script: {rel} ({'with' if back else 'without'} back-translation, {time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
