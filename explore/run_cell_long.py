#!/usr/bin/python3 -I
"""explore-v3 cell runner for sim/run_queue.py --runner (the registered queue and sweep_eval stay untouched).

    GTC_Q_DEFAULT_EP_S=200 GTC_Q_CELLS=config/explore_v3_cells.csv \\
        python3 -I sim/run_queue.py run --cells config/explore_v3_cells.csv --results-subdir explore_v3 \\
        --runner explore/run_cell_long.py
The queue calls this with (cell_id, start_episode, n_episodes). It builds the same command the queue builds for a
normal cell (sim/run_queue.py run_cell), with explore/sweep_eval_long.py instead of sim/sweep_eval.py, the same
container name (the queue's watchdog kills gtc-cell-<cell>), and the queue's timeout formula
STARTUP_S + remaining episodes x DEFAULT_EP_S x 1.5 (the queue does not wrap a runner in timeout itself).
In runner mode the queue skips its server ping, so the server is pinged here first (exit with "[EXIT] code 3").
"""
import csv
import os
import subprocess
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]


def main(cell, k, n):
    cells = {r["cell_id"]: r for r in csv.DictReader(open(GTC / os.environ.get("GTC_Q_CELLS", "config/explore_v3_cells.csv")))}
    c = cells[cell]
    ping = subprocess.run([str(GTC / ".venv" / "bin" / "python"), "-I", str(GTC / "sim" / "server_ping.py"), "--timeout", "10", "--wait", "120"])
    if ping.returncode != 0:
        print("[EXIT] code 3 (policy server did not answer)", flush=True)
        return 3
    startup = float(os.environ.get("GTC_Q_STARTUP_S", 150))
    ep_s = float(os.environ.get("GTC_Q_DEFAULT_EP_S", 45.0))
    tmo = int(startup + (int(n) - int(k)) * ep_s * 1.5)
    sub = os.environ.get("GTC_Q_SUBDIR", "explore_v3")
    cmd = ["timeout", "-k", "60", str(tmo), str(GTC / "sim" / "run_sim.sh"), f"gtc-cell-{cell}"[:60],
           "python", "/workspace/gtc/explore/sweep_eval_long.py", "--headless", "--cell_id", cell,
           "--overrides", c["overrides_json"] or "{}", "--n_episodes", n, "--start_episode", k,
           "--seed_base", c["seed_base"], "--task", c.get("task") or "Lerobot-So101-Teleop-Vials-To-Rack-Eval",
           "--checkpoint", c.get("checkpoint", ""), "--results", f"/workspace/gtc/results/{sub}",
           "--media", f"/workspace/gtc/media/{sub}"]
    if int(c.get("seed_mod") or 0):
        cmd += ["--seed_mod", str(int(c["seed_mod"]))]
    print(f"[RUNNER] timeout {tmo}s: {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
