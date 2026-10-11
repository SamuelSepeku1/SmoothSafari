"""
Phase 1: CV vehicle counting per lane (offline / batch).

Reads the video, detects vehicles with YOLOv8n, counts how many fall inside each
lane polygon, and writes one JSON line per processed frame to queue_counts.json.
That file feeds signal_controller.py (Phase 2).

Settings (video path, lane zones) come from site_config.py.
"""

import json
from datetime import datetime, timezone

import numpy as np
import supervision as sv
from ultralytics import YOLO

from site_config import LANE_ZONES, MODEL_PATH, VIDEO_PATH

# ---------------- CONFIG ----------------

OUTPUT_PATH = "queue_counts.json"
PROCESS_EVERY_N_FRAMES = 3     # skip frames for CPU speed
PRINT_TO_CONSOLE = True
VEHICLE_CLASS_IDS = [2, 3, 5, 7]   # COCO: car, motorcycle, bus, truck

# -----------------------------------------


def main():
    model = YOLO(MODEL_PATH)
    frames = sv.get_video_frames_generator(source_path=VIDEO_PATH)

    zones = {name: sv.PolygonZone(polygon=poly) for name, poly in LANE_ZONES.items()}

    frame_count = 0
    open(OUTPUT_PATH, "w").close()   # start a fresh log each run

    for frame in frames:
        frame_count += 1
        if frame_count % PROCESS_EVERY_N_FRAMES != 0:
            continue

        results = model(frame, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = detections[np.isin(detections.class_id, VEHICLE_CLASS_IDS)]

        queue_counts = {}
        for name, zone in zones.items():
            in_zone_mask = zone.trigger(detections=detections)
            queue_counts[name] = int(in_zone_mask.sum())

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "frame": frame_count,
            "queue_counts": queue_counts,
        }

        if PRINT_TO_CONSOLE:
            print(record)

        with open(OUTPUT_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")

    print(f"\nDone. Queue-count log written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
