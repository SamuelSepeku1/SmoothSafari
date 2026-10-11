"""
Live server: Phase 1 + Phase 2 running together in real time, plus Phase 4 routing.

A background thread reads the video frame by frame, detects vehicles with
YOLOv8n, counts how many sit inside each lane polygon, computes the adaptive
signal plan (same functions as signal_controller.py) and draws everything on the
frame.

Endpoints used by the React dashboard:
  GET /video_feed                    annotated video as an MJPEG stream
  GET /api/latest                    live counts + signal plan + congestion flag
  GET /api/route?congested=true      Dijkstra route for that congestion state
                                     (if the parameter is omitted, the live
                                     congestion flag is used)

Run:  python liveserver.py     (port 8000)
"""

import asyncio
import threading
import time
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import cv2
import numpy as np
import supervision as sv
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ultralytics import YOLO

from signal_controller import (
    MAX_GREEN_SECONDS,
    SMOOTHING_WINDOW,
    allocate_green_time,
    check_congestion,
    smoothed_queue_counts,
)
from site_config import LANE_ZONES, MODEL_PATH, VIDEO_PATH

# ---------------- CONFIG ----------------

PROCESS_EVERY_N_FRAMES = 2   # skip frames for CPU speed (video still plays at real speed)
INFERENCE_SIZE = 640         # YOLO resizes internally; boxes come back in original coordinates
CONFIDENCE = 0.25
VEHICLE_CLASS_IDS = [2, 3, 5, 7]   # COCO: car, motorcycle, bus, truck

STREAM_WIDTH = 960           # width of the frames sent to the browser
JPEG_QUALITY = 70

# BGR colours, one per lane
LANE_COLORS = [(255, 170, 60), (90, 200, 90), (60, 170, 255), (200, 100, 220)]

# -----------------------------------------

_lock = threading.Lock()
_stop = threading.Event()
_latest_jpeg = None
_frame_id = 0
_state = {"status": "starting"}


def detect_vehicles(model, frame):
    results = model(
        frame,
        imgsz=INFERENCE_SIZE,
        conf=CONFIDENCE,
        classes=VEHICLE_CLASS_IDS,
        verbose=False,
    )[0]
    return sv.Detections.from_ultralytics(results)


def zone_mask(zone, detections):
    if len(detections) == 0:
        return np.zeros(0, dtype=bool)
    return zone.trigger(detections=detections)


def draw_overlay(frame, counts, detections, inside_any):
    scale = frame.shape[1] / 1280
    font_scale = max(0.5, 0.75 * scale)
    thickness = max(1, int(round(2 * scale)))

    # translucent lane fills
    overlay = frame.copy()
    for i, poly in enumerate(LANE_ZONES.values()):
        cv2.fillPoly(overlay, [poly.astype(np.int32)], LANE_COLORS[i % len(LANE_COLORS)])
    frame = cv2.addWeighted(overlay, 0.22, frame, 0.78, 0)

    # lane outlines + live counts
    for i, (name, poly) in enumerate(LANE_ZONES.items()):
        color = LANE_COLORS[i % len(LANE_COLORS)]
        cv2.polylines(frame, [poly.astype(np.int32)], True, color, thickness)

        label = f"{name.replace('_', ' ')}: {counts[name]}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        x, y = poly[poly[:, 1].argmin()]
        x, y = int(x), max(int(y) - 10, th + 8)
        cv2.rectangle(frame, (x - 4, y - th - 6), (x + tw + 4, y + 6), (0, 0, 0), -1)
        cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

    # vehicle boxes: green when inside a lane, grey otherwise
    for (x1, y1, x2, y2), inside in zip(detections.xyxy, inside_any):
        color = (80, 230, 120) if inside else (150, 150, 150)
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)

    return frame


def pipeline_worker():
    global _latest_jpeg, _frame_id

    model = YOLO(MODEL_PATH)
    zones = {name: sv.PolygonZone(polygon=poly) for name, poly in LANE_ZONES.items()}

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        with _lock:
            _state.clear()
            _state.update({"status": "error", "message": f"Could not open video: {VIDEO_PATH}"})
        return

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    target_dt = PROCESS_EVERY_N_FRAMES / source_fps   # keeps playback at real-time speed

    history = []
    processed = 0
    fps = 0.0
    failed_reads = 0

    while not _stop.is_set():
        t0 = time.time()

        ok, frame = cap.read()
        if not ok:
            failed_reads += 1
            if failed_reads > 5:
                with _lock:
                    _state.clear()
                    _state.update({"status": "error", "message": f"Could not read frames from {VIDEO_PATH}"})
                return
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)   # loop the video
            history.clear()
            continue
        failed_reads = 0

        for _ in range(PROCESS_EVERY_N_FRAMES - 1):
            cap.grab()

        detections = detect_vehicles(model, frame)

        counts = {}
        inside_any = np.zeros(len(detections), dtype=bool)
        for name, zone in zones.items():
            mask = zone_mask(zone, detections)
            counts[name] = int(mask.sum())
            inside_any |= mask

        # Phase 2 logic, unchanged
        history.append({"queue_counts": counts})
        del history[:-SMOOTHING_WINDOW]
        avg_counts = smoothed_queue_counts(history, window=SMOOTHING_WINDOW)
        green_times = allocate_green_time(avg_counts)
        congested, total = check_congestion(avg_counts)

        annotated = draw_overlay(frame, counts, detections, inside_any)
        h, w = annotated.shape[:2]
        if w > STREAM_WIDTH:
            annotated = cv2.resize(annotated, (STREAM_WIDTH, int(h * STREAM_WIDTH / w)))
        encoded_ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

        processed += 1
        with _lock:
            if encoded_ok:
                _latest_jpeg = buf.tobytes()
                _frame_id += 1
            _state.clear()
            _state.update({
                "status": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "frame": processed,
                "fps": round(fps, 1),
                "live_counts": counts,
                "avg_queue_counts": {k: round(v, 2) for k, v in avg_counts.items()},
                "green_time_seconds": green_times,
                "priority_lane": max(green_times, key=green_times.get),
                "congested": congested,
                "total_vehicles": total,
                "reroute_suggested": congested,
                "max_green_seconds": MAX_GREEN_SECONDS,
            })

        spare = target_dt - (time.time() - t0)
        if spare > 0:
            time.sleep(spare)

        loop_dt = max(time.time() - t0, 1e-3)
        fps = 1.0 / loop_dt if fps == 0.0 else 0.9 * fps + 0.1 * (1.0 / loop_dt)

    cap.release()


async def mjpeg_frames():
    last_id = -1
    while True:
        with _lock:
            jpeg, fid = _latest_jpeg, _frame_id
        if jpeg is not None and fid != last_id:
            last_id = fid
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                + str(len(jpeg)).encode()
                + b"\r\n\r\n"
                + jpeg
                + b"\r\n"
            )
        await asyncio.sleep(0.02)


def _warm_route_plan():
    """Prepare the road graph in the background so the first map load is fast."""
    try:
        import reroute
        reroute.get_plan()
        print("Route engine ready.")
    except Exception as e:   # never stop the video server because routing is not ready
        print(f"Route engine not ready: {e}")


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=pipeline_worker, daemon=True).start()
    threading.Thread(target=_warm_route_plan, daemon=True).start()
    yield
    _stop.set()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/latest")
def get_latest():
    with _lock:
        return dict(_state)


@app.get("/api/route")
def get_route(congested: Optional[bool] = None):
    """Dijkstra route: through the intersection when free, around it when congested."""
    if congested is None:
        with _lock:
            congested = bool(_state.get("congested", False))
    try:
        import reroute
        return reroute.get_route(congested)
    except Exception as e:
        return {"error": str(e), "route": []}


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
