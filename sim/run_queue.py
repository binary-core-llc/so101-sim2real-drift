#!/usr/bin/env python3
"""C4: unattended sweep queue with watchdog (stdlib only, runs on the host).

    python3 -I sim/run_queue.py run    --cells config/cells_pilot.csv     (blocks; start it with setsid/nohup)
    python3 -I sim/run_queue.py status | pause | resume | stop

cells.csv columns: cell_id, priority, lane, checkpoint, task, overrides_json, n_episodes, seed_base, notes
(re-read between cells, so cells can be appended while the queue runs).

Per cell: count the finished episodes in results/sim/<cell>.jsonl, run the rest through
sim/run_sim.sh + sim/sweep_eval.py --start_episode k under `timeout`, retry twice.
Watchdog while a cell runs (every 15 s):
  - heartbeat older than max(600 s, 5 x median episode time) -> docker kill the cell container;
  - server ping (real ZMQ timeout) fails 3 times in a row -> docker restart groot-server, kill the cell;
  - free disk < 30 GB -> pause after this cell;
  - nvidia-smi every 60 s -> logs/queue/gpu_minutely.csv.
3 consecutive failed cells -> the queue pauses itself (queue/PAUSE) so a systematic bug can't burn the week.
GPU lock: flock on /run/lock/gtc-gpu.lock (every GPU job takes it).
PAUSE: finish the current cell, then wait. STOP: sweep_eval leaves before its next episode; the queue exits.
"""
import csv
import datetime as dt
import fcntl
import json
import os
import shutil
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
_ROOT = Path(os.environ.get("GTC_Q_ROOT", GTC))                # test root (T10a); default = the repo
Q = _ROOT / "queue"
LOGS = _ROOT / "logs" / "queue"
RES = _ROOT / "results" / "sim"
LOCK = Path(os.environ.get("GTC_Q_LOCK", "/run/lock/gtc-gpu.lock"))
PY = str(GTC / ".venv" / "bin" / "python")
STARTUP_S = float(os.environ.get("GTC_Q_STARTUP_S", 150))      # env overrides only for the mock tests (T10a)
DEFAULT_EP_S = float(os.environ.get("GTC_Q_DEFAULT_EP_S", 45.0))
MIN_STALE_S = float(os.environ.get("GTC_Q_MIN_STALE_S", 600))
POLL_S = float(os.environ.get("GTC_Q_POLL_S", 15))
MAX_ATTEMPTS, MAX_CONSEC_FAIL, MIN_FREE_GB = 3, 3, 30


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(msg):
    LOGS.mkdir(parents=True, exist_ok=True)
    line = f"{utc()} {msg}"
    print(line, flush=True)
    with open(LOGS / "queue.log", "a") as f:
        f.write(line + "\n")


def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, ""


def read_cells(path):
    with open(path) as f:
        rows = [r for r in csv.DictReader(f) if r.get("cell_id") and not r["cell_id"].startswith("#")]
    for i, r in enumerate(rows):
        r["_order"] = i
        r["n_episodes"] = int(r["n_episodes"])
        r["seed_base"] = int(r["seed_base"])
        r["priority"] = int(r.get("priority") or 0)
    return sorted(rows, key=lambda r: (r["priority"], r["_order"]))


def done_rows(cell):
    p = RES / f"{cell}.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in open(p):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue  # a torn last line from a kill
        if r.get("status") == "ok" and "episode" in r:
            rows.append(r)
    return rows


def next_episode(cell):
    eps = {r["episode"] for r in done_rows(cell)}
    k = 0
    while k in eps:
        k += 1
    return k


def episode_times(cell):
    return [r["wall_s"] for r in done_rows(cell)]


def ping():
    rc, _ = sh(f"{PY} -I {GTC}/sim/server_ping.py --timeout 10", timeout=30)
    return rc == 0


def ensure_server(checkpoint):
    rc, cmd = sh("docker inspect groot-server --format '{{json .Config.Cmd}}'")
    running = rc == 0 and sh("docker inspect groot-server --format '{{.State.Running}}'")[1] == "true"
    if running and checkpoint and checkpoint not in cmd:
        log(f"server serves another checkpoint; restarting for {checkpoint}")
        sh("docker rm -f groot-server")
        running = False
    if not running:
        sh("docker rm -f groot-server")
        rc, out = sh(f"{GTC}/sim/run_server.sh {checkpoint}" if checkpoint else f"{GTC}/sim/run_server.sh", timeout=120)
        log(f"started groot-server rc={rc} {out[-200:]}")
    t0 = time.time()
    while time.time() - t0 < 600:
        if ping():
            return True
        time.sleep(5)
    return False


def gpu_minutely():
    p = LOGS / "gpu_minutely.csv"
    if not p.exists():
        p.write_text("utc,mem_used_mib,mem_total_mib,util_pct,temp_c\n")
    _, out = sh("nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits")
    with open(p, "a") as f:
        f.write(f"{utc()},{out.replace(' ', '')}\n")
    return out


def free_gb():
    return shutil.disk_usage(GTC).free / 1e9


def write_status(cells, state, extra=None):
    Q.mkdir(exist_ok=True)
    per = []
    total_n = total_done = 0
    times = []
    for c in cells:
        d = done_rows(c["cell_id"])
        times += [r["wall_s"] for r in d]
        per.append({"cell": c["cell_id"], "done": len(d), "n": c["n_episodes"], "successes": sum(r["success"] for r in d),
                    "state": state.get("cells", {}).get(c["cell_id"], {}).get("state", "pending")})
        total_n += c["n_episodes"]
        total_done += min(len(d), c["n_episodes"])
    med = st.median(times) if times else DEFAULT_EP_S
    remaining = sum(max(0, p["n"] - p["done"]) for p in per)
    s = {"utc": utc(), "episodes_done": total_done, "episodes_total": total_n,
         "eta_h": round((remaining * med + STARTUP_S * sum(1 for p in per if p["done"] < p["n"])) / 3600, 2),
         "median_episode_s": round(med, 1), "paused": (Q / "PAUSE").exists(), "stopped": (Q / "STOP").exists(),
         "free_disk_gb": round(free_gb(), 1), "cells": per, **(extra or {}), "state": state}
    tmp = Q / "status.json.tmp"
    tmp.write_text(json.dumps(s, indent=1))
    os.replace(tmp, Q / "status.json")
    md = [f"# queue status {s['utc']}", f"{total_done}/{total_n} episodes, ETA {s['eta_h']} h, median {s['median_episode_s']} s/ep, "
          f"paused={s['paused']} stopped={s['stopped']}, disk free {s['free_disk_gb']} GB", "",
          "| cell | done/n | successes | state |", "|---|---|---|---|"]
    md += [f"| {p['cell']} | {p['done']}/{p['n']} | {p['successes']} | {p['state']} |" for p in per]
    (Q / "status.md").write_text("\n".join(md) + "\n")


def run_cell(c, attempt, state, runner):
    cell, n = c["cell_id"], c["n_episodes"]
    k = next_episode(cell)
    if k >= n:
        return "done"
    times = episode_times(cell)
    p95 = sorted(times)[int(0.95 * (len(times) - 1))] if len(times) >= 5 else DEFAULT_EP_S
    med = st.median(times) if times else DEFAULT_EP_S
    tmo = int(STARTUP_S + (n - k) * p95 * 1.5)
    stale = max(MIN_STALE_S, 5 * med)
    name = f"gtc-cell-{cell}"[:60]
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    clog = LOGS / f"{cell}_a{attempt}_{ts}.log"
    if runner:
        cmd = [runner, cell, str(k), str(n)]
    else:
        ov = c["overrides_json"] or "{}"
        cmd = ["timeout", "-k", "60", str(tmo), str(GTC / "sim" / "run_sim.sh"), name,
               "python", "/workspace/gtc/sim/sweep_eval.py", "--headless", "--cell_id", cell, "--overrides", ov,
               "--n_episodes", str(n), "--start_episode", str(k), "--seed_base", str(c["seed_base"]),
               "--task", c.get("task") or "Lerobot-So101-Teleop-Vials-To-Rack-Eval", "--checkpoint", c.get("checkpoint", "")]
        if int(c.get("seed_mod") or 0):
            cmd += ["--seed_mod", str(int(c["seed_mod"]))]
        if str(c.get("as_shipped") or "").strip() in ("1", "true", "True"):
            cmd += ["--as_shipped"]
    env = dict(os.environ, GTC_GIT=sh(f"git -C {GTC} rev-parse HEAD")[1],
               GTC_IMAGE=sh("docker image inspect --format '{{.Id}}' teleop-docker")[1])
    log(f"cell {cell} attempt {attempt}: episodes {k}..{n - 1}, timeout {tmo}s, stale {stale:.0f}s -> {clog.name}")
    sh(f"docker rm -f {name}")
    hb = RES / f"{cell}.heartbeat"
    t0 = time.time()
    with open(clog, "w") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        last_ping, ping_fail, last_gpu, last_ep_seen = 0.0, 0, 0.0, time.time()
        reason = None
        while proc.poll() is None:
            time.sleep(POLL_S)
            now = time.time()
            age = now - (hb.stat().st_mtime if hb.exists() else t0)
            if age > stale and now - t0 > STARTUP_S:
                reason = f"heartbeat stale {age:.0f}s"
            if not runner and now - last_ping > 60:
                last_ping = now
                ping_fail = 0 if ping() else ping_fail + 1
                if ping_fail >= 3:
                    reason = "server ping failed 3 times"
                    log("server ping failed 3 times: docker restart groot-server")
                    sh("docker restart groot-server", timeout=120)
                    ping_fail = 0
            if now - last_gpu > 60:
                last_gpu = now
                gpu_minutely()
            if free_gb() < MIN_FREE_GB and not (Q / "PAUSE").exists():
                (Q / "PAUSE").write_text(f"disk free {free_gb():.1f} GB < {MIN_FREE_GB} at {utc()}\n")
                log("disk guard: PAUSE written")
            write_status(state["_cells"], state, {"running": cell, "attempt": attempt, "heartbeat_age_s": round(age)})
            if reason:
                log(f"watchdog: {reason}: docker kill {name} + kill the process group")
                sh(f"docker kill {name}")
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, 15)
                break
        try:
            rc = proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, 9)
            rc = proc.wait()
    # T08 bookkeeping: time from the last episode row to the process end
    rows = done_rows(cell)
    end = time.time()
    last_row_t = max((dt.datetime.fromisoformat(r["utc"]).timestamp() for r in rows), default=None)
    exit_lag = round(end - last_row_t, 1) if last_row_t else None
    got = next_episode(cell)
    # the course's python.sh turns every non-zero exit into 1, so read sweep_eval's own "[EXIT] code N" line
    code = None
    for line in open(clog, errors="replace"):
        if line.startswith("[EXIT] code "):
            try:
                code = int(line.split()[2])
            except (IndexError, ValueError):
                pass
    log(f"cell {cell} attempt {attempt} ended rc={rc} exit_code={code} after {end - t0:.0f}s; episodes now {got}/{n}; "
        f"exit lag after last row {exit_lag}s{'; ' + reason if reason else ''}")
    state["cells"].setdefault(cell, {}).setdefault("attempts", []).append(
        {"attempt": attempt, "rc": rc, "exit_code": code, "seconds": round(end - t0), "from": k, "to": got,
         "exit_lag_s": exit_lag, "watchdog": reason, "log": clog.name})
    if code == 10 or (Q / "STOP").exists():
        return "stopped"
    return "done" if got >= n else "failed"


def cmd_run(cells_path, runner=None):
    Q.mkdir(exist_ok=True)
    state_p = Q / "state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {"cells": {}}
    log(f"queue start: {cells_path} (pid {os.getpid()})")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lockf = open(LOCK, "a+")
    consec_fail = 0
    while True:
        if (Q / "STOP").exists():
            log("STOP file present: queue exits")
            break
        if (Q / "PAUSE").exists():
            write_status(read_cells(cells_path), state, {"running": None})
            time.sleep(30)
            continue
        cells = read_cells(cells_path)
        state["_cells"] = cells
        todo = [c for c in cells if next_episode(c["cell_id"]) < c["n_episodes"]
                and state["cells"].get(c["cell_id"], {}).get("state") != "failed"]
        if not todo:
            write_status(cells, state, {"running": None})
            log("queue empty: all cells done or failed")
            break
        c = todo[0]
        cs = state["cells"].setdefault(c["cell_id"], {})
        if not runner and not ensure_server(c.get("checkpoint", "")):
            log("server does not come up: PAUSE")
            (Q / "PAUSE").write_text(f"server down at {utc()}\n")
            continue
        fcntl.flock(lockf, fcntl.LOCK_EX)          # wait for any other GPU job
        try:
            res = "failed"
            for attempt in range(1, MAX_ATTEMPTS + 1):
                cs["state"] = "running"
                res = run_cell(c, attempt, state, runner)
                if res in ("done", "stopped"):
                    break
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)
        cs["state"] = res
        state.pop("_cells", None)
        state_p.write_text(json.dumps(state, indent=1))
        if res == "stopped":
            log("cell left on STOP: queue exits")
            break
        consec_fail = consec_fail + 1 if res == "failed" else 0
        if consec_fail >= MAX_CONSEC_FAIL:
            (Q / "PAUSE").write_text(f"{consec_fail} consecutive cell failures at {utc()}\n")
            log(f"{consec_fail} consecutive cell failures: queue PAUSED")
    state.pop("_cells", None)
    state_p.write_text(json.dumps(state, indent=1))
    write_status(read_cells(cells_path), state, {"running": None})


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("run", "status", "pause", "resume", "stop"):
        print(__doc__)
        return 2
    Q.mkdir(exist_ok=True)
    if a[0] == "pause":
        (Q / "PAUSE").write_text(f"manual pause at {utc()}\n")
    elif a[0] == "resume":
        for f in ("PAUSE", "STOP"):
            (Q / f).unlink(missing_ok=True)
    elif a[0] == "stop":
        (Q / "STOP").write_text(f"manual stop at {utc()}\n")
    elif a[0] == "status":
        p = Q / "status.md"
        print(p.read_text() if p.exists() else "no status yet")
    else:
        cells = a[a.index("--cells") + 1] if "--cells" in a else str(GTC / "config" / "cells.csv")
        runner = a[a.index("--runner") + 1] if "--runner" in a else None
        cmd_run(cells, runner)
    return 0


if __name__ == "__main__":
    sys.exit(main())
