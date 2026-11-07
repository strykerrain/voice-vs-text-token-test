#!/usr/bin/env python3
"""Gemini Live runner: ONE continuous BidiGenerateContent session per run.
Voice run streams the shared PCM masters (16kHz) in realtime chunks with
manual activity start/end (automatic VAD disabled) so turn boundaries are
exact; text run sends the same words as clientContent text turns into the
same Live session type.
Auth: (1) websocket x-goog-api-key header carrying the surrogate (egress
proxy swaps it); (2) fallback ?key=<surrogate> query param (literal form,
per the runtime's surrogate matching rule). Which path worked is logged.
Usage: python gemini_runner.py --mode voice|text [--turns 13] [--tag full1]
"""
import argparse, asyncio, base64, json, sys, time
import websockets

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (get_surrogate, count_sentences, count_words, load_pcm,
                    save_result, patch_websockets_connection_check)
from script_turns import TURNS

HOST = "generativelanguage.googleapis.com"
WS_PATH = "/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
MODELS = ["gemini-3.1-flash-live-preview",
          "gemini-2.5-flash-native-audio-latest",
          "gemini-3.8-live"]

async def connect(model, surr):
    url = f"wss://{HOST}{WS_PATH}"
    try:
        ws = await websockets.connect(url, additional_headers={
            "x-goog-api-key": surr}, max_size=None, open_timeout=30, proxy=True)
        return ws, "surrogate_header"
    except Exception as e:
        print(f"header connect failed: {type(e).__name__}: {e}")
    ws = await websockets.connect(f"{url}?key={surr}", max_size=None,
                                  open_timeout=30, proxy=True)
    return ws, "surrogate_query_param"

async def setup_session(ws, model):
    await ws.send(json.dumps({"setup": {
        "model": f"models/{model}",
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {
                "prebuiltVoiceConfig": {"voiceName": "Kore"}}},
        },
        "realtimeInputConfig": {"automaticActivityDetection": {"disabled": True}},
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
    }}))
    end = time.monotonic() + 20
    while time.monotonic() < end:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "setupComplete" in msg:
            return True
        if "error" in msg:
            raise RuntimeError(f"setup error: {msg['error']}")
    raise TimeoutError("no setupComplete")

async def run(mode, n_turns, tag):
    patch_websockets_connection_check()
    surr = get_surrogate("custom.gemini")
    ws, model, auth_path, last_err = None, None, None, None
    for cand in MODELS:
        try:
            ws_c, path = await connect(cand, surr)
            await setup_session(ws_c, cand)
            ws, model, auth_path = ws_c, cand, path
            break
        except Exception as e:
            last_err = e
            print(f"model {cand}: {type(e).__name__}: {e}")
            try:
                await ws_c.close()
            except Exception:
                pass
    if ws is None:
        raise RuntimeError(f"all Live models failed; last: {last_err}")
    print(f"connected: model={model} auth={auth_path}")
    result = {"platform": "gemini", "model": model, "mode": mode, "tag": tag,
              "auth_path": auth_path,
              "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "turns": [], "errors": []}

    for i in range(n_turns):
        text = TURNS[i]
        turn = {"turn": i + 1, "mode": mode, "prompt_text": text,
                "prompt_words": count_words(text)}
        if mode == "voice":
            pcm = load_pcm("pcm16", i + 1)
            turn["prompt_audio_seconds"] = round(len(pcm) / 2 / 16000, 3)
            await ws.send(json.dumps({"realtimeInput": {"activityStart": {}}}))
            step = 16000 * 2 // 10  # 100ms of PCM16 16kHz
            for off in range(0, len(pcm), step):
                # mediaChunks is deprecated on this API version; use realtimeInput.audio
                await ws.send(json.dumps({"realtimeInput": {"audio": {
                    "mimeType": "audio/pcm;rate=16000",
                    "data": base64.b64encode(pcm[off:off + step]).decode()}}}))
                await asyncio.sleep(0.1)  # realtime pacing, as the API expects
            await ws.send(json.dumps({"realtimeInput": {"activityEnd": {}}}))
        else:
            await ws.send(json.dumps({"clientContent": {
                "turns": [{"role": "user", "parts": [{"text": text}]}],
                "turnComplete": True}}))
        t_end = time.monotonic()
        t_first = None
        out_text, in_text, audio_bytes, usage = [], [], 0, None
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=90)
                msg = json.loads(raw)
                if msg.get("usageMetadata"):
                    usage = msg["usageMetadata"]
                sc = msg.get("serverContent") or {}
                mt = sc.get("modelTurn") or {}
                for part in mt.get("parts", []):
                    if "inlineData" in part:
                        if t_first is None:
                            t_first = time.monotonic()
                        audio_bytes += len(base64.b64decode(
                            part["inlineData"].get("data", "")))
                ot = sc.get("outputTranscription") or {}
                if ot.get("text"):
                    if t_first is None:
                        t_first = time.monotonic()
                    out_text.append(ot["text"])
                it = sc.get("inputTranscription") or {}
                if it.get("text"):
                    in_text.append(it["text"])
                if sc.get("turnComplete"):
                    break
                if "error" in msg:
                    result["errors"].append(f"turn {i+1}: {msg['error']}")
                    break
        except Exception as e:
            result["errors"].append(f"turn {i+1} recv: {type(e).__name__}: {e}")
        t_done = time.monotonic()
        reply = "".join(out_text)
        turn.update({
            "time_to_first_response_s": round(t_first - t_end, 3) if t_first else None,
            "time_to_complete_s": round(t_done - t_end, 3),
            "usage_raw": usage,
            "input_transcript_heard": "".join(in_text),
            "reply_transcript": reply,
            "reply_words": count_words(reply),
            "reply_sentences": count_sentences(reply),
            "reply_audio_seconds": round(audio_bytes / 2 / 24000, 3),  # Live out = 24kHz
        })
        if usage:
            pd = {d.get("modality"): d.get("tokenCount")
                  for d in usage.get("promptTokensDetails", [])}
            rd = {d.get("modality"): d.get("tokenCount")
                  for d in usage.get("responseTokensDetails", [])}
            turn.update({
                "input_tokens": usage.get("promptTokenCount"),
                "input_audio_tokens": pd.get("AUDIO"),
                "input_text_tokens": pd.get("TEXT"),
                "input_cached_tokens": usage.get("cachedContentTokenCount"),
                "output_tokens": usage.get("responseTokenCount",
                                           usage.get("candidatesTokenCount")),
                "output_audio_tokens": rd.get("AUDIO"),
                "output_text_tokens": rd.get("TEXT"),
                "total_tokens": usage.get("totalTokenCount"),
            })
        result["turns"].append(turn)
        print(f"[{mode}] turn {i+1}: first={turn['time_to_first_response_s']}s "
              f"complete={turn['time_to_complete_s']}s in={turn.get('input_tokens')} "
              f"out={turn.get('output_tokens')} reply_words={turn['reply_words']}")
    await ws.close()
    result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    save_result(result, f"gemini_{mode}_{tag}.json")
    return result

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["voice", "text"], required=True)
    ap.add_argument("--turns", type=int, default=13)
    ap.add_argument("--tag", default="full1")
    a = ap.parse_args()
    asyncio.run(run(a.mode, a.turns, a.tag))
