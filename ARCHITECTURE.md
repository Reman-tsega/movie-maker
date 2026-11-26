# Architecture

## One contract, five stages

```
storyboard.json ──(schema/storyboard.schema.json, validated before every stage)
      │
      ├─ script.py      screenplay + Gemini back-translation     → outputs/script/
      ├─ narration.py   Gemini TTS, one WAV per shot            → outputs/narration/
      ├─ keyframes.py   FLUX (Cloudflare), refs then one/shot    → outputs/keyframes/
      ├─ shots.py       Wan clip (from Kaggle) or Ken Burns      → outputs/shots/
      ├─ music.py       chosen ACE-Step track or temp pad        → outputs/music/
      └─ assemble.py    FFmpeg: cut, duck, subtitles, loudness,  → outputs/final/
                        end card, 16:9 + 9:16
```

`storyboard.json` is the only place creative decisions live: shots, reasons, prompts, seeds,
narration, subtitles, music cues, voice and model names. Stages never hard-code prompts.

Each stage writes `outputs/<stage>/manifest.json`, mapping shot ids to the current output file.
The next stage reads that manifest, not a glob, so a stage only sees the outputs that match the
current storyboard.

## Validation

`common.load_storyboard()` validates against the JSON Schema (8–12 shots, required reason per
shot, allowed shot sizes, motion modes) and then checks what the schema cannot: unique shot ids,
known characters, and music cues that point to real shots.

## Caching

Every output file is named `<shot>_<hash>`, where the hash covers everything that affects it:

| Stage | Hash inputs |
|---|---|
| narration | TTS model, voice, style instruction, narration text |
| keyframes | image model, full prompt (shot + character descriptions + style block), seed |
| shots | keyframe file, motion settings, duration, mode, Wan source clip, **shots.py source** |
| assemble | timeline, music file, ducking settings, end card, shot files, **assemble.py source** |

If the file exists, it is a cache hit: no model call, and a `cache_hit: true` log line.
Changing one narration line changes one narration hash. That changes the shot's duration, so
only that shot's clip and the final assembly rebuild. The source-code hash was added after a
real bug, where a code change did not invalidate cached videos (FAILURES.md, F1).

## Timing

Narration drives the edit: shot length = max(storyboard `duration_s`, narration length + 1.0 s),
and narration starts 0.4 s into each shot. `assemble.py` refuses to run if a shot clip's length
no longer matches the timeline (a stale shot).

## Failure handling

- `with_retries()`: 3 attempts with exponential backoff on HTTP 429/5xx and network errors.
  Permanent errors (4xx) fail fast with the response body.
- Every failure is logged to `runs.jsonl` with `status: "error"`.
- Fallbacks: a `wan` shot with no Wan clip renders as Ken Burns (logged as `status: "fallback"`).
  No chosen score renders a temp pad. The film always renders.

## Audio

Narration track → music looped, trimmed, faded, −6 dB → `sidechaincompress` keyed by the voice
(threshold 0.02, ratio 6, attack 300 ms, release 1500 ms) → mix → `loudnorm` to −14 LUFS, −1 dBTP.

## Picture

Keyframes are square (1024²) with the subject centred, so one master crops cleanly to 16:9
(1280×720) and 9:16 (720×1280). Subtitles: at most 2 lines of 40 characters, white with an
outline; raised (`MarginV`) in vertical to stay clear of the platform buttons.

## Logging

`runs.jsonl`: one JSON line per model call or cache hit: `ts, stage, shot, model, params, seed,
latency_s, gpu_s, cost_usd_list_equiv, cache_hit, status, output, error`.

## Validators (one per stage)
`pipeline/validators.py <stage|all>` runs after each stage in `make film`; any FAIL exits non-zero
and stops the run. 144 checks today, including regression tests for real failures (F4 speaking
rate, F13 nested WAV and line-edge noise, E15 true peak). Results are logged as `validate:<stage>`.

## Audio tuner
Before mixing, each narration line goes through `audio_tuning` from the storyboard: a high-pass
(rumble), a short fade-in and a fade-out, so no line can click at a cut (F13).

## API keys and quota
Gemini TTS has two keys (two Google projects, separate daily quotas). Order: same model on key 1 →
same model on key 2 → next model. Before the first use of key 2, the run **asks** (interactive) or
follows `MM_FALLBACK_KEY=yes|no` (non-interactive, default yes); the decision is logged.

## Delivery tags and timing
Per-shot `delivery` tags (`[warm, calm storyteller]`) are sent before the line and are not spoken
(E14). `timing.lead_s` and `timing.pad_after_s` set where narration starts and how long a shot
holds after it. 0.4 s crossfades keep the cut points (and the narration sync) unchanged (E16).

## What is committed
API and GPU outputs (narration WAVs with C2PA, keyframes, the chosen score, `runs.jsonl`) are
committed; FFmpeg outputs (shot clips, final renders) are rebuilt exactly by `make film` (F12).

## Script stage
`script.py` turns the storyboard into a screenplay (`outputs/script/script_<hash>.md`): each shot's
beat, reason, size, delivery, Amharic line, English subtitle, and a Gemini back-translation of the
Amharic so subtitles can be checked against meaning. If the API call fails, the screenplay is
still written and the error logged; this stage never blocks the film.

## Cost per call
`log_call()` records `cost_usd_list_equiv` for every model call: TTS from the audio length
($9 / 1M audio tokens, 25 tokens/s), FLUX.2 klein from output and reference tiles
($0.011 / 1k neurons), Gemini text from input tokens. Prices are constants in `common.py`, with
sources in COSTS.md.
