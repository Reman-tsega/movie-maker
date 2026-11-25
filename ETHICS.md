# Ethics: consent, labelling, licences

## Consent
- **No real person appears or is voiced.** The characters are an illustrated rabbit and tortoise.
- The narrator is a **stock Gemini TTS voice** ("Kore"); no voice is cloned.
- The story is a fable told in my family, in public tradition (Aesop's "The Tortoise and the Hare"),
  retold in my own Amharic words.

## Labelling
- The film ends with a 4-second **"Made with AI"** end card that names each model.
- The platform's AI-content disclosure will be switched on when the film is posted.
- Model watermarks and metadata are left intact. No step strips SynthID or C2PA data.

## Licences

| Component | Licence / terms | Use here |
|---|---|---|
| Gemini TTS (Google AI Studio free tier) | Gemini API Terms; free-tier inputs may be used to improve Google products | Narration; only the story text is sent, no private family data |
| FLUX.2 [klein] 4B (Black Forest Labs) via Cloudflare Workers AI | Apache 2.0 (the 9B is non-commercial, so not used) | Keyframes and reference sheets |
| FLUX.1 [schnell] via Cloudflare Workers AI | Apache 2.0 | Smoke test only (see EXPERIMENTS E3) |
| Wan 2.2 TI2V-5B | Apache 2.0 | Moving shots |
| ACE-Step 1.5 | MIT; outputs usable commercially | Score |
| FFmpeg | LGPL/GPL | Assembly (a tool, not shipped) |
| DejaVu Sans font | Bitstream Vera licence (free) | Subtitles, end card |

## Private data
Only the fable text and image prompts are sent to hosted APIs. No names, photos or voices of
family members.

## Style
Prompts describe qualities ("hand-painted children's picture-book, gouache texture"), never a
living artist's name.
