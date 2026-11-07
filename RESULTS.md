# RESULTS — n = 3, November 6, 2026

All figures are the APIs' own reported usage, recorded per turn and
summed by the harness. Machine-readable sources: `results/aggregates.csv`,
`results/sessions.csv`, `results/turns.csv`, and one JSON per run in
`results/`. The narrative run log (kept unedited) is `results/RUNS.md`.

## Session totals — input tokens (13 turns per run)

| Platform | Mode | full1 | full2 | full3 | Mean | SD | Mean per turn |
|---|---|---|---|---|---|---|---|
| OpenAI `gpt-realtime` | voice | 12,244 | 12,247 | 12,511 | 12,334 | 153 | 949 |
| OpenAI `gpt-realtime` | text | 8,075 | 8,086 | 7,796 | 7,986 | 164 | 614 |
| Gemini `gemini-3.1-flash-live-preview` | voice | 41,059 | 50,870 | 49,251 | 47,060 | 5,260 | 3,620 |
| Gemini `gemini-3.1-flash-live-preview` | text | 26,147 | 29,417 | 33,212 | 29,592 | 3,536 | 2,276 |

## The ratio (voice ÷ text, input tokens)

| Platform | full1 pair | full2 pair | full3 pair | Ratio of means |
|---|---|---|---|---|
| OpenAI | 1.516 | 1.515 | 1.605 | **1.545** |
| Gemini | 1.570 | 1.729 | 1.483 | **1.590** |

All six paired ratios fall between 1.48 and 1.73. The voice premium is
~1.5× on both platforms — but repeatability is not equal: OpenAI's run
totals vary by ~1–2% (SD), Gemini's by ~11–12%, and Gemini's spread is
mostly its own reply-length behavior (see Limitations).

Output tokens (mean per run): OpenAI voice 2,641 / text 2,552 —
Gemini voice 3,535 / text 2,843. Output is roughly mode-independent;
the voice premium is an input-side cost.

Per-turn growth, run 1 (input tokens, turn 1 → turn 13): OpenAI voice
290 → 1,517, text 175 → 1,057; Gemini voice 831 → 5,578, text 410 →
3,645. The climb is the conversation history being re-sent (and
re-billed) every turn, in both modes.

## Quality (fixed rubrics, auto-scored — see METHOD.md)

| Platform | Mode | Correct (of 18 checked, 3 runs) | Partly | Wrong | Cap compliance (mean) | Filler hits (total) |
|---|---|---|---|---|---|---|
| OpenAI | voice | 18 | 0 | 0 | 89.7% | 0 |
| OpenAI | text | 18 | 0 | 0 | 92.3% | 0 |
| Gemini | voice | 17 | 1 | 0 | 46.2% | 3 |
| Gemini | text | 18 | 0 | 0 | 97.4% | 0 |

Correctness was consistently high everywhere. The one quality signal
that moved: **Gemini voice largely stopped obeying the two-sentence cap
in repeats full2/full3** (23.1% compliance in both, vs. 92.3% in full1),
answering in 3–6 sentences. That is also the main driver of its token
spread (below).

## Latency (time to first response, pooled median across the 3 runs)

| Platform | Voice | Text | Notes |
|---|---|---|---|
| OpenAI | 0.361 s | 0.252 s | Max 0.634 s anywhere in the repeats — no stalls |
| Gemini | 1.14 s | 0.855 s | full1 voice had two stalls (~45 s, ~52 s); they did not repeat |

Measured from one machine on one connection; includes network time.
See METHOD.md for definitions.

## Spend

- **OpenAI: ≈ $1.80 estimated, total**, out of a $5 account credit.
  Estimate = recorded usage × published `gpt-realtime` rates used in the
  run log (audio $32 in / $64 out, text $4 / $24, cached $0.40, per 1M
  tokens). Breakdown: full1 voice ≈ $0.32, text ≈ $0.22, smokes ≈ $0.04;
  repeats ≈ $1.22. The billing dashboard was not scraped; treat $1.80
  as a computed estimate, not an invoice figure.
- **Gemini: no cost figure exists.** The Live API returns no cost field,
  and no invoice data was pulled. Recorded Gemini usage across all runs
  (smokes + fulls) is on the order of 300k tokens — cents at published
  Live rates, and $0 if the key was on the free tier. We don't claim a
  number we weren't given.

## Limitations and anomalies

Written by us, before anyone else has to. Everything flagged in the raw
run log (`results/RUNS.md`) is carried over here.

**Limitations of the test itself**

- **The voice is a synthetic TTS voice, not a human.** It is clean,
  steady-paced, and identical across runs — that's the control — but a
  human speaker adds pauses, fillers, and restarts that would change
  audio durations and possibly token counts. Results describe this
  script spoken this way.
- **One script, one session shape.** A single 13-turn, question-and-answer
  script with capped replies. Longer conversations, tool use, or
  uncapped replies will scale differently (history re-billing grows
  with everything the model says).
- **API ≠ consumer apps.** These are developer APIs. The findings are
  about the APIs' billing mechanics, not about what any app charges
  against a subscription quota.
- **Model IDs are previews and can change.** `gpt-realtime` and
  especially `gemini-3.1-flash-live-preview` are moving targets; the
  same test later may measure different behavior. Dates are on every run.
- **n = 3.** Enough to see that the ratio is stable-ish and where the
  variance lives; not enough for tight confidence intervals.
- **Blind human directness scoring was designed but not performed.**
  No directness scores appear anywhere in these results.
- OpenAI's lower absolute counts lean on **prompt caching** (~39% of
  voice input tokens cached in run 1). Cache behavior is the platform's,
  not something the test controlled; on a colder cache the absolutes
  could look different.

**Anomalies observed in the data (kept in, not cleaned)**

- **Gemini voice full1 is a low outlier** (−16.6% vs. the sibling
  median total). The cause is visible in the runs: in full2/full3 the
  model mostly ignored Prompt Zero's two-sentence cap (compliance
  23.1% in both, output ≈ 4,000 tokens vs. full1's 2,652), so its longer
  replies re-entered history and inflated every later turn's input.
  Gemini's spread is mostly reply-length variance, not measurement noise.
- **Gemini voice cap compliance collapsed in the repeats** (92.3% in
  full1 → 23.1% in both full2 and full3) — a behavior change across
  identical inputs, recorded as-is.
- **Gemini text totals climb monotonically** across the three repeats
  (26,147 → 29,417 → 33,212). Outputs climb in step (2,448 → 2,813 →
  3,268) even though cap compliance stayed ≥ 92.3% — the sentences
  themselves got longer across successive runs.
- **Gemini voice full3, turn 5 is unmeasured.** The receive timed out
  (92.3 s, empty reply, no usage record), so full3's voice total of
  49,251 is a **floor** — turn 5's own usage (siblings suggest ~2.5–3k
  input tokens) is missing, though later turns' history includes the
  exchange. Turn 9's output count is also missing in full3 (a server
  usage-attribution quirk also seen in full1 around turns 9/10).
- **OpenAI turn-7 dip is systematic.** Per-turn input dips at turn 7 in
  5 of 6 OpenAI runs (e.g. text 630→529, 637→526, 708→542) at the same
  script point — reproducible platform behavior, not noise. Small
  (~15%) and does not move totals materially.
- **Gemini full1's latency stalls did not repeat.** Turns 2 and 10 of
  the first Gemini voice run took ~45 s and ~52 s to first response
  (median ~1.2 s). full2/full3 max was 1.67 s / 1.74 s.
- **Text runs accumulate audio tokens on both platforms** (Gemini text
  turn 13: 2,494 audio prompt tokens; OpenAI text run total: 1,820).
  The model's replies are spoken even when the prompt was text, and
  those replies stay in session history as audio.

## Redactions made for publication

One, and only one, category: the run `.log` files in `results/`
originally ended with the operator's local absolute file path
(`saved /home/…/results/<file>.json`). In the copies in this repo that
path was shortened to `results/<file>.json`. Nothing else in any copied
file was altered — all JSONs, CSVs, and `RUNS.md` are byte-identical to
the originals. See SECURITY.md for the full scrub that was run.
