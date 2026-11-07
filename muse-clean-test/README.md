# Addendum: the Muse clean test (Nov 6, 2026)

The main test in this repo covers the two platforms that expose a realtime voice
API (OpenAI, Gemini). Muse — the product where the original observation was
made — has no realtime voice API, so it could only be tested inside its own app,
with its per-turn usage logs as the source. This addendum records what happened
when we tried. It is an addendum rather than a results section because the
outcome is not a ratio: **Muse's voice-mode usage is not recorded anywhere a
user can reach, so no clean Muse voice-vs-text ratio exists.**

## Text leg (measured, complete)

The identical 13-turn script from the main test was sent as text into a fresh
Muse chat. Every turn is logged. Source: the product's per-message usage
records for that chat.

- Total input: **1,157,335 tokens** over 13 turns (mean 89,026/turn)
- Total output: **4,041 tokens**
- Turn 1 carries first-message overhead (153,901 in); turns 2–13 climb slowly
  from 80,452 to 86,379 as history accumulates.
- Per-turn data: `text-leg-turns.csv`

Note the scale: a Muse chat carries the product's full standing context
(system prompt, memory, configuration) on every turn, so per-turn inputs are
~100x the bare-API runs. That is the harness, and it applies to both modes —
which is exactly why a within-product ratio was the thing worth measuring.

## Voice leg (run clean; usage never recorded)

The identical script was then read aloud in a live Muse voice call in a fresh
chat. The call completed all 13 turns, stayed within the script's two-sentence
cap, and answered the checkable questions correctly (60 mph; Sunday; heart
chambers). Then the logs were pulled:

- **Zero usage records exist for the call's turns** — under the chat, under its
  session and agent identifiers, under every message ID in every format, and in
  every usage store in the product's local database. The database schema was
  swept; there is no voice-usage table.
- A live voice call runs through a native speech-to-speech pipeline that writes
  transcript records only. Its model usage is billed somewhere server-side and
  never itemized on the user side. (Consistent with the original Nov 5
  observation: the subscription meter moved ~1 percentage point across an
  evening of voice use, with no per-turn accounting anywhere.)

## Replication attempt: text-first entry

Hypothesis: if a chat starts as text (logging pipeline) and then switches to
voice, the voice turns might execute — and log — through the same pipeline.

- Fresh chat, primed with one text turn: logged normally (149,844 input).
- Voice call then placed inside that same chat, 2 script questions: answered
  correctly.
- Result: the call still ran through the speech-to-speech pipeline. **Zero
  usage records** for the voice turns. Entry point does not change the routing.

## How the original Nov 5 numbers existed at all

The Nov 5 session that produced the original "3.2x" figures turns out to have
run through a different pipeline: the regular agent runtime, where the voice
conversation's turns (including delegated tool work) executed as ordinary agent
turns and were logged like text. Its execution agent's logged turns were
recovered on Nov 6:

- The first 14 logged turns sum to **exactly 12,577,757 input / 20,265 output
  tokens** — the originally published figures, to the token.
  Per-turn data: `nov-5-session-turns.csv`
- All 24 logged turns through that session's end sum to 18,121,255 / 28,167;
  the original measurement covered the first 14.
- One single turn (turn 13) billed 4,088,463 input tokens — delegated agent
  work, not a spoken answer. This is part of why the uncontrolled session's
  ratio (3.16x vs a text replay of the question turns: 6,823,804 input over
  24 messages, independently re-verified from the same logs) is so much larger
  than the controlled ~1.5x voice premium.
- That agent-runtime voice routing no longer handles voice calls (see the two
  attempts above), so this measurement path is not repeatable.

## Conclusion

- APIs (this repo's main test): voice ≈ **1.5x** text on input tokens, both
  platforms, fully logged and reproducible.
- Muse voice mode: **not measurable from the product.** No voice API to test,
  and the app's own usage logs contain no record of voice-call turns — three
  separate attempts confirmed the absence.
- The only Muse voice numbers that exist (Nov 5) came from a retired routing
  path and measured voice + full agent context + delegated work, which is a
  different quantity from the API premium.
