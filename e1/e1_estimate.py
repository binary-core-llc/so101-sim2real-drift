#!/usr/bin/env python3
"""E1 (D_software C13; v2 item 2): Cosmos-Reason2-2B, local, two labelled images -> the Appendix C estimate.

    .venv-e1/bin/python -I e1/e1_estimate.py --variant v1|v2 --ref A.png --cases cases.json --out-dir DIR
cases.json: [{"photo_id", "photo"}]; A = the sim reference (rendered with the C920's measured focal at the sim nominal),
B = each case's photo. Model as registered: revision 9ce19a19, BF16, sdpa, the checkpoint's generation config (sampling)
seeded with 0 per case, max_new_tokens 4096 (model card), the card's <think>/<answer> format.
Variants (one is chosen on simulated scenes only, before E1 sees any real photo):
  v1: metric deltas (degrees and metres);
  v2: per axis a direction (+, -, none) and a size bin (small / medium / large), turned into numbers at the bin centres.
  v1b, v2b (round 2, Nov 8): the same, with typed placeholders instead of an example answer (round 1 answered the
  example's zeros / "none" almost always) and one sentence on what to compare.
Parser (D C13): the last <answer>...</answer>, else the first balanced {...}; code fences stripped; json.loads with no
repair beyond trailing commas; types and units checked. status: ok | parse_fail | no_estimate.
Writes one Appendix C JSON per case (<out-dir>/<photo_id>_<variant>.json) with the raw text.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
MODEL = Path.home() / "sim2real" / "models" / "nvidia" / "Cosmos-Reason2-2B"
REVISION = "9ce19a195e423419c349abfc86fd07178b230561"
FORMAT = ("Answer the question in the following format: <think>\nyour reasoning\n</think>\n\n<answer>\nyour answer\n"
          "</answer>.")
MAX_NEW = 4096
CAM_KEYS = ["tilt_down_deg", "pan_deg", "roll_deg", "lateral_m", "depth_m", "height_m"]
RACK_KEYS = ["x_m", "y_m", "yaw_deg"]

SCENE = (
    "Image A is a simulated reference view of a robot workcell, taken by the front camera at its nominal pose. "
    "Image B is the current photo of the same workcell from the same camera. The workcell is a white box. Inside it "
    "are a black mat, a yellow rack with four holes, three tubes lying on the mat, and an orange robot arm on the "
    "right. The camera hangs on the left wall of the box (the camera wall) and looks down across the mat toward the "
    "right wall; the back wall is at the top left of the image and the robot stands at the open front. Between A and "
    "B, either the camera has moved (the rack is then at its nominal place) or the rack has moved (the camera is then "
    "at its nominal pose), or nothing has moved. The tubes may lie differently; ignore them. Treat the scene in A "
    "as the true nominal scene.\n\n"
    "Sign definitions:\n"
    "- camera tilt_down_deg > 0: the camera is tilted further down than in A;\n"
    "- camera pan_deg > 0: the camera is turned toward the back wall (away from the robot);\n"
    "- camera roll_deg > 0: the camera is rolled clockwise as seen from behind the camera;\n"
    "- camera lateral_m > 0: the camera moved toward the camera wall; depth_m > 0: toward the back wall; "
    "height_m > 0: up;\n"
    "- rack x_m > 0: the rack moved toward the back wall; y_m > 0: toward the camera wall; yaw_deg > 0: the rack "
    "turned counter-clockwise as seen from above.\n")
ASK_V1 = (
    "Estimate the change from A to B. \"moved\" is one of \"camera\", \"rack\" or \"none\". Replace the zeros below "
    "with your estimates in degrees and metres (keep 0 where nothing changed) and keep every key. Put only this JSON "
    "in the answer:\n"
    '{"moved": "none", "camera_delta": {"tilt_down_deg": 0, "pan_deg": 0, "roll_deg": 0, "lateral_m": 0, "depth_m": 0, '
    '"height_m": 0}, "rack_delta": {"x_m": 0, "y_m": 0, "yaw_deg": 0}}')
ASK_V2 = (
    "Estimate the change from A to B. \"moved\" is one of \"camera\", \"rack\" or \"none\". For every quantity give "
    "a direction, \"+\", \"-\" or \"none\", and a size: \"small\" (angles 0.5-2 deg, distances 3-10 mm), \"medium\" "
    "(angles 2-5 deg, distances 10-25 mm) or \"large\" (angles over 5 deg, distances over 25 mm); [\"none\", \"none\"] "
    "means no change. Replace the entries below with your estimates and keep every key. Put only this JSON in the "
    "answer:\n"
    '{"moved": "none", "camera": {"tilt_down": ["none", "none"], "pan": ["none", "none"], "roll": ["none", "none"], '
    '"lateral": ["none", "none"], "depth": ["none", "none"], "height": ["none", "none"]}, '
    '"rack": {"x": ["none", "none"], "y": ["none", "none"], "yaw": ["none", "none"]}}')
LOOK = ("Compare where the yellow rack, the edges of the black mat and the box's walls and corners appear in A and in B. ")
ASK_V1B = (
    "Estimate the change from A to B. " + LOOK + "Answer with this JSON, writing a value in place of each <...>: "
    "<moved> is \"camera\", \"rack\" or \"none\"; every other <...> is a number, distances in metres (0.02 = 2 cm), "
    "angles in degrees, 0 where nothing changed:\n"
    '{"moved": <moved>, "camera_delta": {"tilt_down_deg": <...>, "pan_deg": <...>, "roll_deg": <...>, "lateral_m": <...>, '
    '"depth_m": <...>, "height_m": <...>}, "rack_delta": {"x_m": <...>, "y_m": <...>, "yaw_deg": <...>}}')
ASK_V2B = (
    "Estimate the change from A to B. " + LOOK + "Answer with this JSON, writing a value in place of each <...>: "
    "<moved> is \"camera\", \"rack\" or \"none\"; each <dir> is \"+\", \"-\" or \"none\"; each <size> is \"small\" "
    "(angles 0.5-2 deg, distances 3-10 mm), \"medium\" (angles 2-5 deg, distances 10-25 mm), \"large\" (angles over "
    "5 deg, distances over 25 mm) or \"none\" (no change):\n"
    '{"moved": <moved>, "camera": {"tilt_down": [<dir>, <size>], "pan": [<dir>, <size>], "roll": [<dir>, <size>], '
    '"lateral": [<dir>, <size>], "depth": [<dir>, <size>], "height": [<dir>, <size>]}, '
    '"rack": {"x": [<dir>, <size>], "y": [<dir>, <size>], "yaw": [<dir>, <size>]}}')
BIN_DEG = {"none": 0.0, "small": 1.25, "medium": 3.5, "large": 7.0}
BIN_M = {"none": 0.0, "small": 0.0065, "medium": 0.0175, "large": 0.035}


def parse(text):
    """D C13: the last <answer>...</answer>, else the first balanced {...} (searched after the last </think> when there
    is one, so braces quoted in the reasoning are not taken); fences stripped; trailing commas only."""
    m = re.findall(r"<answer>(.*?)</answer>", text, flags=re.S)
    body = m[-1] if m else None
    if body is None:
        text = text.rsplit("</think>", 1)[-1]
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        for i in range(start, len(text)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                body = text[start:i + 1]
                break
        if body is None:
            return None
    body = re.sub(r"```(?:json)?", "", body).strip()
    s = body.find("{")
    e = body.rfind("}")
    if s < 0 or e < 0:
        return None
    body = re.sub(r",\s*([}\]])", r"\1", body[s:e + 1])
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def to_estimate(variant, j):
    """(camera_delta, rack_delta, status) in Appendix C units from a parsed answer."""
    num = lambda v: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    if variant in ("v1", "v1b"):
        cd, rd = j.get("camera_delta", {}), j.get("rack_delta", {})
        if not isinstance(cd, dict) or not isinstance(rd, dict):
            return None, None, "no_estimate"
        filled = [k for k in CAM_KEYS if k not in cd] + [k for k in RACK_KEYS if k not in rd]
        cam = {k: num(cd.get(k, 0)) for k in CAM_KEYS}                  # a key left out = no change (0), recorded
        rack = {k: num(rd.get(k, 0)) for k in RACK_KEYS}
        if any(v is None for v in list(cam.values()) + list(rack.values())):
            return None, None, "no_estimate"
        to_estimate.filled = filled
        return cam, rack, "ok"
    c, r = j.get("camera", {}), j.get("rack", {})
    if not isinstance(c, dict) or not isinstance(r, dict):
        return None, None, "no_estimate"
    filled = [f"camera.{k}" for k in ("tilt_down", "pan", "roll", "lateral", "depth", "height") if k not in c] + \
        [f"rack.{k}" for k in ("x", "y", "yaw") if k not in r]
    c = {k: c.get(k, ["none", "none"]) for k in ("tilt_down", "pan", "roll", "lateral", "depth", "height")}
    r = {k: r.get(k, ["none", "none"]) for k in ("x", "y", "yaw")}
    to_estimate.filled = filled

    def val(pair, bins):
        if not (isinstance(pair, list) and len(pair) == 2 and pair[0] in ("+", "-", "none") and pair[1] in bins):
            return None
        return 0.0 if pair[0] == "none" else (1 if pair[0] == "+" else -1) * bins[pair[1]]
    cam = {"tilt_down_deg": val(c.get("tilt_down"), BIN_DEG), "pan_deg": val(c.get("pan"), BIN_DEG),
           "roll_deg": val(c.get("roll"), BIN_DEG), "lateral_m": val(c.get("lateral"), BIN_M),
           "depth_m": val(c.get("depth"), BIN_M), "height_m": val(c.get("height"), BIN_M)}
    rack = {"x_m": val(r.get("x"), BIN_M), "y_m": val(r.get("y"), BIN_M), "yaw_deg": val(r.get("yaw"), BIN_DEG)}
    if any(v is None for v in list(cam.values()) + list(rack.values())):
        return None, None, "no_estimate"
    return cam, rack, "ok"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["v1", "v2", "v1b", "v2b"], required=True)
    ap.add_argument("--ref", required=True, help="image A: the sim reference with the C920's focal")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    import torch
    import transformers
    from PIL import Image
    prompt = SCENE + "\n" + {"v1": ASK_V1, "v2": ASK_V2, "v1b": ASK_V1B, "v2b": ASK_V2B}[a.variant]
    pid = hashlib.sha256(prompt.encode()).hexdigest()[:12]
    t0 = time.time()
    model = transformers.Qwen3VLForConditionalGeneration.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda",
                                                                         attn_implementation="sdpa")
    proc = transformers.AutoProcessor.from_pretrained(MODEL)
    load_s = time.time() - t0
    A = Image.open(a.ref).convert("RGB")
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for case in json.loads(Path(a.cases).read_text()):
        B = Image.open(case["photo"]).convert("RGB")
        content = [{"type": "text", "text": "Image A:"}, {"type": "image", "image": A},
                   {"type": "text", "text": "Image B:"}, {"type": "image", "image": B}, {"type": "text", "text": prompt}]
        msgs = [{"role": "system", "content": [{"type": "text", "text": FORMAT}]}, {"role": "user", "content": content}]
        inputs = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                                          return_tensors="pt").to(model.device)
        torch.manual_seed(0)
        t = time.time()
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=MAX_NEW)
        secs = time.time() - t
        text = proc.decode(gen[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        j = parse(text)
        to_estimate.filled = []
        cam, rack, status = (None, None, "parse_fail") if not isinstance(j, dict) else to_estimate(a.variant, j)
        rec = {"photo_id": case["photo_id"], "method": "E1", "model_id": f"nvidia/Cosmos-Reason2-2B@{REVISION[:8]}",
               "prompt_id": f"{a.variant}-{pid}", "version_hash": code_hash, "seconds": round(secs, 2), "status": status,
               "camera_delta": cam, "rack_delta": rack, "filled_as_no_change": to_estimate.filled, "moved": (j or {}).get("moved") if isinstance(j, dict) else None,
               "intrinsics_ref": hashlib.sha256((GTC / "config" / "c920_intrinsics.json").read_bytes()).hexdigest(),
               "raw_path": case["photo"], "ref_path": a.ref, "output_tokens": int(gen.shape[1] - inputs["input_ids"].shape[1]),
               "raw_text": text, "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "load_s": round(load_s, 1)}
        (out / f"{case['photo_id']}_{a.variant}.json").write_text(json.dumps(rec, indent=1))
        print(f"{case['photo_id']:24s} {a.variant} {status:11s} moved={rec['moved']} {secs:5.1f} s {rec['output_tokens']} tok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
