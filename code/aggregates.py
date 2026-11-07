#!/usr/bin/env python3
"""n=3 aggregates over full runs only (tags full1/full2/full3).
Writes results/aggregates.csv and prints a JSON summary used for RUNS.md.
Anomaly flags are computed, not hidden: latency stalls (TTFR > 10s), per-turn
input dips >15% vs the previous turn (possible server attribution offset),
missing output-token counts, and run totals deviating >10% from the sibling
median for the same platform/mode."""
import csv, json, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rollup import filler_hits, auto_correctness

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RESULTS = os.path.join(ROOT, "results")
TAGS = ["full1", "full2", "full3"]

def load(platform, mode, tag):
    p = os.path.join(RESULTS, f"{platform}_{mode}_{tag}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)

def run_stats(run):
    turns = run["turns"]
    ins = [t.get("input_tokens") or 0 for t in turns]
    ttfr = [t["time_to_first_response_s"] for t in turns
            if t.get("time_to_first_response_s") is not None]
    stalls = [(t["turn"], t["time_to_first_response_s"]) for t in turns
              if (t.get("time_to_first_response_s") or 0) > 10]
    dips = [(turns[i]["turn"], ins[i - 1], ins[i]) for i in range(1, len(ins))
            if ins[i] < 0.85 * ins[i - 1]]
    missing_out = [t["turn"] for t in turns if t.get("output_tokens") is None]
    capped = sum(1 for t in turns if (t.get("reply_sentences") or 99) <= 2)
    corr = {"correct": 0, "partly": 0, "wrong": 0}
    for t in turns:
        c = auto_correctness(t["turn"], t.get("reply_transcript"))
        if c in corr:
            corr[c] += 1
    return {
        "tag": run["tag"], "started_at": run.get("started_at"),
        "turns": len(turns), "total_input": sum(ins),
        "total_output": sum(t.get("output_tokens") or 0 for t in turns),
        "avg_input_per_turn": round(sum(ins) / len(ins), 1),
        "median_ttfr": round(statistics.median(ttfr), 3) if ttfr else None,
        "max_ttfr": max(ttfr) if ttfr else None,
        "cap_compliance_pct": round(100 * capped / len(turns), 1),
        "filler_hits": sum(filler_hits(t.get("reply_transcript")) for t in turns),
        "correct": corr["correct"], "partly": corr["partly"], "wrong": corr["wrong"],
        "errors": len(run.get("errors", [])),
        "stalls": stalls, "input_dips": dips, "missing_output_turns": missing_out,
    }

def main():
    groups, rows, summary = {}, [], {}
    for platform in ("openai", "gemini"):
        for mode in ("voice", "text"):
            stats = []
            for tag in TAGS:
                run = load(platform, mode, tag)
                if run:
                    stats.append(run_stats(run))
            if not stats:
                continue
            totals = [s["total_input"] for s in stats]
            med_total = statistics.median(totals)
            for s in stats:
                s["dev_from_sibling_median_pct"] = round(
                    100 * (s["total_input"] - med_total) / med_total, 1)
                s["material_deviation"] = abs(s["dev_from_sibling_median_pct"]) > 10
            pooled_ttfr = []
            for tag in TAGS:
                run = load(platform, mode, tag)
                if run:
                    pooled_ttfr += [t["time_to_first_response_s"] for t in run["turns"]
                                    if t.get("time_to_first_response_s") is not None]
            g = {
                "platform": platform,
                "model": load(platform, mode, stats[0]["tag"]).get("model"),
                "mode": mode, "n": len(stats),
                "run_totals_input": totals,
                "mean_total_input": round(statistics.mean(totals), 1),
                "min_total_input": min(totals), "max_total_input": max(totals),
                "sd_total_input": round(statistics.stdev(totals), 1) if len(totals) > 1 else 0.0,
                "mean_avg_input_per_turn": round(statistics.mean(
                    [s["avg_input_per_turn"] for s in stats]), 1),
                "mean_total_output": round(statistics.mean(
                    [s["total_output"] for s in stats]), 1),
                "mean_cap_compliance_pct": round(statistics.mean(
                    [s["cap_compliance_pct"] for s in stats]), 1),
                "total_correct": sum(s["correct"] for s in stats),
                "total_partly": sum(s["partly"] for s in stats),
                "total_wrong": sum(s["wrong"] for s in stats),
                "total_filler_hits": sum(s["filler_hits"] for s in stats),
                "pooled_median_ttfr_s": round(statistics.median(pooled_ttfr), 3) if pooled_ttfr else None,
                "runs": stats,
            }
            groups[(platform, mode)] = g
            rows.append({k: (json.dumps(v) if k == "run_totals_input" else v)
                         for k, v in g.items() if k != "runs"})
            summary[f"{platform}_{mode}"] = g
    # per-pair + ratio-of-means
    ratios = {}
    for platform in ("openai", "gemini"):
        v, t = groups.get((platform, "voice")), groups.get((platform, "text"))
        if not v or not t:
            continue
        vt = {s["tag"]: s["total_input"] for s in v["runs"]}
        tt = {s["tag"]: s["total_input"] for s in t["runs"]}
        pair = {tag: round(vt[tag] / tt[tag], 3) for tag in TAGS if tag in vt and tag in tt}
        ratios[platform] = {
            "per_pair_ratios": pair,
            "ratio_of_means": round(v["mean_total_input"] / t["mean_total_input"], 3),
        }
    summary["ratios"] = ratios
    with open(os.path.join(RESULTS, "aggregates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote aggregates.csv: {len(rows)} rows")
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
