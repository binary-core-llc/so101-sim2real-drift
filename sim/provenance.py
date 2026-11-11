#!/usr/bin/env python3
"""Host-side provenance for a sim run, printed as KEY=VALUE lines (read by sim/run_sim.sh).

    python3 -I sim/provenance.py
GTC_GIT           HEAD of this repo
GTC_DIRTY         1 if any tracked or untracked (not ignored) file under sim/, config/, tools/ or docker/
                  differs from HEAD, else 0; results, logs, queue and media are not code and do not count
GTC_IMAGE         image ID of teleop-docker:latest (the sim image)
GTC_COURSE_GIT    HEAD of the course repo (../Sim-to-Real-SO-101-Workshop)
GTC_SERVER_IMAGE  image ID the running groot-server container was created from
GTC_MODEL_REV     Hugging Face revision of the checkpoint groot-server serves (--model-path), from the
                  download metadata `hf download` writes under <repo>/.cache/huggingface/download/;
                  "mixed" if its files disagree
A value is empty when it cannot be read (e.g. no server running). Stdlib only.
"""
import json
import os
import subprocess
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
COURSE = GTC.parent / "Sim-to-Real-SO-101-Workshop"
MODELS = Path(os.environ.get("MODELS_DIR", Path.home() / "sim2real" / "models"))
MODELS_CTR = "/workspace/models"   # sim/run_server.sh mounts MODELS there
CODE_DIRS = ("sim", "config", "tools", "docker")


def sh(*cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def model_rev(cmd_json):
    try:
        cmd = json.loads(cmd_json)
        path = cmd[cmd.index("--model-path") + 1]
    except (ValueError, IndexError, TypeError):
        return ""
    if not path.startswith(MODELS_CTR + "/"):
        return ""
    parts = Path(path[len(MODELS_CTR) + 1:]).parts            # org / repo / [subfolder ...]
    meta = MODELS.joinpath(*parts[:2], ".cache", "huggingface", "download", *parts[2:])
    revs = {f.read_text().splitlines()[0].strip() for f in meta.rglob("*.metadata")} if meta.is_dir() else set()
    return revs.pop() if len(revs) == 1 else ("mixed" if revs else "")


def main():
    porcelain = sh("git", "-C", str(GTC), "status", "--porcelain", "--untracked-files=all", "--", *CODE_DIRS)
    running = sh("docker", "inspect", "groot-server", "--format", "{{.State.Running}}") == "true"
    out = {
        "GTC_GIT": sh("git", "-C", str(GTC), "rev-parse", "HEAD"),
        "GTC_DIRTY": "1" if porcelain else "0",
        "GTC_IMAGE": sh("docker", "image", "inspect", "--format", "{{.Id}}", "teleop-docker:latest"),
        "GTC_COURSE_GIT": sh("git", "-C", str(COURSE), "rev-parse", "HEAD"),
        "GTC_SERVER_IMAGE": sh("docker", "inspect", "groot-server", "--format", "{{.Image}}") if running else "",
        "GTC_MODEL_REV": model_rev(sh("docker", "inspect", "groot-server", "--format", "{{json .Config.Cmd}}")) if running else "",
    }
    for k, v in out.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
