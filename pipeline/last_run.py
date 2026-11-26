"""Summarise the most recent run from runs.jsonl: which shots made a real model call and which
were cache hits. Used in the walkthrough to show that only the changed shot regenerated."""
import json
import sys
from datetime import datetime, timedelta

from common import RUNS


def main() -> int:
    rows = [json.loads(l) for l in RUNS.read_text(encoding="utf-8").splitlines() if l.strip()]
    run_id = rows[-1].get("run")
    if run_id:                                   # rows from the latest `python pipeline/film.py`
        recent = [r for r in rows if r.get("run") == run_id]
        label = f"run {run_id}"
    else:                                        # older logs without run ids: last 15 minutes
        end = datetime.strptime(rows[-1]["ts"][:19], "%Y-%m-%dT%H:%M:%S")
        recent = [r for r in rows if datetime.strptime(r["ts"][:19], "%Y-%m-%dT%H:%M:%S") >= end - timedelta(minutes=15)]
        label = "last 15 min"
    gen = [r for r in recent if r["stage"] in ("narration", "keyframes", "shots") and not r["cache_hit"]
           and r.get("status") not in ("error", "fallback") and r["model"] != "key-switch"]
    hits = [r for r in recent if r["stage"] in ("narration", "keyframes", "shots") and r["cache_hit"]]
    print(f"\nlast run ({label}):")
    for stage in ("narration", "keyframes", "shots"):
        g = sorted({r["shot"] for r in gen if r["stage"] == stage and r["shot"]})
        h = sorted({r["shot"] for r in hits if r["stage"] == stage and r["shot"]})
        print(f"  {stage:<10} regenerated: {', '.join(g) or '-':<12} cache hits: {len(h)}")
    for r in gen:
        print(f"  NEW CALL  {r['stage']:<10} {r['shot']:<6} {r['model']:<40} {r['latency_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
