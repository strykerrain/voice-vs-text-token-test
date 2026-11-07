# RUNS — Nov 6, 2026 (all times UTC; 14:xx PST)

Harness built and smoke-tested; full runs executed for Gemini, and for OpenAI
once the operator's $5 credit landed (17:09 PT). **Both platforms now COMPLETE.**
(The OpenAI blocked section below is the earlier same-day record, superseded
by the OpenAI — COMPLETE section that follows it.)

## Audio masters
- Generated once with local Piper TTS (`en_US-lessac-medium`, offline ONNX).
  edge-tts was tried first and returned empty audio through the egress proxy.
- 13 turns, 70.2s total per voice run. `audio/manifest.json` has per-turn
  durations; `audio/pcm24/` feeds OpenAI, `audio/pcm16/` feeds Gemini.

## OpenAI — BLOCKED (zero API credit)
- Runner: `code/openai_runner.py`, model `gpt-realtime`, one session per run,
  manual commit (VAD off). Auth path that worked: **surrogate Authorization
  header on the websocket** — handshake returned 101 and the session was
  created (the ephemeral client-secrets fallback was coded but not needed).
- Both smoke attempts (voice + text, 2 turns) were closed by the server with
  close code 1013: `insufficient_quota.credit_balance_exhausted`.
- Confirming probe: `POST /v1/chat/completions` (gpt-4o-mini) → HTTP 429
  "You have no credits remaining… code: credit_balance_exhausted".
  `GET /v1/models` returns 200 — the key is valid; the account is unfunded.
- Full evidence in `results/openai_blocked.json`. Fix: the operator tops up ~$5 at
  platform.openai.com/settings/organization/billing (setup doc step 1.2),
  then both OpenAI runs execute as-is. No OpenAI spend occurred ($0).

## Gemini — COMPLETE (smoke + full, both modes)
- Runner: `code/gemini_runner.py`, model `gemini-3.1-flash-live-preview`
  (first choice in the fallback chain; no fallback needed), one continuous
  Live session per run, manual activity start/end, audio streamed in
  realtime-paced 100ms chunks. Auth: **surrogate `x-goog-api-key` header**.
- Smoke (2 turns each): voice 22:28:37Z, text 22:29:23Z — both clean.
- Full voice: 22:29:53Z → 22:34:44Z, 13/13 turns, no errors.
  Input tokens grew 831 → 5,578/turn (total 41,059; **avg 3,158/turn**);
  output total 2,652. Turn-13 split: 4,293 audio + 781 text input tokens.
- Full text: 22:34:49Z → 22:36:40Z, 13/13 turns, no errors.
  Input tokens grew 410 → 3,645/turn (total 26,147; **avg 2,011/turn**);
  output total 2,448.
- **Headline: Gemini voice ≈ 1.57× the input tokens per turn of text**
  (3,158 vs 2,011 avg), with the same growth-curve shape in both modes —
  history re-billing dominates; voice adds an audio premium on top.
- Cost: the Live API returns no cost field; token totals are above. No
  Gemini invoice data was pulled; usage is ~70k tokens total across all
  Gemini runs — cents at published Live rates, $0 if the key is on free tier.

## OpenAI — COMPLETE (after $5 top-up, Nov 6 ~17:10 PT)

- Credit check first: `gpt-4o-mini` probe (the one that returned 429 before)
  returned HTTP 200 with a real completion — credit confirmed live before
  any run. No retry loop needed.
- Smokes (tag `smoke2`, 2 turns each): voice clean (in 290/424), text clean
  (in 175/246). No errors.
- Full voice: 01:10:26Z → 01:10:54Z, 13/13 turns, no errors.
  Input tokens grew 290 → 1,517/turn (total 12,244; **avg 942/turn**);
  output total 2,590. Turn-13 split: 594 text + 923 audio input, of which
  1,088 cached.
- Full text: 01:10:57Z → 01:11:23Z, 13/13 turns, no errors.
  Input tokens grew 175 → 1,057/turn (total 8,075; **avg 621/turn**);
  output total 2,658.
- **Headline: OpenAI voice ≈ 1.52× the input tokens per turn of text**
  (942 vs 621 avg) — very close to Gemini's 1.57× ratio, at roughly a third
  of Gemini's absolute per-turn counts.
- Latency: voice time-to-first-response median 0.382s, range 0.331–0.491s —
  flat all run, **no outliers** (contrast Gemini voice's two 45–52s stalls).
  Text median 0.252s, range 0.240–0.286s.
- Quality (harness scoring): auto-correctness 6/6 checked turns in both
  modes; cap compliance 92.3% in both modes; filler hits 0 in both.
- Spend (ESTIMATE from usage × published gpt-realtime-2.1 rates — audio
  $32 in / $64 out, text $4 / $24, cached $0.40 per 1M): voice full ≈ $0.32,
  text full ≈ $0.22, smokes ≈ $0.04 — **≈ $0.58 total** against the $5
  credit, plus <$0.001 for the credit probe.
- Quirks: (1) Caching is doing heavy lifting — 4,736 of the voice run's
  12,244 input tokens (~39%) were cached, which is a big part of why
  OpenAI's absolute counts sit far below Gemini's while the ratio matches.
  (2) The text run still accumulated **audio** input tokens (1,820 total;
  247 on turn 13): the assistant's replies are spoken even in a text-input
  Realtime session, so they re-enter history as audio — the same quirk
  Gemini showed. (3) Output totals are near-identical across modes
  (2,590 vs 2,658): Prompt Zero's cap held output constant, so the whole
  voice premium lands on the input side.

## Aggregates — REPEATS, n=3 (Nov 6, 2026, the operator approved 17:21 PT)

Two additional full runs per platform/mode (tags `full2`, `full3`), same
script, same audio masters, same runner settings as `full1`. Run order
(interleaved across platforms/modes so time-of-day doesn't cluster):
OpenAI voice f2 → Gemini text f2 → OpenAI text f2 → Gemini voice f2 →
Gemini voice f3 → OpenAI text f3 → Gemini text f3 → OpenAI voice f3
(01:21:34Z → 01:37:35Z). All 8 runs exit-clean, 13 turn entries each.
Machine-readable: `results/aggregates.csv` (from `code/aggregates.py`).

### OpenAI (gpt-realtime) — extremely stable
- Voice totals: 12,244 / 12,247 / 12,511 — mean 12,334, SD 153 (~1.2%).
  Mean avg 949 input tokens/turn. Mean output 2,641.
- Text totals: 8,075 / 8,086 / 7,796 — mean 7,986, SD 164 (~2.1%).
  Mean avg 614 input tokens/turn. Mean output 2,552.
- **Voice/text ratio: per-pair 1.516 / 1.515 / 1.605; ratio of means 1.545.**
- Quality across all 3 runs: correctness 18/18 checked turns per mode,
  filler 0, cap compliance 89.7% voice / 92.3% text (mean).
- Latency: pooled median time-to-first-response 0.361s voice / 0.252s text.
  No stalls in any repeat (max 0.634s).
- Repeat spend (ESTIMATE, usage × the same published gpt-realtime rates as
  the full1 estimate): voice f2 $0.39, voice f3 $0.41, text f2 $0.22,
  text f3 $0.20 — **≈ $1.22 for all four repeats**, inside the ~$4.42 of
  credit that remained. All-in OpenAI estimate incl. full1 + smokes ≈ $1.80
  of the $5 credit.

### Gemini (gemini-3.1-flash-live-preview) — noisier, and the noise is behavioral
- Voice totals: 41,059 / 50,870 / 49,251 — mean 47,060, SD 5,260 (~11%).
  Mean avg 3,620 input tokens/turn. Mean output 3,535.
- Text totals: 26,147 / 29,417 / 33,212 — mean 29,592, SD 3,536 (~12%).
  Mean avg 2,276 input tokens/turn. Mean output 2,843.
- **Voice/text ratio: per-pair 1.570 / 1.729 / 1.483; ratio of means 1.590.**
- Quality: correctness 17 correct + 1 partly of 18 checked (voice), 18/18
  (text); filler 3 total (all in voice repeats); cap compliance mean 46.2%
  voice / 97.4% text.
- Latency: pooled median time-to-first-response 1.14s voice / 0.855s text.
  full1's 45–52s stalls did NOT repeat — full2/full3 max was 1.67s / 1.74s.

### Flags (kept in the data, not averaged away)
- **Gemini voice full1 is a material low outlier** (−16.6% vs the sibling
  median total). Cause is visible in the runs themselves: in full2/full3
  the model largely ignored Prompt Zero's 2-sentence cap (cap compliance
  23.1% in both, replies of 3–6 sentences, output ≈ 4,000 tokens vs
  full1's 2,652), so its own longer replies re-entered history and
  inflated every later turn's input. Gemini's spread is mostly reply-length
  variance, not measurement noise.
- **Gemini text totals climb monotonically** (26,147 → 29,417 → 33,212;
  full1 −11.1% and full3 +12.9% vs the sibling median). Outputs climb in
  step (2,448 → 2,813 → 3,268) even though sentence-cap compliance stayed
  ≥92.3% — the sentences themselves got longer across successive runs.
- **Gemini voice full3 turn 5 is unmeasured**: the receive timed out
  (`turn 5 recv: TimeoutError`, 92.3s, empty reply, no usage record), so
  full3's voice total (49,251) is a FLOOR — turn 5's own usage (siblings
  suggest ~2.5–3k input) is missing, though later turns' history includes
  the exchange. Turn 9's output count is also missing in full3 (same
  server attribution quirk as full1 turn 9). The run is kept as-recorded.
- **OpenAI turn-7 dip is systematic**: per-turn input dips at turn 7 in
  5 of 6 OpenAI runs (e.g. text 630→529, 637→526, 708→542 across all three
  text runs) at the same script point — reproducible platform behavior,
  not noise. Small (~15%) and does not move totals materially.
- OpenAI run-to-run deviation max was 3.5% — no material outliers.

### Bottom line at n=3
The ~1.5× convergence HOLDS: ratio of means 1.545 (OpenAI) and 1.590
(Gemini); all six per-pair ratios fall between 1.48 and 1.73. OpenAI's
absolute counts remain ~2.6–3.8× lower than Gemini's at the same ratio
(caching), and OpenAI is far more repeatable (SD ~1–2% vs ~11–12%).

## Anomalies / quirks (recorded, not cleaned up)
- Gemini text runs still accumulate **audio** prompt tokens (turn 13: 2,494):
  the model's spoken replies stay in Live-session history as audio, so even
  "text" input pays audio-history rates in a voice session.
- Voice run turns 2 and 10 show time-to-first-response of ~45s and ~52s
  (median across the run is ~1.2s); turn 9's usage arrived without a
  response-token count and turn 10's input total dipped — looks like one
  response cycle was attributed across the turn 9/10 boundary by the server.
- OpenAI's edge returns `Connection: close` on the WS upgrade; websockets 17
  rejects it. `common.patch_websockets_connection_check()` removes only that
  header check (status/Upgrade/Accept validation intact).
- Gemini deprecated `realtimeInput.mediaChunks` → runner uses
  `realtimeInput.audio`. Usage field is `responseTokenCount` on this version.
- Auto-correctness (keyword checks, spot-verified by eye): 6/6 checked turns
  correct in both full runs. Cap compliance: text 100%, voice 92.3%.
  Filler hits: 0 in both. Blind 1–5 directness is NOT scored — needs a human.

## Files
- Per-run JSON: `gemini_{voice,text}_{smoke,full1,full2,full3}.json`, `openai_{voice,text}_{smoke2,full1,full2,full3}.json` (+ run logs).
- Roll-ups: `turns.csv` (164 rows incl. smokes), `sessions.csv` (16 rows), `aggregates.csv` (n=3, full runs only; `code/aggregates.py`).
- Blocker record: `openai_blocked.json` (historical; resolved same day).

## Not done (by design)
- No Grok.
- No analysis or post draft beyond these aggregates — per the task.
