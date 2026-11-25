"""Append the Kaggle GPU logs (outputs/*/runs_kaggle.jsonl) to runs.jsonl, without duplicates."""
import json
import sys

from common import OUT, RUNS


def main() -> int:
    seen = set()
    if RUNS.exists():
        for line in RUNS.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            seen.add((r.get("ts"), r.get("stage"), r.get("shot"), r.get("output"), r.get("seed")))
    added = 0
    with RUNS.open("a", encoding="utf-8") as f:
        for p in sorted(OUT.glob("*/runs_kaggle.jsonl")):
            for line in p.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                k = (r.get("ts"), r.get("stage"), r.get("shot"), r.get("output"), r.get("seed"))
                if k not in seen:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    seen.add(k)
                    added += 1
    print(f"merged {added} Kaggle log lines into runs.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
