"""
site_config.py - the ONLY file you edit for your own camera and intersection.

Every other script (Vehicle_counter.py, pick_coordinates.py, liveserver.py,
reroute.py) reads these values from here, so nothing can get out of sync.
"""

import numpy as np

# ---------------- VIDEO ----------------
VIDEO_PATH = "Vehicle Dataset Sample 2(720P_HD).mp4"   # your fixed-camera video (the camera must not move)
MODEL_PATH = "yolov8n.pt"                # downloads automatically on first run (~6 MB)

# ---------------- INTERSECTION (used for the map and the routes) ----------------
# Copy the SAME lat/lng you put in dashboard-react/src/config.js.
INTERSECTION_NAME = "Ubungo Interchange, Dar es Salaam"
INTERSECTION_LAT = -6.7924
INTERSECTION_LNG = 39.2083

# ---------------- LANE ZONES ----------------
# PASTE YOUR OWN VALUES HERE. Run `python pick_coordinates.py`, click the corners
# of each lane, and replace the placeholder block below with what it prints.
# (The four rectangles below are placeholders only.)
LANE_ZONES = {
    "lane_1": np.array([(577, 3), (618, 3), (529, 160), (359, 492), (259, 707), (10, 694), (9, 551), (423, 164), (538, 37),(573, 6)]),
    "lane_2": np.array([(617, 6), (667, 4), (661, 305), (661, 545), (656, 701), (257, 707)]),
    "lane_3": np.array([(667, 7), (717, 9), (776, 151), (896, 374), (1048, 697), (656, 704)]),
    "lane_4": np.array([(717, 5), (774, 6), (914, 132), (1272, 460), (1269, 682), (1042, 695)]),
}