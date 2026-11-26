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

The three testers are family friends: Amharic-speaking adults (they also work as developers). They
judge language and pacing well. **No child watched this round**, so user test 2 adds family members
and, where possible, a child, to check whether the lesson lands for the core audience.

| Who | What they said | Insight | What I changed |
|---|---|---|---|
| Yonas Tewabe (developer) | "The pace is mostly good. On some words it would use the wrong consonant that should be improved." | Confirms my own finding that the voice flattens ejectives (ጫ→ቻ, ጠ→ተ, ቅ→ክ, FAILURES F8). | Already switched to `gemini-3.8-flash-tts` after a native-speaker A/B (E11). I re-checked: ጫ / ጠ / ቅ are now correct. |
| Bilkis Elias (developer) | "Awo, a lot… yaw AI sihon sitebq enna silala manbeb betam aza nw miyaregew." (≈ "Yes, a lot… since it's AI, its reading of the ጠበቅ / ላላ [geminated vs. single] sounds makes it very dull.") Suggested writing the script with timed sections and delivery cues, like `[0:00 – Opening \| Calm, cinematic storytelling]`, and trying ElevenLabs for Amharic. | Amharic script doesn't mark gemination, so the TTS guesses; flat delivery makes it dull. Delivery cues per line might help. | Added a `delivery` field per shot in the storyboard: bracketed tags like `[proudly, with a playful smile]` and inline `[short pause]`. Tested first: the tags are **not** spoken, the pause is honoured, and the tone reads as "narrative and expressive" (EXPERIMENTS E14). ElevenLabs: see the ceiling notes. |
| Reman (developer) | "Clear and easy to follow … a natural-enough warm tone, though you can still tell it is TTS … the borrowed word ዲሲፕሊን rather than a purely idiomatic Amharic phrase." Pace "slightly slow … can feel a bit dragged out between beats." "Black screen for almost the entire ~71 seconds … attention easily drops." | The loan word sounds foreign in a children's story. The gaps between lines are too long. A radio cut on black is hard to watch for 70 s. | (1) Replaced **ዲሲፕሊን** with **ትጋት** in s06 and s10. (2) Tightened the timing in the storyboard: `lead_s` 0.4→0.3, `pad_after_s` 1.0→0.7, and shorter minimum lengths for s01, s05, s06, s09. (3) Pictures: the rough cut now has keyframes with movement on every shot. |

**Follow-up check (me, native speaker):** with the new delivery tags, s04 lost a syllable
(በመኩራራት → በመኩራት). I removed the tags from s04 only; the earlier, correct recording came
back from the cache with no API call.

**Storyboard diff from this test:** the commit "User test 1 → storyboard: delivery tags, ትጋት, tighter timing".

## User test 2: near-final cut (score A, pictures, all test-1 changes), 26 Nov
Shown on a phone (vertical cut) to three people from the audience: a friend, my sister and my
little brother. The questions: who watched, what happened, what is the lesson, was anything unclear
or confusing, and one thing to change. The answers below are as reported to me, summarised into
the five-question format.

| Who | Story / lesson in their words | Unclear or confusing | One change | What I changed |
|---|---|---|---|---|
| Yonas (friend, adult) | "Speed doesn't win on its own if you get careless; steady effort, patience, and focus get you across the line." | Narration "clear and easy to follow"; "camera pans feel a bit stiff/mechanical in a couple of spots." | "Smooth out the camera movement … transitions … a little less abrupt." | **Eased camera moves** (cosine ease-in-out instead of constant speed) in `shots.py`; **0.4 s crossfades** between shots in `assemble.py`, with the cut points unchanged so the narration stays in sync (E16). |
| Hana (sister, adult) | "Consistent effort, patience, and paying attention matter more than just being fast at the start." | Nothing confusing; "some shots are mostly slow pans over fairly still scenes." | "A tiny bit more lively character motion during the race and nap moments." | Partly: a faster, bigger move on s02 (the race start). **Not done:** real character animation needs Wan 2.2 on a GPU, and every Kaggle GPU job stayed queued (FAILURES F9). |
| Degem (little brother, about 9) | "The fast bunny ran ahead, fell asleep under a tree, and the slow turtle kept walking and won!" Lesson: "Don't sleep during a race and don't show off; keep going and you can win!" | Words easy; "when the camera slides sideways it looks a little funny/jerky." | "Make the bunny run a little faster at the start and make the turtle look extra happy when she wins!" | **s02:** zoom 1.0→1.25 with a pan right, so the start feels faster. **s09:** new keyframe, the tortoise **breaking the red ribbon with a huge joyful smile** (E17). Sideways pan in 9:16 is now eased. |

**Did the film meet its intent?** Yes. The 9-year-old, the core audience, stated the lesson
unprompted and in his own words ("don't show off; keep going and you can win"), and both adults
named steady effort over speed. No one found the Amharic unclear after the voice change (E11) and
the ትጋት rewording.

**What I'd still change with more time:** real character motion (Wan 2.2 on a free GPU), as Hana asked.
