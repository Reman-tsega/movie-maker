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
