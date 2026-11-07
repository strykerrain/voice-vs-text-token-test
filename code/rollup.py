#!/usr/bin/env python3
"""Roll results/*.json into results/turns.csv + results/sessions.csv using
exactly the metrics-spec fields. Filler hits and correctness here are simple
deterministic auto-checks (keyword rules fixed before publication); the
blind 1-5 directness score is NOT auto-scored — it needs a human scorer."""
import csv, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RESULTS = os.path.join(ROOT, "results")

FILLERS = ["great question", "as an ai", "let me know if", "feel free",
           "happy to help", "hope this helps", "certainly!", "of course!",
           "anything else", "glad you asked"]

def filler_hits(text):
    low = (text or "").lower()
    return sum(low.count(f) for f in FILLERS)

# Keyword auto-checks keyed by turn number (script's known answers).
# Required = list of groups; a group passes if ANY alternative in it appears.
CHECKS = {
    4:  ([["60"]], ["divid", "180", "per hour", "mph"]),
    7:  ([["interest on", "earn interest", "compounding", "compounds"]], ["$100", "100"]),
    8:  ([["gare"], ["bahnhof"]], ["estación", "estacion", "où", "dónde", "donde"]),
    9:  ([["212"], ["100"]], ["pressure", "altitude", "lower"]),
    11: ([["sunday"]], ["remainder", "mod", "100"]),
    13: ([["atrium"], ["ventricle"]], ["lung", "body"]),
}

def auto_correctness(turn_no, text):
    if turn_no not in CHECKS:
        return ""  # gist/form turns scored by a human later
    low = (text or "").lower()
    groups, supporting = CHECKS[turn_no]
    if all(any(alt in low for alt in g) for g in groups):
        return "correct" if any(s in low for s in supporting) else "partly"
    return "wrong"

def main():
    turn_rows, session_rows = [], []
    for path in sorted(glob.glob(os.path.join(RESULTS, "*.json"))):
        with open(path) as f:
            run = json.load(f)
        if "mode" not in run or not run.get("turns"):
            print(f"skip {os.path.basename(path)} (no completed turns)")
            continue
        cum_in = 0
        for t in run["turns"]:
            cum_in += t.get("input_tokens") or 0
            turn_rows.append({
                "platform": run["platform"], "model": run["model"],
                "mode": run["mode"], "tag": run["tag"], "turn": t["turn"],
                "prompt_words": t["prompt_words"],
                "prompt_audio_seconds": t.get("prompt_audio_seconds", ""),
                "input_tokens": t.get("input_tokens"),
                "input_audio_tokens": t.get("input_audio_tokens"),
                "input_text_tokens": t.get("input_text_tokens"),
                "input_cached_tokens": t.get("input_cached_tokens"),
                "cumulative_input_tokens": cum_in,
                "output_tokens": t.get("output_tokens"),
                "output_audio_tokens": t.get("output_audio_tokens"),
                "output_text_tokens": t.get("output_text_tokens"),
                "time_to_first_response_s": t.get("time_to_first_response_s"),
                "time_to_complete_s": t.get("time_to_complete_s"),
                "reply_words": t.get("reply_words"),
                "reply_sentences": t.get("reply_sentences"),
                "reply_audio_seconds": t.get("reply_audio_seconds"),
                "verbosity_ratio": round(t["reply_words"] / t["prompt_words"], 2)
                    if t.get("prompt_words") else "",
                "filler_hits": filler_hits(t.get("reply_transcript")),
                "auto_correctness": auto_correctness(t["turn"], t.get("reply_transcript")),
            })
        turns = run["turns"]
        firsts = [t["time_to_first_response_s"] for t in turns
                  if t.get("time_to_first_response_s") is not None]
        capped = sum(1 for t in turns if (t.get("reply_sentences") or 99) <= 2)
        session_rows.append({
            "platform": run["platform"], "model": run["model"],
            "mode": run["mode"], "tag": run["tag"],
            "turns_completed": len(turns),
            "total_input_tokens": sum(t.get("input_tokens") or 0 for t in turns),
            "total_output_tokens": sum(t.get("output_tokens") or 0 for t in turns),
            "avg_input_tokens_per_turn": round(
                sum(t.get("input_tokens") or 0 for t in turns) / len(turns), 1) if turns else "",
            "total_reply_audio_seconds": round(
                sum(t.get("reply_audio_seconds") or 0 for t in turns), 1),
            "avg_time_to_first_response_s": round(sum(firsts) / len(firsts), 3) if firsts else "",
            "worst_time_to_first_response_s": max(firsts) if firsts else "",
            "latency_first_turn_s": firsts[0] if firsts else "",
            "latency_last_turn_s": firsts[-1] if firsts else "",
            "cap_compliance_pct": round(100 * capped / len(turns), 1) if turns else "",
            "total_filler_hits": sum(filler_hits(t.get("reply_transcript")) for t in turns),
            "auto_correctness_correct": sum(
                1 for t in turns if auto_correctness(t["turn"], t.get("reply_transcript")) == "correct"),
            "auto_correctness_partly": sum(
                1 for t in turns if auto_correctness(t["turn"], t.get("reply_transcript")) == "partly"),
            "auto_correctness_wrong": sum(
                1 for t in turns if auto_correctness(t["turn"], t.get("reply_transcript")) == "wrong"),
            "errors": len(run.get("errors", [])),
        })
    for name, rows in (("turns.csv", turn_rows), ("sessions.csv", session_rows)):
        if not rows:
            print(f"no rows for {name}"); continue
        with open(os.path.join(RESULTS, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"wrote {name}: {len(rows)} rows")

if __name__ == "__main__":
    main()
