"""
Phase 2: Rule-based adaptive signal timing + congestion/reroute flagging.

Reads the Phase 1 queue-count log (queue_counts.json), smooths recent
queue lengths per lane to reduce frame-to-frame noise, and computes:
  - a green-light duration per lane for the next signal cycle
  - a congestion flag used to trigger a reroute suggestion

Output: appends one decision record to signal_decisions.json.
This is the exact data Phase 3's dashboard will display and act on.
"""

import json
from collections import defaultdict

# ---------------- CONFIG ----------------

QUEUE_LOG_PATH = "queue_counts.json"
DECISION_LOG_PATH = "signal_decisions.json"

CYCLE_TIME_SECONDS = 60      # total green time available to split across all lanes per cycle
MIN_GREEN_SECONDS = 10       # every lane gets at least this much, even if empty
MAX_GREEN_SECONDS = 35       # cap so one lane can't take the whole cycle
SMOOTHING_WINDOW = 10        # number of recent frame-records averaged per lane

CONGESTION_THRESHOLD = 12    # total vehicles across all lanes that counts as "congested"

# -----------------------------------------


def read_all_records(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def smoothed_queue_counts(records, window=SMOOTHING_WINDOW):
    """Average the last `window` records per lane to reduce frame-to-frame noise."""
    recent = records[-window:]
    lane_values = defaultdict(list)
    for r in recent:
        for lane, count in r["queue_counts"].items():
            lane_values[lane].append(count)
    return {lane: sum(vals) / len(vals) for lane, vals in lane_values.items()}


def allocate_green_time(avg_counts):
    """Split CYCLE_TIME_SECONDS across lanes proportional to queue length, clamped."""
    total = sum(avg_counts.values())
    lanes = list(avg_counts.keys())

    if total == 0:
        equal_share = CYCLE_TIME_SECONDS / len(lanes)
        return {lane: round(equal_share, 1) for lane in lanes}

    raw = {lane: (count / total) * CYCLE_TIME_SECONDS for lane, count in avg_counts.items()}
    clamped = {lane: min(max(secs, MIN_GREEN_SECONDS), MAX_GREEN_SECONDS) for lane, secs in raw.items()}
    return {lane: round(secs, 1) for lane, secs in clamped.items()}


def check_congestion(avg_counts):
    total = sum(avg_counts.values())
    return total >= CONGESTION_THRESHOLD, round(total, 1)


def make_decision(records):
    avg_counts = smoothed_queue_counts(records)
    green_times = allocate_green_time(avg_counts)
    is_congested, total_vehicles = check_congestion(avg_counts)

    return {
        "timestamp": records[-1]["timestamp"],
        "avg_queue_counts": {k: round(v, 2) for k, v in avg_counts.items()},
        "green_time_seconds": green_times,
        "priority_lane": max(green_times, key=green_times.get),
        "congested": is_congested,
        "total_vehicles": total_vehicles,
        "reroute_suggested": is_congested,
    }


def main():
    records = read_all_records(QUEUE_LOG_PATH)

    if not records:
        print(f"No records found in {QUEUE_LOG_PATH}. Run vehicle_counter.py first.")
        return

    decision = make_decision(records)
    print(json.dumps(decision, indent=2))

    with open(DECISION_LOG_PATH, "a") as f:
        f.write(json.dumps(decision) + "\n")

    print(f"\nDecision logged to {DECISION_LOG_PATH}")


if __name__ == "__main__":
    main()
