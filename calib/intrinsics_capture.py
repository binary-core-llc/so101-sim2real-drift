#!/usr/bin/env python3
"""Guided capture for the C920x lens calibration (B section 3.2), with a live coverage map.

    .venv/bin/python -I calib/intrinsics_capture.py --set A          # then a second, independent set: --set B
    .venv/bin/python -I calib/intrinsics_capture.py --set A --resume --missing-corner bottom-left
Keys: SPACE save the view (only if >= 12 corners and the image is still), u undo the last view, q quit.
Saves media/calib/intrinsics/<set>/view_NNN.png (lossless, RGB as LeRobot returns it) and
results/calib/intrinsics_<set>_capture.json (camera identity, lock readback, per-view corner count and tilt).
A set folder that already holds views is never overwritten: without --resume the tool stops. --resume (Nov 7) keeps
the saved views, takes their stats from the capture JSON (recomputed from the image where the JSON lacks one), numbers
new views after them, re-applies and reads back the camera lock, and records each session; u never removes a view
saved before the resume. The JSON being replaced is kept as intrinsics_<set>_capture_before_<utc>.json.

Requirements shown live (B 3.2, coverage per set): >= 45 views captured so that >= 30 remain after rejection;
corners seen in all 9 cells of a 3x3 grid; within 40 px of each image corner in >= 3 views; >= 12 tilted views
(>= 25 deg), >= 4 about each image axis. Tilt uses a rough K (fx --fx-guess, centred) only for this display.
Live per image corner (Nov 7): the nearest ChArUco dot now, in px, green within 80 px, with the saved count, so the
board is placed by the number. Dots are shown down to 4 corners; SPACE still needs 12. --missing-corner marks a corner
accepted as unreachable (display only; the solve's option of the same name decides).
"""
import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock
import capture
import live
from charuco import Detector

GTC = Path(__file__).resolve().parents[1]
W, H = 640, 480
MIN_CORNERS, TARGET_VIEWS, MIN_KEEP = 12, 45, 30
TILT_DEG, MIN_TILTED, MIN_PER_AXIS, CORNER_PX, CORNER_VIEWS = 25.0, 12, 4, 40, 3
CORNER_PX_WARN = 80     # B 3.2 asks 40 px; the outermost ChArUco corner sits one square (~25-35 px) inside the board
                        # edge, so 40 px needs the board's corner almost on the image corner. 80 px = WARN band.
CORNER_NAMES = ("top-left", "top-right", "bottom-left", "bottom-right")     # the order of view_stats' corner lists
CORNER_XY = ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1))
LIVE_MIN_CORNERS = 4    # dots shown live from this many corners (SPACE still needs MIN_CORNERS)


def nearest_dots(det):
    """Nearest detected ChArUco dot to each image corner (px), or None per corner when nothing is detected."""
    if det is None:
        return [None] * 4
    return [float(np.hypot(det["img"][:, 0] - cx, det["img"][:, 1] - cy).min()) for cx, cy in CORNER_XY]


def view_stats(det, K):
    pts = det["img"]
    cells = {(min(2, int(x // (W / 3))), min(2, int(y // (H / 3)))) for x, y in pts}
    near = [float(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy).min()) for cx, cy in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1))]
    zones = {i for i, dmin in enumerate(near) if dmin <= CORNER_PX}
    zones_warn = {i for i, dmin in enumerate(near) if dmin <= CORNER_PX_WARN}
    tilt, axis = 0.0, None
    if len(pts) >= 6:
        ok, rv, _ = cv2.solvePnP(det["obj"], pts, K, None, flags=cv2.SOLVEPNP_IPPE)
        if ok:
            n = cv2.Rodrigues(rv)[0][:, 2]
            tilt = math.degrees(math.acos(min(1.0, abs(n[2]))))
            axis = "y" if abs(n[0]) > abs(n[1]) else "x"
    return {"n": int(len(pts)), "cells": sorted(cells), "zones": sorted(zones), "zones_warn": sorted(zones_warn),
            "corner_dist_px": [round(x, 1) for x in near], "tilt_deg": round(tilt, 1),
            "tilt_axis": axis if tilt >= TILT_DEG else None}


def coverage(stats):
    cells = np.zeros((3, 3), int)
    zones, zones_warn = [0, 0, 0, 0], [0, 0, 0, 0]
    for s in stats:
        for cx, cy in s["cells"]:
            cells[cy, cx] += 1
        for z in s["zones"]:
            zones[z] += 1
        for z in s.get("zones_warn", []):
            zones_warn[z] += 1
    tilted = [s for s in stats if s["tilt_axis"]]
    return {"views": len(stats), "cells": cells.tolist(), "cells_ok": bool((cells > 0).all()), "corner_zones": zones,
            "corners_ok": all(z >= CORNER_VIEWS for z in zones), "corner_zones_80px": zones_warn,
            "corners_ok_80px": all(z >= CORNER_VIEWS for z in zones_warn), "tilted": len(tilted),
            "tilted_x": sum(s["tilt_axis"] == "x" for s in tilted), "tilted_y": sum(s["tilt_axis"] == "y" for s in tilted),
            "tilted_ok": len(tilted) >= MIN_TILTED and min(sum(s["tilt_axis"] == a for s in tilted) for a in "xy") >= MIN_PER_AXIS,
            "views_ok": len(stats) >= TARGET_VIEWS}


def draw(rgb, det, cov, near=None, missing=None):
    img = rgb.copy()
    for i in (1, 2):
        cv2.line(img, (int(i * W / 3), 0), (int(i * W / 3), H), (90, 90, 90), 1)
        cv2.line(img, (0, int(i * H / 3)), (W, int(i * H / 3)), (90, 90, 90), 1)
    for r in range(3):
        for c in range(3):
            n = cov["cells"][r][c]
            cv2.putText(img, str(n), (int(c * W / 3) + 6, int(r * H / 3) + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 255, 0) if n else (255, 60, 60), 2)
    for i, (cx, cy) in enumerate(((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1))):
        cv2.circle(img, (cx, cy), CORNER_PX, (0, 255, 0) if cov["corner_zones"][i] >= CORNER_VIEWS else (255, 60, 60), 2)
        cv2.circle(img, (cx, cy), CORNER_PX_WARN, (255, 200, 0) if cov["corner_zones_80px"][i] >= CORNER_VIEWS else (120, 60, 60), 1)
    if det is not None:
        for x, y in det["img"]:
            cv2.circle(img, (int(round(x)), int(round(y))), 3, (255, 255, 0), -1)
    for i, (lx, ly) in enumerate(((86, 150), (W - 170, 150), (86, H - 92), (W - 170, H - 92))):
        if near is None:
            break
        saved = cov["corner_zones_80px"][i]
        if missing == CORNER_NAMES[i]:
            txt, col = "accepted missing", (160, 160, 160)
        else:
            d = near[i]
            txt = "--" if d is None else f"{d:.0f} px"
            col = (160, 160, 160) if d is None else (0, 255, 0) if d <= CORNER_PX_WARN else (255, 80, 80)
        for t, c, th in ((txt, (0, 0, 0), 4), (txt, col, 2)):
            cv2.putText(img, t, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.8, c, th, cv2.LINE_AA)
        s = f"saved {saved}/{CORNER_VIEWS}"
        for c, th in (((0, 0, 0), 3), ((0, 255, 0) if saved >= CORNER_VIEWS else (255, 200, 0), 1)):
            cv2.putText(img, s, (lx, ly + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, th, cv2.LINE_AA)
    return img


def existing_views(out):
    return sorted(Path(out).glob("view_*.png"))


def meta_path(set_name, meta_dir=None):
    return Path(meta_dir or GTC / "results" / "calib") / f"intrinsics_{set_name}_capture.json"


class Session:
    def __init__(self, src, set_name, square_mm, fx_guess, out_dir=None, resume=False, meta_dir=None, missing=None):
        self.src, self.set, self.missing = src, set_name, missing
        self.det = Detector(square_mm, min_corners=MIN_CORNERS)
        self.det_live = Detector(square_mm, min_corners=LIVE_MIN_CORNERS)
        self.K = np.array([[fx_guess, 0, W / 2], [0, fx_guess, H / 2], [0, 0, 1]])
        self.out = Path(out_dir or GTC / "media" / "calib" / "intrinsics" / set_name)
        self.out.mkdir(parents=True, exist_ok=True)
        self.stats, self.files, self.frame, self.prev, self.cur, self.msg = [], [], None, None, None, ""
        self.live, self.prior_sessions, self.n_resumed = None, [], 0
        have = existing_views(self.out)
        if have and not resume:
            raise SystemExit(f"STOP: {self.out} already holds {len(have)} views; use --resume to add to them "
                             "(nothing is overwritten)")
        if resume:
            self._resume(have, meta_dir)

    def _resume(self, have, meta_dir):
        names = [f.name for f in have]
        if names != [f"view_{i:03d}.png" for i in range(len(names))]:
            raise SystemExit(f"STOP: {self.out} views are not numbered view_000..view_{len(names) - 1:03d}; not resuming")
        p = meta_path(self.set, meta_dir)
        old = json.loads(p.read_text()) if p.exists() else {}
        by_file = {v["file"]: v for v in old.get("views", [])}
        extra = sorted(set(by_file) - set(names))
        if extra:
            raise SystemExit(f"STOP: the capture JSON lists views missing from {self.out}: {extra[:5]}")
        for f in have:
            st = by_file.get(f.name)
            if st is None:                                  # no JSON entry (e.g. the window closed without q)
                det = self.det.detect(capture.load_rgb(f))
                if det is None:
                    raise SystemExit(f"STOP: {f.name} has fewer than {MIN_CORNERS} corners; not resuming")
                st = {**view_stats(det, self.K), "file": f.name, "recomputed_on_resume": True,
                      "utc": dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")}
            self.files.append(f.name)
            self.stats.append(st)
        self.prior_sessions = old.get("sessions") or ([{k: old.get(k) for k in ("lock_readback_ok", "camera", "settings")}
                                                        | {"n_views_at_end": len(old.get("views", []))}] if old else [])
        self.n_resumed = len(self.files)
        self.msg = f"resumed: {self.n_resumed} views kept, next view_{self.n_resumed:03d}"

    def step(self):
        self.prev, self.frame = self.frame, self.src.read()
        self.live = self.det_live.detect(self.frame)
        self.cur = self.live if self.live is not None and len(self.live["ids"]) >= MIN_CORNERS else None
        cov = coverage(self.stats)
        still = self.prev is not None and float(np.abs(self.frame.astype(int) - self.prev.astype(int)).mean()) < 3.0
        s = view_stats(self.cur, self.K) if self.cur is not None else None
        near = nearest_dots(self.live)
        n_live = len(self.live["ids"]) if self.live is not None else 0
        lines = [f"set {self.set}: {cov['views']}/{TARGET_VIEWS} views   now: {n_live} corners"
                 f"{'' if n_live >= MIN_CORNERS or not n_live else ' (SPACE needs %d)' % MIN_CORNERS}"
                 f"{', tilt %.0f deg' % s['tilt_deg'] if s else ''}{'' if still else ', MOVING'}",
                 f"cells {'OK' if cov['cells_ok'] else 'missing'}   image corners <=40px {cov['corner_zones']}"
                 f"  <=80px {cov['corner_zones_80px']} (>= {CORNER_VIEWS} each)",
                 f"tilted {cov['tilted']}/{MIN_TILTED} (x {cov['tilted_x']}, y {cov['tilted_y']}; >= {MIN_PER_AXIS} each)",
                 "nearest dot now (px): " + "  ".join(
                     f"{n.split('-')[0][0].upper()}{n.split('-')[1][0].upper()} " + ("skip" if n == self.missing else
                                                                                   "--" if d is None else f"{d:.0f}")
                     for n, d in zip(CORNER_NAMES, near)) + "   (green <= 80)",
                 "SPACE save   u undo   q quit   " + self.msg]
        return live.put_lines(draw(self.frame, self.live, cov, near, self.missing), lines), lines

    def save(self):
        if self.cur is None:
            self.msg = "not saved: board not found"
            return
        if self.prev is not None and float(np.abs(self.frame.astype(int) - self.prev.astype(int)).mean()) >= 3.0:
            self.msg = "not saved: hold the board still"
            return
        f = self.out / f"view_{len(self.files):03d}.png"
        capture.save_rgb(f, self.frame)
        self.files.append(f.name)
        self.stats.append({**view_stats(self.cur, self.K), "file": f.name,
                           "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
        self.msg = f"saved {f.name}"

    def undo(self):
        if len(self.files) > self.n_resumed:
            (self.out / self.files.pop()).unlink(missing_ok=True)
            self.stats.pop()
            self.msg = "removed the last view"
        elif self.files:
            self.msg = "not removed: views saved before the resume are kept"

    def write_meta(self, extra, meta_dir=None):
        cov = coverage(self.stats)
        this = {"utc_end": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "camera": self.src.identity,
                "settings": self.src.settings, "n_views_at_start": self.n_resumed, "n_views_at_end": len(self.files), **extra}
        sessions = self.prior_sessions + [this]
        locks = [s.get("lock_readback_ok") for s in sessions]
        meta = {"set": self.set, "dir": str(self.out.relative_to(GTC)) if self.out.is_relative_to(GTC) else str(self.out),
                "camera": self.src.identity, "settings": self.src.settings, "square_mm_at_capture": self.det.board.getSquareLength() * 1000,
                "fx_guess_for_tilt": float(self.K[0, 0]), "views": self.stats, "coverage": cov, **extra,
                "lock_readback_ok": None if None in locks else all(locks), "sessions": sessions,
                "missing_corner_display": self.missing}
        p = meta_path(self.set, meta_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and self.n_resumed:
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            p.rename(p.with_name(f"intrinsics_{self.set}_capture_before_{stamp}.json"))
        p.write_text(json.dumps(meta, indent=1))
        return p, cov


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--square-mm", type=float, default=30.0)
    ap.add_argument("--fx-guess", type=float, default=500.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--meta-dir", default=None, help="test only: where the capture JSON goes")
    ap.add_argument("--headless-auto", type=int, default=None, help="test only: save every detected view, N frames")
    ap.add_argument("--resume", action="store_true", help="add to the set's saved views (never overwrites them)")
    ap.add_argument("--missing-corner", choices=CORNER_NAMES, default=None,
                    help="display only: show this image corner as accepted missing")
    a = ap.parse_args(argv)
    out = Path(a.out or GTC / "media" / "calib" / "intrinsics" / a.set)
    if existing_views(out) and not a.resume:              # fail before touching the camera
        raise SystemExit(f"STOP: {out} already holds {len(existing_views(out))} views; use --resume to add to them "
                         "(nothing is overwritten)")
    lock_state = None
    if a.source.startswith("camera:"):
        lock_state = camera_lock.cmd_apply(a.source.split(":", 1)[1], write=True)
        if lock_state != 0:
            raise SystemExit("STOP: camera lock does not read back; fix it before calibrating")
    src = capture.open_source(a.source)
    ses = Session(src, a.set, a.square_mm, a.fx_guess, a.out, resume=a.resume, meta_dir=a.meta_dir, missing=a.missing_corner)
    if ses.n_resumed:
        print(f"resumed set {a.set}: {ses.n_resumed} views kept, new views start at view_{ses.n_resumed:03d}")
    try:
        if a.headless_auto:
            for _ in range(a.headless_auto):
                ses.step()
                ses.prev = ses.frame
                ses.save()
        else:
            live.run(ses.step, {"space": ses.save, "u": ses.undo, "q": lambda: "quit"}, f"intrinsics set {a.set}")
    finally:
        src.close()
    p, cov = ses.write_meta({"lock_readback_ok": lock_state == 0 if lock_state is not None else None}, a.meta_dir)
    print(f"{cov['views']} views saved in {ses.out}; cells_ok {cov['cells_ok']}, corners {cov['corner_zones']}, "
          f"tilted {cov['tilted']} (x {cov['tilted_x']}, y {cov['tilted_y']}) -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
