"""One command on any OS (Windows has no `make`): every stage, each followed by its validator.

    python pipeline/film.py            # = make film
    python pipeline/film.py --radio    # = make radio
A failing stage or validator stops the run with a non-zero exit code.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def step(args: list[str], allow_fail: bool = False) -> None:
    print(f"\n>>> {' '.join(args)}", flush=True)
    rc = subprocess.run([PY, str(HERE / args[0]), *args[1:]]).returncode
    if rc and not allow_fail:
        sys.exit(f"stopped: {args[0]} exited with {rc}")


def main() -> None:
    radio = "--radio" in sys.argv
    step(["validate.py"]); step(["validators.py", "storyboard"])
    step(["narration.py"]); step(["narration_check.py"], allow_fail=True); step(["validators.py", "narration"])
    if not radio:
        step(["keyframes.py"]); step(["validators.py", "keyframes"])
        step(["shots.py"]); step(["validators.py", "shots"])
    step(["music.py"]); step(["validators.py", "music"])
    if radio:
        step(["assemble.py", "--radio"])
    else:
        step(["assemble.py"]); step(["validators.py", "assemble"])
    step(["last_run.py"])


if __name__ == "__main__":
    main()
