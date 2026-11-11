#!/usr/bin/env python3
"""Summarize a T03 run directory: startup time, seconds per episode, success, peak VRAM.
    .venv/bin/python -I sim/summarize_t03.py results/t03_<utc>
Writes <dir>/summary.json and prints a short table.
"""
import csv
import datetime as dt
import json
import re
import statistics as st
import sys
from pathlib import Path


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main(d):
    d = Path(d)
    lines = []
    for raw in (d / "eval.log").read_text(errors="replace").splitlines():
        t, _, txt = raw.partition(" ")
        try:
            lines.append((ts(t), txt))
        except ValueError:
            pass
    launch = ts((d / "launch_utc.txt").read_text().strip())

    ep_start, ep_steps, ep_rate_before = {}, {}, {}
    connected = final = evaluated = None
    for t, txt in lines:
        if connected is None and "Policy server connected" in txt:
            connected = t
        m = re.search(r"Rollout \(ep (\d+), success: ([\d.]+)%\)", txt)
        if m:
            k = int(m.group(1))
            ep_start.setdefault(k, t)
            ep_rate_before.setdefault(k, float(m.group(2)))
            n = re.search(r"\|\s*(\d+)/(\d+)", txt)
            if n:
                ep_steps[k] = max(ep_steps.get(k, 0), int(n.group(1)))
                max_steps = int(n.group(2))
        if "Success Rate:" in txt:
            final = txt.strip()
        if evaluated is None and re.search(r"Evaluated \d+ episodes", txt):
            evaluated = t

    eps = sorted(ep_start)
    per_ep = []
    for i, k in enumerate(eps):
        end = ep_start.get(k + 1) or evaluated
        if end is None:
            continue
        # successes after k episodes, from the rate shown at the start of episode k+1
        if k + 1 in ep_rate_before:
            succ_after = round(ep_rate_before[k + 1] * k / 100)
        elif final:
            succ_after = int(re.search(r"(\d+)/(\d+)", final).group(1))
        else:
            succ_after = None
        prev = round(ep_rate_before[k] * (k - 1) / 100) if k > 1 else 0
        per_ep.append({"ep": k, "wall_s": round((end - ep_start[k]).total_seconds(), 2),
                       "last_step_seen": ep_steps.get(k),
                       "success": None if succ_after is None else bool(succ_after - prev)})

    gpu = list(csv.DictReader(open(d / "gpu.csv")))
    used = [int(r["mem_used_mib"]) for r in gpu]
    total = int(gpu[0]["mem_total_mib"]) if gpu else None
    base = st.median(used[:3]) if len(used) >= 3 else None
    peak_i = max(range(len(used)), key=used.__getitem__) if used else None
    procs = {}
    for r in csv.DictReader(open(d / "gpu.procs.csv")):
        key = f'{r["pid"]} {r["process_name"]}'
        procs[key] = max(procs.get(key, 0), int(r["used_mib"]))

    walls = [e["wall_s"] for e in per_ep]
    run = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    n_req = run.get("num_episodes")
    # the course loop opens one extra progress bar (ep N+1) before it checks the count; and its final
    # "Success Rate" print can be lost (buffered stdout, then the app exits by itself)
    by_steps = sum(1 for e in per_ep if e["last_step_seen"] is not None and e["last_step_seen"] < max_steps)
    s = {
        "dir": str(d),
        "status": json.loads((d / "status.json").read_text())["status"] if (d / "status.json").exists() else None,
        "final_line": final,
        "episodes_requested": n_req,
        "episodes_completed": len(per_ep),
        "completed": n_req is not None and len(per_ep) >= n_req,
        "successes_by_steps_lt_max": by_steps,
        "max_episode_steps": max_steps,
        "successes": sum(1 for e in per_ep if e["success"]),
        "startup_s_launch_to_first_episode": round((ep_start[eps[0]] - launch).total_seconds(), 1) if eps else None,
        "startup_s_launch_to_server_connected": round((connected - launch).total_seconds(), 1) if connected else None,
        "s_per_episode": {"mean": round(st.mean(walls), 2), "median": round(st.median(walls), 2),
                          "min": min(walls), "max": max(walls)} if walls else None,
        "vram_mib": {"total": total, "baseline_before_sim": base, "peak": max(used) if used else None,
                     "peak_utc": gpu[peak_i]["utc"] if used else None,
                     "headroom_at_peak": (total - max(used)) if used else None},
        "vram_peak_per_process_mib": procs,
        "per_episode": per_ep,
    }
    (d / "summary.json").write_text(json.dumps(s, indent=2) + "\n")
    print(json.dumps({k: v for k, v in s.items() if k != "per_episode"}, indent=2))
    for e in per_ep:
        print(f'ep {e["ep"]:2d}  {e["wall_s"]:7.2f} s  steps {e["last_step_seen"]}  success {e["success"]}')


if __name__ == "__main__":
    main(sys.argv[1])
