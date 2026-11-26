"""Summarise runs.jsonl into the measured table for COSTS.md: calls, cache hits, failures,
mean and total latency, and GPU minutes per stage and model."""
import collections
import json
import sys

from common import RUNS


def main() -> int:
    rows = [json.loads(l) for l in RUNS.read_text(encoding="utf-8").splitlines() if l.strip()]
    agg = collections.defaultdict(lambda: {"calls": 0, "hits": 0, "fail": 0, "lat": [], "gpu": 0.0})
    for r in rows:
        k = (r["stage"], r["model"].split(" (")[0])
        a = agg[k]
        if r.get("cache_hit"):
            a["hits"] += 1
            continue
        a["calls"] += 1
        a["fail"] += r.get("status") == "error"
        if r.get("status") != "error" and r.get("latency_s"):
            a["lat"].append(r["latency_s"])
        a["gpu"] += r.get("gpu_s") or 0
    print("| Stage | Model | Real calls | Failed | Cache hits | Mean latency (s) | Total (s) | GPU min |")
    print("|---|---|---|---|---|---|---|---|")
    for (stage, model), a in sorted(agg.items()):
        mean = sum(a["lat"]) / len(a["lat"]) if a["lat"] else 0
        print(f"| {stage} | {model} | {a['calls']} | {a['fail']} | {a['hits']} | {mean:.1f} | "
              f"{sum(a['lat']):.0f} | {a['gpu'] / 60:.1f} |")
    print(f"\n{len(rows)} log lines, {sum(a['hits'] for a in agg.values())} cache hits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
