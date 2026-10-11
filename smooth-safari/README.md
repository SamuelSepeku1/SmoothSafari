# Smooth Safari - updated project

Two folders go side by side, as on your machine:

    SmoothSafari/
      SSproject/          Python backend (copy these files in)
      dashboard-react/    React dashboard (copy these files in)

## The only things you edit

1. `SSproject/site_config.py`
   - `VIDEO_PATH`: your fixed-camera video
   - `LANE_ZONES`: paste YOUR zones (the ones in there are placeholders)
   - `INTERSECTION_NAME / LAT / LNG`: your intersection
2. `dashboard-react/src/config.js`: the same `lat` / `lng` (fallback for the map)

Do not overwrite your real LANE_ZONES with the placeholders. If you already have them in your
old Vehicle_counter.py or liveserver.py, copy that block into `site_config.py`.

## Run order (first time)

    # backend, inside SSproject with your venv active
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements.txt

    python pick_coordinates.py            # only if you need new lane zones -> paste into site_config.py
    python reroute.py --build-graph       # downloads the road map ONCE (needs internet)
    python liveserver.py                  # detection + signal plan + routes on port 8000

    # dashboard, in a second terminal
    cd dashboard-react
    npm install
    npm run dev                           # open the address it prints (usually http://localhost:5173)

Next runs: `python liveserver.py` and `npm run dev`. Re-run `reroute.py --build-graph`
only if you change the intersection coordinates.

## What each file does

| File | Role |
|---|---|
| `site_config.py` | video, lane zones, intersection coordinates (single source of truth) |
| `pick_coordinates.py` | click lane corners on a video frame, prints LANE_ZONES |
| `Vehicle_counter.py` | Phase 1, offline: YOLOv8n per-lane counts -> `queue_counts.json` |
| `signal_controller.py` | Phase 2: smoothed queues -> green times + congestion flag (also imported by liveserver) |
| `reroute.py` | Phase 4: Dijkstra routes on the OpenStreetMap graph |
| `liveserver.py` | live detection + signal plan + `/api/route`; serves the dashboard |
| `dashboard-react/` | video feed, lane bars, status banner, route map, architecture diagram |

`Vehicle_counter.py` and `signal_controller.py` run on their own for testing. The live
dashboard does not need them: `liveserver.py` does the same work in memory.

## How the routing behaves

- Not congested: Dijkstra's shortest path from A to B, chosen so it passes through the intersection (blue).
- Congested: Dijkstra again with every road near the intersection made 1000x more expensive, so it takes another path (red).
- The dashboard sends the live congestion flag; no `route.json` or manual step is needed.

To see the red route in a demo, lower `CONGESTION_THRESHOLD` in `signal_controller.py`
(for example 8), then restart `liveserver.py`.
