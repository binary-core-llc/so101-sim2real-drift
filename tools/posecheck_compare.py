#!/usr/bin/env python3
"""Pose check, real vs sim (V28-01 follow-up): where does the real arm stand against the sim arm at the same joint
values, seen through the real front camera?

    .venv/bin/python -I tools/posecheck_compare.py --posecheck results/real/posecheck/L00.jsonl --pose r0 [--out DIR]
For each pose-check record (real/pose_check.py: the joint values the real arm reached, and its front frame): the sim
arm is placed at those values through the course's conversion (lerobot_interface.py get_mapped_actions_vectorized:
v in -100..100 -> joint_min..joint_max deg; gripper 0..100) by tools/arm_fk.py, and its visual meshes are rendered
into the real camera (measured pose --pose, C920 focal, the ideal pinhole of the undistorted frame). The real arm's
orange parts are segmented in the undistorted frame. The image shift that best lines the sim's wrist + gripper + jaw
silhouette up with the real orange parts (maximum overlap within +-60 px) is the arm's offset in the image; it is
converted to mm at the gripper's depth. Overlay: sim silhouette outlines (magenta: wrist, gripper, jaw; cyan: the
rest) on the frame. Writes <out>/posecheck_compare.json and one PNG per record.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "sim"), str(GTC / "tools")]

import arm_fk as A  # noqa: E402
import image_matched_pose as M  # noqa: E402

COURSE = {"shoulder_pan.pos": (-110, 110), "shoulder_lift.pos": (-100, 100), "elbow_flex.pos": (-100, 90),
          "wrist_flex.pos": (-95, 95), "wrist_roll.pos": (-160, 160), "gripper.pos": (-10, 100)}
DISTAL = ("wrist", "gripper", "jaw")


def to_sim_rad(v):
    out = []
    for k, (lo, hi) in COURSE.items():
        n = v[k] / 100.0 if k == "gripper.pos" else (v[k] + 100.0) / 200.0
        out.append(np.radians(lo + n * (hi - lo)))
    return out


class _Tris:
    def __init__(self, tris, cls):
        self.tris, self.cls, self.closed = tris, cls, np.zeros(len(cls), bool)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--posecheck", required=True)
    ap.add_argument("--pose", required=True, help="results/poses/<tag>.json of the camera when the frames were taken")
    ap.add_argument("--out", default=str(GTC / "results" / "real" / "posecheck_compare"))
    ap.add_argument("--scale", help="JSON {joint: factor}: the sim arm at v * factor (e.g. the real calibrated range over the "
                    "sim range, entry 1's table): tests whether the range difference explains the offset")
    ap.add_argument("--tag", default="", help="suffix for the output names")
    a = ap.parse_args(argv)
    pr = json.loads((GTC / "results" / "poses" / f"{a.pose}.json").read_text())
    R, C = np.array(pr["R_E_cv"]), np.array(pr["C_E_m"])
    j = json.loads((GTC / "config" / "c920_intrinsics.json").read_text())
    K, dist = np.array(j["K"]), np.array(j["dist"]).ravel()
    f = float(K[0, 0])
    Ki = np.array([[f, 0, 320.0], [0, f, 240.0], [0, 0, 1]])
    mx, my = cv2.initUndistortRectifyMap(K, dist, None, Ki, (640, 480), cv2.CV_32FC1)
    st, chain = A.load_chain()
    meshes = A.link_meshes(st)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for line in open(a.posecheck):
        r = json.loads(line)
        scale = json.loads(a.scale) if a.scale else {}
        v_pol = r.get("reached_policy") or r["reached"]           # with a joint map: the policy's units
        q = to_sim_rad({k: v * scale.get(k, 1.0) for k, v in v_pol.items()})
        pose = A.fk(chain, q)
        tris, cls = [], []
        for i, link in enumerate(A.LINKS):
            P = pose[link]
            t = meshes[link] @ P[:3, :3].T + P[:3, 3]
            tris.append(t)
            cls.append(np.full(len(t), i + 1, np.int8))
        lab = M.render(_Tris(np.concatenate(tris), np.concatenate(cls)), R, C, f, 640, 480)
        distal = np.isin(lab, [A.LINKS.index(k) + 1 for k in DISTAL])
        img = cv2.remap(cv2.imread(str(GTC / r["front"]))[:, :, ::-1], mx, my, cv2.INTER_LINEAR)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
        orange = (((h <= 19) | (h >= 170)) & (s >= 120) & (v >= 50)).astype(np.float32)
        ys, xs = np.nonzero(distal)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        S = 60
        pad = cv2.copyMakeBorder(orange, S, S, S, S, cv2.BORDER_CONSTANT, value=0)
        cc = cv2.matchTemplate(pad[y0:y1 + 2 * S, x0:x1 + 2 * S], distal[y0:y1, x0:x1].astype(np.float32), cv2.TM_CCORR)
        dy, dx = np.unravel_index(int(np.argmax(cc)), cc.shape)
        dx, dy = int(dx) - S, int(dy) - S
        cover0 = float((orange * distal).sum() / distal.sum())
        cover1 = float(cc.max() / distal.sum())
        # the shift in mm at the gripper's depth (the gripper link origin's camera z)
        g = pose["gripper"][:3, 3]
        zc = float((g - C) @ R[:, 2])
        u0 = np.array([xs.mean(), ys.mean()])
        rays = [np.array([(u[0] - 320) / f, (u[1] - 240) / f, 1.0]) * zc for u in (u0, u0 + (dx, dy))]
        dE = 1000 * (R @ (rays[1] - rays[0]))
        rec = {"chunk": r["chunk"], "reached": r["reached"], "sim_deg": [round(float(np.degrees(x)), 2) for x in q],
               "shift_px": [dx, dy], "shift_E_mm_at_gripper_depth": [round(float(x), 1) for x in dE],
               "distal_covered_by_real_orange": {"as_is": round(cover0, 3), "after_shift": round(cover1, 3)},
               "operator_note": r.get("operator_note")}
        rows.append(rec)
        vis = img.copy()
        for m, col in ((lab > 0, (0, 255, 255)), (distal, (255, 0, 255))):
            cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(vis, cs, -1, col, 1)
        moved = cv2.warpAffine(distal.astype(np.uint8), np.float32([[1, 0, dx], [0, 1, dy]]), (640, 480),
                               flags=cv2.INTER_NEAREST) > 0
        cs, _ = cv2.findContours(moved.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(vis, cs, -1, (0, 255, 0), 1)
        cv2.imwrite(str(out_dir / f"{Path(a.posecheck).stem}_chunk{r['chunk']:03d}_{a.pose}{a.tag}.png"), vis[:, :, ::-1])
        print(f"chunk {r['chunk']}: sim arm (wrist, gripper, jaw) vs the real orange parts: shift {dx:+d} / {dy:+d} px "
              f"= E ({dE[0]:+.1f}, {dE[1]:+.1f}, {dE[2]:+.1f}) mm at the gripper depth; covered {cover0:.2f} as is, "
              f"{cover1:.2f} shifted")
    (out_dir / f"posecheck_compare{a.tag}.json").write_text(json.dumps({"pose": a.pose, "posecheck": a.posecheck,
                                                                       "scale": a.scale, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
