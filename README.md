# የጥንቸል እና የኤሊ ሩጫ: The Rabbit and the Tortoise

A 60–90 second Amharic-narrated short film for children in Ethiopian families, made by a
code pipeline that turns one file, `storyboard.json`, into keyframes, moving shots, music,
narration and a finished edit in 16:9 and 9:16, with English subtitles and an AI end card.

## Run it

```bash
git clone https://github.com/Reman-tsega/movie-maker.git && cd movie-maker
make setup                 # pip install -r requirements.txt (needs Python 3.10+ and FFmpeg)
cp .env.example .env       # add GEMINI_API_KEY, CF_ACCOUNT_ID, CF_API_TOKEN
make film                  # validate → narration → keyframes → shots → music → assemble
```

**Tested from a clean clone (26 Nov):** `make film` rebuilt both versions in **58 s with 0 new
image or voice calls**. The committed narration, keyframes and chosen score are cache hits, and
only the FFmpeg stages run. Delete a file in `outputs/narration/` or `outputs/keyframes/` (or edit
its shot in `storyboard.json`) and only that item is regenerated through the API.

Outputs: `outputs/final/heritage_16x9_<hash>.mp4`, `outputs/final/heritage_9x16_<hash>.mp4`
and `outputs/final/subtitles_en.srt`. Every model call is logged in `runs.jsonl`.

Every stage is followed by its validator; `make check` re-runs all of them (144 checks).
If the first Gemini key's daily quota runs out, the run asks before using `GEMINI_API_KEY_2`
(non-interactive: set `MM_FALLBACK_KEY=yes` or `no`).

Other targets: `make smoke` (one call per provider), `make radio` (narration on black, for
user testing), `make refs` (character reference sheets only).

GPU stages (Wan 2.2 moving shots, ACE-Step score) run in a Kaggle notebook. See
`kaggle/README.md`. Their outputs are committed under `outputs/wan/` and `outputs/music/`,
so `make film` reproduces the film without a GPU. Shots without a Wan clip fall back to a
Ken Burns move automatically.

### Windows (no `make`)

```powershell
winget install Gyan.FFmpeg            # then reopen the terminal
pip install -r requirements.txt
copy .env.example .env                # add your keys
python pipeline/film.py               # = make film (stages + validators + last-run summary)
```

## Change one shot

Edit a shot's `narration`, `image_prompt` or `motion` in `storyboard.json` and run `make film`.
Each stage hashes its inputs, so only that shot is regenerated. Check `runs.jsonl`, or run `python pipeline/last_run.py`, which lists the regenerated shots and
the cache hits.

## What it costs

See [COSTS.md](COSTS.md). Everything runs on free tiers.

## Documents

[DESIGN.md](DESIGN.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [EXPERIMENTS.md](EXPERIMENTS.md) ·
[FAILURES.md](FAILURES.md) · [COSTS.md](COSTS.md) · [ETHICS.md](ETHICS.md)

## Tools

Coding agent: Claude Code wrote most of the pipeline code under my direction; I designed the
stages, the story and the storyboard, and reviewed every script. Models: Gemini TTS (narration),
FLUX on Cloudflare Workers AI (keyframes), Wan 2.2 TI2V-5B (motion), ACE-Step 1.5 (score),
FFmpeg (assembly).
