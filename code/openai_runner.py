#!/usr/bin/env python3
"""OpenAI Realtime runner: ONE continuous session per run.
Voice run streams the shared PCM masters (24kHz) turn-by-turn with manual
commit (server VAD off) so timing is exact; text run sends the same words as
text items into the same session type/model.
Auth: (1) websocket with surrogate Authorization header (egress proxy swaps
it); (2) fallback — POST /v1/realtime/client_secrets via surrogate HTTPS to
mint an ephemeral key, connect with that. Which path worked is logged.
Usage: python openai_runner.py --mode voice|text [--turns 13] [--tag full1]
"""
import argparse, asyncio, base64, json, sys, time, urllib.request, urllib.error
import websockets

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (get_surrogate, count_sentences, count_words, load_pcm,
                    save_result, patch_websockets_connection_check)
from script_turns import TURNS
from dynamic_credentials import add_surrogate_to_request

MODEL = "gpt-realtime"
HOST = "api.openai.com"
SILENCE_24K = b"\x00" * (24000 * 2 * 0 // 1000)  # placeholder, computed below
TAIL_SILENCE = b"\x00" * int(24000 * 2 * 0.30)    # 300ms tail silence per turn

def ephemeral_key(surrogate_used):
    """Mint a Realtime ephemeral key via the surrogate HTTPS path."""
    body = json.dumps({"session": {"type": "realtime", "model": MODEL}}).encode()
    req = urllib.request.Request(
        f"https://{HOST}/v1/realtime/client_secrets", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(req, "custom.openai", allowed_hosts=[HOST])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return data.get("value") or data.get("client_secret", {}).get("value")
    except urllib.error.HTTPError as e:
        print(f"client_secrets HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}")
        return None

async def connect():
    """Return (websocket, auth_path). Never prints credential material."""
    url = f"wss://{HOST}/v1/realtime?model={MODEL}"
    surr = get_surrogate("custom.openai")
    try:
        ws = await websockets.connect(url, additional_headers={
            "Authorization": f"Bearer {surr}"}, max_size=None,
            open_timeout=30, proxy=True)
        return ws, "surrogate_header"
    except Exception as e:
        print(f"surrogate websocket connect failed: {type(e).__name__}: {e}")
    ek = ephemeral_key(True)
    if not ek:
        raise RuntimeError("ephemeral key minting failed")
    ws = await websockets.connect(url, additional_headers={
        "Authorization": f"Bearer {ek}"}, max_size=None,
        open_timeout=30, proxy=True)
    return ws, "ephemeral_key"

async def run(mode, n_turns, tag):
    patch_websockets_connection_check()
    ws, auth_path = await connect()
    result = {"platform": "openai", "model": MODEL, "mode": mode, "tag": tag,
              "auth_path": auth_path, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "turns": [], "errors": []}
    await ws.send(json.dumps({
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": MODEL,
            "output_modalities": ["audio"],
            "instructions": "",
            "audio": {
                "input": {"format": {"type": "audio/pcm", "rate": 24000},
                          "turn_detection": None,
                          "transcription": {"model": "gpt-4o-mini-transcribe"}},
                "output": {"format": {"type": "audio/pcm", "rate": 24000},
                           "voice": "alloy"},
            },
        }}))

    async def wait_for(types, timeout=90):
        """Collect events until one of `types` arrives; return (event, collected)."""
        collected = []
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            raw = await asyncio.wait_for(ws.recv(), timeout=max(1, end - time.monotonic()))
            ev = json.loads(raw)
            collected.append(ev)
            if ev.get("type") in types:
                return ev, collected
        raise TimeoutError(f"none of {types} within {timeout}s")

    # drain session.created / session.updated
    try:
        await wait_for({"session.updated"}, timeout=15)
    except Exception as e:
        result["errors"].append(f"session.updated wait: {e}")

    for i in range(n_turns):
        text = TURNS[i]
        turn = {"turn": i + 1, "mode": mode, "prompt_text": text,
                "prompt_words": count_words(text)}
        if mode == "voice":
            pcm = load_pcm("pcm24", i + 1)
            turn["prompt_audio_seconds"] = round(len(pcm) / 2 / 24000, 3)
            # stream in 100ms chunks, back-to-back (manual commit => pacing-free)
            step = 24000 * 2 // 10
            for off in range(0, len(pcm), step):
                await ws.send(json.dumps({"type": "input_audio_buffer.append",
                    "audio": base64.b64encode(pcm[off:off + step]).decode()}))
            await ws.send(json.dumps({"type": "input_audio_buffer.append",
                "audio": base64.b64encode(TAIL_SILENCE).decode()}))
            await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            await ws.send(json.dumps({"type": "response.create"}))
        else:
            await ws.send(json.dumps({"type": "conversation.item.create", "item": {
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": text}]}}))
            await ws.send(json.dumps({"type": "response.create"}))
        t_end = time.monotonic()
        t_first = None
        transcript_parts, audio_bytes, usage, in_transcript = [], 0, None, ""
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=90)
                ev = json.loads(raw)
                et = ev.get("type", "")
                if t_first is None and et in (
                        "response.output_audio.delta", "response.audio.delta",
                        "response.output_audio_transcript.delta",
                        "response.audio_transcript.delta",
                        "response.output_text.delta", "response.text.delta"):
                    t_first = time.monotonic()
                if et in ("response.output_audio.delta", "response.audio.delta"):
                    audio_bytes += len(base64.b64decode(ev.get("delta", "")))
                elif et in ("response.output_audio_transcript.delta",
                            "response.audio_transcript.delta"):
                    transcript_parts.append(ev.get("delta", ""))
                elif et == "conversation.item.input_audio_transcription.completed":
                    in_transcript = ev.get("transcript", "")
                elif et == "response.done":
                    usage = ev.get("response", {}).get("usage")
                    if ev.get("response", {}).get("status") not in (None, "completed"):
                        result["errors"].append(
                            f"turn {i+1} status={ev['response'].get('status')} "
                            f"{ev['response'].get('status_details')}")
                    break
                elif et == "error":
                    result["errors"].append(f"turn {i+1}: {ev.get('error')}")
                    break
        except Exception as e:
            result["errors"].append(f"turn {i+1} recv: {type(e).__name__}: {e}")
        t_done = time.monotonic()
        reply = "".join(transcript_parts)
        turn.update({
            "time_to_first_response_s": round(t_first - t_end, 3) if t_first else None,
            "time_to_complete_s": round(t_done - t_end, 3),
            "usage_raw": usage,
            "input_transcript_heard": in_transcript,
            "reply_transcript": reply,
            "reply_words": count_words(reply),
            "reply_sentences": count_sentences(reply),
            "reply_audio_seconds": round(audio_bytes / 2 / 24000, 3),
        })
        if usage:
            itd = usage.get("input_token_details") or {}
            otd = usage.get("output_token_details") or {}
            turn.update({
                "input_tokens": usage.get("input_tokens"),
                "input_audio_tokens": itd.get("audio_tokens"),
                "input_text_tokens": itd.get("text_tokens"),
                "input_cached_tokens": itd.get("cached_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "output_audio_tokens": otd.get("audio_tokens"),
                "output_text_tokens": otd.get("text_tokens"),
                "total_tokens": usage.get("total_tokens"),
            })
        result["turns"].append(turn)
        print(f"[{mode}] turn {i+1}: first={turn['time_to_first_response_s']}s "
              f"complete={turn['time_to_complete_s']}s in={turn.get('input_tokens')} "
              f"out={turn.get('output_tokens')} reply_words={turn['reply_words']}")
    await ws.close()
    result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    save_result(result, f"openai_{mode}_{tag}.json")
    return result

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["voice", "text"], required=True)
    ap.add_argument("--turns", type=int, default=13)
    ap.add_argument("--tag", default="full1")
    a = ap.parse_args()
    asyncio.run(run(a.mode, a.turns, a.tag))
