# Design

## Audience
Children aged about 5–12 in Ethiopian families, watching on a parent's phone (vertical) or the
family TV or laptop (horizontal), usually with an adult nearby. They understand Amharic. Some
older siblings and parents read the English subtitles.

## Intent
At the end, a child should be able to say the lesson in their own words: being fast is not
enough; keeping going steadily (ዲሲፕሊን እና ትጋት) is what wins.

## Why this story
It is a story I heard as a child, and one parents use to teach patience. Retelling it in Amharic,
in an Ethiopian highland landscape (meskel daisies, acacia trees), and giving the characters a
woven tibeb shawl and a scarf in the flag colours makes a familiar fable feel like ours.

## Design choices
- **Two characters, one trail:** fewer characters means fewer consistency problems, and the race
  is easy for a child to follow.
- **A reason for every shot:** stored in `storyboard.json` (`reason`).
- **Ending on kindness:** the last shot shows the two sitting together, so the lesson is about
  effort, not about shaming the rabbit.
- **Narration sets the timing:** shots stretch to fit each spoken line.

## Language review (before any audio was generated)
- s05: "ላረፍ ብላ" corrected to "ልረፍ ብላ" (native-speaker read-through of all 10 lines).

## User test 1: radio cut (narration + temp music on a black screen), 26 Nov
Shared radio cut v3 (71.6 s) with 3 colleagues on Slack/chat, with these questions: was any Amharic
word unclear, mispronounced or robotic? Was the pace too fast, too slow or right? Did any part
confuse you or lose your attention, and what one thing would you change?

**Honest limitation:** all three are Amharic-speaking developers, not children or parents in the
audience. They're good judges of language and pacing, but not of whether a 7-year-old gets the
lesson. User test 2 therefore goes to parents and children in my family.

| Who | What they said | Insight | What I changed |
|---|---|---|---|
| Yonas Tewabe (developer) | "The pace is mostly good. On some words it would use the wrong consonant that should be improved." | Confirms my own finding that the voice flattens ejectives (ጫ→ቻ, ጠ→ተ, ቅ→ክ, FAILURES F8). | Already switched to `gemini-3.8-flash-tts` after a native-speaker A/B (E11). I re-checked: ጫ / ጠ / ቅ are now correct. |
| Bilkis Elias (developer) | "Awo, a lot… yaw AI sihon sitebq enna silala manbeb betam aza nw miyaregew." (≈ "Yes, a lot… since it's AI, its reading of the ጠበቅ / ላላ [geminated vs. single] sounds makes it very dull.") Suggested writing the script with timed sections and delivery cues, like `[0:00 – Opening \| Calm, cinematic storytelling]`, and trying ElevenLabs for Amharic. | Amharic script doesn't mark gemination, so the TTS guesses; flat delivery makes it dull. Delivery cues per line might help. | Added a `delivery` field per shot in the storyboard: bracketed tags like `[proudly, with a playful smile]` and inline `[short pause]`. Tested first: the tags are **not** spoken, the pause is honoured, and the tone reads as "narrative and expressive" (EXPERIMENTS E14). ElevenLabs: see the ceiling notes. |
| Reman (developer) | "Clear and easy to follow … a natural-enough warm tone, though you can still tell it is TTS … the borrowed word ዲሲፕሊን rather than a purely idiomatic Amharic phrase." Pace "slightly slow … can feel a bit dragged out between beats." "Black screen for almost the entire ~71 seconds … attention easily drops." | The loan word sounds foreign in a children's story. The gaps between lines are too long. A radio cut on black is hard to watch for 70 s. | (1) Replaced **ዲሲፕሊን** with **ትጋት** in s06 and s10. (2) Tightened the timing in the storyboard: `lead_s` 0.4→0.3, `pad_after_s` 1.0→0.7, and shorter minimum lengths for s01, s05, s06, s09. (3) Pictures: the rough cut now has keyframes with movement on every shot. |

**Storyboard diff from this test:** the commit "User test 1 → storyboard: delivery tags, ትጋት, tighter timing".

## User test 2: near-final cut
_To do._

| Who | What they said | What I changed |
|---|---|---|
| | | |
