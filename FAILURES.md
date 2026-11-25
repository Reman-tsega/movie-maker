# Failures

Format: what broke, what I tried, what fixed it.

## F1: The cache did not notice code changes (25 Nov)
- **Broke:** I fixed the end-card layout and the subtitle size in `assemble.py`, re-ran it, and
  the output looked identical. The output name was a hash of the *inputs* only, so the old video
  was reused.
- **Tried:** deleting `outputs/final` by hand. That works once, but it defeats caching.
- **Fixed:** added `code_version(__file__)` (a hash of the stage's own source) to the cache key for
  `shots.py` and `assemble.py`. Changing the code now rebuilds only that stage's outputs.

## F2: An API key was pasted into a chat (25 Nov)
- **Broke:** while setting up, the Gemini key was pasted into a chat with the coding agent.
- **Fix:** revoke that key in Google AI Studio and create a new one (_status: to confirm_). Keys live
  only in `.env` (git-ignored) or in the environment's secret store, and `.env.example` documents
  the names. The exposed key was never written to any file in this repo.

## F3: Gemini TTS free tier allows 10 requests a day per model (25 Nov)
- **Broke:** after 2 smoke-test calls and 8 narration lines, Gemini returned HTTP 429:
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: "10"`, `retryDelay: 52261s`.
  The brief says only "free tier"; the real limit is **10 TTS requests per model per day**.
- **Tried:** the retry with backoff (3 attempts). That was useless for a daily quota, and it wasted time.
- **Fixed:** (1) a daily-quota 429 now fails fast instead of retrying; (2) `models.tts_fallbacks` in
  the storyboard: each Gemini TTS model has its own quota, so a shot can fall back to the next model,
  logged with `status: "fallback"`; (3) the cache means the finished lines were never re-requested.
  Note: on the re-run, the main model served s09 and s10 again, so the quota did not behave as a
  strict 10-per-day counter. Logged as observed, cause unknown.
- **Lesson:** with 10 calls a day, narration retakes are the scarce resource. Fix the text first
  (native-speaker review), then generate.

## F4: The narration is twice as long as planned (25 Nov)
- **Broke:** 10 lines, 90 Amharic words, produced 173 s of speech (s01: 9 words in 18 s), so the
  radio cut is 187 s against a 60–90 s target. s02 (5 words) was a normal 4.9 s.
- **Suspected cause:** the long English style instruction placed before the text is sometimes read
  aloud. Being checked by listening (s01 vs s02).
- **Also:** Gemini's text models returned 503 "high demand" for a transcription check, and
  `gemini-2.5-flash` returned 404, "no longer available to new users".

## F5: FLUX.1 schnell on Cloudflare rejects a seed (25 Nov)
- **Broke:** HTTP 400 `Additional or unevaluated properties '/seed' ... not allowed`.
- **Fixed:** switched to FLUX.2 klein 4B (Apache 2.0), which accepts multipart input with reference
  images. See EXPERIMENTS E3 and E4.
