#!/usr/bin/env python3
"""Generate the 13 script turns ONCE as audio masters with local Piper TTS
(en_US-lessac-medium, ONNX, fully offline — edge-tts was tried first and
returned empty audio through the egress proxy, so Piper is the master source).
Outputs per-turn WAV masters + derived PCM files:
  audio/pcm24/turnNN.pcm  (OpenAI Realtime input: PCM16 LE 24kHz mono)
  audio/pcm16/turnNN.pcm  (Gemini Live input:    PCM16 LE 16kHz mono)
plus audio/manifest.json with per-turn durations. Runners read ONLY these
files; audio is never regenerated per platform or per run."""
import json, os, subprocess, sys, wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_turns import TURNS

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "..", "audio")
MODEL = os.path.join(AUDIO, "voices", "en_US-lessac-medium.onnx")

def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", path], capture_output=True, text=True)
    return float(json.loads(out.stdout)["format"]["duration"])

def main():
    from piper import PiperVoice
    voice = PiperVoice.load(MODEL)
    os.makedirs(os.path.join(AUDIO, "pcm24"), exist_ok=True)
    os.makedirs(os.path.join(AUDIO, "pcm16"), exist_ok=True)
    manifest = {"tts": "piper-tts local ONNX, voice=en_US-lessac-medium", "turns": []}
    total = 0.0
    for i, text in enumerate(TURNS, 1):
        raw = os.path.join(AUDIO, f"turn{i:02d}_raw.wav")
        wav = os.path.join(AUDIO, f"turn{i:02d}.wav")
        with wave.open(raw, "wb") as wf:
            voice.synthesize_wav(text, wf)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw,
                        "-ac", "1", "-ar", "24000", wav], check=True)
        os.remove(raw)
        for rate, sub in ((24000, "pcm24"), (16000, "pcm16")):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ac", "1",
                            "-ar", str(rate), "-f", "s16le",
                            os.path.join(AUDIO, sub, f"turn{i:02d}.pcm")], check=True)
        d = duration(wav)
        total += d
        manifest["turns"].append({"turn": i, "text": text, "wav": f"turn{i:02d}.wav",
                                  "seconds": round(d, 3),
                                  "words": len(text.split())})
        print(f"turn {i:02d}: {d:.2f}s, {len(text.split())} words")
    manifest["total_seconds"] = round(total, 3)
    with open(os.path.join(AUDIO, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"TOTAL {total:.1f}s across {len(TURNS)} turns; manifest written")

if __name__ == "__main__":
    main()
