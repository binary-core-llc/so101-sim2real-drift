#!/usr/bin/env python3
"""E3 real side: a front-camera photo -> E3 class images (render.E3_CLASSES) on the renderer's ideal pinhole.

1. Undistort with the measured intrinsics (K, dist) onto K_ideal = [[f, 0, 320], [0, f, 240], [0, 0, 1]], f = the
   measured fx: the photo as the renderer's square-pixel, centred camera would see it from the same pose.
2. Classes by colour (OpenCV HSV, H 0-180):
   - rack: the largest component of the trial runner's yellow band (H 20-38, S >= 90, V >= 90), plus the warm saturated
     pixels (H 12-38, S >= 200, V >= 22) joined to it within `rack_reach` px, filled to their convex hull (rack_region;
     Nov 8: before, the hole interiors went to robot and a shaded side face to mat, which biased rack y on sim scenes);
   - robot: orange-red (H <= 19 or >= 170, S >= 120, V >= 50), not rack, grown by `robot_grow` px -> don't care (the arm's
     rest pose differs from photo to photo; its dark servos look like the mat);
   - tube caps: blue (H 95-130, S >= 80, V >= 50) -> don't care;
   - mat: dark (V < `dark_v`), not rack, not robot;
   - white (floor and walls): bright and grey (V > `white_v`, S < `white_s`);
   - anything else (edges, shading between the levels) -> don't care.
3. Anything enclosed by the mat that is not rack (tubes lying on it, their caps) -> don't care.
4. Soft class maps at the working resolution: the share of each class per cell (area resize), and the cell's share of
   valid (not don't-care) pixels.
Tuned on development photos only (DEV, and the R0 frames that no hypothesis grades).
"""
import cv2
import numpy as np

PARAMS = {"dark_v": 75, "white_v": 90, "white_s": 90, "robot_grow": 24, "yellow": ([20, 90, 90], [38, 255, 255]),
          "blue": ([95, 80, 50], [130, 255, 255]), "rack_warm": ([12, 200, 22], [38, 255, 255]), "rack_reach": 48}


def ideal_K(K):
    f = float(K[0, 0])
    return np.array([[f, 0, 320.0], [0, f, 240.0], [0, 0, 1.0]])


def undistort(rgb, K, dist):
    Ki = ideal_K(K)
    mx, my = cv2.initUndistortRectifyMap(K, dist, None, Ki, (640, 480), cv2.CV_32FC1)
    return cv2.remap(rgb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0), \
        cv2.remap(np.full(rgb.shape[:2], 255, np.uint8), mx, my, cv2.INTER_NEAREST, borderValue=0) > 0


def rack_region(hsv, p=PARAMS):
    """The rack's silhouette: the largest yellow component (the core), plus the warm saturated pixels joined to it within
    `rack_reach` px (the hole interiors, orange-brown like the robot, and a shaded side face), filled to their convex hull
    (a box's silhouette is convex)."""
    yellow = cv2.inRange(hsv, np.array(p["yellow"][0], np.uint8), np.array(p["yellow"][1], np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(yellow)
    if n < 2:
        return np.zeros(hsv.shape[:2], bool)
    core = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    r = p["rack_reach"]
    near = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    warm = cv2.inRange(hsv, np.array(p["rack_warm"][0], np.uint8), np.array(p["rack_warm"][1], np.uint8))
    cand = ((warm > 0) & (near > 0)) | (core > 0)
    n, lab = cv2.connectedComponents(cand.astype(np.uint8))
    keep = np.isin(lab, np.unique(lab[core > 0]))
    out = np.zeros(core.shape, np.uint8)
    cv2.fillConvexPoly(out, cv2.convexHull(cv2.findNonZero(keep.astype(np.uint8))), 1)
    return out > 0


def classify(rgb_ideal, inside=None, p=PARAMS):
    """Full-resolution E3 class image (0 don't care, 1 white, 2 mat, 3 rack)."""
    hsv = cv2.cvtColor(rgb_ideal, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    rack = rack_region(hsv, p)
    robot = ((h <= 19) | (h >= 170)) & (s >= 120) & (v >= 50) & ~rack
    n, lab, st, _ = cv2.connectedComponentsWithStats(robot.astype(np.uint8))
    robot = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 200])
    g = p["robot_grow"]
    robot = cv2.dilate(robot.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g + 1, 2 * g + 1))) > 0
    blue = cv2.inRange(hsv, np.array(p["blue"][0], np.uint8), np.array(p["blue"][1], np.uint8)) > 0
    mat = (v < p["dark_v"]) & ~rack & ~robot
    white = (v > p["white_v"]) & (s < p["white_s"]) & ~robot
    out = np.zeros(v.shape, np.uint8)
    out[white] = 1
    out[mat] = 2
    out[rack] = 3
    out[robot | blue] = 0
    # inside the mat: whatever is not mat or rack (tubes, caps) is don't care
    filled = mat.astype(np.uint8).copy()
    cnt, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnt:
        big = max(cnt, key=cv2.contourArea)
        hull = np.zeros_like(filled)
        cv2.drawContours(hull, [big], -1, 1, -1)
        out[(hull > 0) & (out == 1)] = 0
    if inside is not None:
        out[~inside] = 0
    return out


def soft_maps(cls_full, w, h, n_cls=4):
    """(maps (n_cls, h, w) = class share per cell, valid share per cell) at the working resolution."""
    maps = np.stack([cv2.resize((cls_full == c).astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
                     for c in range(n_cls)])
    valid = 1.0 - maps[0]
    return maps, valid
