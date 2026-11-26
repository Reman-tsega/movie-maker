"""Stage: assembly (FFmpeg only, deterministic).

  python pipeline/assemble.py --radio   narration + temp music on black, with subtitles (user test 1)
  python pipeline/assemble.py           final film in 16:9 and 9:16

Timeline: shot i lasts d_i = max(duration_s, narration_i + 1.0 s); narration starts 0.4 s into the shot.
Audio: narration track -> music trimmed, faded and ducked under the voice with sidechaincompress
-> mixed -> loudnorm to -14 LUFS / -1 dBTP. Subtitles come from subtitle_en, timed to each
narration line, at most 2 lines of 40 characters, kept inside the vertical safe area.
"""
from __future__ import annotations

import argparse
import sys
import textwrap
import time
from pathlib import Path

from common import (OUT, ROOT, code_version, input_hash, load_storyboard, log_call, media_duration,
                    read_manifest, run)

FPS = 24
LEAD = 0.4
PAD_AFTER_NARRATION = 1.0   # default; storyboard timing.pad_after_s overrides
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
ASPECTS = {"16x9": (1280, 720), "9x16": (720, 1280)}


def timeline(sb, narr):
    global LEAD
    LEAD = sb.get("timing", {}).get("lead_s", LEAD)
    pad = sb.get("timing", {}).get("pad_after_s", PAD_AFTER_NARRATION)
    t, rows = 0.0, []
    for s in sb["shots"]:
        d = round(max(s["duration_s"], narr[s["id"]]["duration_s"] + pad), 2)
        rows.append({"id": s["id"], "start": t, "dur": d, "narr_s": narr[s["id"]]["duration_s"],
                     "sub": s["subtitle_en"]})
        t += d
    return rows, t


def srt_time(x: float) -> str:
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(rows, path: Path) -> None:
    events = []
    for r in rows:
        lines = textwrap.wrap(r["sub"], 40)
        chunks = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        start = r["start"] + LEAD
        span = max(r["narr_s"], 1.5)
        total_chars = sum(len(" ".join(c)) for c in chunks)
        for c in chunks:
            part = span * len(" ".join(c)) / total_chars
            events.append((start, start + part, "\n".join(c)))
            start += part
    path.write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n\n"
                            for i, (a, b, txt) in enumerate(events, 1)), encoding="utf-8")


def build_audio(sb, rows, total, narr, music_file: Path, dst: Path) -> None:
    duck = sb["music"].get("duck", {})
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for r in rows:
        args += ["-i", str(ROOT / narr[r["id"]]["file"])]
    args += ["-i", str(music_file)]
    n = len(rows)
    f = []
    for i, r in enumerate(rows):
        f.append(f"[{i}]aresample=48000,aformat=channel_layouts=stereo,adelay={int(LEAD * 1000)}:all=1,"
                 f"apad,atrim=duration={r['dur']}[n{i}]")
    f.append("".join(f"[n{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,apad,atrim=duration={total}[voice]")
    f.append("[voice]asplit=2[v_mix][v_key]")
    f.append(f"[{n}]aresample=48000,aformat=channel_layouts=stereo,aloop=loop=-1:size=2e9,"
             f"atrim=duration={total},afade=t=in:d=1.5,afade=t=out:st={max(total - 4, 0)}:d=4,"
             f"volume={duck.get('music_gain_db', -6)}dB[mus]")
    f.append(f"[mus][v_key]sidechaincompress=threshold={duck.get('threshold', 0.02)}:"
             f"ratio={duck.get('ratio', 6)}:attack={duck.get('attack_ms', 300)}:"
             f"release={duck.get('release_ms', 1500)}[ducked]")
    f.append("[v_mix][ducked]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1:LRA=11,"
             "alimiter=limit=0.708:level=disabled,aresample=48000[out]")  # E15: single-pass loudnorm overshot to +0.2 dB
    args += ["-filter_complex", ";".join(f), "-map", "[out]", "-c:a", "pcm_s16le", str(dst)]
    run(args)


def end_card_inputs(sb, w, h, tmp: Path):
    vertical = h > w
    blocks = []
    for i, line in enumerate(sb["end_card"]["lines"]):
        size = int(h * (0.05 if i == 0 else 0.02)) if vertical else int(h * (0.08 if i == 0 else 0.03))
        wrapped = textwrap.wrap(line, 34 if vertical else 70)
        blocks.append((wrapped, size))
    gap = int(h * 0.03)
    heights = [len(wr) * int(sz * 1.3) for wr, sz in blocks]
    y = (h - sum(heights) - gap * (len(blocks) - 1)) // 2
    draws = []
    for i, ((wrapped, size), bh) in enumerate(zip(blocks, heights)):
        for j, text in enumerate(wrapped):
            tf = tmp / f"endcard_{i}_{j}.txt"
            tf.write_text(text, encoding="utf-8")
            draws.append(f"drawtext=fontfile={FONT}:textfile={tf}:fontcolor=white:fontsize={size}:"
                         f"x=(w-text_w)/2:y={y + j * int(size * 1.3)}")
        y += bh + gap
    return ",".join(draws)


def build_video(sb, rows, total, shots, aspect, audio: Path, srt: Path, dst: Path, radio: bool, tmp: Path):
    w, h = ASPECTS[aspect]
    ec = sb["end_card"]["duration_s"]
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    f = []
    if radio:
        body = total
        f.append(f"color=c=black:s={w}x{h}:r={FPS}:d={body}[body]")
    else:
        for r in rows:
            args += ["-i", str(ROOT / shots[r["id"]]["file"])]
        n_chars = {s["id"]: len(s["characters"]) for s in sb["shots"]}
        for i, r in enumerate(rows):
            # 9:16 cuts a square frame to its middle third; with two characters side by side one is
            # lost, so pan slowly from left to right across the whole frame instead (rough cut v1 review)
            if h > w and n_chars[r["id"]] > 1:
                crop = f"crop={w}:{h}:x='(in_w-out_w)*min(t/{r['dur']},1)':y=0"
            else:
                crop = f"crop={w}:{h}"
            f.append(f"[{i}]scale={max(w, h)}:{max(w, h)},{crop},setsar=1,fps={FPS},"
                     f"tpad=stop_mode=clone:stop_duration=2,trim=duration={r['dur']},setpts=PTS-STARTPTS[v{i}]")
        f.append("".join(f"[v{i}]" for i in range(len(rows))) + f"concat=n={len(rows)}:v=1:a=0[body]")
    f.append(f"color=c=black:s={w}x{h}:r={FPS}:d={ec},{end_card_inputs(sb, w, h, tmp)},"
             f"fade=t=in:d=0.6[card]")
    f.append("[body][card]concat=n=2:v=1:a=0[joined]")
    vertical = h > w
    style = ("FontName=DejaVu Sans,FontSize={fs},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={mv}").format(
        fs=8 if vertical else 18, mv=70 if vertical else 24)
    f.append(f"[joined]subtitles={srt.name}:force_style='{style}',format=yuv420p[vout]")
    args += ["-i", str(audio)]
    audio_idx = 0 if radio else len(rows)
    args += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", f"{audio_idx}:a",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dst)]
    import subprocess
    p = subprocess.run(args, capture_output=True, text=True, cwd=srt.parent)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2500:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radio", action="store_true")
    args = ap.parse_args()
    sb = load_storyboard()
    narr = read_manifest("narration")
    music = read_manifest("music")
    rows, body = timeline(sb, narr)
    total = round(body + sb["end_card"]["duration_s"], 2)
    shots = None if args.radio else read_manifest("shots")
    if shots:
        for r in rows:
            if abs(shots[r["id"]]["duration_s"] - r["dur"]) > 0.05:
                print(f"shot {r['id']} is stale (re-run the shots stage)")
                return 1
    final = OUT / "final"
    tmp = final / "work"
    tmp.mkdir(parents=True, exist_ok=True)

    h = input_hash([r for r in rows], music["file"], sb["music"].get("duck"), sb["end_card"],
                   None if args.radio else {k: v["file"] for k, v in shots.items()}, code_version(__file__))
    srt = tmp / f"subs_{h}.srt"
    write_srt(rows, srt)
    audio = tmp / f"mix_{h}.wav"
    t0 = time.time()
    if not audio.exists():
        # the music bed runs under the whole film, end card included
        build_audio(sb, rows, total, narr, ROOT / music["file"], audio)
    outs = {}
    targets = ["16x9"] if args.radio else list(ASPECTS)
    for aspect in targets:
        name = f"radio_cut_{h}.mp4" if args.radio else f"heritage_{aspect}_{h}.mp4"
        dst = final / name
        if dst.exists():
            log_call("assemble", "ffmpeg", params={"aspect": aspect, "radio": args.radio},
                     cache_hit=True, output=str(dst.relative_to(ROOT)))
        else:
            build_video(sb, rows, body, shots, aspect, audio, srt, dst, args.radio, tmp)
            log_call("assemble", "ffmpeg", latency_s=time.time() - t0,
                     params={"aspect": aspect, "radio": args.radio, "total_s": total},
                     output=str(dst.relative_to(ROOT)))
        outs[aspect] = dst
        print(f"  {aspect}: {dst.relative_to(ROOT)} ({media_duration(dst):.1f}s)")
    srt_out = final / "subtitles_en.srt"
    srt_out.write_text(srt.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"assembled: {total:.1f}s total (body {body:.1f}s + end card)")
    lo, hi = sb.get("target_total_s", [60, 90])
    if not lo <= total <= hi:
        print(f"  warning: total {total:.1f}s is outside {lo}-{hi}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
