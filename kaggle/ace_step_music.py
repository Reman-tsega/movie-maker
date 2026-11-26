"""Kaggle (GPU T4) - generate score candidates with ACE-Step 1.5 from storyboard.json.

Run in a Kaggle notebook with GPU + Internet on, one cell each:

    !git clone https://github.com/Reman-tsega/movie-maker.git
    !git clone https://github.com/ACE-Step/ACE-Step-1.5.git
    !cd ACE-Step-1.5 && pip install -q -e .
    !hf download ACE-Step/Ace-Step1.5 --local-dir /kaggle/working/ACE-Step-1.5/checkpoints
    !python movie-maker/kaggle/ace_step_music.py --seeds 11,22,33 --duration 75

Then download movie-maker/outputs/music/ (the WAVs and runs_kaggle.jsonl) and copy them into the
repo's outputs/music/. Run `python pipeline/merge_kaggle_logs.py` and set music.chosen_track.

API from ACE-Step docs/en/INFERENCE.md (Quick Start). The 5 Hz LM planner is skipped
(thinking=False) because bpm, key and duration are fixed in the storyboard.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("MM_REPO", Path(__file__).resolve().parent.parent))
ACE = Path("/kaggle/working/ACE-Step-1.5")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--duration", type=float, default=75)
    ap.add_argument("--backend", default="pt", help="pt (safe on T4) or vllm")
    ap.add_argument("--device", default="cuda", help="cuda, or cpu when no GPU is free (F9)")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]

    sys.path.insert(0, str(ACE))
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler

    sb = json.loads((REPO / "storyboard.json").read_text(encoding="utf-8"))
    m = sb["music"]
    out = REPO / "outputs" / "music"
    out.mkdir(parents=True, exist_ok=True)
    log = out / "runs_kaggle.jsonl"

    t0 = time.time()
    dit = AceStepHandler()
    dit.initialize_service(project_root=str(ACE), config_path="acestep-v15-turbo", device=args.device)
    llm = LLMHandler()
    llm.initialize(checkpoint_dir=str(ACE / "checkpoints"), lm_model_path="acestep-5Hz-lm-0.6B",
                   backend=args.backend, device=args.device)
    load_s = time.time() - t0
    print(f"models loaded in {load_s:.0f}s")

    params = GenerationParams(caption=m["caption"], lyrics="[Instrumental]", instrumental=True,
                              bpm=m.get("bpm"), keyscale=m.get("key", ""), duration=args.duration,
                              thinking=False)
    rec_base = {"stage": "music", "shot": None, "cost_usd_list_equiv": 0.0, "cache_hit": False,
                "model": f"ACE-Step-1.5 acestep-v15-turbo ({args.device})"}
    done = 0
    for seed in seeds:  # one at a time: a slow CPU run can't lose the other candidates (FAILURES F11)
        config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format="wav")
        t1 = time.time()
        result = generate_music(dit, llm, params, config, save_dir=str(out / "raw"))
        gen_s = time.time() - t1
        rec = {**rec_base, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seed": seed,
               "latency_s": round(gen_s, 1), "gpu_s": round(gen_s, 1) if args.device == "cuda" else 0.0,
               "params": {"caption": m["caption"], "bpm": m.get("bpm"), "key": m.get("key"),
                          "duration_s": args.duration, "batch": 1, "model_load_s": round(load_s, 1)}}
        with log.open("a", encoding="utf-8") as f:
            if not result.success:
                f.write(json.dumps({**rec, "status": "error", "error": str(result.error)[:300]}) + "\n")
                print(f"seed {seed} FAILED after {gen_s:.0f}s: {result.error}")
                continue
            dst = out / f"score_seed{seed}.wav"
            shutil.copy(result.audios[0]["path"], dst)
            f.write(json.dumps({**rec, "status": "ok", "output": str(dst.relative_to(REPO))},
                               ensure_ascii=False) + "\n")
            done += 1
            print(f"seed {seed} -> {dst.relative_to(REPO)} in {gen_s:.0f}s", flush=True)
    print(f"{done}/{len(seeds)} candidates done")
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
