# Costs and latency (measured)

Everything ran on free tiers, with no payment card. The numbers below are generated from
`runs.jsonl` by `python pipeline/costs.py` (re-run it to refresh). "Real calls" are model or
FFmpeg runs; "cache hits" are skipped re-runs.

| Stage | Model | Real calls | Failed | Cache hits | Mean latency (s) | Total (s) | GPU min |
|---|---|---|---|---|---|---|---|
| assemble | ffmpeg | 9 | 0 | 1 | 21.2 | 191 | 0.0 |
| keyframes | @cf/black-forest-labs/flux-2-klein-4b | 26 | 0 | 12 | 9.5 | 248 | 0.0 |
| music | ffmpeg-placeholder | 2 | 0 | 0 | 1.1 | 2 | 0.0 |
| narration | gemini-2.5-flash-preview-tts | 7 | 0 | 1 | 5.7 | 40 | 0.0 |
| narration | gemini-3.1-flash-tts-preview | 12 | 1 | 34 | 4.3 | 47 | 0.0 |
| narration | gemini-3.8-flash-tts | 17 | 1 | 59 | 5.5 | 88 | 0.0 |
| narration_check | gemini-3-flash-preview | 5 | 0 | 0 | 14.4 | 72 | 0.0 |
| shots | ffmpeg-zoompan | 17 | 0 | 3 | 1.2 | 20 | 0.0 |
| shots | wan-missing->kenburns | 8 | 0 | 0 | 0.0 | 0 | 0.0 |
| smoke | @cf/black-forest-labs/flux-1-schnell | 1 | 1 | 0 | 0.0 | 0 | 0.0 |
| smoke | @cf/black-forest-labs/flux-2-klein-4b | 1 | 0 | 0 | 5.8 | 6 | 0.0 |
| smoke | gemini-3.8-flash-tts | 2 | 0 | 0 | 5.5 | 11 | 0.0 |
| smoke | gemini:list-models | 2 | 0 | 0 | 0.4 | 1 | 0.0 |
| tts_compare | gemini-2.5-flash-preview-tts | 3 | 0 | 0 | 4.1 | 12 | 0.0 |
| tts_compare | gemini-3.1-flash-tts-preview | 3 | 1 | 0 | 4.4 | 9 | 0.0 |
| tts_compare | gemini-3.8-flash-tts | 6 | 2 | 0 | 3.1 | 12 | 0.0 |

231 log lines, 110 cache hits.

## Free-tier limits found (versus what the brief said)

| Service | Brief said | What I actually hit |
|---|---|---|
| Gemini TTS (AI Studio key) | "Free tier" | **About 10 requests per model per day per project** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: "10"`), plus a per-minute limit (calls 25–60 s apart recovered). Each model has its own quota, and a second project key doubles it (FAILURES F3, E11) |
| Gemini text (transcription check) | — | `gemini-2.5-flash` 404 for new users; `gemini-3.8-flash` 503 "high demand" at night; `gemini-3-flash-preview` worked |
| Cloudflare Workers AI | "roughly 50–170 images a day" | 10,000 neurons a day free. A 1024² FLUX.2 klein image ≈ 104 neurons out + 5.4 per 512² reference tile, so **about 90 images a day**. Never hit the limit (25 images) |
| Kaggle GPU | "about 30 GPU hours a week" | Hours are not the limit; **the queue is**. A GPU job sat `QUEUED` for 14+ hours (F9); a CPU job started in under a minute |

## List-price equivalent (what this would cost on paid tiers)

| Item | Measured usage | List price | Cost |
|---|---|---|---|
| Gemini 3.8 Flash TTS | 336 s of audio generated across all takes and experiments (25 audio tokens/s → 8,400 tokens) | $9.00 per 1M audio output tokens until 31 Dec 2026, then $18.00 | **≈ $0.08** (the final 54 s of narration alone ≈ $0.01) |
| FLUX.2 klein 4B (Cloudflare) | 25 images at 1024², most with 1–2 reference images | $0.011 per 1,000 neurons; ≈ 110 neurons/image | **≈ $0.03** |
| Gemini text (narration checks) | 5 calls with 10 short audio clips each | free tier | ≈ $0 |
| FFmpeg (Ken Burns, assembly) | CPU only, ≈ 1.2 s per shot, ≈ 21 s per export | — | $0 |
| Kaggle (ACE-Step, Wan) | see the GPU minutes in the table | free tier | $0 |

**Total list-price equivalent so far: under $0.15.** Money was never the constraint. Quotas and
queues were. The scarcest resource was **10 TTS requests a day**, which is why caching, per-line
regeneration and the native-speaker review *before* generating mattered most.

## Frontier comparison
No frontier lane (Omni Flash, Nano Banana, Lyria 3.5) was opened for this cohort, so there is no
paid-versus-open comparison. The only "versus" measured is between the Gemini TTS models (E11).

Sources: Google Cloud Text-to-Speech pricing page (Gemini 3.8 Flash TTS);
Cloudflare Workers AI pricing page (flux-2-klein-4b tiles, $0.011 / 1k neurons, 10k free neurons a day).
