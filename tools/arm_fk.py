#!/usr/bin/env python3
"""Forward kinematics of the course's SO-101 USD (SO-ARM101-USD.usd) and its visual meshes at any joint state.

Chain (UsdPhysics revolute joints, axis Z): base -Rotation-> shoulder -Pitch-> upper_arm -Elbow-> lower_arm
-Wrist_Pitch-> wrist -Wrist_Roll-> gripper -Jaw-> jaw. A joint's frame is (localPos0, localRot0) in body0 and
(localPos1, localRot1) in body1, so child = parent * T(lp0, lr0) * Rz(q) * T(lp1, lr1)^-1. The base is placed at the
course's robot root (frames_sim.json robot.root: (-0.05, 0, 0), yaw 90 deg). Joint values are the sim's joint
positions in rad (Rotation, Pitch, Elbow, Wrist_Pitch, Wrist_Roll, Jaw), e.g. a trace record's joint_pos_rad.

    .venv/bin/python -I tools/arm_fk.py check          # FK link origins vs the sim trace's recorded body positions
"""
import json
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
USD = GTC.parent / "Sim-to-Real-SO-101-Workshop" / "source" / "sim_to_real_so101" / "assets" / "usd" / "SO-ARM101-USD.usd"
JOINTS = ["Rotation", "Pitch", "Elbow", "Wrist_Pitch", "Wrist_Roll", "Jaw"]
LINKS = ["base", "shoulder", "upper_arm", "lower_arm", "wrist", "gripper", "jaw"]


def q2R(q):
    w, x, y, z = q
    n = np.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def T(R, t):
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, t
    return M


def Rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def load_chain(usd=USD):
    from pxr import Usd, UsdPhysics
    st = Usd.Stage.Open(str(usd))
    chain = []
    for name in JOINTS:
        j = UsdPhysics.Joint(st.GetPrimAtPath(f"/so101_new_calib/joints/{name}"))
        g = lambda a: np.array(a.Get(), float)
        lr0, lr1 = j.GetLocalRot0Attr().Get(), j.GetLocalRot1Attr().Get()
        chain.append((name, str(j.GetBody0Rel().GetTargets()[0]).split("/")[-1], str(j.GetBody1Rel().GetTargets()[0]).split("/")[-1],
                      T(q2R([lr0.GetReal(), *lr0.GetImaginary()]), g(j.GetLocalPos0Attr())),
                      T(q2R([lr1.GetReal(), *lr1.GetImaginary()]), g(j.GetLocalPos1Attr()))))
    return st, chain


def fk(chain, q_rad, base_pos=(-0.05, 0.0, 0.0), base_quat=(0.7071068, 0.0, 0.0, 0.7071068)):
    """{link: 4x4 pose in E} for the six joint angles (rad)."""
    pose = {"base": T(q2R(base_quat), np.asarray(base_pos, float))}
    for (name, b0, b1, J0, J1), q in zip(chain, q_rad):
        pose[b1] = pose[b0] @ J0 @ T(Rz(q), np.zeros(3)) @ np.linalg.inv(J1)
    return pose


def link_meshes(st):
    """{link: triangles (n, 3, 3) in the link frame}, visual meshes only."""
    from pxr import Usd, UsdGeom
    xc = UsdGeom.XformCache()
    out = {}
    for link in LINKS:
        lp = st.GetPrimAtPath(f"/so101_new_calib/{link}")
        Ml = np.array(xc.GetLocalToWorldTransform(lp), float)
        R_l, t_l = Ml[:3, :3].T, Ml[3, :3]
        tris = []
        for p in Usd.PrimRange(st.GetPrimAtPath(f"/so101_new_calib/{link}/visuals"), Usd.TraverseInstanceProxies()):
            if p.GetTypeName() == "Mesh" and UsdGeom.Imageable(p).ComputeVisibility() != UsdGeom.Tokens.invisible:
                m = UsdGeom.Mesh(p)
                pts = np.array(m.GetPointsAttr().Get(), float)
                M = np.array(xc.GetLocalToWorldTransform(p), float)
                w = pts @ M[:3, :3] + M[3, :3]
                cnt = np.array(m.GetFaceVertexCountsAttr().Get())
                idx = np.array(m.GetFaceVertexIndicesAttr().Get())
                starts = np.r_[0, np.cumsum(cnt)[:-1]]
                tri = [np.c_[idx[s] * np.ones(c - 2, int), idx[s + 1:s + c - 1], idx[s + 2:s + c]] for s, c in zip(starts, cnt) if c >= 3]
                tris.append((w[np.concatenate(tri)] - t_l) @ R_l)      # file world -> link frame
        out[link] = np.concatenate(tris) if tris else np.zeros((0, 3, 3))
    return out


def check():
    st, chain = load_chain()
    recs = [r for r in (json.loads(l) for l in open(GTC / "results" / "sim" / "trace" / "L00_nominal.jsonl")) if "joint_pos_rad" in r]
    worst = 0.0
    for r in recs[:40]:
        pose = fk(chain, r["joint_pos_rad"])
        for link in LINKS:
            worst = max(worst, float(np.linalg.norm(pose[link][:3, 3] - np.array(r["bodies"][link]))))
    print(f"FK vs the trace's body positions, {min(40, len(recs))} records x {len(LINKS)} links: worst {1000 * worst:.3f} mm")
    return 0 if worst < 1e-3 else 1


if __name__ == "__main__":
    sys.exit(check() if sys.argv[1:] == ["check"] else 2)
