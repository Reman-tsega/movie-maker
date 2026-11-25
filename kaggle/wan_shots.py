"""Kaggle (2x T4) - animate the storyboard's "wan" shots with Wan 2.2 TI2V-5B (image-to-video).

Wan's README says TI2V-5B needs >= 24 GB VRAM with offloading; a T4 has 16 GB. So this script
tries, in order: (1) single GPU with --offload_model --convert_model_dtype --t5_cpu, then
(2) both T4s with FSDP + Ulysses (torchrun, 2 processes). Every attempt, success or failure,
is logged with its GPU seconds. Shots that fail keep the Ken Burns fallback in pipeline/shots.py.

Notebook cells (GPU T4 x2, Internet on):

    !git clone https://github.com/Reman-tsega/movie-maker.git
    !git clone https://github.com/Wan-Video/Wan2.2.git
    !cd Wan2.2 && pip install -q -r requirements.txt   # flash_attn is optional; skip it if it fails
    !huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir /kaggle/working/Wan2.2-TI2V-5B
    !python movie-maker/kaggle/wan_shots.py --frames 73 --steps 30
    # or one shot only:  --only s05

Copy movie-maker/outputs/wan/ (MP4s + runs_kaggle.jsonl) back into the repo, then run
`python pipeline/merge_kaggle_logs.py && make film`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("MM_REPO", Path(__file__).resolve().parent.parent))
WAN = Path("/kaggle/working/Wan2.2")
CKPT = Path("/kaggle/working/Wan2.2-TI2V-5B")


def attempt(cmd: list[str], timeout: int) -> tuple[bool, float, str]:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=WAN, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, time.time() - t0, (p.stderr or p.stdout)[-600:]
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, f"timeout after {timeout}s"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--frames", type=int, default=73, help="must be 4n+1; 73 = ~3 s at 24 fps")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--size", default="1280*704", help="area; aspect follows the input image")
    ap.add_argument("--timeout", type=int, default=2400)
    args = ap.parse_args()

    sb = json.loads((REPO / "storyboard.json").read_text(encoding="utf-8"))
    keys = json.loads((REPO / "outputs/keyframes/manifest.json").read_text(encoding="utf-8"))["shots"]
    out = REPO / "outputs" / "wan"
    out.mkdir(parents=True, exist_ok=True)
    log = out / "runs_kaggle.jsonl"
    only = set(filter(None, args.only.split(",")))

    for shot in sb["shots"]:
        sid = shot["id"]
        if shot["motion"]["mode"] != "wan" or (only and sid not in only):
            continue
        key = REPO / keys[sid]
        key_hash = key.stem.split("_")[-1]          # pipeline/shots.py looks for <sid>_<keyhash>*.mp4
        dst = out / f"{sid}_{key_hash}_s{shot['seed']}.mp4"
        if dst.exists():
            print(f"{sid}: cached")
            continue
        common = ["--task", "ti2v-5B", "--size", args.size, "--ckpt_dir", str(CKPT),
                  "--image", str(key), "--prompt", shot["motion"]["prompt"],
                  "--frame_num", str(args.frames), "--sample_steps", str(args.steps),
                  "--base_seed", str(shot["seed"]), "--save_file", str(dst)]
        plans = [
            ("1xT4 offload", [sys.executable, "generate.py", *common, "--offload_model", "True",
                              "--convert_model_dtype", "--t5_cpu"]),
            ("2xT4 fsdp", ["torchrun", "--nproc_per_node=2", "generate.py", *common,
                           "--dit_fsdp", "--t5_fsdp", "--ulysses_size", "2"]),
        ]
        for name, cmd in plans:
            ok, secs, tail = attempt(cmd, args.timeout)
            gpus = 2 if "2xT4" in name else 1
            rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stage": "shots", "shot": sid,
                   "model": "Wan2.2-TI2V-5B", "seed": shot["seed"],
                   "params": {"plan": name, "size": args.size, "frames": args.frames, "steps": args.steps,
                              "prompt": shot["motion"]["prompt"]},
                   "latency_s": round(secs, 1), "gpu_s": round(secs * gpus, 1),
                   "cost_usd_list_equiv": 0.0, "cache_hit": False,
                   "status": "ok" if ok and dst.exists() else "error",
                   "output": str(dst.relative_to(REPO)) if ok else None,
                   "error": None if ok else tail}
            with log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{sid} [{name}]: {'OK' if ok else 'FAILED'} in {secs / 60:.1f} min")
            if ok and dst.exists():
                break
            print("   ", tail.strip().splitlines()[-1] if tail.strip() else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
