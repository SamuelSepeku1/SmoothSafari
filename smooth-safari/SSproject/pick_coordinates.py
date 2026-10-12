"""
Coordinate picker for lane zones.

Opens the first frame of your video (VIDEO_PATH in site_config.py). Click the
corner points of each lane; each click prints the (x, y) pixel coordinate and
marks it on the image.

Controls:
  - Left click: record a point
  - 'n'       : start a new lane
  - 'q'       : quit and print the LANE_ZONES block

Paste the printed block into site_config.py.
"""

import cv2

from site_config import VIDEO_PATH

current_lane = 1
all_lanes = {1: []}


def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        all_lanes[current_lane].append((x, y))
        print(f"lane_{current_lane}: ({x}, {y})")
        cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)
        if len(all_lanes[current_lane]) > 1:
            cv2.line(frame, all_lanes[current_lane][-2], (x, y), (0, 255, 0), 2)
        cv2.imshow("frame", frame)


cap = cv2.VideoCapture("Vehicle Dataset Sample 2(720P_HD).mp4")
ret, frame = cap.read()
cap.release()

if not ret:
    raise RuntimeError(f"Could not read a frame from {VIDEO_PATH} - check the path in site_config.py.")

print(f"Frame size: {frame.shape[1]}x{frame.shape[0]} (width x height)")
print("Click corner points for lane_1. Press 'n' for next lane, 'q' when done.\n")

cv2.imshow("frame", frame)
cv2.setMouseCallback("frame", click_event)

while True:
    key = cv2.waitKey(1) & 0xFF
    if key == ord("n"):
        current_lane += 1
        all_lanes[current_lane] = []
        print(f"\n--- Now clicking lane_{current_lane} ---")
    elif key == ord("q"):
        break

cv2.destroyAllWindows()

print("\nPaste this into site_config.py (replace the old LANE_ZONES):\n")
print("LANE_ZONES = {")
for lane_num, pts in all_lanes.items():
    if pts:
        print(f'    "lane_{lane_num}": np.array({pts}),')
print("}")
