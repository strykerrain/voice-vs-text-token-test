# METHOD — the full protocol

Everything needed to judge or replicate the test. All runs: **November 6,
2026 (UTC)**, from one machine on one connection. Times below are UTC as
recorded by the harness.

## The script

Thirteen turns. Turn 1 is "Prompt Zero," sent identically in every run on
every platform, in both modes (pasted as text, or spoken as the same words
via the generated audio).

### Prompt Zero (turn 1, verbatim)

> This is a controlled test. Rules for the whole conversation: answer every message in two sentences or fewer. Do not use web search or any tools. Do not ask me follow-up questions. Do not offer to do anything else. Just answer what I asked. Confirm you understand in one short sentence.

Why it exists: without a length cap, one assistant writes essays and the
next writes a paragraph, and every later turn inherits that difference.
The cap makes reply length a *measured behavior* instead of a free
variable.

### Turns 2–13 (verbatim)

2. What is the difference between a virus and a bacterium, in plain language?
3. Give me a simple way to remember the order of the planets from the sun outward.
4. If a car travels 180 miles in 3 hours, what is its average speed, and how do you get that number?
5. Summarize the plot of Romeo and Juliet, focusing on why the ending happens.
6. What are three common reasons a houseplant's leaves turn yellow?
7. Explain what compound interest is, using a $100 example.
8. Translate "Where is the nearest train station?" into French, German, and Spanish.
9. What is the boiling point of water at sea level in Fahrenheit and Celsius, and why does it change on a mountain?
10. Give me a two-line poem about autumn rain.
11. If today is Friday, what day of the week will it be 100 days from now? Show your working briefly.
12. What is the difference between a simile and a metaphor, with one example of each?
13. Name the four chambers of the human heart and what each side of the heart does.

Design rules: no current events (nothing can trigger a search), no personal
data (nothing pulls in account context), answers are stable across
platforms, and **no turn depends on the previous answer** — so if a model
answers oddly, the next prompt still makes sense and the runs cannot
diverge in what they ask.

Note: the audio for turn 8 was synthesized from a single-quoted version
of the sentence (`Translate 'Where is the nearest train station?' …`) —
the text in `audio/manifest.json` is the exact string that was spoken and
sent. The wording is otherwise identical.

## Audio generation

- Engine: **Piper TTS, voice `en_US-lessac-medium`** (local ONNX model,
  run fully offline). An earlier attempt with a cloud TTS returned empty
  audio through the test machine's network proxy and was abandoned;
  this is recorded in `results/RUNS.md`.
- The 13 turns were generated **once**, into WAV masters (`audio/turn01.wav`
  … `turn13.wav`, mono). They were never regenerated per platform or
  per run — every voice run on every platform heard the identical files.
- `audio/manifest.json` lists each turn's exact text, duration, and word
  count. Total spoken prompt audio per voice run: **70.217 seconds**
  (turn 1 is 16.8s of that — Prompt Zero is long).
- Per-platform conversions (ffmpeg, from the masters):
  - OpenAI: `audio/pcm24/` — raw PCM, 24 kHz, 16-bit mono.
  - Gemini: `audio/pcm16/` — raw PCM, 16 kHz, 16-bit mono.
- The 63 MB Piper voice model itself is **not** in this repo (it is a
  third-party downloadable artifact); its config JSON is in
  `audio/voices/` for identification, and `code/gen_audio.py` regenerates
  the masters if the model is present.

## Session configuration

Every run is **one continuous session** per platform/mode — the same
conversation shape as a real voice call. No fresh context between turns;
history accumulates (and is re-billed) exactly as the API does it.

### OpenAI — `gpt-realtime` (Realtime API, websocket)

- Endpoint: `wss://api.openai.com/v1/realtime?model=gpt-realtime`
- **Server VAD / turn detection: OFF** (`turn_detection: null`). The runner
  appends the turn's audio, then commits the buffer manually, so turn
  boundaries are exact and timing is measurable. A 300 ms tail of silence
  is appended per turn.
- Input/output audio format: PCM 24 kHz. Output voice: `alloy`.
  Input transcription (for the reply/prompt record): `gpt-4o-mini-transcribe`.
- Text runs: the identical strings are sent as text items into the same
  session type and model. The model still replies in audio (that's the
  session's nature) — see the audio-history quirk in RESULTS.md.
- Auth: credential in the websocket `Authorization` header (see
  ARCHITECTURE.md for how the key itself was handled).

### Gemini — `gemini-3.1-flash-live-preview` (Live API, BidiGenerateContent websocket)

- Endpoint: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
- **Automatic activity detection: DISABLED** in the session setup.
  The runner sends explicit activity start/end around each turn's audio,
  so turn boundaries are exact. Audio is streamed in realtime-paced
  100 ms chunks of PCM 16 kHz.
- Response modality: AUDIO. Output voice: prebuilt voice `Kore`
  (Live audio output is 24 kHz). Input and output audio transcription
  enabled, which is where reply transcripts come from.
- The runner held a fallback chain (`gemini-3.1-flash-live-preview`, then
  `gemini-2.5-flash-native-audio-latest`, then `gemini-3.8-live`); the
  first model connected and was used for **every** Gemini run.
- Auth: credential in the `x-goog-api-key` websocket header.
- Text runs: the identical strings sent as text turns in the same Live
  session configuration.

## Definitions

- **A turn** = one script prompt (audio or text) plus the model's complete
  reply to it, inside the continuous session. A run = 13 turns.
- **Input tokens** = the per-turn usage figure the API itself reports for
  that turn (OpenAI: `response.done` usage; Gemini: the turn's
  `usageMetadata`). Splits (audio / text / cached) are recorded where the
  API provides them. All figures in `results/` are as reported — not
  recomputed, not normalized.
- **Time to first response** = from the moment the prompt finishes sending
  (audio fully streamed / text sent) to the first reply audio or token
  arriving.
- **Time to complete** = from prompt-finish to the reply fully arrived.
- Latency is measured from one machine on one connection, identical for
  every platform, so cross-platform comparisons are fair. Absolute numbers
  include network time and are not a lab benchmark.

## Runs executed

Smoke tests first (2 turns, tags `smoke` / `smoke2`), then full 13-turn
runs. The full runs used for the n=3 statistics:

| Run | UTC window (2026) |
|---|---|
| Gemini voice full1 | Nov 6, 22:29:53 → 22:34:44 |
| Gemini text full1 | Nov 6, 22:34:49 → 22:36:40 |
| OpenAI voice full1 | Nov 7, 01:10:26 → 01:10:54 |
| OpenAI text full1 | Nov 7, 01:10:57 → 01:11:23 |
| OpenAI voice full2 | Nov 7, 01:21:35 → 01:22:03 |
| Gemini text full2 | Nov 7, 01:22:04 → 01:24:07 |
| OpenAI text full2 | Nov 7, 01:24:08 → 01:24:34 |
| Gemini voice full2 | Nov 7, 01:24:35 → 01:28:39 |
| Gemini voice full3 | Nov 7, 01:28:40 → 01:34:19 |
| OpenAI text full3 | Nov 7, 01:34:21 → 01:34:45 |
| Gemini text full3 | Nov 7, 01:34:46 → 01:37:06 |
| OpenAI voice full3 | Nov 7, 01:37:07 → 01:37:35 |

full1 runs were done as platform pairs (Gemini pair first, then OpenAI
after its account credit landed — see the blocker note in
`results/RUNS.md`). The repeats (full2/full3) were run **interleaved
across platforms and modes** in exactly the order listed above, so
time-of-day can't cluster on one condition.

Also in `results/` for completeness: the two 2-turn smoke runs per
platform, and `openai_blocked.json` — the record of OpenAI refusing the
first smoke attempts because the account had zero API credit (resolved
the same day with a $5 top-up).

## Scoring (rubrics fixed before the runs)

Implemented in `code/rollup.py` and `code/aggregates.py`, deterministic —
no model judging.

### Correctness — keyword answer key, 6 checkable turns

Checked turns: 4, 7, 8, 9, 11, 13. A turn is **correct** if every required
keyword group is present *and* at least one supporting term is present;
**partly** if the groups pass without support; **wrong** otherwise. The
remaining turns are gist/form questions and are not auto-scored.

| Turn | Required (all groups) | Supporting (any) | The actual answer |
|---|---|---|---|
| 4 — average speed | "60" | divid / 180 / per hour / mph | 180 ÷ 3 = 60 mph |
| 7 — compound interest | interest on / earn interest / compounding / compounds | $100 / 100 | interest earns interest on itself |
| 8 — translations | gare; bahnhof | estación / où / dónde … | FR gare, DE Bahnhof, ES estación |
| 9 — boiling point | 212; 100 | pressure / altitude / lower | 212°F / 100°C; lower at altitude, less pressure |
| 11 — 100 days from Friday | sunday | remainder / mod / 100 | 100 mod 7 = 2 → Sunday |
| 13 — heart chambers | atrium; ventricle | lung / body | atria + ventricles; right side → lungs, left → body |

The keyword checks were spot-verified by eye against the transcripts
during the runs.

### Cap compliance

Percentage of replies at **≤ 2 sentences** (Prompt Zero's cap). Sentences
are counted by terminator splitting (minimum 1 for a non-empty reply) —
see `count_sentences()` in `code/common.py`.

### Filler hits

Case-insensitive count of fixed phrases in each reply transcript:
"great question", "as an ai", "let me know if", "feel free",
"happy to help", "hope this helps", "certainly!", "of course!",
"anything else", "glad you asked".

### Not scored

The metrics design also called for a blind 1–5 human directness score.
**It was not done** — no human scored it, and no score is claimed anywhere
in the results.
