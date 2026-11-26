# Final Project Report: The Rabbit and the Tortoise (የጥንቸል እና የኤሊ ሩጫ)

**Challenge:** AI-Content Generation (B2W0)
**Author / Director:** Haylemichael Tsega
**Date:** 26 November 2026
**Repository:** https://github.com/Reman-tsega/movie-maker

**Primary deliverables** (rebuilt by the pipeline; the `<hash>` changes when an input changes):
- **Vertical master (9:16):** `outputs/final/heritage_9x16_<hash>.mp4`, 720×1280, 69.6 s, −14.5 LUFS / −1.5 dBTP
- **Horizontal master (16:9):** `outputs/final/heritage_16x9_<hash>.mp4`, 1280×720, 69.6 s, −14.5 LUFS / −1.5 dBTP
- **Subtitles:** `outputs/final/subtitles_en.srt`
- **Public post (primary):** https://lnkd.in/p/eQFqueZX (LinkedIn) · also on YouTube Shorts: https://youtube.com/shorts/GlGOu8khYUc (AI label on) ·
  **Film files:** https://drive.google.com/drive/folders/1m1z7Ug0wlr6v-WjR0Pk4qgK7SySBNioZ

**What the pipeline does:** `storyboard.json` (validated by a JSON Schema) → **script** (screenplay +
back-translation check) → **narration** (Gemini 3.8 Flash TTS) → **keyframes** (FLUX.2 klein 4B on
Cloudflare, from character reference sheets) → **shots** (eased FFmpeg camera moves) → **music**
(chosen ACE-Step 1.5 track) → **assembly** (FFmpeg: crossfades, ducking, subtitles, −14 LUFS, AI end
card, 9:16 + 16:9). Each stage is cached by a hash of its inputs, retried on transient errors,
validated afterwards, and every call is logged in `runs.jsonl` with model, parameters, seed,
latency and list-price cost. **What it costs:** under $0.15 at list price; $0 on the free tiers used.

**Single reproduction entry point:** `make film`, or on any OS (Windows too) `python pipeline/film.py`

---

## 0. How to run it (from a clean clone)

```bash
git clone https://github.com/Reman-tsega/movie-maker.git && cd movie-maker
pip install -r requirements.txt            # Python 3.10+; FFmpeg must be on PATH
cp .env.example .env                       # GEMINI_API_KEY, GEMINI_API_KEY_2, CF_ACCOUNT_ID, CF_API_TOKEN
make film                                  # or: python pipeline/film.py
```

Windows: `winget install Gyan.FFmpeg`, then `copy .env.example .env` and `python pipeline/film.py`.

- Each stage is followed by its **validator**; a FAIL stops the run. `make check` re-runs all
  144 checks.
- **Tested from a clean clone:** both versions were rebuilt in **58 s with 0 image or voice calls**.
  The committed narration, keyframes and chosen score are cache hits, and only FFmpeg runs.
- **Change one shot:** edit its `narration`, `image_prompt` or `motion` in `storyboard.json` and run
  again. `python pipeline/last_run.py` lists what was regenerated (only that shot) and the cache hits.
- If the first Gemini key's daily TTS quota runs out, the run **asks** before using
  `GEMINI_API_KEY_2` (non-interactive: `MM_FALLBACK_KEY=yes|no`).
- GPU stages (ACE-Step score, optional Wan 2.2 motion) run on Kaggle through `kaggle/push_job.sh`;
  see `kaggle/README.md`.
- Other targets: `make smoke` (one call per provider), `make radio` (narration on black, for user
  testing), `make refs` (reference sheets only).

| Document | Contents |
|---|---|
| [DESIGN.md](DESIGN.md) | audience, intent, both user tests and what changed |
| [ARCHITECTURE.md](ARCHITECTURE.md) | stages, contract, caching, validators, failure handling |
| [EXPERIMENTS.md](EXPERIMENTS.md) | 19 hypothesis → change → result entries |
| [FAILURES.md](FAILURES.md) | 13 real blockers and how each was solved |
| [COSTS.md](COSTS.md) | measured latency, quotas found, list-price equivalent |
| [ETHICS.md](ETHICS.md) | consent, licences, labelling, provenance |

---

## 1. Project overview: what I set out to make and for whom

### 1.1 The story and intention
*The Rabbit and the Tortoise* is a 70-second fable, narrated in **Amharic**, retold for children in
Ethiopian families. A proud, fast rabbit naps in the middle of a race while a steady tortoise keeps
walking and wins. It is a story parents use to teach patience. To make it feel like ours, it is set in
the Ethiopian highlands (acacia trees, meskel daisies); the rabbit wears a green, yellow and red scarf,
and the tortoise wears a white shawl with a **tibeb** border.

**Central message:** being fast is not enough; steady effort (**ትጋት**), patience and focus win.

### 1.2 Target audience
Written in `DESIGN.md` before anything was generated:
- **Children aged 5–12 in Ethiopian families** who understand Amharic, watching on a parent's phone
  (vertical), usually with an adult nearby.
- **Parents and older siblings**, who use the fable to teach patience; some read the English subtitles.

**Success criterion:** at the end, a child can say the lesson in their own words.

### 1.3 Creative and ethical boundaries
- **No real person is shown or voiced.** The characters are an illustrated rabbit and tortoise, and the
  narrator is a stock Gemini TTS voice ("Kore"); no voice cloning.
- **Transparency:** a 4-second **"Made with AI"** end card credits FLUX.2 klein, Gemini 3.8 TTS,
  ACE-Step 1.5 and FFmpeg; the YouTube AI label is on. The **C2PA** content credentials that Gemini
  embeds in each narration file are kept intact (`ETHICS.md`, FAILURES F13).
- Prompts describe qualities ("hand-painted gouache picture-book"), never a living artist's name.

## 2. Learning from the audience: user tests 1 and 2

### 2.1 Test 1: the radio cut
- **Artifact:** radio cut v3, 71.6 s: Amharic narration and a temporary music pad on a black screen,
  with English subtitles.
- **Participants:** three Amharic-speaking adults (family friends): Yonas, Bilkis, Reman.
- **What they said, and what changed:**
  - *Yonas:* "on some words it would use the wrong consonant." This confirmed what I had heard: the
    voice flattened the **ejectives** (ጫ→ቻ, ጠ→ተ, ቅ→ክ). A blind A/B of three TTS models led to
    **Gemini 3.8 Flash TTS** (E11).
  - *Bilkis:* the reading of **ጠበቅ / ላላ** (geminated versus single consonants) "makes it very dull";
    use delivery cues. I added a per-shot `delivery` field (`[proudly, with a playful smile]`), first
    tested on one line to confirm the tags are not spoken (E14).
  - *Reman:* the loanword **ዲሲፕሊን** sounds foreign, the pauses drag, and a black screen loses
    attention. ዲሲፕሊን became **ትጋት**, `timing` in the storyboard was tightened (lead 0.4→0.3 s, hold
    1.0→0.7 s), and pictures were added.

### 2.2 Test 2: the near-final cut
- **Artifact:** the near-final 9:16 cut, 70.7 s, with score, pictures and all test-1 changes, watched on a phone.
- **Participants:** Yonas (friend, adult), Hana (sister, adult), **Degem (brother, about 9)**.
- **What they said, and what changed:**
  - *Yonas:* pans "stiff / mechanical," cuts "abrupt" → **cosine-eased camera moves** and **0.4 s
    crossfades**, with the cut points unchanged so the narration stays in sync (E16).
  - *Degem:* "make the bunny run a little faster at the start and make the turtle look extra happy when
    she wins!" → a faster move on s02, and a **new s09: the tortoise breaking the red ribbon with a huge
    smile** (E17). His "jerky" sideways pan is now eased.
  - *Hana:* "mostly slow pans over fairly still scenes"; wanted livelier characters → **only partly
    met**. Real character animation needs Wan 2.2 on a GPU, and no slot opened (F9).
- **Result against intent:** Degem said, unprompted, *"Don't sleep during a race and don't show off.
  Keep going and you can win!"* The film's goal was met by its core audience.

## 3. The hardest technical problem and how I solved it

### 3.1 The problem: making an AI voice speak Amharic correctly
The narration failed in four ways, one after another:
1. **The instruction was spoken (F4, E7).** 90 Amharic words produced **173 s** of audio: Gemini TTS
   read my English style prompt aloud before every line. A transcription by a second model proved it.
2. **Ejectives were flattened (F8, E11).** ጫ / ጠ / ቅ came out as plain consonants, and Ge'ez spelling
   can't force them. My automatic transcription check **missed it**; my own ear caught it.
3. **Ten requests a day (F3).** The free tier allowed about 10 TTS requests per model per day per
   project (HTTP 429 `PerDay`).
4. **Noise at every scene change (F13).** Each line started at the same sample value (the bytes "RI")
   and ended in a −4 dB burst.

### 3.2 The solution, in `pipeline/narration.py` and `pipeline/validators.py`
- **Text only, with tags:** only the Amharic is sent, plus short bracketed delivery tags at the start
  of a line (not spoken; E14). 173 s → **57 s**.
- **Model choice by native ear:** the same three lines were recorded on three models (`tts_compare.py`)
  and Gemini 3.8 was chosen.
- **Quota discipline:** a daily-quota 429 fails fast (no wasted retries); fallbacks run same model on
  key 2 (after asking) → next model; every line is cached by a hash of what is sent; a retake happens
  only after a native-speaker review.
- **The noise:** Gemini 3.8 returns a **complete WAV with a C2PA chunk**, and I had wrapped it in a
  second header, so the inner header played as a click and the C2PA data as noise. `save_audio()` now
  stores the WAV as returned (**provenance intact, never played**); `unwrap_if_nested()` repaired all
  10 lines **from the cache with 0 API calls**; an **audio tuner** (`audio_tuning`: 70 Hz high-pass,
  10 ms fade-in, 60 ms fade-out) runs on every line; and two validator checks fail the build if it
  returns. Line endings went from −4 dB to −70 to −90 dB.

## 4. Suggested practices, tested honestly

### 4.1 Beat my instinct: the radio cut before pictures
- **Instinct:** start with images, the exciting part.
- **Practice:** narration first, as a radio cut, tested before the picture.
- **Evidence:** the radio cut exposed the 173 s narration bug before any shot length depended on it,
  and test 1 reshaped the script (ትጋት, delivery tags, timing) while that was cheap. *Caveat:*
  because of the deadline the keyframes were generated before test 1's answers came back; a keyframe
  costs about 10 s to redo, so the risk was small. *Also helped:* the **three-attempts-per-shot**
  limit. s09's third attempt lost the tortoise, so attempt two was restored from the cache (E17).

### 4.2 Did not hold: "a short style instruction improves a voice more than switching voices"
- **Evidence:** for Amharic both halves were reversed. The instruction was **spoken aloud** (E7; even
  "Say warmly…:" leaked English), and **switching the voice model** fixed the ejectives (E11). What
  worked was narrower: bracketed tags at the start of a line (E14). A tag *inside* a sentence
  (`[short pause]` in s04) swallowed a syllable, so that line went back to its untagged take.

### 4.3 Partial fit: a reference sheet before keyframes
- Identity held (face, fur, scarf), but a **multi-pose** sheet leaked into the shots: 4 of 10 frames
  showed two or three rabbits. Single-pose references plus "exactly one rabbit" fixed it (E5).

## 5. Curiosity beyond the floor (ceiling work)

### 5.1 A small Amharic TTS study
Ejectives compared blind across three Gemini TTS models (E11); gemination flagged by a native listener;
evidence that an LLM transcription check (`narration_check.py`) catches gross errors (spoken English,
E9) but **misses pronunciation**.

### 5.2 Validators as regression gates
`pipeline/validators.py` runs 144 checks after the stages (resolution, length, loudness, true peak,
nested WAV, line-edge noise, speaking rate…). Re-creating the F13 bug in a copy makes the narration
validator fail with **exit code 1** (E18).

### 5.3 Measured audio mastering
Narration lines are tuned, the score is ducked with `sidechaincompress` (threshold 0.02, ratio 6,
attack 300 ms, release 1500 ms) and normalised with `loudnorm`. Measuring the **encoded MP4**, not the
mix, showed the **AAC encoder** adding up to +2.4 dB of overshoot (the MP4 at +1.0 dBFS while the mix
was −1.4); a −3 dB limiter before encoding gives **−14.5 LUFS / −1.5 dBTP** (E15).

### 5.4 Working around the GPU queue
A Kaggle GPU job sat queued for **14+ hours** (F9). The same ACE-Step job on **Kaggle CPU** started in
under a minute, after I fixed Python 3.13 (with `uv` and 3.12), the retired `huggingface-cli` (now
`hf`), and ACE-Step's 600 s timeout (F10, F11). Three 70 s candidates took about 11.5 min each. The
caption's **krar and masenqo** came back as keyboard and percussion: a cultural gap in the model (E13).

### 5.5 Dual format and smooth motion from one contract
Square 1024² keyframes with centred subjects are cropped to both formats; in 9:16, shots with two
characters get an **eased left-to-right pan** so both appear (E12); crossfades keep the cut points
exact (E16).

## 6. What I would build next
1. **Real character motion:** run `kaggle/wan_shots.py` (Wan 2.2 TI2V-5B, ready but never given a GPU)
   for the race and nap shots, Hana's unmet request.
2. **An Amharic pronunciation benchmark:** 30 lines rich in ejectives and gemination, rated blind by 5
   native speakers, comparing Gemini TTS with **ElevenLabs v4** (Bilkis's suggestion).
3. **A family story tool:** a web app where a relative types or says a story in Amharic and gets a
   storyboard and film back.
4. **More languages:** Afaan Oromo and Tigrinya, logging where each model fails.

## 7. Project metrics and cost summary
Measured from `runs.jsonl` by `python pipeline/costs.py`; details in `COSTS.md`.

| Stage | Model / tool | Mean latency | Calls (cache hits) | Free-tier limit found | List-price equivalent |
|---|---|---|---|---|---|
| Narration | Gemini 3.8 Flash TTS | 5.5 s / line | 28 (127) | ~10 requests / model / day / project | ≈ $0.08 for all takes ($9 / 1M audio tokens) |
| Narration check | Gemini 3 Flash | 15.3 s / batch | 10 | — | ≈ $0 |
| Reference sheets + keyframes | FLUX.2 klein 4B, Cloudflare | 9.3 s / image | 29 (57) | 10k neurons/day ≈ 90 images | ≈ $0.03 ($0.011 / 1k neurons) |
| Shots | FFmpeg zoompan (eased) | 1.3 s / shot | 61 (49) | local CPU | $0 |
| Score | ACE-Step 1.5 turbo | ≈ 11.5 min / 70 s track | 3 | Kaggle GPU queue 14+ h → CPU | $0 |
| Assembly (both formats) | FFmpeg | ≈ 25 s / export | 35 | local CPU | $0 |
| Validators | `validators.py` | < 6 s / stage | every run | — | $0 |
| **Total** | | **58 s rebuild from a clean clone** | | | **< $0.15 (all free tiers)** |

Logs: 19 experiments, 13 failures, 539+ `runs.jsonl` lines, 273+ cache hits, 144 validator checks.

## 8. Conclusion
A familiar fable, retold in Amharic for the children it was always meant for, made by one storyboard
and five logged, cached, validated stages. The engineering made it reproducible; the audience made it
right. A 9-year-old said the lesson back in his own words, and a native ear caught the consonants
that no automated check heard.

---

**Tools and roles.** Coding agent: **Claude Code** wrote most of the pipeline code under my direction.
I chose the story, audience and stages, ran both user tests, judged every voice, picture and score by
ear and eye, and reviewed every script. Models: Gemini 3.8 Flash TTS, Gemini 3 Flash, FLUX.2 klein 4B
(Cloudflare Workers AI), ACE-Step 1.5 (Kaggle). Assembly: FFmpeg.
