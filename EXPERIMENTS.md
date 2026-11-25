# Experiments

Format: **hypothesis → change → result → decision.** Seeds are fixed unless the change is the seed.

## E1: Code version in the cache key
- **Hypothesis:** hashing only the inputs is enough for correct caching.
- **Change:** edited `assemble.py` (end-card layout), re-ran with the same inputs.
- **Result:** the stale video was reused (see FAILURES F1). After adding the source hash, only the
  assembly rebuilt; all 10 shot clips stayed cache hits.
- **Decision:** source hash in the key for every FFmpeg stage.

## E2: Vertical subtitle size
- **Hypothesis:** the same subtitle style works for 16:9 and 9:16.
- **Change:** rendered both with FontSize 18 (16:9) and 11 (9:16).
- **Result:** in 9:16, the first subtitle wrapped to 3 lines (the limit is 2). FontSize 8 with the
  same 40-character wrap gives 2 lines.
- **Decision:** a separate style per aspect ratio.
