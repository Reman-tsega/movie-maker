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
- **Cause (confirmed):** Gemini TTS **read the English style instruction aloud**. A transcription of
  s01 by `gemini-3-flash-preview` gave 0:00–0:11 English ("Read this in Amharic like a warm
  grandmother…"), then 0:11–0:18 the Amharic line. My tester couldn't make out a voice at all in
  VLC: the file sounded like the wrong content in the wrong language.
- **Tried:** two prompt formats on one line (EXPERIMENTS E7). "Say warmly …: <text>" still had
  English at the start.
- **Fixed:** send the Amharic text only (`voice.style_instruction` is now empty); tone comes from
  the voice choice. Speech went from 173 s to 56.7 s, and the radio cut from 187 s to 71.5 s.
  Added `pipeline/narration_check.py`, which transcribes every line and flags non-Amharic speech or
  a slow rate; the result is 10/10 OK.
- **Also:** Gemini's text models returned 503 "high demand" for a transcription check, and
  `gemini-2.5-flash` returned 404, "no longer available to new users".

## F5: FLUX.1 schnell on Cloudflare rejects a seed (25 Nov)
- **Broke:** HTTP 400 `Additional or unevaluated properties '/seed' ... not allowed`.
- **Fixed:** switched to FLUX.2 klein 4B (Apache 2.0), which accepts multipart input with reference
  images. See EXPERIMENTS E3 and E4.

## F6: The one-request batch could not be split at the pauses (25 Nov)
- **Broke:** to save quota I sent all 10 lines in one TTS request (18.6 s) and cut the audio at the
  9 longest pauses. The length check rejected the cut, because the voice does not pause clearly
  enough between some lines.
- **Fixed (fallback):** the pipeline logged the batch as an error and generated per line. One
  request was spent on a failed idea, but nothing broke.
- **Side effect:** the main TTS model hit its quota on s07, so s07 used `gemini-2.5-flash-preview-tts`.
  The voice may differ slightly, so it will be re-recorded when the quota resets.

## F7: The history rewrite deleted a cached file (25 Nov)
- **Broke:** to get the repo bundle under the size limit I removed large regenerable files from git
  history (`filter-branch`). That also deleted the working copy of the placeholder music, and the
  next `assemble` failed.
- **Fixed:** `music.py` recreated it, because it is deterministic. Lesson: keep regenerable binaries
  out of git from the start (`.gitignore` now covers them).

## F8: Gemini TTS flattens Amharic ejective consonants (25 Nov)
- **Broke:** a native-speaker listen (me) found the voice replacing ejectives with plain consonants:
  ሩ**ጫ** said as ሩቻ (ጫ→ቻ), ሮ**ጠ**ች as ሮተች (ጠ→ተ), ሩ**ቅ** as ሩክ (ቅ→ክ). The automatic
  transcription check (E9) did **not** catch this. It "heard" the right words, because a text
  model transcribes what it expects. Only a human ear caught it.
- **Why it matters:** ejectives are distinctive Amharic sounds, so a child hears an accent.
- **Can't fix with spelling:** Ge'ez script already writes the ejective; there is no stronger spelling.
- **Trying:** the same three lines with three models (EXPERIMENTS E11), chosen by ear.

## F9: The Kaggle GPU job sat in the queue for more than 3 hours (25 Nov)
- **Broke:** `kaggle kernels push` with `enable_gpu: true` at 17:44 UTC; still `QUEUED` at 20:50 UTC.
  Account phone-verified, dataset `ready`.
- **Tried:** checked status, dataset readiness and kernel list.
- **Next:** start the same kernel from the Kaggle web UI with the accelerator set to "GPU T4 x2".
  The brief is right that GPU queueing, not money, is the binding constraint.
