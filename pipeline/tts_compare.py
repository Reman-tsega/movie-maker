"""Experiment: which TTS model/voice pronounces Amharic ejectives (ጫ ጠ ቅ ...) best?
Generates the same shots with several (model, voice) variants and writes one MP3 per variant
to outputs/tts_compare/, for a native speaker to judge by ear. Every call is logged.

  python pipeline/tts_compare.py s01,s02,s03 gemini-3.8-flash-tts:Kore gemini-2.5-flash-preview-tts:Kore
"""
import os
import sys
import time
import wave

from common import OUT, input_hash, load_env, load_storyboard, log_call, run
from narration import SAMPLE_RATE, tts


def main() -> int:
    load_env()
    sb = load_storyboard()
    ids = sys.argv[1].split(",")
    variants = [v.split(":") for v in sys.argv[2:]]
    keys = [k for k in (os.environ.get("GEMINI_API_KEY_2"), os.environ.get("GEMINI_API_KEY")) if k]
    out = OUT / "tts_compare"
    out.mkdir(parents=True, exist_ok=True)
    for model, voice in variants:
        parts = []
        for sid in ids:
            text = next(s["narration"] for s in sb["shots"] if s["id"] == sid)
            p = out / f"{sid}_{model}_{voice}_{input_hash(model, voice, text)}.wav"
            if not p.exists():
                t0 = time.time()
                pcm, err = None, None
                for key in keys:
                    try:
                        pcm = tts(model, voice, "", text, key=key)
                        break
                    except Exception as e:  # noqa: BLE001
                        err = str(e)[:200]
                if pcm is None:
                    log_call("tts_compare", model, shot=sid, status="error", error=err, params={"voice": voice})
                    print(f"  {model}/{voice} {sid}: FAILED {err}")
                    continue
                with wave.open(str(p), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(pcm)
                log_call("tts_compare", model, shot=sid, latency_s=time.time() - t0,
                         params={"voice": voice}, output=str(p.relative_to(OUT.parent)))
            parts.append(p)
        if parts:
            lst = out / f"list_{model}_{voice}.txt"
            lst.write_text("".join(f"file '{x.resolve()}'\n" for x in parts))
            mp3 = out / f"compare_{model}_{voice}.mp3"
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-af", "apad=pad_dur=0.6", "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)])
            print(f"  {model}/{voice}: {mp3.relative_to(OUT.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
