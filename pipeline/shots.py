"""Stage: moving shots. One clip per shot -> outputs/shots/<shot>_<hash>.mp4 (square, 24 fps).

- motion.mode == "wan": use the Wan 2.2 clip produced by kaggle/wan_shots.py if it exists for
  this keyframe (outputs/wan/<shot>_<keyframe-hash>.mp4). If it is missing, fall back to Ken Burns
  and log the fallback, so the film always renders.
- motion.mode == "kenburns": slow zoom/pan over the keyframe with FFmpeg's zoompan filter.

Shot length = max(storyboard duration_s, narration length + 1.0 s).
Cache key = (keyframe file, motion, length, source clip), so changing one shot only rebuilds it.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from common import (OUT, ROOT, code_version, input_hash, load_storyboard, log_call, media_duration,
                    read_manifest, run, write_manifest)

FPS = 24
SIZE = 1024  # square master; assembly crops it to 16:9 and 9:16
PAD_AFTER_NARRATION = 1.0


def kenburns(src: Path, dst: Path, dur: float, zoom: list[float], pan: str) -> None:
    frames = int(round(dur * FPS))
    z0, z1 = zoom
    z = f"{z0}+({z1}-{z0})*on/{max(frames - 1, 1)}"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    drift = f"(on/{max(frames - 1, 1)})*(iw-iw/zoom)/2"
    x, y = cx, cy
    if pan == "left":
        x = f"(iw-iw/zoom)/2+(iw-iw/zoom)/4-{drift}/2"
    elif pan == "right":
        x = f"(iw-iw/zoom)/4+{drift}/2"
    elif pan == "up":
        y = f"(ih-ih/zoom)/2+(ih-ih/zoom)/4-{drift}/2"
    elif pan == "down":
        y = f"(ih-ih/zoom)/4+{drift}/2"
    # upscale first so the zoom is smooth (zoompan works in whole pixels)
    vf = (f"scale={SIZE * 2}:{SIZE * 2},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={SIZE}x{SIZE}:fps={FPS},"
          f"format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src), "-vf", vf,
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(dst)])


def fit_clip(src: Path, dst: Path, dur: float) -> None:
    """Square-crop a Wan clip, trim its weak first 0.3 s, hold the last frame if it is too short."""
    vf = (f"trim=start=0.3,setpts=PTS-STARTPTS,crop='min(iw,ih)':'min(iw,ih)',scale={SIZE}:{SIZE},"
          f"fps={FPS},tpad=stop_mode=clone:stop_duration={dur},trim=duration={dur},format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(dst)])


def main() -> int:
    sb = load_storyboard()
    keys = read_manifest("keyframes")["shots"]
    narr = read_manifest("narration")
    out_dir = OUT / "shots"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for shot in sb["shots"]:
        sid = shot["id"]
        key = ROOT / keys[sid]
        dur = round(max(shot["duration_s"], narr[sid]["duration_s"] + PAD_AFTER_NARRATION), 2)
        mode = shot["motion"]["mode"]
        wan_src = None
        if mode == "wan":
            cands = sorted((OUT / "wan").glob(f"{sid}_{key.stem.split('_')[-1]}*.mp4"))
            wan_src = cands[-1] if cands else None
            if wan_src is None:
                mode = "kenburns"
                log_call("shots", "wan-missing->kenburns", shot=sid, status="fallback",
                         error="no Wan clip for this keyframe yet")
        h = input_hash(keys[sid], shot["motion"], dur, mode, str(wan_src), code_version(__file__))
        dst = out_dir / f"{sid}_{h}.mp4"
        rel = str(dst.relative_to(ROOT))
        model = "ffmpeg-zoompan" if mode == "kenburns" else "wan2.2-ti2v-5b(fit)"
        if dst.exists():
            log_call("shots", model, shot=sid, cache_hit=True, output=rel)
            print(f"  {sid}: cached ({mode})")
        else:
            t0 = time.time()
            if mode == "kenburns":
                kenburns(key, dst, dur, shot["motion"].get("zoom", [1.0, 1.1]), shot["motion"].get("pan", "center"))
            else:
                fit_clip(wan_src, dst, dur)
            log_call("shots", model, shot=sid, latency_s=time.time() - t0,
                     params={"duration_s": dur, "mode": mode}, output=rel)
            print(f"  {sid}: {mode} {dur}s in {time.time() - t0:.1f}s")
        manifest[sid] = {"file": rel, "duration_s": dur, "mode": mode,
                         "check_s": round(media_duration(dst), 2)}
    write_manifest("shots", manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
