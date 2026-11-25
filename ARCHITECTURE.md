# Architecture

## One contract, five stages

```
storyboard.json ──(schema/storyboard.schema.json, validated before every stage)
      │
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
