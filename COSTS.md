# Costs and latency (measured)

All numbers come from `runs.jsonl`. They will be filled in from the real runs.

| Stage | Model / tool | Where | Calls | Mean latency | GPU minutes | Free-tier limit found | List-price equivalent |
|---|---|---|---|---|---|---|---|
| narration | Gemini TTS | Gemini API (free) | | | – | | |
| keyframes | FLUX.1 schnell | Cloudflare Workers AI (free) | | | – | | |
| shots | Wan 2.2 TI2V-5B | Kaggle 2×T4 | | | | | |
| shots | Ken Burns (FFmpeg) | local CPU | 10 | ~1 s/shot (dry run) | 0 | – | $0 |
| music | ACE-Step 1.5 | Kaggle T4 | | | | | |
| assemble | FFmpeg | local CPU | | ~13 s per aspect (dry run) | 0 | – | $0 |
