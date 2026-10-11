"""
site_config.py - the ONLY file you edit for your own camera and intersection.

Every other script (Vehicle_counter.py, pick_coordinates.py, liveserver.py,
reroute.py) reads these values from here, so nothing can get out of sync.
"""

import numpy as np

# ---------------- VIDEO ----------------
VIDEO_PATH = "27260-362770008.mp4"   # your fixed-camera video (the camera must not move)
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
    "lane_1": np.array([(892, 30), (904, 26), (923, 87), (897, 181), (826, 360), (709, 616), (564, 940), (183, 951), (553, 492), (836, 143), (879, 68), (890, 32)]),
    "lane_2": np.array([(902, 23), (929, 22), (964, 57), (989, 160), (999, 273), (988, 467), (978, 630), (971, 842), (956, 955), (566, 948)]),
    "lane_3": np.array([(927, 22), (951, 17), (1005, 51), (1045, 94), (1088, 161), (1128, 249), (1174, 356), (1229, 515), (1276, 629), (1312, 870), (1330, 940), (960, 955)]),
    "lane_4": np.array([(949, 13), (979, 13), (1013, 38), (1050, 57), (1079, 77), (1125, 115), (1169, 156), (1229, 227), (1308, 307), (1371, 394), (1472, 509), (1545, 622), (1621, 701), (1677, 801), (1726, 873), (1757, 912), (1330, 943)]),
}