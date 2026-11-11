#!/usr/bin/env python3
"""ChArUco board model, detection, multi-frame pose, frame conventions, and a synthetic renderer for tests.

Board (docs/charuco_board.json): 8x6 squares, 30 mm squares, 22 mm markers, DICT_5X5_100, non-legacy pattern
(the PDF was made with OpenCV 5.0; setLegacyPattern(False) is required, 35/35 corners on the raster here).
The square size is the measured print value (B section 3.1); the marker scales with it.
OpenCV object frame K: origin at the grid's outer corner, x along the 8-square side, y along the 6-square
side, z into the board. Camera frame CV: x right, y down, z forward. USD camera: R_usd = R_cv * diag(1,-1,-1).
Angles follow B section 1.3: depression (+ = further down), heading (atan2(z.y, z.x) in E), roll
atan2(-x.z, -y.z) (+ = camera turned clockwise seen from behind).
"""
import json
import math
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
DOCS = GTC / "docs" if (GTC / "docs" / "charuco_board.json").exists() else GTC.parent / "docs"   # in the repo, else beside it
SPEC = json.loads((DOCS / "charuco_board.json").read_text())
SQUARE_MM = SPEC["square_m"] * 1000
MARKER_MM = SPEC["marker_m"] * 1000


def make_board(square_mm=SQUARE_MM):
    a = cv2.aruco
    b = a.CharucoBoard((SPEC["cols"], SPEC["rows"]), square_mm / 1000, MARKER_MM / SQUARE_MM * square_mm / 1000,
                       a.getPredefinedDictionary(getattr(a, SPEC["dictionary"])))
    b.setLegacyPattern(False)
    return b


class Detector:
    def __init__(self, square_mm=SQUARE_MM, min_corners=6):
        self.board = make_board(square_mm)
        self.det = cv2.aruco.CharucoDetector(self.board)
        self.min_corners = min_corners
        self.n_corners = len(self.board.getChessboardCorners())

    def detect(self, rgb_or_gray):
        g = rgb_or_gray if rgb_or_gray.ndim == 2 else cv2.cvtColor(rgb_or_gray, cv2.COLOR_RGB2GRAY)
        cc, ci, _, _ = self.det.detectBoard(g)
        if ci is None or len(ci) < self.min_corners:
            return None
        obj, img = self.board.matchImagePoints(cc, ci)
        return {"ids": ci.ravel().astype(int), "img": img.reshape(-1, 2).astype(np.float64),
                "obj": obj.reshape(-1, 3).astype(np.float64)}


# ---------------------------------------------------------------- rigid transforms (4x4, column vectors)
def T(R=np.eye(3), t=(0, 0, 0)):
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, np.ravel(t)
    return M


def Rz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_to_quat(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    q = np.array([w, x, y, z])
    return (q / np.linalg.norm(q)).tolist()


def angles(R_E_cv):
    """B section 1.3 angles of a camera (columns x_c, y_c, z_c in E), degrees."""
    x, y, z = R_E_cv[:, 0], R_E_cv[:, 1], R_E_cv[:, 2]
    return {"depression_deg": math.degrees(math.asin(-z[2])), "heading_deg": math.degrees(math.atan2(z[1], z[0])),
            "roll_deg": math.degrees(math.atan2(-x[2], -y[2]))}


def rot_from_angles(depression, heading, roll):
    """Inverse of angles(): R_E_cv from B 1.3 depression, heading and roll (degrees)."""
    d, h, r = map(math.radians, (depression, heading, roll))
    z = np.array([math.cos(d) * math.cos(h), math.cos(d) * math.sin(h), -math.sin(d)])
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.column_stack([math.cos(r) * x + math.sin(r) * y, -math.sin(r) * x + math.cos(r) * y, z])


def angle_between(R1, R2):
    return math.degrees(float(np.linalg.norm(cv2.Rodrigues(np.asarray(R1).T @ np.asarray(R2))[0])))


def delta(pose_a, pose_b):
    """b - a in B section 1.3 terms (both dicts from pose_record)."""
    d = {k: pose_b["angles"][k] - pose_a["angles"][k] for k in ("depression_deg", "heading_deg", "roll_deg")}
    d["heading_deg"] = (d["heading_deg"] + 180) % 360 - 180
    dc = np.subtract(pose_b["C_E_m"], pose_a["C_E_m"])
    Ra, Rb = np.array(pose_a["R_E_cv"]), np.array(pose_b["R_E_cv"])
    return {"tilt_down_deg": d["depression_deg"], "pan_deg": d["heading_deg"], "roll_deg": d["roll_deg"],
            "lateral_m": dc[1], "depth_m": dc[0], "height_m": dc[2], "rotation_total_deg": angle_between(Ra, Rb)}


# ---------------------------------------------------------------- pose from several frames (B section 4.4)
def average_corners(dets, min_frac=0.75):
    """Mean image position per corner ID over frames; keeps IDs seen in >= min_frac of the frames."""
    dets = [d for d in dets if d is not None]
    if not dets:
        return None
    seen = {}
    for d in dets:
        for i, p, o in zip(d["ids"], d["img"], d["obj"]):
            seen.setdefault(int(i), ([], o))[0].append(p)
    keep = sorted(i for i, (ps, _) in seen.items() if len(ps) >= min_frac * len(dets))
    return {"ids": np.array(keep), "img": np.array([np.mean(seen[i][0], axis=0) for i in keep]),
            "obj": np.array([seen[i][1] for i in keep]), "n_frames": len(dets),
            "frame_sd_px": float(np.mean([np.std(seen[i][0], axis=0).mean() for i in keep]))}


def solve_pose(det, K, dist):
    """T_cv_K (board in camera) by IPPE + LM refinement; reprojection RMS in px."""
    obj, img = det["obj"].astype(np.float64), det["img"].astype(np.float64)
    ok, rv, tv = cv2.solvePnP(obj, img, K, dist, flags=cv2.SOLVEPNP_IPPE)
    if not ok:
        return None
    rv, tv = cv2.solvePnPRefineLM(obj, img, K, dist, rv, tv)
    proj, _ = cv2.projectPoints(obj, rv, tv, K, dist)
    rms = float(np.sqrt(np.mean(np.sum((proj.reshape(-1, 2) - img) ** 2, axis=1))))
    return {"T_cv_K": T(cv2.Rodrigues(rv)[0], tv.ravel()), "rms_px": rms, "n_corners": len(obj)}


def board_in_E(path):
    """T_E_K from board_in_E.json; lengths in mm. Board axes as B 4.2: board x = +x_E, board y = -y_E (grid origin =
    the printed top-left corner, toward the back wall and the camera wall), R_E_K = Rz(yaw) * diag(1, -1, -1).
      method "sled" (B 4.2): origin (-0.0011 + d_x, 0.0208 + d_y, 0.0301 + h_K) from the robot's front lobes.
      method "mat" (fallback without the sled): the board lies flat on the mat; origin (mat_front_x + a,
      mat_left_y - b, mat_top + t), with a = mat front edge (robot side) to grid column line 0 along +x,
      b = mat left edge (camera side) to grid row line 0, t = board thickness above the mat top; mat edges from
      config/layouts.json mat_env (sim), mat top z 0.035 (B 1.2)."""
    b = json.loads(Path(path).read_text())
    if b.get("T_E_K") is not None:
        return np.array(b["T_E_K"]), b
    R = Rz(b.get("yaw_deg", 0.0)) @ np.diag([1.0, -1.0, -1.0])
    if b.get("method", "sled") == "mat":
        mat = json.loads((GTC / "config" / "layouts.json").read_text())["mat_env"]
        o = (mat["front_x"] + b["a_mm"] / 1000, mat["left_y"] - b["b_mm"] / 1000, 0.035 + b["t_mm"] / 1000)
    else:
        o = (-0.0011 + b["d_x_mm"] / 1000, 0.0208 + b["d_y_mm"] / 1000, 0.0301 + b["h_K_mm"] / 1000)
    return T(R, o), b


def pose_record(sol, T_E_K=None):
    """Camera pose: in the board frame always; in E (centre, R_E_cv, quats, angles) when T_E_K is known."""
    T_K_cv = np.linalg.inv(sol["T_cv_K"])
    rec = {"rms_px": sol["rms_px"], "n_corners": sol["n_corners"], "C_K_m": T_K_cv[:3, 3].tolist(),
           "R_K_cv": T_K_cv[:3, :3].tolist()}
    if T_E_K is not None:
        T_E_cv = T_E_K @ T_K_cv
        R = T_E_cv[:3, :3]
        rec.update({"C_E_m": T_E_cv[:3, 3].tolist(), "R_E_cv": R.tolist(), "q_wxyz_cv": rot_to_quat(R),
                    "q_wxyz_usd": rot_to_quat(R @ np.diag([1.0, -1.0, -1.0])), "angles": angles(R)})
    else:   # no board_in_E: angles as if the board lay flat with the sled's axes (R_E_K = diag(1, -1, -1))
        rec["angles_board_frame"] = angles(np.diag([1.0, -1.0, -1.0]) @ T_K_cv[:3, :3])
    return rec


# ---------------------------------------------------------------- synthetic views of the real print (tests)
def pdf_texture(dpi=300):
    """The print PDF rasterised, plus the homography from board object coordinates (m) to texture pixels."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", str(DOCS / "ChArUco_GTC_SO101_letter.pdf"),
                        f"{d}/p"], check=True)
        tex = cv2.imread(f"{d}/p.png", cv2.IMREAD_GRAYSCALE)
    det = Detector().detect(tex)
    H, _ = cv2.findHomography(det["obj"][:, :2], det["img"])
    return tex, H, len(det["ids"])


def render_view(tex, H_obj2tex, K, dist, T_cv_K, size=(640, 480), bg=110, blur=0.6, noise=1.0, rng=None, ss=4):
    """Grayscale view of the textured board plane (z = 0 in K) by a camera with K, dist (OpenCV model),
    supersampled ss x ss per pixel (box filter), so the 300 dpi texture does not alias."""
    W, Hh = size
    w, h = W * ss, Hh * ss
    u = (np.arange(w) + 0.5) / ss - 0.5                                # high-res pixel centres in output pixels
    v = (np.arange(h) + 0.5) / ss - 0.5
    uv = np.stack(np.meshgrid(u, v), -1).reshape(-1, 1, 2).astype(np.float64)
    rays = cv2.undistortPointsIter(uv, K, dist, None, None,
                                   (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 40, 1e-10)).reshape(-1, 2)
    d = np.hstack([rays, np.ones((len(rays), 1))])                    # direction in CV
    T_K_cv = np.linalg.inv(T_cv_K)
    o, D = T_K_cv[:3, 3], d @ T_K_cv[:3, :3].T                         # in the board frame
    s = -o[2] / D[:, 2]
    P = o[None, :2] + s[:, None] * D[:, :2]
    q = np.hstack([P, np.ones((len(P), 1))]) @ H_obj2tex.T
    mx, my = (q[:, 0] / q[:, 2]).reshape(h, w).astype(np.float32), (q[:, 1] / q[:, 2]).reshape(h, w).astype(np.float32)
    behind = (s <= 0).reshape(h, w)
    img = cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                    borderValue=bg).astype(np.float64)
    img[behind] = bg
    img = cv2.resize(img, (W, Hh), interpolation=cv2.INTER_AREA)
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    if noise:
        img += (rng or np.random.default_rng(0)).normal(0, noise, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def look_at_pose(cam_K, target_K, up_hint=(0, -1, 0)):
    """T_cv_K for a camera at cam_K (board frame, m) looking at target_K."""
    z = np.subtract(target_K, cam_K)
    z /= np.linalg.norm(z)
    x = np.cross(up_hint, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R_K_cv = np.column_stack([x, y, z])
    return np.linalg.inv(T(R_K_cv, cam_K))
