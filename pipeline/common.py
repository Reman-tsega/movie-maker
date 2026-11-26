"""Shared helpers for every pipeline stage.

- load_storyboard(): read storyboard.json and validate it against schema/ before any work.
- input_hash(): stable hash of a stage's inputs; outputs are named by it, so a re-run
  only regenerates what changed (cache hit = file already exists).
- log_call(): append one line per model call (or cache hit) to runs.jsonl.
- with_retries(): retry transient failures (HTTP 429/5xx, timeouts) with backoff.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import jsonschema

# Windows consoles default to a legacy code page and crash on Amharic output
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"
OUT = ROOT / "outputs"
RUNS = ROOT / "runs.jsonl"

# List prices for the per-call cost logged in runs.jsonl (free tiers were used; this is the
# paid-tier equivalent). Sources and dates in COSTS.md.
PRICE_TTS_PER_AUDIO_TOKEN = 9.00 / 1e6        # Gemini 3.8 Flash TTS, $ per audio output token (to 31 Dec 2026)
TTS_TOKENS_PER_SECOND = 25                     # audio is billed at 25 tokens per second
PRICE_CF_PER_NEURON = 0.011 / 1000             # Cloudflare Workers AI
FLUX2_KLEIN_NEURONS_OUT_TILE = 26.05           # per 512x512 output tile (1024^2 = 4 tiles)
FLUX2_KLEIN_NEURONS_IN_TILE = 5.37             # per 512x512 input (reference) tile
PRICE_GEMINI3_FLASH_AUDIO_IN = 1.00 / 1e6      # Gemini 3 Flash, $ per audio/text input token (input side only)


def tts_cost(seconds: float) -> float:
    return round(seconds * TTS_TOKENS_PER_SECOND * PRICE_TTS_PER_AUDIO_TOKEN, 6)


def flux_cost(n_refs: int, out_tiles: int = 4) -> float:
    neurons = out_tiles * FLUX2_KLEIN_NEURONS_OUT_TILE + n_refs * FLUX2_KLEIN_NEURONS_IN_TILE
    return round(neurons * PRICE_CF_PER_NEURON, 6)


def load_env() -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no extra dependency)."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_storyboard(path: Path = STORYBOARD) -> dict:
    sb = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(sb, schema)
    # Checks JSON Schema cannot express
    ids = [s["id"] for s in sb["shots"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate shot ids: {ids}")
    for s in sb["shots"]:
        for c in s["characters"]:
            if c not in sb["characters"]:
                raise ValueError(f"{s['id']}: unknown character '{c}'")
    for cue in sb["music"]["cues"]:
        for k in ("from_shot", "to_shot"):
            if cue[k] not in ids:
                raise ValueError(f"music cue {cue['id']}: unknown shot {cue[k]}")
    return sb


def code_version(path: str) -> str:
    """Hash of a stage's source file, so changing the code invalidates its cached outputs."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:8]


def input_hash(*parts) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def log_call(stage: str, model: str, *, shot: str | None = None, params: dict | None = None,
             seed: int | None = None, latency_s: float = 0.0, cost_usd: float = 0.0,
             gpu_s: float = 0.0, cache_hit: bool = False, status: str = "ok",
             output: str | None = None, error: str | None = None) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "stage": stage, "shot": shot, "model": model, "params": params or {},
        "seed": seed, "latency_s": round(latency_s, 3), "gpu_s": round(gpu_s, 1),
        "cost_usd_list_equiv": cost_usd, "cache_hit": cache_hit, "status": status,
        "output": output, "error": error,
        "run": os.environ.get("MM_RUN_ID"),     # set by film.py, groups one end-to-end run
    }
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class Retryable(Exception):
    pass


def with_retries(fn, *, attempts: int = 3, base_delay: float = 4.0, what: str = "call"):
    last = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Retryable as e:
            last = e
            if i < attempts:
                delay = base_delay * (2 ** (i - 1))
                print(f"  ! {what} failed ({e}); retry {i}/{attempts - 1} in {delay:.0f}s")
                time.sleep(delay)
    raise RuntimeError(f"{what} failed after {attempts} attempts: {last}")


def check_http(resp) -> None:
    """Raise Retryable for transient HTTP errors, RuntimeError for permanent ones."""
    if resp.status_code == 429 or resp.status_code >= 500:
        raise Retryable(f"HTTP {resp.status_code}: {resp.text[:200]}")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")


def run(cmd: list[str]) -> None:
    """Run an FFmpeg/ffprobe command; show stderr only on failure."""
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd[:6])} ...\n{p.stderr[-2000:]}")


def media_duration(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(p.stdout.strip())


def manifest_path(stage: str) -> Path:
    return OUT / stage / "manifest.json"


def write_manifest(stage: str, data: dict) -> None:
    p = manifest_path(stage)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_manifest(stage: str) -> dict:
    p = manifest_path(stage)
    if not p.exists():
        raise FileNotFoundError(f"run the '{stage}' stage first ({p} missing)")
    return json.loads(p.read_text(encoding="utf-8"))
