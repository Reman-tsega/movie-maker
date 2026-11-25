#!/usr/bin/env bash
# Usage: kaggle/push_job.sh music "--seeds 11,22,33 --duration 75"
#        kaggle/push_job.sh wan   "--frames 73 --steps 30"
# 1) snapshots the repo (no .env, no outputs except keyframes) into a private Kaggle dataset,
# 2) pushes kaggle/kernel_runner.py as a GPU script kernel with that dataset attached.
# Fetch results later with: kaggle kernels output <user>/movie-maker-<job> -p outputs/kaggle_<job>
set -euo pipefail
JOB=$1; ARGS=${2:-}
USER=$(kaggle config view | awk '/username/{print $3}')
ROOT=$(cd "$(dirname "$0")/.." && pwd)
STAGE=$(mktemp -d)
mkdir -p "$STAGE/data/outputs"
cp -r "$ROOT/storyboard.json" "$ROOT/kaggle" "$STAGE/data/"
[ -d "$ROOT/outputs/keyframes" ] && cp -r "$ROOT/outputs/keyframes" "$STAGE/data/outputs/"
cat > "$STAGE/data/dataset-metadata.json" <<J
{"title": "movie-maker-repo", "id": "$USER/movie-maker-repo", "licenses": [{"name": "other"}]}
J
if kaggle datasets status "$USER/movie-maker-repo" >/dev/null 2>&1; then
  kaggle datasets version -p "$STAGE/data" -m "snapshot $(date -u +%FT%TZ)" -r zip -q
else
  kaggle datasets create -p "$STAGE/data" -r zip -q
fi
mkdir -p "$STAGE/kernel"
sed -e "s|__JOB__|$JOB|" -e "s|__ARGS__|$ARGS|" "$ROOT/kaggle/kernel_runner.py" > "$STAGE/kernel/runner.py"
cat > "$STAGE/kernel/kernel-metadata.json" <<J
{"id": "$USER/movie-maker-$JOB", "title": "movie-maker-$JOB", "code_file": "runner.py",
 "language": "python", "kernel_type": "script", "is_private": true,
 "enable_gpu": true, "enable_internet": true,
 "dataset_sources": ["$USER/movie-maker-repo"], "competition_sources": [], "kernel_sources": []}
J
sleep 20   # let the new dataset version finish processing before the kernel mounts it
kaggle kernels push -p "$STAGE/kernel"
echo "pushed $USER/movie-maker-$JOB; status: kaggle kernels status $USER/movie-maker-$JOB"
