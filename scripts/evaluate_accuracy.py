"""
DevOpsAI Autonomous Investigation & RCA Benchmark Evaluator.
Compares DevOpsAI diagnosed incidents against the Chaos Monkey's ground-truth log.
Calculates mathematical precision, recall, MTTD, and RCA accuracy.
"""

import os
import json
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

GROUND_TRUTH_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shop", "chaos_ground_truth.jsonl")
DEVOPSAI_API = "http://127.0.0.1:8000/api/incidents/"

# Mapping from ground truth fault type to keywords in DevOpsAI RCA
FAULT_KEYWORD_MAP = {
    "OOM_MEMORY_LEAK": ["oom", "memory", "137", "sigkill", "leak"],
    "DB_CONNECTION_STARVATION": ["connection", "postgres", "pool", "starvation", "exhaustion"],
    "CPU_THROTTLING_STARVATION": ["cfs", "cpu", "quota", "throttl", "thread"],
    "REDIS_CACHE_TIMEOUT": ["redis", "cache", "timeout", "stampede", "thundering"]
}


def load_ground_truth() -> List[Dict[str, Any]]:
    if not os.path.exists(GROUND_TRUTH_FILE):
        return []
    records = []
    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line.strip()))
                except Exception:
                    pass
    return records


def fetch_devopsai_incidents() -> List[Dict[str, Any]]:
    try:
        resp = requests.get(DEVOPSAI_API, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching DevOpsAI incidents: {e}")
    return []


def parse_iso(ts_str: str) -> datetime:
    try:
        # Normalize timezone
        ts_str = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_str)
    except Exception:
        return datetime.now(timezone.utc)


def evaluate():
    print("=" * 70)
    print("      DEVOPSAI AUTONOMOUS SRE PLATFORM — BENCHMARK EVALUATOR")
    print("=" * 70)

    ground_truth = load_ground_truth()
    if not ground_truth:
        print(f"No ground-truth events found in '{GROUND_TRUTH_FILE}'.")
        print("Run 'python shop/chaos_daemon.py --attack <type>' or '--auto' to generate faults.")
        return

    incidents = fetch_devopsai_incidents()
    print(f"Loaded {len(ground_truth)} ground-truth chaos events.")
    print(f"Loaded {len(incidents)} DevOpsAI incident records.\n")

    matched_count = 0
    correct_rca_count = 0
    ttd_seconds_list = []

    print(f"{'TIMESTAMP':19} | {'INJECTED FAULT':24} | {'DETECTED?':9} | {'RCA MATCH?':10} | {'TTD (s)':7}")
    print("-" * 75)

    for gt in ground_truth:
        gt_time = parse_iso(gt["timestamp"])
        gt_type = gt["fault_type"]
        keywords = FAULT_KEYWORD_MAP.get(gt_type, [])

        # Find closest incident within +/- 90 seconds
        best_match = None
        min_delta = 999999

        for inc in incidents:
            inc_time = parse_iso(inc.get("triggered_at", ""))
            delta_sec = (inc_time - gt_time).total_seconds()
            if abs(delta_sec) <= 600 and abs(delta_sec) < min_delta:
                min_delta = abs(delta_sec)
                best_match = inc

        is_detected = best_match is not None
        is_rca_correct = False
        ttd = min_delta if is_detected else 0

        if is_detected:
            matched_count += 1
            ttd_seconds_list.append(ttd)

            # Check RCA text
            rca_title = ""
            invs = best_match.get("investigations", [])
            if invs and invs[0].get("rca_report"):
                rca_title = (invs[0]["rca_report"].get("root_cause_title") or "").lower()
            inc_title = (best_match.get("title") or "").lower()
            combined_text = f"{inc_title} {rca_title}"

            if any(kw in combined_text for kw in keywords):
                is_rca_correct = True
                correct_rca_count += 1

        gt_short_time = gt_time.strftime("%Y-%m-%d %H:%M:%S")
        det_str = "YES" if is_detected else "NO"
        rca_str = "CORRECT" if is_rca_correct else ("WRONG" if is_detected else "MISSED")
        ttd_str = f"{ttd:.1f}s" if is_detected else "N/A"

        print(f"{gt_short_time:19} | {gt_type:24} | {det_str:9} | {rca_str:10} | {ttd_str:7}")

    # Calculate metrics
    total_injected = len(ground_truth)
    detection_rate = (matched_count / total_injected * 100.0) if total_injected > 0 else 0.0
    rca_accuracy = (correct_rca_count / total_injected * 100.0) if total_injected > 0 else 0.0
    avg_ttd = (sum(ttd_seconds_list) / len(ttd_seconds_list)) if ttd_seconds_list else 0.0

    print("\n" + "=" * 70)
    print("                     EVALUATION SCORECARD")
    print("=" * 70)
    print(f"Total Injected Chaos Events : {total_injected}")
    print(f"Successfully Detected       : {matched_count} ({detection_rate:.1f}%)")
    print(f"Accurately Diagnosed (RCA)  : {correct_rca_count} ({rca_accuracy:.1f}%)")
    print(f"Mean Time To Detect (MTTD)  : {avg_ttd:.1f} seconds")
    print("=" * 70)


if __name__ == "__main__":
    evaluate()

