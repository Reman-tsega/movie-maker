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

## E3: Is a fixed seed reproducible on Cloudflare FLUX.2 klein?
- **Hypothesis:** the same prompt and seed (7) give the same image, so the seed can anchor consistency.
- **Change:** called `flux-2-klein-4b` twice with an identical prompt and seed 7.
- **Result:** two clearly different rabbits (different pose and background); the files differ.
  Latency 16.4 s and 14.4 s.
- **Decision:** don't rely on seeds for consistency on this endpoint. Seeds are still logged, but
  consistency comes from reference images (E4), and reproducibility comes from caching the files.

## E4: Does a reference image keep the character the same?
- **Hypothesis:** passing the first rabbit as `input_image_0` keeps her identity in a new scene.
- **Change:** same model; prompt "the same rabbit ... asleep under a large tree", plus the reference.
- **Result:** same face, fur, eye colour and painted style in a new pose (7.7 s). **But the scarf
  disappeared**, because the prompt did not mention it.
- **Decision:** every keyframe gets (a) the character reference sheet as an input image **and**
  (b) the full locked character description in the prompt. Implemented in `keyframes.py`.
