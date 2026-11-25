# GPU stages on Kaggle

Kaggle gives about 30 free GPU hours a week (phone-verified account). Settings: **Accelerator: GPU T4 x2**, **Internet: On**.

| Script | What | Output (copy back into the repo) |
|---|---|---|
| `ace_step_music.py` | 3 instrumental score candidates from `music.caption`, `bpm`, `key` (seeds 11, 22, 33) | `outputs/music/score_seed*.wav`, `outputs/music/runs_kaggle.jsonl` |
| `wan_shots.py` | Image-to-video for every shot with `motion.mode = "wan"`, from its keyframe | `outputs/wan/<shot>_<keyhash>_s<seed>.mp4`, `outputs/wan/runs_kaggle.jsonl` |

Each script's docstring lists the exact notebook cells to run.

After copying the outputs back:

```bash
python pipeline/merge_kaggle_logs.py     # Kaggle GPU calls join runs.jsonl
# choose a score: set "music.chosen_track": "outputs/music/score_seed22.wav" in storyboard.json
make film
```

Known risk: Wan 2.2's README states TI2V-5B needs at least 24 GB of VRAM with offloading, and a T4
has 16 GB. The script tries a single T4 with offloading, then both T4s with FSDP. Shots without a
Wan clip render as Ken Burns moves automatically.
