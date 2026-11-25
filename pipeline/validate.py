"""Stage 0: validate storyboard.json against the schema and report the narration budget."""
import sys

from common import load_storyboard


def main() -> int:
    try:
        sb = load_storyboard()
    except Exception as e:  # noqa: BLE001
        print(f"storyboard INVALID: {e}")
        return 1
    shots = sb["shots"]
    planned = sum(s["duration_s"] for s in shots) + sb["end_card"]["duration_s"]
    words = sum(len(s["narration"].split()) for s in shots)
    lo, hi = sb.get("target_total_s", [60, 90])
    print(f"storyboard OK: {len(shots)} shots, planned {planned:.0f}s (target {lo}-{hi}s), "
          f"{words} narration words")
    if not lo <= planned <= hi:
        print("  warning: planned length is outside the target; narration timing will decide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
