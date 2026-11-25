"""Stage: keyframes. Character reference sheets first, then one keyframe per shot.

Every prompt = shot image_prompt + the locked description of each character in the shot
+ the shared style block. Same text + same seed = same image, so consistency comes
from never re-describing a character differently.

Usage: python pipeline/keyframes.py [--refs-only] [--only s03,s05]
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import time

from pathlib import Path

import requests

from common import (OUT, Retryable, check_http, input_hash, load_env, load_storyboard,
                    log_call, read_manifest, run, with_retries, write_manifest)

CF = "https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"


def generate(model: str, prompt: str, seed: int, steps: int = 4, refs: list | None = None) -> bytes:
    """One image. FLUX.2 klein takes multipart form data and up to 4 reference images
    (input_image_0..3); FLUX.1 schnell takes JSON and no seed (see EXPERIMENTS E3)."""
    acct = os.environ.get("CF_ACCOUNT_ID")
    if not acct:
        raise RuntimeError("CF_ACCOUNT_ID is not set (see .env.example)")
    url = CF.format(acct=acct, model=model)
    headers = {"Authorization": f"Bearer {os.environ.get('CF_API_TOKEN', '')}"}

    def call():
        try:
            if "flux-2" in model:
                form = {"prompt": (None, prompt), "seed": (None, str(seed)), "steps": (None, str(steps)),
                        "width": (None, "1024"), "height": (None, "1024")}
                for i, ref in enumerate((refs or [])[:4]):
                    form[f"input_image_{i}"] = (Path(ref).name, Path(ref).read_bytes(), "image/jpeg")
                r = requests.post(url, headers=headers, files=form, timeout=180)
            else:
                r = requests.post(url, headers=headers, timeout=120, json={"prompt": prompt, "steps": steps})
        except requests.RequestException as e:
            raise Retryable(str(e))
        check_http(r)
        data = r.json()
        if not data.get("success", True) or "image" not in (data.get("result") or {}):
            raise RuntimeError(f"Cloudflare error: {str(data)[:300]}")
        return base64.b64decode(data["result"]["image"])

    return with_retries(call, what=f"image {model}")


def small_ref(path: Path) -> Path:
    """512 px copy of a reference image (smaller upload, same identity)."""
    dst = path.with_name(path.stem + "_512.jpg")
    if not dst.exists():
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vf", "scale=512:512", str(dst)])
    return dst


def build_prompt(sb: dict, shot: dict) -> str:
    chars = "; ".join(f"the {c} is {sb['characters'][c]['description']}" for c in shot["characters"])
    return f"{shot['shot_size']} shot. {shot['image_prompt']}. {chars}. Style: {sb['style_block']}"


def make(stage_dir, key: str, model: str, prompt: str, seed: int, log_shot: str,
         refs: list | None = None) -> str:
    ref_ids = [Path(r).name for r in (refs or [])]
    h = input_hash(model, prompt, seed, ref_ids)
    path = stage_dir / f"{key}_{h}.jpg"
    rel = str(path.relative_to(OUT.parent))
    if path.exists():
        log_call("keyframes", model, shot=log_shot, seed=seed, cache_hit=True, output=rel)
        print(f"  {key}: cached")
        return rel
    t0 = time.time()
    try:
        img = generate(model, prompt, seed, refs=refs)
    except Exception as e:  # noqa: BLE001
        log_call("keyframes", model, shot=log_shot, seed=seed, latency_s=time.time() - t0,
                 status="error", error=str(e)[:300], params={"refs": ref_ids})
        raise
    path.write_bytes(img)
    log_call("keyframes", model, shot=log_shot, seed=seed, latency_s=time.time() - t0,
             params={"steps": 4, "prompt_chars": len(prompt), "refs": ref_ids}, output=rel)
    print(f"  {key}: generated in {time.time() - t0:.1f}s")
    return rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs-only", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated shot ids")
    args = ap.parse_args()
    load_env()
    sb = load_storyboard()
    model = sb["models"]["image"]
    out_dir = OUT / "keyframes"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:  # keep entries for shots not regenerated in this run (--only)
        manifest = read_manifest("keyframes")
    except FileNotFoundError:
        manifest = {"references": {}, "shots": {}}

    for name, c in sb["characters"].items():
        if c.get("reference_prompt"):
            prompt = f"{c['reference_prompt']}. Style: {sb['style_block']}"
            manifest["references"][name] = make(out_dir, f"ref_{name}", model, prompt,
                                                c.get("reference_seed", 0), f"ref_{name}")
    if not args.refs_only:
        only = set(filter(None, args.only.split(",")))
        for shot in sb["shots"]:
            if only and shot["id"] not in only:
                continue
            refs = [small_ref(OUT.parent / manifest["references"][c]) for c in shot["characters"]
                    if c in manifest["references"]]
            manifest["shots"][shot["id"]] = make(out_dir, shot["id"], model, build_prompt(sb, shot),
                                                 shot["seed"], shot["id"], refs=refs)
    write_manifest("keyframes", manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
