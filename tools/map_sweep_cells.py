#!/usr/bin/env python3
"""Map the pre-registered sweep_cells_v1.csv to queue cells (sim/overrides.py), using the T06 sign table.

    python3 -I tools/map_sweep_cells.py [sweep_cells_v1.csv] [--priorities 1,2,3]
Writes config/cells_sweep_v1.csv (the queue's format) and config/cells_sweep_v1_mapping.json (every row,
its physical level and the code override it maps to; priority-4 rows are listed as "not mapped yet").

Directions (config/sign_table.json, measured on Oct 24):
  tilt_down_deg  -> camera code pitch +, radians (+10 deg code = 9.995 deg down; the lens sits on the axis)
  rack_y_cm      -> rack code y + (toward the camera wall), metres
  rack_x_cm      -> rack code x + (toward the back wall), metres
  cam_yaw_code_deg -> camera code yaw +, radians (code units; +10 deg code = 16.7 deg physical pan)
  cam_up_cm      -> camera code z + (up), metres (wall limit +4.1 cm)
  light_ev       -> exposure_ev, absolute EV (centre -1)
  ext_hfov_deg   -> camera_focal_mm = 2.4 / (2 tan(hfov/2)) with horizontalAperture 2.4 mm
  nominal        -> {} (everything at the centre)
  course_eval_as_shipped -> the Eval task unchanged (--as_shipped)
Seeds: "a-b" -> seed_base a, n = b - a + 1; "a-b x k repeats" -> seed_base a, seed_mod (b - a + 1), n as given.
"""
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
CK = "aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left/checkpoint-10000"
TASK = "Lerobot-So101-Teleop-Vials-To-Rack-Eval"
HAP_MM = 2.4


def overrides_for(factor, level):
    if factor == "nominal":
        return {}, "all at centre"
    if factor == "course_eval_as_shipped":
        return {}, "as shipped (no overrides)"
    v = float(level)
    if factor == "tilt_down_deg":
        return {"camera": {"pitch": math.radians(v)}}, f"camera code pitch {math.radians(v):+.6f} rad"
    if factor == "rack_y_cm":
        return {"rack": {"y": v / 100}}, f"rack code y {v / 100:+.4f} m"
    if factor == "rack_x_cm":
        return {"rack": {"x": v / 100}}, f"rack code x {v / 100:+.4f} m"
    if factor == "cam_yaw_code_deg":
        return {"camera": {"yaw": math.radians(v)}}, f"camera code yaw {math.radians(v):+.6f} rad"
    if factor == "cam_up_cm":
        if v > 4.1:
            raise ValueError(f"camera up {v} cm is past the 4.1 cm ceiling limit")
        return {"camera": {"z": v / 100}}, f"camera code z {v / 100:+.4f} m"
    if factor == "light_ev":
        return {"exposure_ev": v}, f"exposure {v:+.2f} EV (absolute)"
    if factor == "ext_hfov_deg":
        f = HAP_MM / (2 * math.tan(math.radians(v) / 2))
        return {"camera_focal_mm": round(f, 6)}, f"external focal {f:.6f} mm (hAp {HAP_MM} mm)"
    raise KeyError(f"no mapping for factor {factor!r}")


def seeds_of(s, n):
    m = re.fullmatch(r"\s*(\d+)-(\d+)(?:\s*x\s*(\d+)\s*repeats?)?\s*", s)
    if not m:
        raise ValueError(f"seed spec {s!r}")
    a, b, k = int(m.group(1)), int(m.group(2)), m.group(3)
    span = b - a + 1
    if k:
        assert span * int(k) == n, f"{s} vs {n} episodes"
        return a, span
    assert span == n, f"{s} vs {n} episodes"
    return a, 0


def main():
    args = sys.argv[1:]
    src = Path(args[0]) if args and not args[0].startswith("--") else GTC.parent / "sweep_cells_v1.csv"
    pri = {int(x) for x in (args[args.index("--priorities") + 1] if "--priorities" in args else "1,2,3").split(",")}
    raw = src.read_bytes()
    rows = list(csv.DictReader(raw.decode().splitlines()))
    out, mapping = [], []
    for r in rows:
        p = int(r["priority"])
        rec = {"cell_id": r["cell_id"], "priority": p, "factor": r["factor"], "level": r["level"], "unit": r["unit"],
               "episodes": int(r["episodes"]), "seeds": r["seeds"]}
        if p not in pri:
            rec["mapped"] = "not mapped yet (priority 4 waits for the Oct 26 measurements)" if p == 4 else "skipped"
            mapping.append(rec)
            continue
        ov, how = overrides_for(r["factor"], r["level"])
        base, smod = seeds_of(r["seeds"], int(r["episodes"]))
        rec.update({"overrides": ov, "code": how, "seed_base": base, "seed_mod": smod,
                    "as_shipped": r["factor"] == "course_eval_as_shipped"})
        mapping.append(rec)
        out.append({"cell_id": r["cell_id"], "priority": p, "lane": "A", "checkpoint": CK, "task": TASK,
                    "overrides_json": json.dumps(ov), "n_episodes": int(r["episodes"]), "seed_base": base,
                    "seed_mod": smod, "as_shipped": int(rec["as_shipped"]), "notes": f"{r['factor']} {r['level']} {r['unit']}: {how}"})
    dst = GTC / "config" / "cells_sweep_v1.csv"
    with open(dst, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    meta = {"source": str(src.name), "source_md5": hashlib.md5(raw).hexdigest(), "priorities": sorted(pri),
            "cells": len(out), "episodes": sum(c["n_episodes"] for c in out), "rows": mapping}
    (GTC / "config" / "cells_sweep_v1_mapping.json").write_text(json.dumps(meta, indent=1))
    print(f"{src.name} md5 {meta['source_md5']}: {meta['cells']} cells, {meta['episodes']} episodes (priorities {sorted(pri)})")
    for rec in mapping:
        print(f"  P{rec['priority']} {rec['cell_id']:26s} {rec.get('code', rec.get('mapped'))}"
              + (f" | seeds {rec['seed_base']}.. mod {rec['seed_mod']}" if "seed_base" in rec else ""))


if __name__ == "__main__":
    main()
