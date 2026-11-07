# Voice vs. Text: What Does Voice Mode Actually Cost in Tokens?

A controlled test of a simple question nobody had published numbers for:
**when you talk to an AI instead of typing the exact same words, how many
more input tokens does the conversation use?**

Same script. Same words. Same order. One run spoken, one run typed, on two
different voice APIs — repeated three times each.

## Headline findings (n = 3 per condition)

| Platform (API model) | Voice, mean input tokens/turn | Text, mean input tokens/turn | Ratio of means | Per-pair ratios |
|---|---|---|---|---|
| OpenAI (`gpt-realtime`) | 949 | 614 | **1.545×** | 1.516 / 1.515 / 1.605 |
| Gemini (`gemini-3.1-flash-live-preview`) | 3,620 | 2,276 | **1.590×** | 1.570 / 1.729 / 1.483 |

- **Voice costs roughly 1.5× the input tokens of text** for the same words,
  on both platforms, across all six paired runs (every pair landed between
  1.48× and 1.73×).
- Session totals (13 turns), voice vs. text — OpenAI: 12,244 / 12,247 /
  12,511 vs. 8,075 / 8,086 / 7,796. Gemini: 41,059 / 50,870 / 49,251 vs.
  26,147 / 29,417 / 33,212.
- Most of the growth is **not** the audio itself. In both modes, on both
  platforms, each new turn re-sends the whole conversation history, so
  per-turn input climbs steadily from turn 1 to turn 13. Voice adds an
  audio premium on top of that climb.
- The platforms differ a lot in absolute numbers (Gemini's per-turn counts
  are roughly 3–4× OpenAI's) while landing on nearly the same ratio.
  OpenAI's prompt caching is a big part of its lower absolutes — about 39%
  of its voice-run input tokens were served from cache in run 1.
- Output tokens were nearly identical between voice and text. The voice
  premium is an input-side cost.
- Quirk worth knowing: even in the *text* runs, the model's spoken replies
  re-enter the session history as audio, so a text conversation inside a
  live voice session still accumulates audio tokens.

## Why this exists

Consumer voice products (apps, assistants) don't show token counts at all —
they show quota percentages or nothing. The labs publish per-minute or
per-token *prices*, but nobody had published a like-for-like, same-script,
voice-vs-text token measurement. This is that measurement, with everything
open so anyone can check it or re-run it.

## How the test works (short version)

1. A fixed 13-turn script: a setup turn ("Prompt Zero") that caps every
   reply at two sentences and forbids tools/web/follow-ups, then 12
   stand-alone questions with known answers.
2. The script is turned into audio **once** (synthetic speech, one voice),
   and that same audio is streamed to each voice API, turn by turn, inside
   one continuous session. Text runs send the identical strings as text
   into the same session type.
3. Every turn, the harness records the usage numbers the API itself
   reports (input/output tokens, split audio/text/cached where the API
   provides it), plus response latency, reply length, and reply audio
   duration.
4. Replies are scored against a fixed answer key (correctness), a
   two-sentence cap check, and a filler-phrase list. Rubrics were fixed
   before the runs.
5. Three full repeats per platform per mode. Nothing is averaged away —
   anomalies are flagged in the open, in [RESULTS.md](RESULTS.md).

Full detail: [METHOD.md](METHOD.md) — [ARCHITECTURE.md](ARCHITECTURE.md) —
[RESULTS.md](RESULTS.md) — raw run log: [results/RUNS.md](results/RUNS.md)

## Run it yourself

You need: an OpenAI API account and/or a Google AI Studio (Gemini) API key.
Neither requires a consumer subscription; both are pay-as-you-go. The full
set of runs in this repo cost about **$1.80 estimated on OpenAI** (out of a
$5 credit) and an unreported-but-tiny amount on Gemini (the Live API
returns no cost field).

```bash
pip install websockets piper-tts   # plus ffmpeg on your PATH
# put your keys where the runners can reach them — see "Credentials" below
python code/gen_audio.py            # only if audio/ is missing
python code/openai_runner.py --mode voice --turns 13 --tag full1
python code/openai_runner.py --mode text  --turns 13 --tag full1
python code/gemini_runner.py --mode voice --turns 13 --tag full1
python code/gemini_runner.py --mode text  --turns 13 --tag full1
python code/rollup.py               # -> results/turns.csv, results/sessions.csv
python code/aggregates.py           # -> results/aggregates.csv (n=3 stats)
```

### Credentials

This repo contains **no API keys**, and the code as run never stored one:
the operator's keys stayed in a separate credential vault, and the runners
fetched a short-lived surrogate value per connection that the network layer
swapped for the real key (see [ARCHITECTURE.md](ARCHITECTURE.md) and
[SECURITY.md](SECURITY.md)). To re-run standalone, replace the
`get_surrogate()` call in `code/common.py` with your own key lookup
(e.g. an environment variable) — that one function is the only credential
touch-point.

## Repo map

| File | What it is |
|---|---|
| `METHOD.md` | The full protocol: script verbatim, session settings, definitions, scoring rubrics |
| `ARCHITECTURE.md` | How the harness is built, with a diagram |
| `RESULTS.md` | n=3 tables, quality/latency summaries, spend, limitations & anomalies |
| `code/` | The harness exactly as run (runners, audio generation, rollup, aggregates, scoring) |
| `audio/` | The WAV audio masters (one per turn), the manifest with durations, and the per-platform PCM conversions |
| `results/` | Every per-run JSON, run logs, CSVs, and the original `RUNS.md` log — unedited |
| `SECURITY.md` | Credential design and the pre-publication scrub that was run on this repo |

## Limitations, up front

One script, one synthetic voice (not a human), one session shape, one
machine and connection. The Gemini model is a preview build and its
behavior varied noticeably between repeats in ways OpenAI's did not.
The full, unflattering list is in [RESULTS.md](RESULTS.md#limitations-and-anomalies).

## License

MIT — see [LICENSE](LICENSE). Author: Erik Hurley, 2026.
