# Ethics: consent, labelling, licences

## Consent
- **No real person appears or is voiced.** The characters are an illustrated rabbit and tortoise.
- The narrator is a **stock Gemini TTS voice** ("Kore"); no voice is cloned.
- The story is a fable told in my family, in public tradition (Aesop's "The Tortoise and the Hare"),
  retold in my own Amharic words.

## Labelling
- The film ends with a 4-second **"Made with AI"** end card that names each model.
- **Posted** as a YouTube Short (https://youtube.com/shorts/GlGOu8khYUc) with YouTube's "Altered or synthetic content" disclosure switched on.
- Model watermarks and metadata are left intact. No step strips SynthID or C2PA data. Each narration WAV keeps the **C2PA content-credentials chunk** Gemini embeds (FAILURES F13: it is stored, never played).

## Licences (every model, tool and output)

| Component | Model / tool licence | Its output in this film | Output terms |
|---|---|---|---|
| Gemini 3.8 Flash TTS (AI Studio, free tier) | Gemini API Additional Terms | 10 narration WAVs | Google claims no ownership of generated content; use is subject to the Gemini API terms and prohibited-use policy. Free-tier inputs may be used to improve Google products, so only the fable text was sent |
| Gemini 3 Flash (preview) | Gemini API Additional Terms | transcription check, script back-translation (text, not in the film) | same as above |
| FLUX.2 [klein] 4B via Cloudflare Workers AI | Apache 2.0 (the 9B is non-commercial, so not used) | 2 reference sheets, 10 keyframes | Apache 2.0 model; outputs usable, including commercially; Cloudflare's service terms apply |
| FLUX.1 [schnell] via Cloudflare | Apache 2.0 | smoke-test image only | as above |
| ACE-Step 1.5 (turbo) | MIT | the score (`score_chosen.wav`) | MIT; the project states outputs may be used commercially (trained on licensed, royalty-free and synthetic data) |
| Wan 2.2 TI2V-5B | Apache 2.0 | none (never ran, F15) | — |
| FFmpeg (gyan.dev full build on Windows; distro build on Linux) | GPL/LGPL | shots, mix, final MP4s | FFmpeg places no restriction on its outputs |
| DejaVu Sans font (bundled in `assets/fonts`) | Bitstream Vera licence | subtitles, end card | free to embed and redistribute |
| **This repository's code and the film** | mine | the film | released by me; credits on the end card |

## Private data
Only the fable text and image prompts are sent to hosted APIs. No names, photos or voices of
family members.

## Style
Prompts describe qualities ("hand-painted children's picture-book, gouache texture"), never a
living artist's name.
