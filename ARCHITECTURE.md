# ARCHITECTURE — how the harness works

Design goal: the *only* differences between a voice run and a text run —
and between platforms — should be the ones being measured. Everything
upstream of the API call is shared and frozen.

```text
                    ┌─────────────────────────────────────────────┐
                    │  script (code/script_turns.py)              │
                    │  13 turns, verbatim, frozen before runs     │
                    └──────────────┬──────────────────────────────┘
                                   │
              ┌────────────────────┴─────────────────────┐
              │                                          │
   TEXT RUNS  │ send the strings as-is        VOICE RUNS │ audio, generated ONCE
              │                                          │
              │                              ┌───────────┴────────────┐
              │                              │ Piper TTS (offline)    │
              │                              │ en_US-lessac-medium    │
              │                              │ -> audio/turnNN.wav    │
              │                              │ -> audio/manifest.json │
              │                              └───────────┬────────────┘
              │                              ffmpeg conversions (once)
              │                        ┌─────────┴──────────┐
              │                  pcm24 (24 kHz)        pcm16 (16 kHz)
              │                        │                    │
              ▼                        ▼                    ▼
   ┌──────────────────┐   ┌──────────────────┐   (Gemini uses pcm16)
   │  openai_runner   │   │  gemini_runner   │
   │  gpt-realtime    │   │  gemini-3.1-     │
   │  Realtime API    │   │  flash-live-     │
   │                  │   │  preview, Live   │
   └────────┬─────────┘   └────────┬─────────┘
            │  ONE continuous websocket session per run
            │  manual turn boundaries (no server VAD)
            ▼                      ▼
   per-turn capture: usage as the API reports it (tokens, split
   audio/text/cached where provided), first-response + completion
   timestamps, reply audio bytes, reply transcript
            │                      │
            └──────────┬───────────┘
                       ▼
            results/<run>.json   (one file per run, as recorded)
                       │
              code/rollup.py ──► results/turns.csv
                       │         results/sessions.csv
              code/aggregates.py ──► results/aggregates.csv (n=3)
```

## Components

- **`code/script_turns.py`** — the 13 prompts as data. The single source
  of truth: text runs send these strings; TTS speaks these strings.
- **`code/gen_audio.py`** — one-time audio generation (Piper, offline)
  and the ffmpeg conversions to each platform's PCM format. Run once;
  outputs are committed under `audio/` so runs never depend on a TTS
  being available at run time.
- **`code/openai_runner.py`** — opens one Realtime websocket session,
  configures it once (VAD off, PCM 24 kHz, voice, transcription), then
  for each turn: streams the PCM (voice) or sends the text item (text),
  commits, and waits for the completed response while timestamping
  first-audio and completion. Usage is taken from the API's own
  per-response usage object.
- **`code/gemini_runner.py`** — opens one Live (BidiGenerateContent)
  websocket, sends the session setup once (activity detection disabled,
  AUDIO modality, voice, transcriptions on), then per turn: activity
  start → realtime-paced 100 ms audio chunks (voice) or a text turn
  (text) → activity end. Usage is taken from the per-turn
  `usageMetadata` the API returns.
- **`code/common.py`** — shared helpers: credential surrogate fetch,
  sentence/word counting, PCM loading, result writing — and one
  documented patch (below).
- **`code/rollup.py` / `code/aggregates.py`** — pure post-processing of
  the recorded JSONs into CSVs and the n=3 statistics, including the
  fixed-rubric scoring (answer-key keyword checks, cap compliance,
  filler counts). Scoring never touches the network.

## Credential design (no secrets in this repo)

The runners need API keys, but no key ever appears in code, config,
results, or this repo:

1. The operator's real keys live in a separate credential vault, outside
   the harness entirely.
2. When a runner connects, it asks the vault for a **short-lived
   surrogate value** (`hsurr:…`) — not the key — via
   `get_surrogate()` in `code/common.py`.
3. The surrogate is placed in the websocket auth header
   (`Authorization: Bearer` for OpenAI, `x-goog-api-key` for Gemini).
   On the way out, the operator's network egress layer recognizes the
   surrogate and swaps in the real key for that one request.
4. Run logs and JSONs therefore only ever contain the literal string
   `surrogate_header` as the recorded auth path.

For a standalone re-run, replace `get_surrogate()` with your own key
lookup — it is the only credential touch-point in the codebase. (The
as-run code also references the operator's local helper path for the
vault client; that path is environment-specific and is the other thing
to adjust.)

## Known platform adaptations (discovered during the runs, kept visible)

- **OpenAI's edge returns `Connection: close` on the websocket upgrade**,
  which the `websockets` library (v17) rejects even though the upgrade
  is valid. `common.patch_websockets_connection_check()` removes *only*
  that one header check; status, Upgrade, and Sec-WebSocket-Accept
  validation are untouched. The patch is in the open in `code/common.py`.
- **Gemini deprecated `realtimeInput.mediaChunks`** — the runner uses
  `realtimeInput.audio`. On this model version, output usage is reported
  in the `responseTokenCount` field.
- Both quirks, and everything else odd the runs produced, are recorded
  in `results/RUNS.md` rather than cleaned up.
