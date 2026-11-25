"""Stage: music. Uses the chosen ACE-Step score (music.chosen_track, generated on Kaggle by
kaggle/ace_step_music.py). If none is chosen yet, synthesises a quiet placeholder pad in FFmpeg
so the radio cut and rough cuts still have a temp track.
"""
from __future__ import annotations

import sys
import time

from common import OUT, ROOT, input_hash, load_storyboard, log_call, media_duration, run, write_manifest


def placeholder(dst, seconds: float) -> None:
    # soft C-major pad (C3, E3, G3) with slow tremolo: an obvious temp track, not the score
    expr = ("0.08*sin(2*PI*130.81*t)+0.06*sin(2*PI*164.81*t)+0.05*sin(2*PI*196.00*t)")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         f"aevalsrc='{expr}':s=48000:d={seconds}",
         "-af", "tremolo=f=0.2:d=0.5,afade=t=in:d=2,aformat=channel_layouts=stereo", str(dst)])


def main() -> int:
    sb = load_storyboard()
    out_dir = OUT / "music"
    out_dir.mkdir(parents=True, exist_ok=True)
    chosen = sb["music"].get("chosen_track")
    if chosen:
        path = ROOT / chosen
        if not path.exists():
            print(f"music: chosen track {chosen} not found")
            return 1
        log_call("music", "ACE-Step-1.5 (chosen)", cache_hit=True, output=chosen,
                 params={"caption": sb["music"].get("caption")})
        write_manifest("music", {"file": chosen, "placeholder": False, "duration_s": media_duration(path)})
        print(f"music: using chosen score {chosen}")
        return 0
    seconds = 120
    h = input_hash("placeholder-pad-v1", seconds)
    dst = out_dir / f"placeholder_{h}.wav"
    rel = str(dst.relative_to(ROOT))
    if dst.exists():
        log_call("music", "ffmpeg-placeholder", cache_hit=True, output=rel)
    else:
        t0 = time.time()
        placeholder(dst, seconds)
        log_call("music", "ffmpeg-placeholder", latency_s=time.time() - t0, output=rel)
    write_manifest("music", {"file": rel, "placeholder": True, "duration_s": seconds})
    print("music: placeholder pad (no ACE-Step track chosen yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
