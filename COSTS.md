# Costs and latency (measured)

All figures come from `runs.jsonl` (refresh with `python pipeline/costs.py`). Everything ran on
**free tiers with no payment card**; the dollar figures are what the same usage would cost at list price.

## Per stage: latency, compute, cost
| Stage | Model / tool | Where it ran | Mean latency | GPU minutes | CPU minutes | List-price equivalent |
|---|---|---|---|---|---|---|
| Script (screenplay + back-translation) | Gemini 3 Flash | Google (hosted) | 6.8 s / call | hosted, not metered to me | — | $0.0003 / call (343 input tokens; input side only) |
| Narration | Gemini 3.8 Flash TTS | Google (hosted) | 5.5 s / line | hosted | — | **≈ $0.08** for all 336 s of audio generated (all takes and experiments); the final 56 s ≈ $0.013 |
| Narration check | Gemini 3 Flash | Google (hosted) | 15.3 s / batch | hosted | — | ≈ $0.001 / run |
| Keyframes (2 refs + 10 shots, all retakes) | FLUX.2 klein 4B | Cloudflare (hosted) | 9.3 s / image | hosted | — | **≈ $0.03** (≈ 115 neurons per image with references; $0.011 / 1k neurons) |
| Shots | FFmpeg zoompan (eased) | local CPU | 1.3 s / shot | 0 | ≈ 0.2 per full set | $0 |
| Music (3 candidates, 70 s each) | ACE-Step 1.5 turbo | **Kaggle CPU** (GPU job queued 14+ h, F9) | ≈ 11.5 min / track | **0** | **≈ 34.4** (686 + 679 + 697 s) | $0 (Kaggle free) |
| Moving shots | Wan 2.2 TI2V-5B | not run (F9, F15) | — | **0** | — | — |
| Assembly (both formats) | FFmpeg | local CPU | ≈ 25 s / export | 0 | ≈ 0.8 per film | $0 |
| Validators (144+ checks) | `validators.py` + ffprobe | local CPU | < 6 s / stage | 0 | < 0.5 | $0 |
| **Full rebuild from a clean clone** | | | **58 s** (0 API calls) | **0** | ≈ 1 | **$0** |

**Total list-price equivalent of the whole project: under $0.15.** GPU minutes used: **0**. The
only heavy compute (ACE-Step) ran on Kaggle CPU because no GPU slot opened.

Since 26 Nov every new model call logs its own `cost_usd_list_equiv` (TTS from audio seconds, FLUX
from output and reference tiles, Gemini text from input tokens). Earlier lines were logged before
that field was filled, so their totals above are computed from the files and counts.

## Raw log summary (`python pipeline/costs.py`)
| Stage | Model | Real calls | Failed | Cache hits | Mean latency (s) | Total (s) | GPU min |
|---|---|---|---|---|---|---|---|
| assemble | ffmpeg | 35 | 0 | 3 | 25.2 | 881 | 0.0 |
| keyframes | @cf/black-forest-labs/flux-2-klein-4b | 29 | 0 | 69 | 9.3 | 269 | 0.0 |
| music | ACE-Step-1.5 | 0 | 0 | 5 | 0.0 | 0 | 0.0 |
| music | ACE-Step-1.5 acestep-v15-turbo | 3 | 0 | 0 | 687.5 | 2062 | 0.0 |
| music | ffmpeg-placeholder | 2 | 0 | 0 | 1.1 | 2 | 0.0 |
| narration | gemini-2.5-flash-preview-tts | 8 | 0 | 1 | 5.8 | 46 | 0.0 |
| narration | gemini-3.1-flash-tts-preview | 12 | 1 | 34 | 4.3 | 47 | 0.0 |
| narration | gemini-3.8-flash-tts | 28 | 1 | 137 | 5.5 | 148 | 0.0 |
| narration_check | gemini-3-flash-preview | 11 | 0 | 0 | 14.7 | 162 | 0.0 |
| script | gemini-3-flash-preview | 1 | 0 | 0 | 6.8 | 7 | 0.0 |
| shots | ffmpeg-zoompan | 61 | 0 | 59 | 1.3 | 77 | 0.0 |
| shots | wan-missing->kenburns | 40 | 0 | 0 | 0.0 | 0 | 0.0 |
| smoke | @cf/black-forest-labs/flux-1-schnell | 1 | 1 | 0 | 0.0 | 0 | 0.0 |
| smoke | @cf/black-forest-labs/flux-2-klein-4b | 1 | 0 | 0 | 5.8 | 6 | 0.0 |
| smoke | gemini-3.8-flash-tts | 2 | 0 | 0 | 5.5 | 11 | 0.0 |
| smoke | gemini:list-models | 2 | 0 | 0 | 0.4 | 1 | 0.0 |
| tts_compare | gemini-2.5-flash-preview-tts | 3 | 0 | 0 | 4.1 | 12 | 0.0 |
| tts_compare | gemini-3.1-flash-tts-preview | 3 | 1 | 0 | 4.4 | 9 | 0.0 |
| tts_compare | gemini-3.8-flash-tts | 7 | 2 | 0 | 3.2 | 16 | 0.0 |
| validate:assemble | validators.py | 4 | 0 | 0 | 5.6 | 22 | 0.0 |
| validate:keyframes | validators.py | 4 | 0 | 0 | 1.5 | 6 | 0.0 |
| validate:music | validators.py | 4 | 0 | 0 | 0.9 | 4 | 0.0 |
| validate:narration | validators.py | 5 | 0 | 0 | 0.1 | 1 | 0.0 |
| validate:script | validators.py | 1 | 0 | 0 | 0.0 | 0 | 0.0 |
| validate:shots | validators.py | 4 | 0 | 0 | 1.5 | 6 | 0.0 |
| validate:storyboard | validators.py | 4 | 0 | 0 | 0.0 | 0 | 0.0 |

583 log lines, 308 cache hits.

## Free-tier limits found (versus what the brief said)
| Service | Brief said | What I actually hit |
|---|---|---|
| Gemini TTS | "free tier" | **about 10 requests per model per day per project** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quota 10), plus a per-minute limit; each model and each project has its own quota (F3, E11) |
| Gemini text | — | `gemini-2.5-flash` 404 for new users; `gemini-3.8-flash` 503 at peak; `gemini-3-flash-preview` worked |
| Cloudflare Workers AI | "roughly 50–170 images a day" | 10,000 neurons a day ≈ 90 FLUX.2 klein images; never hit (≈ 40 images). One false positive from the safety filter (F14) |
| Kaggle | "about 30 GPU hours a week" | hours were never the limit; **the queue was** (14+ h `QUEUED`); CPU started in < 1 min (F9) |

## Frontier comparison
No frontier lane (Omni Flash, Nano Banana, Lyria 3.5) was opened for this cohort, so there was no
access to compare. The comparison that *was* measured is across Gemini TTS models on Amharic
ejectives (E11: blind, native-speaker judged).

**Price sources (checked 26 Nov 2026):** Google Cloud Text-to-Speech pricing (Gemini 3.8 Flash TTS:
$9.00 per 1M audio output tokens until 31 Dec 2026, 25 tokens per second of audio); Cloudflare
Workers AI pricing (flux-2-klein-4b: 26.05 neurons per 512² output tile, 5.37 per input tile,
$0.011 per 1,000 neurons, 10,000 free neurons a day); Vertex AI pricing (Gemini 3 Flash Preview
input: $0.50 per 1M text tokens, $1.00 per 1M audio tokens).
