"""Validators: one per stage, run after the stage and before the next one uses its output.

    python pipeline/validators.py storyboard|narration|keyframes|shots|music|assemble|all

Each check prints PASS or FAIL with the measured value; any FAIL exits 1, so `make film` stops
before a broken output reaches the next stage. Every run logs one line to runs.jsonl
(stage "validate:<name>"). Several checks are regression tests for real failures:
F4 (spoken instruction → s/word), F13 (nested WAV + C2PA noise → edge levels), E15 (true peak).
"""
from __future__ import annotations

import array
import json
import math
import re
import subprocess
import sys
import textwrap
import time
import wave
from pathlib import Path

from common import OUT, ROOT, load_storyboard, log_call, media_duration, read_manifest

Result = tuple[str, bool, str]


def probe(path: Path, entries: str) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
                       capture_output=True, text=True)
    return json.loads(p.stdout or "{}")


def loudness(path: Path) -> tuple[float, float]:
    """Integrated loudness (LUFS) and true peak (dBFS) of the file as encoded."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    summary = p.stderr[p.stderr.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return i, peak


def rms_db(samples) -> float:
    if not samples:
        return -120.0
    return 20 * math.log10(max(1e-9, math.sqrt(sum(x * x for x in samples) / len(samples))) / 32768)


# ---------------------------------------------------------------- stages
def check_storyboard(sb) -> list[Result]:
    r: list[Result] = [("schema + references (shots, characters, music cues)", True, "load_storyboard() passed")]
    planned = sum(s["duration_s"] for s in sb["shots"]) + sb["end_card"]["duration_s"]
    lo, hi = sb.get("target_total_s", [60, 90])
    r.append(("planned length within target", lo <= planned <= hi, f"{planned:.0f}s in [{lo},{hi}]"))
    for s in sb["shots"]:
        lines = textwrap.wrap(s["subtitle_en"], 40)
        r.append((f"{s['id']} subtitle readable (≤ 4 lines of 40 chars = 2 screens)", len(lines) <= 4, f"{len(lines)} lines"))
        if s["motion"]["mode"] == "wan":
            r.append((f"{s['id']} wan shot has a motion prompt", bool(s["motion"].get("prompt")), ""))
    return r


def check_narration(sb) -> list[Result]:
    r: list[Result] = []
    m = read_manifest("narration")
    for s in sb["shots"]:
        sid = s["id"]
        if sid not in m:
            r.append((f"{sid} narration exists", False, "missing from manifest"))
            continue
        path = ROOT / m[sid]["file"]
        with wave.open(str(path)) as w:
            sr, n = w.getframerate(), w.getnframes()
            raw = w.readframes(n)
        a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
        dur = n / sr
        words = len(re.sub(r"\[[^\]]*\]", "", s["narration"]).split())
        edge = int(sr * 0.05)
        r += [
            (f"{sid} not a nested WAV (F13)", raw[:4] != b"RIFF",
             "audio data starts with a WAV header" if raw[:4] == b"RIFF" else "audio data is PCM"),
            (f"{sid} sample rate 24 kHz", sr == 24000, f"{sr} Hz"),
            (f"{sid} length plausible", 0.8 <= dur <= 15, f"{dur:.2f}s"),
            (f"{sid} not silent", rms_db(a) > -40, f"{rms_db(a):.1f} dB RMS"),
            (f"{sid} speaking rate ≤ 1.2 s/word (F4)", dur / max(words, 1) <= 1.2, f"{dur / max(words, 1):.2f} s/word"),
            (f"{sid} clean ending, last 50 ms < -40 dB (F13)", rms_db(a[-edge:]) < -40, f"{rms_db(a[-edge:]):.1f} dB"),
            (f"{sid} model recorded", bool(m[sid].get("model")), m[sid].get("model", "")),
        ]
    check = OUT / "narration" / "check.json"
    if check.exists():
        flagged = [row["id"] for row in json.loads(check.read_text(encoding="utf-8")) if row["flags"]]
        r.append(("transcription check: no flagged lines", not flagged, f"flagged: {flagged or 'none'}"))
    return r


def check_keyframes(sb) -> list[Result]:
    r: list[Result] = []
    m = read_manifest("keyframes")
    for c in sb["characters"]:
        ok = c in m.get("references", {}) and (ROOT / m["references"][c]).exists()
        r.append((f"reference sheet for {c}", ok, m.get("references", {}).get(c, "missing")))
    for s in sb["shots"]:
        sid = s["id"]
        f = m["shots"].get(sid)
        if not f or not (ROOT / f).exists():
            r.append((f"{sid} keyframe exists", False, "missing"))
            continue
        st = probe(ROOT / f, "stream=width,height")["streams"][0]
        r.append((f"{sid} keyframe 1024x1024", (st["width"], st["height"]) == (1024, 1024), f"{st['width']}x{st['height']}"))
        p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ROOT / f), "-vf", "signalstats,metadata=print",
                            "-f", "null", "-"], capture_output=True, text=True)
        lo = float(re.search(r"YLOW=([\d.]+)", p.stderr).group(1))
        hi = float(re.search(r"YHIGH=([\d.]+)", p.stderr).group(1))
        r.append((f"{sid} keyframe not blank", hi - lo > 40, f"luma range {hi - lo:.0f}"))
    return r


def check_shots(sb) -> list[Result]:
    r: list[Result] = []
    m = read_manifest("shots")
    for s in sb["shots"]:
        sid = s["id"]
        if sid not in m or not (ROOT / m[sid]["file"]).exists():
            r.append((f"{sid} clip exists", False, "missing"))
            continue
        st = probe(ROOT / m[sid]["file"], "stream=width,height,r_frame_rate")["streams"][0]
        dur = media_duration(ROOT / m[sid]["file"])
        r += [
            (f"{sid} clip length matches timeline", abs(dur - m[sid]["duration_s"]) <= 0.1, f"{dur:.2f}s vs {m[sid]['duration_s']}s"),
            (f"{sid} clip 1024x1024 @ 24 fps", (st["width"], st["height"], st["r_frame_rate"]) == (1024, 1024, "24/1"),
             f"{st['width']}x{st['height']} {st['r_frame_rate']}"),
        ]
    return r


def check_music(sb) -> list[Result]:
    m = read_manifest("music")
    path = ROOT / m["file"]
    r: list[Result] = [("music file exists", path.exists(), m["file"])]
    if not path.exists():
        return r
    dur = media_duration(path)
    i, _ = loudness(path)
    r += [
        ("chosen score (not the placeholder)", not m.get("placeholder"), "placeholder" if m.get("placeholder") else "ACE-Step"),
        ("music at least 30 s (looped under the film)", dur >= 30, f"{dur:.1f}s"),
        ("music loudness sane (-30 to -8 LUFS)", -30 <= i <= -8, f"{i:.1f} LUFS"),
    ]
    return r


def check_assemble(sb) -> list[Result]:
    r: list[Result] = []
    lo, hi = sb.get("target_total_s", [60, 90])
    final = OUT / "final"
    for aspect, (w, h) in {"16x9": (1280, 720), "9x16": (720, 1280)}.items():
        files = sorted(final.glob(f"heritage_{aspect}_*.mp4"), key=lambda p: p.stat().st_mtime)
        if not files:
            r.append((f"{aspect} export exists", False, "missing"))
            continue
        f = files[-1]
        streams = probe(f, "stream=codec_type,width,height")["streams"]
        v = next(s for s in streams if s["codec_type"] == "video")
        dur = media_duration(f)
        i, peak = loudness(f)
        r += [
            (f"{aspect} resolution", (v["width"], v["height"]) == (w, h), f"{v['width']}x{v['height']}"),
            (f"{aspect} has audio", any(s["codec_type"] == "audio" for s in streams), ""),
            (f"{aspect} length {lo}-{hi}s", lo <= dur <= hi, f"{dur:.1f}s"),
            (f"{aspect} loudness -14 ±1 LUFS", abs(i + 14) <= 1, f"{i:.1f} LUFS"),
            (f"{aspect} true peak ≤ -1 dBFS (E15)", peak <= -1.0, f"{peak:.1f} dBFS"),
        ]
    srt = final / "subtitles_en.srt"
    n = srt.read_text(encoding="utf-8").count(" --> ") if srt.exists() else 0
    r.append(("subtitles cover every shot", n >= len(sb["shots"]), f"{n} cues for {len(sb['shots'])} shots"))
    return r


CHECKS = {"storyboard": check_storyboard, "narration": check_narration, "keyframes": check_keyframes,
          "shots": check_shots, "music": check_music, "assemble": check_assemble}


def run(stage: str) -> bool:
    t0 = time.time()
    try:
        sb = load_storyboard()
        results = CHECKS[stage](sb)
    except Exception as e:  # noqa: BLE001  (a stage output that can't even be read is a failure)
        results = [(f"{stage} outputs readable", False, str(e)[:200])]
    failed = [x for x in results if not x[1]]
    print(f"validate {stage}: {len(results) - len(failed)}/{len(results)} passed")
    for name, ok, detail in results:
        if not ok or "-v" in sys.argv:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")
    log_call(f"validate:{stage}", "validators.py", latency_s=time.time() - t0,
             status="ok" if not failed else "error",
             params={"checks": len(results), "failed": len(failed)},
             error="; ".join(f"{n} ({d})" for n, _, d in failed)[:300] or None)
    return not failed


def main() -> int:
    stages = list(CHECKS) if sys.argv[1] == "all" else [sys.argv[1]]
    ok = all([run(s) for s in stages])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
