"""Entry point pushed to Kaggle by kaggle/push_job.sh. Copies the repo snapshot (attached as a
private Kaggle dataset) into /kaggle/working, installs the model code and runs one GPU job.
JOB is set by push_job.sh: "music" or "wan". Outputs land in /kaggle/working/movie-maker/outputs/."""
import glob, os, shutil, subprocess, sys, time

JOB = "__JOB__"
ARGS = "__ARGS__"
W = "/kaggle/working"
src = os.path.dirname(glob.glob("/kaggle/input/**/storyboard.json", recursive=True)[0])
repo = f"{W}/movie-maker"
shutil.copytree(src, repo, dirs_exist_ok=True)
os.environ["MM_REPO"] = repo


def sh(cmd):
    print("+", cmd, flush=True)
    t = time.time()
    r = subprocess.run(cmd, shell=True)
    print(f"  ({time.time() - t:.0f}s, exit {r.returncode})", flush=True)
    return r.returncode


sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh("python --version")
if JOB == "music":
    # Kaggle's image is Python 3.13; ACE-Step needs <3.13 -> uv builds a 3.12 venv (FAILURES F10)
    sh("pip install -q uv")
    sh(f"cd {W} && git clone -q https://github.com/ACE-Step/ACE-Step-1.5.git")
    sh(f"cd {W}/ACE-Step-1.5 && uv sync -q 2>&1 | tail -5")
    # huggingface-cli was retired; the replacement is `hf`
    sh(f"hf download ACE-Step/Ace-Step1.5 --local-dir {W}/ACE-Step-1.5/checkpoints > /dev/null")
    rc = sh(f"cd {W}/ACE-Step-1.5 && uv run python {repo}/kaggle/ace_step_music.py {ARGS}")
elif JOB == "wan":
    sh(f"cd {W} && git clone -q https://github.com/Wan-Video/Wan2.2.git")
    sh(f"cd {W}/Wan2.2 && grep -v flash_attn requirements.txt > req.txt && pip install -q -r req.txt 2>&1 | tail -3")
    sh(f"hf download Wan-AI/Wan2.2-TI2V-5B --local-dir {W}/Wan2.2-TI2V-5B > /dev/null")
    rc = sh(f"python {repo}/kaggle/wan_shots.py {ARGS}")
# keep only the outputs in /kaggle/working so the download is small
for d in ("ACE-Step-1.5", "Wan2.2", "Wan2.2-TI2V-5B"):
    shutil.rmtree(f"{W}/{d}", ignore_errors=True)
sys.exit(0)
