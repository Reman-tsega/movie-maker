# Experiments

19 entries. Each has a hypothesis, the change, a measured result and the decision it led to. Seeds are fixed where the model honours them (it doesn't on Cloudflare FLUX, see E3); comparisons change one thing at a time.

| # | Question tested | Planned? |
|---|---|---|
| E1 | Code version in the cache key | reaction to a failure |
| E2 | Vertical subtitle size | planned |
| E3 | Is a fixed seed reproducible on Cloudflare FLUX.2 klein? | planned |
| E4 | Does a reference image keep the character the same? | planned |
| E5 | Multi-pose reference sheets leak into the shots | planned |
| E6 | Fix only the shots that are wrong | planned |
| E7 | How to give the TTS a style without it being read aloud | planned |
| E8 | One TTS request for the whole script | planned |
| E9 | Automatic transcription as a narration check | planned |
| E10 | Is the narration check itself reliable? | reaction to a failure |
| E11 | Which TTS model pronounces Amharic ejectives best? (in progress) | planned |
| E12 | Two characters in a vertical frame | planned |
| E13 | Choosing the score from three ACE-Step candidates | planned |
| E14 | Bracketed delivery tags (from user test 1) | planned |
| E15 | Hitting −14 LUFS without peaks over −1 dB | planned |
| E16 | Smoother camera and softer cuts (from user test 2) | planned |
| E17 | s09, "make the turtle look extra happy when she wins" (a 9-year-old's request) | planned |
| E18 | Validators after every stage | planned |
| E19 | Storyboard reflects what actually ran | reaction to a failure |

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

## E5: Multi-pose reference sheets leak into the shots
- **Hypothesis:** a 3-pose character sheet (front, side, running) is the best reference.
- **Change:** generated all 10 keyframes with the multi-pose sheets as `input_image_0/1`.
- **Result:** identity was very consistent, but 4 of 10 shots (s01, s02, s07, s10) showed 2–3
  copies of the rabbit, and s01 lost the tortoise. The model copied the sheet's layout, not just
  the character.
- **Change 2:** single-pose, full-body references, plus an explicit count in every prompt
  ("exactly one rabbit and exactly one tortoise, no duplicates").
- **Result 2:** 0 of 10 shots with duplicates; s01 now shows both characters at the start line.
  Identity stayed the same. Remaining defect: s04 and s05 copied the reference's blank cream
  background at the bottom.
- **Decision:** single-pose references and explicit counts. Practice note: "a reference sheet
  before keyframes" helped, but the *shape* of the sheet mattered as much as having one.

## E6: Fix only the shots that are wrong
- **Hypothesis:** adding "fully painted edge to edge, no blank areas" to s04 and s05 fixes the cream
  band, and the cache regenerates only those two.
- **Result:** both fixed; `runs.jsonl` shows 2 new image calls and 8 cache hits (and 2 for the refs).
- **Decision:** per-shot prompt fixes, never a full re-run.

## E7: How to give the TTS a style without it being read aloud
- **Hypothesis:** a short "Say warmly …:" prefix steers the tone without being spoken.
- **Change:** the same line (s02) with (A) the Amharic text only and (B) "Say warmly and calmly, like a
  grandmother telling a bedtime story: <text>", both on `gemini-3.1-flash-tts-preview`, then
  transcribed.
- **Result:** (A) 4.3 s, Amharic only. (B) 6.0 s, with English detected at the start.
- **Decision:** text only. Practice note: "a short style instruction improves the voice" (from the
  brief's tips) did *not* hold for Amharic. The model can't tell an English instruction from the
  text it should speak.

## E8: One TTS request for the whole script
- **Hypothesis:** generating all 10 lines in one request and cutting at the longest pauses saves
  9 of the 10 daily requests.
- **Result:** the cut failed the length check (see F6), so it fell back to per-line.
- **Decision:** keep per-line as the default (it also makes retakes cheap). Batch mode stays in the
  code behind a validity check and can be turned off with `--per-line`.

## E9: Automatic transcription as a narration check
- **Hypothesis:** a text model can check TTS output in a language I can't verify by ear at scale.
- **Result:** it caught the spoken instruction (F4) that I had only suspected from durations.
  Now 10/10 lines are Amharic and match the script, apart from spelling variants (ጸ/ፀ).
- **Decision:** `narration_check.py` runs after every narration change.

## E10: Is the narration check itself reliable?
- **Hypothesis:** the transcription check gives the same verdict on the same audio every run.
- **Result:** the first run labelled the language "Amharic" (10/10 OK). The second labelled it
  "amh" (ISO 639-3), and my exact-match check flagged all 10 as non-Amharic: a false alarm from
  the checker, not the audio.
- **Decision:** accept "Amharic", "am" or "amh", and ask for English language names in the prompt.
  An LLM-based check needs its own tolerance for label variation.

## E11: Which TTS model pronounces Amharic ejectives best? (in progress)
- **Hypothesis:** a newer or larger TTS model keeps ጫ / ጠ / ቅ distinct.
- **Change:** s01–s03 (ሩጫ, ሮጠች, ሩቅ) with the same voice (Kore) on three models:
  A `gemini-3.1-flash-tts-preview` (current), B `gemini-3.8-flash-tts`, C `gemini-2.5-flash-preview-tts`
  (`pipeline/tts_compare.py`, outputs in `outputs/tts_compare/`).
- **Result (native-speaker listen, me):** **B, `gemini-3.8-flash-tts`, is clearly the best** at the
  ejectives in ሩጫ / ሮጠች / ሩቅ. A (3.1, the voice in radio cut v3) and C (2.5) flattened them.
- **Decision:** narration switched to 3.8 (`models.tts`). s01–s03 reused from this comparison
  (3 requests saved). The other lines were recorded on the second key; 9/10 are on 3.8. s06 falls
  back to an older model until the daily quota resets, then gets re-recorded with
  `--redo s06`.
- **Quota behaviour seen:** 3.8 calls succeeded and failed alternately within the same minute.
  Spacing calls 25–60 s apart recovered most of them, which points to a per-minute limit on
  top of the daily one.
- **Quota note:** this run also hit the daily quota for 3.1 on both keys, and for 3.8 after 4 calls.

## E12: Two characters in a vertical frame
- **Hypothesis:** a centre crop of the square keyframe works for 9:16.
- **Result (rough cut v1 review):** in s01, s09 and s10 (two characters side by side), the 9:16 centre
  crop cut the tortoise in half.
- **Change:** for 9:16 only, shots with two characters (derived from `shot.characters` in the
  storyboard) pan slowly from left to right across the full width.
- **Result:** the frame at 0.5 s shows the rabbit, at 5 s the tortoise; one-character shots are unchanged.
- **Decision:** keep. The rule lives in `assemble.py` but is driven by the storyboard, so a new
  two-character shot gets it automatically.

## E13: Choosing the score from three ACE-Step candidates
- **Hypothesis:** the caption "gentle instrumental children's folk lullaby, Ethiopian krar and soft
  masenqo, light hand percussion …" (84 BPM, C major) gives an Ethiopian-sounding underscore.
- **Change:** 3 seeds (11, 22, 33), 70 s each, ACE-Step 1.5 turbo with the LM planner off
  (`thinking=False`, because BPM, key and length are fixed), on Kaggle CPU (≈ 11.5 min each, F9–F11).
- **Result:** all three are instrumental and clean (−14.4 / −15.9 / −15.8 LUFS). A first-pass
  description by `gemini-3-flash-preview` heard "synth keyboard and light percussion … not
  Ethiopian" in all three. **The model ignored the krar and masenqo** in the caption. A likely
  cause is little Ethiopian instrumentation in its training data; to test with a caption without
  the instrument names.
- **Choice, by ear** (each candidate under the full ducked narration, A = seed 11, B = 22, C = 33):
  - **A (seed 11): chosen.** Softest and least intrusive under the Amharic voice; the words stay
    clear in every beat, and it keeps a light, playful fable mood.
  - B (seed 22): a slightly stronger melodic and percussive presence between phrases; pleasant, but
    a touch more prominent under the voice than A.
  - C (seed 33): more active melodic and accented phrasing that competes with the narration in places.
- **Decision:** seed 11 → `outputs/music/score_chosen.wav` (`music.chosen_track`). The other two are
  kept locally but not committed (13 MB each, F12).

## E14: Bracketed delivery tags (from user test 1)
- **Hypothesis (Bilkis's suggestion):** delivery cues make the voice less dull, if they aren't spoken.
  E7 showed that a free-text English instruction *is* spoken.
- **Change:** s04 sent as `[proudly, with a playful smile] ጥንቸል በፍጥነቷ በመኩራራት [short pause] «ጊዜ አለኝ» ብላ አሰበች።`
  on `gemini-3.8-flash-tts`, then transcribed.
- **Result:** transcript pure Amharic (tags not spoken); 5.21 s versus 4.66 s untagged, so the pause
  is honoured; tone described as "narrative and expressive, typical of a storyteller."
- **Decision:** a `delivery` field on every shot (applied to all 10 lines only after this one-line test
  passed). Practice note: short bracket tags work where a sentence-long instruction failed (E7).
- **Regression found by ear:** on the full run, s04 with `[short pause]` inside the sentence dropped
  a syllable (በመኩራራት → በመኩራት; the transcription check also showed it, but marked it OK).
  s04 went back to no tags; its earlier recording was a cache hit. Lesson: inline tags *inside* a
  word group can distort it, so keep tags at the start of a line.

## Not done (time): ElevenLabs Eleven v4 for Amharic
- Suggested by Bilkis in user test 1 as better at Amharic than other models. Not tested before the
  deadline: it needs a new account, key and API host. The comparison would reuse `tts_compare.py`
  on the same three ejective lines (s01–s03), blind-rated by a native speaker as in E11.

## E15: Hitting −14 LUFS without peaks over −1 dB
- **Hypothesis:** single-pass `loudnorm=I=-14:TP=-1` is enough.
- **Result:** the final MP4 measured −14.3 LUFS but a **true peak of +0.2 dBFS**. Adding a limiter at
  −1.5 dB made the MP4 *worse* (+1.0 dBFS), even though the WAV mix measured −1.4 dBFS. The
  overshoot came from **AAC encoding**: encoding the same mix at −1.5 / −2.5 dB gain gave
  −2.5 / −3.0 dBFS in AAC.
- **Change:** `alimiter` at −3 dB after `loudnorm`, before AAC.
- **Result:** both exports measure **−14.5 LUFS, true peak −1.5 dBFS** (`ebur128=peak=true` on the MP4).
- **Decision:** keep. Measure the *encoded* file, not the mix, because the codec changes the peaks.

## E16: Smoother camera and softer cuts (from user test 2)
- **Hypothesis:** the "stiff / jerky" feel comes from constant-speed moves that start and stop
  abruptly, and from hard cuts.
- **Change:** (1) Ken Burns zoom and drift follow a cosine ease, `(1-cos(PI*p))/2`, instead of `p`.
  (2) The vertical two-character pan uses the same ease. (3) 0.4 s `xfade` crossfades between
  shots: each clip except the last runs 0.4 s longer and fades into the next *at the original cut
  time*.
- **Result:** the total stays exactly 70.7 s, so the narration sync is unchanged; a frame 0.2 s
  after the s01→s02 cut shows both shots blended. Loudness is unchanged (−14.5 LUFS, −1.5 dBTP).
- **Decision:** keep. A cut-preserving crossfade needed the timeline maths, but no timing change elsewhere.

## E17: s09, "make the turtle look extra happy when she wins" (a 9-year-old's request)
- **Attempt 1** ("beaming with joy … crossing the ribbon"): a mild smile, and the ribbon not visible.
- **Attempt 2** ("breaking through a red ribbon … across her chest, mouth open in a huge joyful
  smile, eyes closed with happiness"): **ribbon and joy right**, rabbit behind; but her white tibeb
  shawl is missing.
- **Attempt 3** (attempt 2 plus "her white shawl … clearly draped over her shell"): the tortoise
  disappeared; only the rabbit was left. The longer prompt diluted the main subject.
- **Decision:** the brief's "three attempts per shot, then take the best" rule. Attempt 2 restored
  **from the cache, with no API call**. Known small inconsistency: no shawl in s09. Practice note: the
  attempt limit beat my instinct to keep re-rolling until it was perfect.

## E18: Validators after every stage
- **Hypothesis:** checks after each stage stop bad outputs before the next stage uses them, and turn
  past failures into regression tests.
- **Change:** `pipeline/validators.py`, run by `make film` after each stage (and `make check` for all):
  storyboard (schema, length, subtitle size), narration (nested WAV, 24 kHz, length, not silent,
  ≤ 1.2 s/word, clean last 50 ms, transcription flags), keyframes (references present, 1024², not
  blank), shots (length matches the timeline, 1024², 24 fps), music (chosen, ≥ 30 s, sane loudness),
  assembly (resolution, audio, 60–90 s, −14 ±1 LUFS, true peak ≤ −1 dBFS, subtitle cues). Each run
  logs a `validate:<stage>` line.
- **Result:** 144/144 checks pass on the current film. **Regression test:** re-wrapping one narration
  file the old way (the F13 bug) in a scratch copy → `validate narration: 69/71`, the two F13 checks
  FAIL, exit code 1, and the pipeline stops.
- **Decision:** keep; every new failure should add a check.

## E19: Storyboard reflects what actually ran
- s02, s05, s06 and s09 were planned as Wan 2.2 shots. No GPU slot ever started (F9), so they always
  fell back to Ken Burns and logged a `fallback` line on every run. They are now `kenburns` in the
  storyboard, so the contract matches the film. `motion.mode = "wan"` is still supported: drop a
  clip from `kaggle/wan_shots.py` into `outputs/wan/` and set the mode back.
