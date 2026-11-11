#!/usr/bin/env python3
"""Record every pinned version into config/versions.json.

Run on the host:  python3 -I tools/capture_versions.py [--hash-weights]
Stdlib only. Missing pieces (an image not built yet, a checkpoint not downloaded)
are written as null with a note, never guessed.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

HOME = Path.home()
GTC = Path(__file__).resolve().parents[1]
COURSE = GTC.parent / "Sim-to-Real-SO-101-Workshop"
MODELS = HOME / "sim2real" / "models"
CKPT_REPO = "aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left"
CKPT_SUB = "checkpoint-10000"


def sh(cmd, timeout=120):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def image_info(tag):
    img_id = sh(f"docker image inspect --format '{{{{.Id}}}}' {tag}")
    if not img_id:
        return {"tag": tag, "id": None, "note": "image not present"}
    created = sh(f"docker image inspect --format '{{{{.Created}}}}' {tag}")
    digests = sh(f"docker image inspect --format '{{{{json .RepoDigests}}}}' {tag}")
    return {"tag": tag, "id": img_id, "created": created,
            "repo_digests": json.loads(digests) if digests else None}


def in_image(tag, cmd):
    # --entrypoint sh so the course entrypoint (pip install -e) does not run
    return sh(f"docker run --rm --entrypoint sh {tag} -c '{cmd}'", timeout=300)


def sha256(path, bufsize=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def checkpoint_info(hash_weights):
    root = MODELS / CKPT_REPO
    info = {"repo": CKPT_REPO, "subfolder": CKPT_SUB, "local_dir": str(root / CKPT_SUB)}
    meta = GTC / "config" / "checkpoint_source.json"
    if meta.exists():
        info.update(json.loads(meta.read_text()))
    d = root / CKPT_SUB
    if not d.exists():
        info["note"] = "not downloaded"
        return info
    files = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(root))
            e = {"bytes": p.stat().st_size}
            if hash_weights or p.stat().st_size < 50_000_000:
                e["sha256"] = sha256(p)
            files[rel] = e
    info["files"] = files
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash-weights", action="store_true", help="sha256 the multi-GB safetensors too")
    args = ap.parse_args()

    smi = sh("nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader")
    cuda = sh("nvidia-smi | grep -o 'CUDA Version: [0-9.]*'")
    gpu = [s.strip() for s in smi.split(",")] if smi else [None] * 4

    dockerfile = (COURSE / "docker/real/Dockerfile.ada").read_text()
    groot_ref = re.search(r"ARG GROOT_REF=(\w+)", dockerfile).group(1)

    v = {
        "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "host": {
            "gpu": gpu[0], "vram_total": gpu[2], "compute_cap": gpu[3],
            "driver": gpu[1], "cuda_driver_api": cuda.split(":")[-1].strip() if cuda else None,
            "kernel": sh("uname -r"),
            "os": sh("lsb_release -ds"),
            "docker": sh("docker version --format '{{.Server.Version}}'"),
            "nvidia_container_toolkit": sh("nvidia-ctk --version | head -1"),
            "git": sh("git --version"),
            "git_lfs": sh("git lfs version"),
        },
        "course": {
            "repo": "https://github.com/isaac-sim/Sim-to-Real-SO-101-Workshop",
            "commit": sh(f"git -C {COURSE} rev-parse HEAD"),
            "dirty": bool(sh(f"git -C {COURSE} status --porcelain")),
            "lfs_files": len((sh(f"git -C {COURSE} lfs ls-files -n") or "").splitlines()),
        },
        "groot": {"ref_in_dockerfile_ada": groot_ref},
        "images": {
            "teleop-docker": image_info("teleop-docker"),
            "real-robot": image_info("real-robot"),
            "base_isaac_lab": image_info("nvcr.io/nvidia/isaac-lab:2.3.2"),
            "base_cuda": image_info("nvidia/cuda:12.8.0-devel-ubuntu24.04"),
        },
        "checkpoint": checkpoint_info(args.hash_weights),
        "gtc_repo": {
            "commit": sh(f"git -C {GTC} rev-parse HEAD"),
            "dirty": bool(sh(f"git -C {GTC} status --porcelain")),
        },
    }

    # BuildKit pulls base images by digest without tagging them; read the digests from our build logs
    bases = {}
    for log in sorted((GTC / "logs" / "build").glob("*.log")):
        for m in re.finditer(r"FROM (\S+?)@(sha256:[0-9a-f]{64})", log.read_text(errors="replace")):
            bases[m.group(1)] = {"digest": m.group(2), "from_log": log.name}
    v["images"]["base_digests_from_build_logs"] = bases

    if v["images"]["real-robot"]["id"]:
        v["groot"]["ref_in_image"] = in_image("real-robot", "git -C /Isaac-GR00T rev-parse HEAD")
        v["groot"]["python_torch_flashattn"] = in_image(
            "real-robot",
            "/Isaac-GR00T/.venv/bin/python -c \"import sys,torch;import flash_attn as f;"
            "print(sys.version.split()[0],torch.__version__,torch.version.cuda,f.__version__)\"")
    if v["images"]["teleop-docker"]["id"]:
        v["sim_stack"] = {
            "isaac_sim_version": in_image("teleop-docker", "cat /workspace/isaaclab/_isaac_sim/VERSION"),
            "isaac_lab_version": in_image("teleop-docker", "cat /workspace/isaaclab/VERSION"),
            "lerobot_commit": in_image("teleop-docker", "git -C /workspace/lerobot rev-parse HEAD"),
        }

    out = GTC / "config" / "versions.json"
    if out.exists():  # keep the sections recorded by hand (prereg repo, sweep provenance, E1, ...); captured keys win
        v = {**json.loads(out.read_text()), **v}
    out.write_text(json.dumps(v, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
